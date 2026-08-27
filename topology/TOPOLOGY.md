# Network Topology

One moderately complex topology hosts all six fault types yet explains in ~5 minutes.
Build it once in Packet Tracer, save a clean **golden** copy, and clone it per fault case.

## Devices

| Device | Role | Key interfaces |
|--------|------|----------------|
| R1 | Router-on-a-stick, inter-VLAN routing for VLAN10/20 | Gig0/0.10, Gig0/0.20, Gig0/1 (WAN to R2) |
| R2 | Router for the remote VLAN30 segment | Gig0/1 (WAN to R1), Gig0/0 |
| SW1 | Access switch for VLAN10/20 hosts, trunk to R1 | Fa0/1–3 access, Fa0/24 trunk |
| SW2 | Access switch for the remote side | Fa0/1 access |
| PC1, PC2 | Users, VLAN10 | — |
| PC3 | Server, VLAN20 | — |
| PC5 | Remote host, VLAN30 (behind R2) | — |

## Addressing (the golden baseline)

| Segment | Subnet | Gateway |
|---------|--------|---------|
| VLAN10 Users | 192.168.10.0/24 | 192.168.10.1 (R1 Gig0/0.10) |
| VLAN20 Servers | 192.168.20.0/24 | 192.168.20.1 (R1 Gig0/0.20) |
| VLAN30 Remote | 192.168.30.0/24 | 192.168.30.1 (R2 Gig0/0) |
| R1–R2 link | 10.0.0.0/30 | R1 10.0.0.1, R2 10.0.0.2 |

| Host | IP | Mask | Gateway |
|------|----|------|---------|
| PC1 | 192.168.10.11 | /24 | 192.168.10.1 |
| PC2 | 192.168.10.12 | /24 | 192.168.10.1 |
| PC3 | 192.168.20.11 | /24 | 192.168.20.1 |
| PC5 | 192.168.30.11 | /24 | 192.168.30.1 |

**Static routes:** R1 → 192.168.30.0/24 via 10.0.0.2; R2 → 192.168.10.0/24 and 192.168.20.0/24 via 10.0.0.1.

The exact same data lives in machine-readable form in [`golden.json`](golden.json) — the rule
engine diffs collected evidence against it, so **if you change the design, change golden.json too.**

## Building it in Packet Tracer (once)

1. Place R1, R2, SW1, SW2, PC1, PC2, PC3, PC5 and cable them per the table above.
2. R1 router-on-a-stick: create sub-interfaces Gig0/0.10 and Gig0/0.20 with `encapsulation dot1Q 10/20` and the gateway IPs; set Gig0/1 to 10.0.0.1/30.
3. SW1: `vlan 10` (Users), `vlan 20` (Servers); assign Fa0/1–2 to VLAN10, Fa0/3 to VLAN20; set Fa0/24 to `switchport mode trunk`.
4. R2: Gig0/1 = 10.0.0.2/30, Gig0/0 = 192.168.30.1/24. SW2 Fa0/1 access for PC5.
5. Add the static routes. Confirm every PC can ping every other PC.
6. **Save As `golden.pkt`.** This is your baseline — never inject faults into it.

## The six fault types (2–3 cases each)

| Fault type | How to inject in the clone |
|------------|----------------------------|
| duplicate_ip | Set a second host's IP equal to an existing one |
| wrong_subnet_mask | Change a host mask (e.g. /24 → /16 or /25) |
| gateway_mismatch | Point a host's default gateway at a non-existent address |
| interface_down | `shutdown` a router interface or switch trunk port |
| missing_vlan_assignment | Move an access port back to VLAN 1 |
| missing_route | Remove a required static route on R1 or R2 |

For each case: clone golden, inject **exactly one** fault, note the symptom, collect evidence
(see the project README, Phase 4). The 12 template evidence files in `../cases/` show the
exact format the parsers expect — replace their contents with your real captures.
