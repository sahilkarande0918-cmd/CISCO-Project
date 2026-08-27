"""
Run the whole pipeline in order:
  1. generate the fault-case bank      (cases/*.txt + cases.json)
  2. rule engine over every case       (results/rule_diagnoses.json)
  3. AI diagnosis over every case       (results/ai_diagnoses.json)  -- skipped if no key
  4. compare + human review (auto)      (results/review_log.json)
  5. metrics report                     (results/metrics.json)

Run:  python src/run_all.py
For the real human-in-the-loop step, run  python src/compare.py  (interactive) instead of --auto.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


def step(msg):
    print("\n" + "#" * 70 + f"\n# {msg}\n" + "#" * 70)


step("1. Generate cases")
runpy.run_path(os.path.join(ROOT, "cases", "generate_cases.py"), run_name="__main__")

step("2. Rule engine")
import rule_engine
rule_engine._run_all()

step("3. AI diagnosis")
import ai_diagnose
key = os.environ.get(ai_diagnose.KEY_ENV) or os.environ.get("AI_API_KEY")
if key:
    ai_diagnose._run_all()
else:
    print(f"Skipped: no {ai_diagnose.KEY_ENV}. "
          f"Set AI_PROVIDER + key, then run  python src/ai_diagnose.py")

step("4. Compare + human review (auto)")
import compare
compare.main(auto=True)

step("5. Metrics")
import metrics
metrics.main()
