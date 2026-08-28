# FaultLine — AI-Assisted Network Fault Diagnosis and Remediation System

A hybrid diagnostic pipeline for common network faults, built on a Cisco Packet Tracer
topology. It combines a **deterministic Python rule engine** and **AI reasoning (Gemini or
Grok)** running in parallel on the same evidence, then puts a **human in the loop** to
validate every AI recommendation before it is applied.

> Internship project for Cisco. Problem: manual network troubleshooting is slow and
> inconsistent. This system detects, explains, and recommends fixes for six common fault
> types, and proves the fix by re-testing.

## Architecture

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

The rule engine and the AI see identical evidence. The **comparison + human review** step is
the core novelty: findings are shown side by side and a human marks each AI recommendation
**Accepted / Edited / Rejected** — logged as evidence of human-in-the-loop governance.

## Fault types covered

`duplicate_ip` · `wrong_subnet_mask` · `gateway_mismatch` · `interface_down` ·
`missing_vlan_assignment` · `missing_route`  (2 cases each → 12 cases)

## Layout

```
topology/   golden.json (baseline = source of truth) + TOPOLOGY.md (design & build guide)
cases/      generate_cases.py, 12 caseNN_evidence.txt, cases.json (ground-truth labels)
src/        rule_engine.py  ai_diagnose.py  compare.py  metrics.py  run_all.py
results/    generated: rule_diagnoses.json, ai_diagnoses.json, review_log.json, metrics.json
report/     REPORT.md (formal write-up)
```

## Setup

```bash
pip install -r requirements.txt
```

Pick an AI provider (either works — same OpenAI-compatible code path):

```bash
# Gemini
set AI_PROVIDER=gemini
set GEMINI_API_KEY=your_key_here
# or Grok
set AI_PROVIDER=grok
set XAI_API_KEY=your_key_here
```

## Run

```bash
python src/run_all.py          # generate cases → rule engine → AI → auto-compare → metrics
```

Individual steps:

```bash
python cases/generate_cases.py     # (re)build the evidence bank from golden.json
python src/rule_engine.py          # rule-based diagnosis → results/rule_diagnoses.json
python src/ai_diagnose.py          # AI diagnosis → results/ai_diagnoses.json  (needs key)
python src/compare.py              # INTERACTIVE human-in-the-loop review
python src/metrics.py              # accuracy / agreement / disagreements report
```

Diagnose a single evidence file:

```bash
python src/rule_engine.py cases/case01_evidence.txt
python src/ai_diagnose.py cases/case01_evidence.txt
```

## Using real Packet Tracer captures

The 12 evidence files are realistic **templates** so the pipeline runs immediately. For the
real submission, build the topology (see [`topology/TOPOLOGY.md`](topology/TOPOLOGY.md)), inject
one fault per case, and replace each `caseNN_evidence.txt` with your actual
`show ip interface brief` / `show ip route` / `show vlan brief` / `ipconfig` / `ping` output.
The parsers key off the `===== DEVICE: X =====` section markers, not the exact wording.

## Workflow per case (Phases 8–9)

1. Diagnose (rule + AI), compare, human decides.
2. Apply the accepted/edited fix in Packet Tracer.
3. Re-run the same `ping` / `show` commands to confirm resolution — record before/after.
4. `metrics.py` reports rule accuracy, AI accuracy, agreement rate, and disagreements.
