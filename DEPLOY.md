# Deployment

Two supported layouts. The frontend already reads its API base from `VITE_API_BASE`
and falls back to a bundled read-only snapshot (`dashboard/public/demo-data.json`) when
no backend is reachable — so it is always viewable on its own.

| Layout | Frontend | Backend | Notes |
|--------|----------|---------|-------|
| **A. Unified (recommended)** | served by the backend | Hugging Face Space (Docker) | one URL, one deploy, real filesystem for review persistence |
| **B. Split** | Vercel (static) | Hugging Face Space (Docker) | frontend built with `VITE_API_BASE=<space-url>` pointing at the backend |

> Why not the backend on Vercel? It runs the pipeline (12 sequential AI calls) and writes
> `results/*.json` — Vercel's serverless functions are stateless and time-limited, so they
> can't host it. A container platform (Hugging Face Spaces, Railway, Fly, Render) is the fit.

---

## A. Unified — Hugging Face Space (Docker)

The repo root already has a multi-stage `Dockerfile` that builds the Vue app and serves it
together with the API. The container listens on port **7860** (Spaces default).

1. Create a new Space → **SDK: Docker** → **Blank**.
2. Push this repo to the Space (or duplicate from GitHub). The Space's `README.md` needs
   this frontmatter at the very top:

   ```yaml
   ---
   title: NetFault Console
   emoji: 🛰️
   colorFrom: blue
   colorTo: indigo
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```
3. In the Space **Settings → Variables and secrets**, add (optional, enables the AI step
   without using the in-app Settings panel):
   - Secret `GEMINI_API_KEY = <your key>`  (and `AI_PROVIDER = gemini`, or `grok` + `XAI_API_KEY`)
4. The Space builds the Dockerfile and boots. Open the Space URL → full interactive dashboard.

> Persistence note: the container filesystem resets on rebuild/restart, so `review_log.json`
> is per-session unless you attach Space **persistent storage** and point `results/` at it.
> Fine for a demo. If the key is set as a Space secret on a *public* Space, anyone can run
> the AI step on it — keep the Space private, or leave the key out and use the in-app Settings panel.

## Pushing to the Space

```bash
git remote add space https://huggingface.co/spaces/<user>/<space-name>
git push space main
```

(You authenticate with your Hugging Face access token when prompted.)

---

## B. Split — Vercel frontend + HF backend

1. Deploy the backend as in **A** (its URL is e.g. `https://<user>-<space>.hf.space`).
2. On Vercel, import the GitHub repo:
   - **Root Directory:** `dashboard`
   - **Framework:** Vite (auto-detected) · Build `npm run build` · Output `dist`
   - **Environment variable:** `VITE_API_BASE = https://<user>-<space>.hf.space`
3. Deploy. The Vercel URL is the live dashboard, talking to the HF backend (CORS is already open).

Without `VITE_API_BASE`, the Vercel build still shows the dashboard populated with the bundled
snapshot in read-only mode (a banner says so).

---

## Local (no deploy)

```bash
pip install -r requirements.txt
cd dashboard && npm install && npm run build && cd ..
python src/dashboard_api.py        # http://localhost:8000
```

Or double-click **run_dashboard.bat** (Windows).
