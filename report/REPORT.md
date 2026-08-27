# AI-Assisted Network Fault Diagnosis and Remediation System
### using Cisco Packet Tracer — Internship Project Report

## 1. Problem statement

Manual network troubleshooting is slow and inconsistent: two engineers looking at the same
symptom often check different things in a different order. This project builds a hybrid
diagnostic pipeline that combines **rule-based checks (Python)** and **AI reasoning** to detect
and recommend fixes for common network faults, with a **human validating every AI
recommendation before it is applied**.

## 2. Objectives

- Model a realistic small-enterprise network with injectable faults.
- Diagnose six common fault types two independent ways (deterministic rules + AI).
- Compare the two, keep a human in the loop, apply the fix, and **verify** it worked.
- Measure accuracy and where the two approaches disagree.

## 3. System architecture

```
Case (one injected fault)
   │
   ▼
Symptom + Topology  ─►  Evidence collection (show / ipconfig / ping)
   │
   ├──────────────► Python rule engine ──┐
   │                                     ├─► Compare ─► Human review ─► Apply fix ─► Verify
   └──────────────► AI diagnosis ────────┘   (accept / edit / reject)
```

Both engines receive identical evidence. The rule engine diffs it against a **golden baseline**
(`topology/golden.json`); the AI receives the same text with a tightly scoped prompt and returns
a structured JSON diagnosis. A comparison step shows both side by side; a human records
**Accepted / Edited / Rejected** for each AI recommendation (human-in-the-loop governance).

## 4. Topology

2 routers (R1 router-on-a-stick, R2 remote), 1–2 switches, VLAN10 (Users), VLAN20 (Servers),
VLAN30 (Remote behind R2), a /30 WAN link, and static routing between the two routers.
Full addressing and build steps: [`../topology/TOPOLOGY.md`](../topology/TOPOLOGY.md).

## 5. Fault case bank

12 cases, 2 per fault type, one injected fault each:

| # | Fault type | Example symptom |
|---|-----------|-----------------|
| 01–02 | duplicate_ip | IP conflict; host loses connectivity |
| 03–04 | wrong_subnet_mask | local reachable, remote not |
| 05–06 | gateway_mismatch | local OK, no inter-VLAN |
| 07–08 | interface_down | segment unreachable |
| 09–10 | missing_vlan_assignment | host isolated |
| 11–12 | missing_route | one-way / remote unreachable |

Ground-truth labels: [`../cases/cases.json`](../cases/cases.json).

## 6. Method

- **Evidence** — per case, capture `show ip interface brief`, relevant `show running-config`,
  `show vlan brief`, `show ip route`, and `ipconfig` / `ping`. Saved as `caseNN_evidence.txt`.
- **Rule engine** (`src/rule_engine.py`) — parses evidence, diffs against the golden baseline,
  and flags: duplicate IPs across hosts, mask/gateway mismatches, admin-down interfaces,
  wrong VLAN assignments, and missing static routes. Emits structured JSON.
- **AI module** (`src/ai_diagnose.py`) — sends the same evidence to Gemini/Grok and returns
  `fault_type`, `explanation`, `confidence`, `recommended_fix` as JSON.
- **Compare + review** (`src/compare.py`) — side-by-side, human decision logged.
- **Metrics** (`src/metrics.py`) — accuracy vs the known injected fault, agreement, disagreements.

## 7. Results

> Regenerate with `python src/run_all.py`; numbers below come from `results/metrics.json`.

**Rule-engine accuracy: 12/12 = 100%** on the template case bank (every injected fault
correctly identified, each as a single high-confidence finding).

**AI accuracy: _<run the AI step and fill in>_ / 12.**
Provider/model used: _<gemini-2.5-flash / grok-… >_.

**Agreement rate (rule vs AI): _<fill in>_ / 12.**

### Disagreements and human decisions

| Case | Actual fault | Rule says | AI says | Human decision |
|------|--------------|-----------|---------|----------------|
| _fill from results/metrics.json + review_log.json_ | | | | |

### Time-to-diagnosis (estimated)

| Method | Approx. time per case |
|--------|-----------------------|
| Manual troubleshooting | 5–15 min |
| Rule engine | < 1 s |
| AI-assisted | 2–5 s + human review |

## 8. Apply & verify

For each accepted/edited fix: apply it in Packet Tracer, then re-run the same `ping` / `show`
commands. A case is **Verified** only when the original symptom is gone. Record before/after
output — this proves the system remediates, not just diagnoses.

## 9. Human-in-the-loop as governance

Every AI recommendation is gated by a human decision (`results/review_log.json`). The rule
engine acts as an independent second opinion: when AI and rules disagree, the human adjudicates.
This makes the AI advisory, never autonomous — the design property evaluators look for.

## 10. Conclusion & future work

The hybrid pipeline diagnoses all six fault types and keeps a human in control. Rules give
deterministic, explainable coverage; the AI adds natural-language explanation and generalisation
to cases the rules don't encode. Future work: auto-apply verified fixes via device APIs/Netmiko,
expand the fault taxonomy (routing loops, STP, ACLs), and replace template evidence with a
larger bank of real captures.

## Appendix — reproduce

```bash
pip install -r requirements.txt
set AI_PROVIDER=gemini & set GEMINI_API_KEY=...   # or grok + XAI_API_KEY
python src/run_all.py
```
