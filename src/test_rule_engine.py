"""Smallest check that fails if evidence parsing or a rule breaks.
Run:  python src/test_rule_engine.py
"""
import json
import os
import rule_engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_cases_match_ground_truth():
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    for c in cases:
        d = rule_engine.diagnose(open(os.path.join(ROOT, c["evidence_file"])).read())
        assert d["fault_type"] == c["fault_type"], \
            f"{c['id']}: rule said {d['fault_type']!r}, expected {c['fault_type']!r}"
        assert len(d["findings"]) == 1, f"{c['id']}: expected 1 finding, got {len(d['findings'])}"
    print(f"OK: {len(cases)}/{len(cases)} cases diagnosed correctly, one finding each.")


if __name__ == "__main__":
    test_all_cases_match_ground_truth()
