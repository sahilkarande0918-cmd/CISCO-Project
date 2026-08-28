// Rule engine ported from src/rule_engine.py (plain JS; valid TS for Deno).
const RECOMMENDED_FIX = {
  duplicate_ip: "Assign a unique IP to the conflicting host.",
  wrong_subnet_mask: "Correct the subnet mask to match the segment (usually 255.255.255.0).",
  gateway_mismatch: "Set the default gateway to the correct router interface IP.",
  interface_down: "Enter the interface and issue 'no shutdown'.",
  missing_vlan_assignment: "Reassign the access port with 'switchport access vlan <id>'.",
  missing_route: "Add the missing static route with 'ip route <net> <mask> <next-hop>'.",
  none: "No rule violation detected.",
};

const maskToPrefix = (m) =>
  m.split(".").reduce((a, o) => a + ((parseInt(o, 10) >>> 0).toString(2).match(/1/g) || []).length, 0);

function splitDevices(text) {
  const parts = text.split(/=====\s*DEVICE:\s*(\S+)\s*=====/);
  const dev = {};
  for (let i = 1; i < parts.length; i += 2) dev[parts[i]] = parts[i + 1];
  return dev;
}

function parseRouter(block) {
  const ifaces = {};
  const brief = /^(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+\w+\s+\w+\s+(.*?)\s+(up|down)\s*$/gm;
  let m;
  while ((m = brief.exec(block))) ifaces[m[1]] = { ip: m[2], status: m[3].trim() };
  const cfg = /interface (\S+)\n(?:.*\n)*? ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)/g;
  while ((m = cfg.exec(block))) if (ifaces[m[1]]) ifaces[m[1]].mask = m[3];
  const routes = new Set();
  const rt = /^[SC]\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)/gm;
  while ((m = rt.exec(block))) routes.add(`${m[1]}/${m[2]}`);
  return { interfaces: ifaces, routes };
}

function parseSwitch(block) {
  const vlanPorts = {};
  const vl = /^(\d+)[ \t]+\S+[ \t]+active[ \t]*(.*)$/gm;
  let m;
  while ((m = vl.exec(block))) {
    const vlan = parseInt(m[1], 10);
    (m[2].match(/(?:Fast|Gigabit)Ethernet\S+/g) || []).forEach((p) => {
      vlanPorts[p.replace(/,$/, "")] = vlan;
    });
  }
  const ifaceStatus = {};
  const st = /^((?:Fast|Gigabit)Ethernet\S+)\s+.*?\b(connected|disabled|notconnect|err-disabled)\b/gm;
  while ((m = st.exec(block))) ifaceStatus[m[1]] = m[2];
  return { vlanPorts, ifaceStatus };
}

function parsePC(block) {
  const grab = (label) => {
    const m = new RegExp(label + ".*?:\\s*(\\S+)").exec(block);
    return m ? m[1] : null;
  };
  return { ip: grab("IPv4 Address"), mask: grab("Subnet Mask"), gateway: grab("Default Gateway") };
}

export function diagnose(text, GOLDEN) {
  const devices = splitDevices(text);
  const findings = [];
  const routers = {}, switches = {}, pcs = {};
  for (const [name, block] of Object.entries(devices)) {
    if (GOLDEN.routers[name]) routers[name] = parseRouter(block);
    else if (GOLDEN.switches[name]) switches[name] = parseSwitch(block);
    else if (GOLDEN.pcs[name]) pcs[name] = parsePC(block);
  }

  // 1. duplicate IP
  const owners = {};
  for (const [name, r] of Object.entries(routers))
    for (const [intf, c] of Object.entries(r.interfaces)) (owners[c.ip] ||= []).push(`${name} ${intf}`);
  for (const [name, p] of Object.entries(pcs)) if (p.ip) (owners[p.ip] ||= []).push(name);
  for (const [ip, o] of Object.entries(owners))
    if (o.length > 1)
      findings.push({ fault_type: "duplicate_ip", device: o.join(", "), detail: `IP ${ip} is configured on more than one host: ${o.join(", ")}` });

  // 2/3. PC mask + gateway
  for (const [name, p] of Object.entries(pcs)) {
    const g = GOLDEN.pcs[name];
    if (!g) continue;
    if (p.mask && p.mask !== g.mask)
      findings.push({ fault_type: "wrong_subnet_mask", device: name, detail: `${name} mask ${p.mask} != expected ${g.mask}` });
    if (p.gateway && p.gateway !== g.gateway)
      findings.push({ fault_type: "gateway_mismatch", device: name, detail: `${name} gateway ${p.gateway} != expected ${g.gateway}` });
  }
  // 2b. router interface mask
  for (const [name, r] of Object.entries(routers))
    for (const [intf, c] of Object.entries(r.interfaces)) {
      const g = GOLDEN.routers[name].interfaces[intf];
      if (g && c.mask && c.mask !== g.mask)
        findings.push({ fault_type: "wrong_subnet_mask", device: `${name} ${intf}`, detail: `${intf} mask ${c.mask} != expected ${g.mask}` });
    }

  // 4. interfaces down
  for (const [name, r] of Object.entries(routers))
    for (const [intf, c] of Object.entries(r.interfaces))
      if (c.status.includes("administratively down") || c.status === "down")
        findings.push({ fault_type: "interface_down", device: `${name} ${intf}`, detail: `${intf} is ${c.status}` });
  for (const [name, s] of Object.entries(switches))
    for (const [port, stx] of Object.entries(s.ifaceStatus))
      if (stx === "disabled" || stx === "err-disabled")
        findings.push({ fault_type: "interface_down", device: `${name} ${port}`, detail: `${port} is ${stx}` });

  // 5. missing VLAN
  for (const [name, s] of Object.entries(switches))
    for (const [port, exp] of Object.entries(GOLDEN.switches[name].vlan_ports)) {
      if (exp === "trunk") continue;
      const actual = s.vlanPorts[port];
      if (actual !== exp)
        findings.push({ fault_type: "missing_vlan_assignment", device: `${name} ${port}`, detail: `${port} in VLAN ${actual} != expected VLAN ${exp}` });
    }

  // 6. missing route
  for (const [name, r] of Object.entries(routers))
    for (const rt of GOLDEN.routers[name].routes) {
      const key = `${rt.network}/${maskToPrefix(rt.mask)}`;
      if (!r.routes.has(key))
        findings.push({ fault_type: "missing_route", device: name, detail: `${name} missing route to ${key} via ${rt.next_hop}` });
    }

  const primary = findings.length ? findings[0].fault_type : "none";
  const confidence = findings.length === 1 ? "high" : findings.length ? "medium" : "low";
  return { fault_type: primary, confidence, recommended_fix: RECOMMENDED_FIX[primary], findings, engine: "rule_based" };
}
