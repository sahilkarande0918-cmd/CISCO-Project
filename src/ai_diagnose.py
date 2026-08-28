"""
AI diagnosis module.

Sends the same evidence file to an LLM with a tightly scoped prompt and logs a
structured diagnosis, so it can be compared against the rule engine.

Works with Gemini or Grok (both expose an OpenAI-compatible endpoint). Pick one:

  Gemini:  set AI_PROVIDER=gemini   &&  set GEMINI_API_KEY=...
  Grok:    set AI_PROVIDER=grok     &&  set XAI_API_KEY=...

Override the model if you like:  set AI_MODEL=gemini-2.5-pro   (or grok-4, etc.)

Run all cases:  python src/ai_diagnose.py
One file:       python src/ai_diagnose.py cases/case01_evidence.txt
"""
import json
import os
import re
import sys
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAULT_TYPES = ["duplicate_ip", "wrong_subnet_mask", "gateway_mismatch",
               "interface_down", "missing_vlan_assignment", "missing_route"]

# provider presets: (base_url, default_model, api_key_env)
PROVIDERS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.6-flash", "GEMINI_API_KEY"),
    "grok":   ("https://api.x.ai/v1", "grok-2-latest", "XAI_API_KEY"),
}


def resolve():
    """Read provider/model/key from env at call time (so the dashboard can switch live)."""
    provider = os.environ.get("AI_PROVIDER", "gemini").lower()
    base_url, default_model, key_env = PROVIDERS.get(provider, PROVIDERS["gemini"])
    model = os.environ.get("AI_MODEL") or default_model
    key = os.environ.get(key_env) or os.environ.get("AI_API_KEY")
    return provider, base_url, model, key_env, key


# module-level snapshot (used by run_all's "is a key set?" check)
PROVIDER, BASE_URL, MODEL, KEY_ENV, _ = resolve()

PROMPT = """You are a network fault diagnosis assistant analysing Cisco Packet Tracer output.

Below is command output collected from one or more devices in a small enterprise
network (2 routers, a switch with VLANs 10/20/30, several PCs). Exactly ONE fault
has been injected. Identify it.

Reported symptom: {symptom}

Evidence:
{evidence}

Respond with ONLY a JSON object, no prose, in exactly this shape:
{{"fault_type": "<one of: {types}>",
  "explanation": "<one or two sentences on what is wrong and why it causes the symptom>",
  "confidence": "<high|medium|low>",
  "recommended_fix": "<the specific Cisco IOS or PC config change to apply>"}}"""


def _extract_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"fault_type": "none", "explanation": text,
                                             "confidence": "low", "recommended_fix": ""}


def diagnose(evidence_text, symptom=""):
    provider, base_url, model, key_env, key = resolve()
    if not key:
        raise RuntimeError(f"No API key. Set {key_env} (provider={provider}).")
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0,
              "messages": [{"role": "user", "content": PROMPT.format(
                  symptom=symptom or "(not provided)", evidence=evidence_text,
                  types=", ".join(FAULT_TYPES))}]},
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    d = _extract_json(text)
    d["engine"] = "ai"
    d["model"] = model
    return d


def _run_all():
    provider, _base, model, _ke, _key = resolve()
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    out = []
    for c in cases:
        text = open(os.path.join(ROOT, c["evidence_file"])).read()
        try:
            d = diagnose(text, c["symptom"])
        except Exception as e:
            d = {"fault_type": "none", "confidence": "low", "explanation": f"error: {e}",
                 "engine": "ai", "model": model}
        d["id"] = c["id"]
        out.append(d)
        print(f"{c['id']}: {d['fault_type']:<24} conf={d.get('confidence')}")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "results", "ai_diagnoses.json"), "w"), indent=2)
    print(f"\nWrote results/ai_diagnoses.json  (provider={provider}, model={model})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(diagnose(open(sys.argv[1]).read()), indent=2))
    else:
        _run_all()
