# Deployment

**Backend:** Supabase Edge Function (Deno) + Postgres — **already deployed and live.**
**Frontend:** Vue/Vite static app — deploy on Vercel (or any static host).

## Live backend

- Function base URL: `https://qfggpxnpnaypoycmrcue.supabase.co/functions/v1/netfault`
- Endpoints: `GET /api/data`, `POST /api/run`, `POST /api/review`, `POST /api/config`
- Persistence: Postgres tables `reviews`, `ai_diagnoses`, `app_config` (RLS on; the function uses the service role).
- Case data + golden baseline are fetched live from this GitHub repo (`cases/`, `topology/golden.json`) and cached.
- The Gemini key is stored in `app_config` (server-side); the AI step reads it. You can also set/replace it from the app's **Settings** panel (writes to `app_config`).

Source of the function lives in the repo under `supabase/functions/netfault/` for reference.
Redeploy (if you edit it) with the Supabase CLI: `supabase functions deploy netfault --no-verify-jwt`.

## Frontend on Vercel

The frontend reads its backend URL from `VITE_API_BASE`, already set in [`dashboard/.env`](dashboard/.env)
to the live function — so a Vercel build works with no extra config.

1. Vercel → **New Project** → import `sahilkarande0918-cmd/CISCO-Project`.
2. **Root Directory:** `dashboard` · Framework **Vite** (auto) · Build `npm run build` · Output `dist`.
3. Deploy. (The `.env` value is picked up at build; to override, set `VITE_API_BASE` in Vercel env vars.)

Without any backend reachable, the app falls back to a bundled read-only snapshot and shows a banner.

## Local

Backend already runs in the cloud, so just the frontend:

```bash
cd dashboard && npm install && npm run dev
```

It uses `VITE_API_BASE` from `.env` (the live Supabase function). To run the **Python** backend
locally instead, unset `VITE_API_BASE` (or point it at `http://localhost:8000`) and run
`python src/dashboard_api.py` — or double-click `run_dashboard.bat`.

## Note on the AI free-tier quota

Gemini's free tier has a small daily request quota. Heavy testing during the build consumed it,
so the AI step currently has 7/12 cases cached; the remaining 5 show as **pending**. Click
**Run AI diagnosis** again after the quota resets (or add billing to the Gemini key / use Grok
via Settings) to complete all 12. The rule engine is unaffected (12/12) and everything else works.
