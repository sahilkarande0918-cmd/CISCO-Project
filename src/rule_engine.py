"""
Rule-based fault checker.

Parses collected Packet Tracer evidence and diffs it against the golden
baseline (topology/golden.json). Deterministic, no AI. Emits a structured
diagnosis so it can be compared side-by-side with the AI module.

Run all cases:   python src/rule_engine.py
One file:        python src/rule_engine.py cases/case01_evidence.txt
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = json.load(open(os.path.join(ROOT, "topology", "golden.json")))

FAULT_TYPES = ["duplicate_ip", "wrong_subnet_mask", "gateway_mismatch",
               "interface_down", "missing_vlan_assignment", "missing_route"]


def mask_to_prefix(mask):
    return sum(bin(int(o)).count("1") for o in mask.split("."))


# --- parsing --------------------------------------------------------------
def split_devices(text):
    """Return {device_name: section_text}."""
    parts = re.split(r"=====\s*DEVICE:\s*(\S+)\s*=====", text)
    devices = {}
    for i in range(1, len(parts), 2):
        devices[parts[i]] = parts[i + 1]
    return devices


def parse_router(block):
    ifaces = {}
    # status + ip from 'show ip interface brief'
    for m in re.finditer(r"^(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+\w+\s+\w+\s+(.*?)\s+(up|down)\s*$",
                         block, re.M):
        ifaces[m.group(1)] = {"ip": m.group(2), "status": m.group(3).strip()}
    # mask from running-config interface blocks
    for m in re.finditer(r"interface (\S+)\n(?:.*\n)*? ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)",
                         block):
        if m.group(1) in ifaces:
            ifaces[m.group(1)]["mask"] = m.group(3)
    # routes (static + connected) as network/prefix
    routes = set()
    for m in re.finditer(r"^[SC]\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", block, re.M):
        routes.add(f"{m.group(1)}/{m.group(2)}")
    return {"interfaces": ifaces, "routes": routes}


def parse_switch(block):
    vlan_ports = {}       # port -> vlan
    for m in re.finditer(r"^(\d+)[ \t]+\S+[ \t]+active[ \t]*(.*)$", block, re.M):
        vlan = int(m.group(1))
        for port in re.findall(r"(?:Fast|Gigabit)Ethernet\S+", m.group(2)):
            vlan_ports[port.rstrip(",")] = vlan
    iface_status = {}     # port -> status word
    for m in re.finditer(r"^((?:Fast|Gigabit)Ethernet\S+)\s+.*?\b(connected|disabled|notconnect|err-disabled)\b",
                         block, re.M):
        iface_status[m.group(1)] = m.group(2)
    return {"vlan_ports": vlan_ports, "iface_status": iface_status}


def parse_pc(block):
    def grab(label):
        m = re.search(label + r".*?:\s*(\S+)", block)
        return m.group(1) if m else None
    return {"ip": grab("IPv4 Address"), "mask": grab("Subnet Mask"),
            "gateway": grab("Default Gateway")}


# --- checks (each appends findings) ---------------------------------------
def diagnose(text):
    devices = split_devices(text)
    findings = []

    routers, switches, pcs = {}, {}, {}
    for name, block in devices.items():
        if name in GOLDEN["routers"]:
            routers[name] = parse_router(block)
        elif name in GOLDEN["switches"]:
            switches[name] = parse_switch(block)
        elif name in GOLDEN["pcs"]:
            pcs[name] = parse_pc(block)

    # 1. duplicate IP across every host IP we can see
    ip_owners = {}
    for name, r in routers.items():
        for intf, c in r["interfaces"].items():
            ip_owners.setdefault(c["ip"], []).append(f"{name} {intf}")
    for name, p in pcs.items():
        if p["ip"]:
            ip_owners.setdefault(p["ip"], []).append(name)
    for ip, owners in ip_owners.items():
        if len(owners) > 1:
            findings.append(dict(fault_type="duplicate_ip", device=", ".join(owners),
                                 detail=f"IP {ip} is configured on more than one host: {', '.join(owners)}"))

    # 2/3. PC subnet mask + gateway vs golden
    for name, p in pcs.items():
        g = GOLDEN["pcs"].get(name)
        if not g:
            continue
        if p["mask"] and p["mask"] != g["mask"]:
            findings.append(dict(fault_type="wrong_subnet_mask", device=name,
                                 detail=f"{name} mask {p['mask']} != expected {g['mask']}"))
        if p["gateway"] and p["gateway"] != g["gateway"]:
            findings.append(dict(fault_type="gateway_mismatch", device=name,
                                 detail=f"{name} gateway {p['gateway']} != expected {g['gateway']}"))

    # 2b. router interface mask vs golden
    for name, r in routers.items():
        for intf, c in r["interfaces"].items():
            g = GOLDEN["routers"][name]["interfaces"].get(intf)
            if g and c.get("mask") and c["mask"] != g["mask"]:
                findings.append(dict(fault_type="wrong_subnet_mask", device=f"{name} {intf}",
                                     detail=f"{intf} mask {c['mask']} != expected {g['mask']}"))

    # 4. interfaces administratively down
    for name, r in routers.items():
        for intf, c in r["interfaces"].items():
            if "administratively down" in c["status"] or "down" == c["status"]:
                findings.append(dict(fault_type="interface_down", device=f"{name} {intf}",
                                     detail=f"{intf} is {c['status']}"))
    for name, s in switches.items():
        for port, st in s["iface_status"].items():
            if st in ("disabled", "err-disabled"):
                findings.append(dict(fault_type="interface_down", device=f"{name} {port}",
                                     detail=f"{port} is {st}"))

    # 5. missing VLAN assignment
    for name, s in switches.items():
        for port, exp_vlan in GOLDEN["switches"][name]["vlan_ports"].items():
            if exp_vlan == "trunk":
                continue
            actual = s["vlan_ports"].get(port)
            if actual != exp_vlan:
                findings.append(dict(fault_type="missing_vlan_assignment", device=f"{name} {port}",
                                     detail=f"{port} in VLAN {actual} != expected VLAN {exp_vlan}"))

    # 6. missing static route
    for name, r in routers.items():
        for rt in GOLDEN["routers"][name]["routes"]:
            key = f"{rt['network']}/{mask_to_prefix(rt['mask'])}"
            if key not in r["routes"]:
                findings.append(dict(fault_type="missing_route", device=name,
                                     detail=f"{name} missing route to {key} via {rt['next_hop']}"))

    primary = findings[0]["fault_type"] if findings else "none"
    confidence = "high" if len(findings) == 1 else ("medium" if findings else "low")
    fix = RECOMMENDED_FIX.get(primary, "Manual investigation required.")
    return dict(fault_type=primary, confidence=confidence,
                recommended_fix=fix, findings=findings, engine="rule_based")


RECOMMENDED_FIX = {
    "duplicate_ip": "Assign a unique IP to the conflicting host.",
    "wrong_subnet_mask": "Correct the subnet mask to match the segment (usually 255.255.255.0).",
    "gateway_mismatch": "Set the default gateway to the correct router interface IP.",
    "interface_down": "Enter the interface and issue 'no shutdown'.",
    "missing_vlan_assignment": "Reassign the access port with 'switchport access vlan <id>'.",
    "missing_route": "Add the missing static route with 'ip route <net> <mask> <next-hop>'.",
    "none": "No rule violation detected.",
}


def _run_all():
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    out = []
    for c in cases:
        text = open(os.path.join(ROOT, c["evidence_file"])).read()
        d = diagnose(text)
        d["id"] = c["id"]
        out.append(d)
        print(f"{c['id']}: {d['fault_type']:<24} conf={d['confidence']} ({len(d['findings'])} finding/s)")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "results", "rule_diagnoses.json"), "w"), indent=2)
    print(f"\nWrote results/rule_diagnoses.json")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(diagnose(open(sys.argv[1]).read()), indent=2))
    else:
        _run_all()
