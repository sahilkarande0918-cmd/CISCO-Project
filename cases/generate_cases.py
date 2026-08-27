"""
Generate the fault-case bank from the golden baseline.

Each case = golden topology + exactly ONE injected fault. We render realistic
Cisco IOS / PC command output so the rest of the pipeline (rule engine, AI,
compare, metrics) has something to run against immediately.

NOTE: these files are realistic *templates*. For the real submission, replace
each caseNN_evidence.txt with actual `show`/`ipconfig`/`ping` captures from
Packet Tracer (same format) — the parsers key off the section markers, not the
exact text. Ground-truth labels live in cases.json.

Run:  python cases/generate_cases.py
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLDEN = json.load(open(os.path.join(ROOT, "topology", "golden.json")))

# --- 12 fault specs: 2 per fault type -------------------------------------
# Each spec mutates the golden model and records the ground truth.
FAULTS = [
    dict(id="case01", type="duplicate_ip",
         symptom="PC2 cannot reach any host; Windows reports an IP address conflict.",
         devices=["R1", "SW1", "PC1", "PC2"],
         mutate=lambda t: t["pcs"]["PC2"].__setitem__("ip", "192.168.10.11"),
         ping=("PC2", "192.168.10.1", False)),
    dict(id="case02", type="duplicate_ip",
         symptom="VLAN20 hosts intermittently lose their default gateway.",
         devices=["R1", "SW1", "PC3"],
         mutate=lambda t: t["pcs"]["PC3"].__setitem__("ip", "192.168.20.1"),
         ping=("PC3", "192.168.20.1", False)),

    dict(id="case03", type="wrong_subnet_mask",
         symptom="PC3 can ping hosts in its own VLAN but nothing beyond it.",
         devices=["R1", "SW1", "PC3"],
         mutate=lambda t: t["pcs"]["PC3"].__setitem__("mask", "255.255.0.0"),
         ping=("PC3", "192.168.30.11", False)),
    dict(id="case04", type="wrong_subnet_mask",
         symptom="PC1 reaches the gateway but not PC2 on the same VLAN reliably.",
         devices=["R1", "SW1", "PC1", "PC2"],
         mutate=lambda t: t["pcs"]["PC1"].__setitem__("mask", "255.255.255.128"),
         ping=("PC1", "192.168.10.12", False)),

    dict(id="case05", type="gateway_mismatch",
         symptom="PC1 pings local hosts but cannot reach other VLANs.",
         devices=["R1", "SW1", "PC1"],
         mutate=lambda t: t["pcs"]["PC1"].__setitem__("gateway", "192.168.10.254"),
         ping=("PC1", "192.168.20.11", False)),
    dict(id="case06", type="gateway_mismatch",
         symptom="PC5 has no inter-VLAN connectivity.",
         devices=["R2", "PC5"],
         mutate=lambda t: t["pcs"]["PC5"].__setitem__("gateway", "192.168.30.254"),
         ping=("PC5", "192.168.10.11", False)),

    dict(id="case07", type="interface_down",
         symptom="Nothing in VLAN30 is reachable from VLAN10/20.",
         devices=["R1", "R2"],
         mutate=lambda t: t["routers"]["R1"]["interfaces"]["GigabitEthernet0/1"].__setitem__("status", "administratively down"),
         ping=("R1", "10.0.0.2", False)),
    dict(id="case08", type="interface_down",
         symptom="VLAN10 hosts lose their gateway and inter-VLAN access.",
         devices=["R1", "SW1", "PC1"],
         mutate=lambda t: t["switches"]["SW1"]["interfaces"]["FastEthernet0/24"].__setitem__("status", "administratively down"),
         ping=("PC1", "192.168.10.1", False)),

    dict(id="case09", type="missing_vlan_assignment",
         symptom="PC1 has no connectivity at all, not even to its gateway.",
         devices=["R1", "SW1", "PC1"],
         mutate=lambda t: t["switches"]["SW1"]["vlan_ports"].__setitem__("FastEthernet0/1", 1),
         ping=("PC1", "192.168.10.1", False)),
    dict(id="case10", type="missing_vlan_assignment",
         symptom="PC3 is isolated from the VLAN20 server segment.",
         devices=["R1", "SW1", "PC3"],
         mutate=lambda t: t["switches"]["SW1"]["vlan_ports"].__setitem__("FastEthernet0/3", 1),
         ping=("PC3", "192.168.20.1", False)),

    dict(id="case11", type="missing_route",
         symptom="VLAN10 to VLAN30 traffic fails one way; return path is missing.",
         devices=["R1", "R2"],
         mutate=lambda t: t["routers"]["R2"]["routes"].__delitem__(0),  # drop route to 192.168.10.0/24
         ping=("PC5", "192.168.10.11", False)),
    dict(id="case12", type="missing_route",
         symptom="VLAN30 is unreachable from every local VLAN.",
         devices=["R1", "R2"],
         mutate=lambda t: t["routers"]["R1"]["routes"].clear(),  # drop route to 192.168.30.0/24
         ping=("PC1", "192.168.30.11", False)),
]


# --- renderers: model -> realistic command output -------------------------
def render_router(name, r):
    out = [f"===== DEVICE: {name} =====", f"{name}# show ip interface brief"]
    out.append("Interface                  IP-Address      OK? Method Status                Protocol")
    for intf, c in r["interfaces"].items():
        proto = "up" if c["status"] == "up" else "down"
        status = c["status"]
        out.append(f"{intf:<26} {c['ip']:<15} YES manual {status:<21} {proto}")
    out += ["", f"{name}# show running-config | section interface"]
    for intf, c in r["interfaces"].items():
        out.append(f"interface {intf}")
        out.append(f" ip address {c['ip']} {c['mask']}")
        if c["status"] != "up":
            out.append(" shutdown")
        out.append("!")
    out += ["", f"{name}# show ip route"]
    out.append("Codes: C - connected, S - static")
    for intf, c in r["interfaces"].items():
        if c["status"] == "up":
            net = _network(c["ip"], c["mask"])
            out.append(f"C    {net} is directly connected, {intf}")
    for rt in r["routes"]:
        out.append(f"S    {rt['network']}/{_prefix(rt['mask'])} [1/0] via {rt['next_hop']}")
    out.append("")
    return "\n".join(out)


def render_switch(name, s):
    out = [f"===== DEVICE: {name} =====", f"{name}# show vlan brief"]
    out.append("VLAN Name                             Status    Ports")
    ports_by_vlan = {}
    for port, vlan in s["vlan_ports"].items():
        if vlan == "trunk":
            continue
        ports_by_vlan.setdefault(vlan, []).append(port)
    names = {1: "default", 10: "Users", 20: "Servers", 30: "Remote"}
    for vlan in sorted(set(list(ports_by_vlan) + [1, 10, 20])):
        ports = ", ".join(ports_by_vlan.get(vlan, []))
        out.append(f"{vlan:<4} {names.get(vlan, 'VLAN'+str(vlan)):<32} active    {ports}")
    out += ["", f"{name}# show interfaces status"]
    out.append("Port      Name       Status       Vlan       Duplex  Speed Type")
    for port, c in s.get("interfaces", {}).items():
        st = "connected" if c["status"] == "up" else "disabled"
        out.append(f"{port:<9}            {st:<12} trunk      a-full  a-100")
    out.append("")
    return "\n".join(out)


def render_pc(name, p, ping):
    out = [f"===== DEVICE: {name} =====", f"C:\\> ipconfig /all", "",
           f"   IPv4 Address. . . . . . . . . . . : {p['ip']}",
           f"   Subnet Mask . . . . . . . . . . . : {p['mask']}",
           f"   Default Gateway . . . . . . . . . : {p['gateway']}", ""]
    if ping and ping[0] == name:
        _, target, ok = ping
        out.append(f"C:\\> ping {target}")
        if ok:
            out.append(f"Reply from {target}: bytes=32 time=1ms TTL=128")
        else:
            out += ["Request timed out.", "Request timed out.",
                    f"Ping statistics for {target}:",
                    "    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),"]
        out.append("")
    return "\n".join(out)


def _network(ip, mask):
    ipo = [int(x) for x in ip.split(".")]
    mo = [int(x) for x in mask.split(".")]
    net = ".".join(str(ipo[i] & mo[i]) for i in range(4))
    return f"{net}/{_prefix(mask)}"


def _prefix(mask):
    return sum(bin(int(o)).count("1") for o in mask.split("."))


def build():
    ground_truth = []
    for f in FAULTS:
        topo = copy.deepcopy(GOLDEN)
        f["mutate"](topo)
        parts = []
        for d in f["devices"]:
            if d in topo["routers"]:
                parts.append(render_router(d, topo["routers"][d]))
            elif d in topo["switches"]:
                parts.append(render_switch(d, topo["switches"][d]))
            elif d in topo["pcs"]:
                parts.append(render_pc(d, topo["pcs"][d], f.get("ping")))
        header = (f"! Case {f['id']} evidence  (fault injected: exactly one)\n"
                  f"! Reported symptom: {f['symptom']}\n"
                  f"! Devices captured: {', '.join(f['devices'])}\n")
        path = os.path.join(HERE, f"{f['id']}_evidence.txt")
        open(path, "w").write(header + "\n" + "\n".join(parts))
        ground_truth.append(dict(id=f["id"], fault_type=f["type"], symptom=f["symptom"],
                                 evidence_file=f"cases/{f['id']}_evidence.txt"))
    json.dump({"cases": ground_truth}, open(os.path.join(HERE, "cases.json"), "w"), indent=2)
    print(f"Generated {len(FAULTS)} cases + cases.json")


if __name__ == "__main__":
    build()
