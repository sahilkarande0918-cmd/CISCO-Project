"""
Compute project metrics from the ground truth and the diagnosis/review logs.

Outputs results/metrics.json and prints a report table:
  - rule-engine accuracy vs actual injected fault
  - AI accuracy vs actual injected fault
  - agreement rate between the two
  - per-case disagreements and the human decision
  - breakdown of human decisions (accepted / edited / rejected)

Run:  python src/metrics.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")


def _load(name):
    path = os.path.join(R, name)
    return {d["id"]: d for d in json.load(open(path))} if os.path.exists(path) else {}


def main():
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    truth = {c["id"]: c["fault_type"] for c in cases}
    rule = _load("rule_diagnoses.json")
    ai = _load("ai_diagnoses.json")
    review = _load("review_log.json")

    n = len(cases)
    rule_correct = ai_correct = agree = 0
    rows, disagreements = [], []
    for c in cases:
        cid = c["id"]
        t = truth[cid]
        rf = rule.get(cid, {}).get("fault_type", "-")
        af = ai.get(cid, {}).get("fault_type", "-")
        rc, ac = rf == t, af == t
        rule_correct += rc
        ai_correct += ac
        if af != "-" and rf == af:
            agree += 1
        if af != "-" and rf != af:
            disagreements.append(dict(id=cid, truth=t, rule=rf, ai=af,
                                      human=review.get(cid, {}).get("final_fault", "-")))
        rows.append((cid, t, rf, "OK" if rc else "X", af, "OK" if ac else "X"))

    decisions = {}
    for d in review.values():
        decisions[d["decision"]] = decisions.get(d["decision"], 0) + 1

    metrics = dict(
        cases=n,
        rule_accuracy=round(rule_correct / n, 3),
        ai_accuracy=round(ai_correct / n, 3) if ai else None,
        agreement_rate=round(agree / n, 3) if ai else None,
        disagreements=disagreements,
        human_decisions=decisions,
    )
    os.makedirs(R, exist_ok=True)
    json.dump(metrics, open(os.path.join(R, "metrics.json"), "w"), indent=2)

    # print report
    print(f"{'case':<8}{'actual':<24}{'rule':<24}{'':<4}{'ai':<24}{''}")
    print("-" * 88)
    for cid, t, rf, rok, af, aok in rows:
        print(f"{cid:<8}{t:<24}{rf:<22}{rok:<4}{af:<22}{aok}")
    print("-" * 88)
    print(f"Rule-engine accuracy : {rule_correct}/{n} = {metrics['rule_accuracy']*100:.0f}%")
    if ai:
        print(f"AI accuracy          : {ai_correct}/{n} = {metrics['ai_accuracy']*100:.0f}%")
        print(f"Agreement rate       : {agree}/{n} = {metrics['agreement_rate']*100:.0f}%")
        print(f"Disagreements        : {len(disagreements)}")
    if decisions:
        print(f"Human decisions      : {decisions}")
    print("\nWrote results/metrics.json")


if __name__ == "__main__":
    main()
