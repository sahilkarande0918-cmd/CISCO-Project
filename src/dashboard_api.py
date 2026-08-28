"""
Dashboard backend — run the whole pipeline from the browser, no terminal needed.

Serves the built Vue dashboard (dashboard/dist) and a small JSON API:

  GET  /api/data              -> metrics + all cases (evidence, rule, ai, review) + config/status
  POST /api/config            -> {provider, model, api_key}  set AI provider/key for this run
  POST /api/run               -> {step: generate|rule|ai|metrics|all}  run a pipeline phase
  POST /api/review            -> {id, decision, final_fault, note}  persist a human decision

Start it (or just double-click run_dashboard.bat):
  python src/dashboard_api.py        then open http://localhost:8000
"""
import contextlib
import io
import json
import os
import runpy
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dashboard", "dist")
RESULTS = os.path.join(ROOT, "results")
sys.path.insert(0, SRC)

import rule_engine    # noqa: E402
import ai_diagnose    # noqa: E402
import metrics        # noqa: E402

PORT = int(os.environ.get("PORT", "8000"))
CONTENT = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
           ".svg": "image/svg+xml", ".json": "application/json", ".ico": "image/x-icon",
           ".woff2": "font/woff2", ".png": "image/png"}


def _load(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p)) if os.path.exists(p) else None


def build_data():
    cases = json.load(open(os.path.join(ROOT, "cases", "cases.json")))["cases"]
    rule = {d["id"]: d for d in (_load("rule_diagnoses.json") or [])}
    ai = {d["id"]: d for d in (_load("ai_diagnoses.json") or [])}
    review = {d["id"]: d for d in (_load("review_log.json") or [])}
    out_cases = []
    for c in cases:
        ev = ""
        p = os.path.join(ROOT, c["evidence_file"])
        if os.path.exists(p):
            ev = open(p).read()
        out_cases.append(dict(
            id=c["id"], symptom=c["symptom"], fault_type=c["fault_type"],
            evidence=ev, rule=rule.get(c["id"]), ai=ai.get(c["id"]),
            review=review.get(c["id"])))
    try:
        m, _rows, _s = metrics.compute()
    except Exception as e:
        m = {"error": str(e)}
    provider, _b, model, key_env, key = ai_diagnose.resolve()
    return dict(metrics=m, cases=out_cases,
                config=dict(provider=provider, model=model, key_env=key_env,
                            key_set=bool(key)),
                status=dict(rule=bool(rule), ai=bool(ai), review=bool(review)))


def run_step(step):
    """Run a pipeline phase, capturing its stdout as a log string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if step in ("generate", "all"):
            runpy.run_path(os.path.join(ROOT, "cases", "generate_cases.py"), run_name="__main__")
        if step in ("rule", "all"):
            rule_engine._run_all()
        if step in ("ai", "all"):
            _p, _b, _m, _ke, key = ai_diagnose.resolve()
            if key:
                ai_diagnose._run_all()
            else:
                print("AI step skipped: no API key set (use Settings).")
        if step in ("metrics", "all", "rule", "ai", "generate"):
            metrics.compute()
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")  # allow a Vercel frontend
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path.startswith("/api/data"):
            return self._json(build_data())
        return self._static(self.path)

    def do_POST(self):
        try:
            if self.path == "/api/config":
                b = self._body()
                if b.get("provider"):
                    os.environ["AI_PROVIDER"] = b["provider"]
                if b.get("model"):
                    os.environ["AI_MODEL"] = b["model"]
                if b.get("api_key"):
                    # set the key under the provider's expected env var
                    _p, _u, _m, key_env, _k = ai_diagnose.resolve()
                    os.environ[key_env] = b["api_key"]
                    os.environ["AI_API_KEY"] = b["api_key"]
                return self._json({"ok": True, "config": build_data()["config"]})

            if self.path == "/api/run":
                step = self._body().get("step", "all")
                log = run_step(step)
                return self._json({"ok": True, "log": log, "data": build_data()})

            if self.path == "/api/review":
                b = self._body()
                log = _load("review_log.json") or []
                log = [r for r in log if r.get("id") != b["id"]]
                log.append(dict(id=b["id"], decision=b.get("decision", "accepted"),
                                final_fault=b.get("final_fault", ""),
                                note=b.get("note", ""),
                                rule_fault=b.get("rule_fault", ""),
                                ai_fault=b.get("ai_fault", ""),
                                agree=b.get("agree", False)))
                os.makedirs(RESULTS, exist_ok=True)
                json.dump(log, open(os.path.join(RESULTS, "review_log.json"), "w"), indent=2)
                return self._json({"ok": True, "data": build_data()})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)
        return self._json({"error": "not found"}, 404)

    def _static(self, path):
        if not os.path.isdir(DIST):
            return self._json({"error": "dashboard not built. Run: cd dashboard && npm install && npm run build"}, 503)
        rel = path.split("?")[0].lstrip("/") or "index.html"
        fp = os.path.join(DIST, rel)
        if not os.path.isfile(fp):
            fp = os.path.join(DIST, "index.html")  # SPA fallback
        ext = os.path.splitext(fp)[1]
        with open(fp, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"Dashboard API on http://localhost:{PORT}  (Ctrl+C to stop)")
    if not os.path.isdir(DIST):
        print("NOTE: frontend not built yet -> cd dashboard && npm install && npm run build")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
