"""
Compare rule-engine vs AI findings side-by-side and capture a human decision
for every case. This is the human-in-the-loop governance step.

For each case you choose:
  [a] Accept  the AI recommendation
  [e] Edit    it (type the corrected fault_type)
  [r] Reject  it (fall back to the rule-engine finding)

Decisions are logged to results/review_log.json.

Run:  python src/compare.py           (interactive)
      python src/compare.py --auto    (non-interactive: accept AI, flag disagreements)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")


def _load(name):
    path = os.path.join(R, name)
    return {d["id"]: d for d in json.load(open(path))} if os.path.exists(path) else {}


def main(auto):
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    rule = _load("rule_diagnoses.json")
    ai = _load("ai_diagnoses.json")
    if not ai:
        print("No results/ai_diagnoses.json found. Run src/ai_diagnose.py first "
              "(needs ANTHROPIC_API_KEY). Continuing with rule engine only.\n")
    auto = auto or not sys.stdin.isatty()

    log = []
    for c in cases:
        cid = c["id"]
        rd, ad = rule.get(cid, {}), ai.get(cid, {})
        rf, af = rd.get("fault_type", "none"), ad.get("fault_type", "none")
        agree = rf == af
        print("=" * 70)
        print(f"{cid}  |  symptom: {c['symptom']}")
        print(f"  RULE : {rf:<24} ({rd.get('confidence','-')})")
        print(f"  AI   : {af:<24} ({ad.get('confidence','-')})  {ad.get('explanation','')}")
        print(f"  agree: {agree}")

        if auto:
            decision, final = "accepted", (af if af != "none" else rf)
            note = "auto"
        else:
            choice = input("  [a]ccept AI / [e]dit / [r]eject->rule ? ").strip().lower()
            if choice == "e":
                final = input("    corrected fault_type: ").strip() or af
                decision = "edited"
            elif choice == "r":
                final, decision = rf, "rejected"
            else:
                final, decision = (af if af != "none" else rf), "accepted"
            note = input("    note (optional): ").strip()

        log.append(dict(id=cid, rule_fault=rf, ai_fault=af, agree=agree,
                        decision=decision, final_fault=final, note=note))
        print(f"  -> {decision}: {final}")

    os.makedirs(R, exist_ok=True)
    json.dump(log, open(os.path.join(R, "review_log.json"), "w"), indent=2)
    print("\nWrote results/review_log.json")


if __name__ == "__main__":
    main("--auto" in sys.argv)
