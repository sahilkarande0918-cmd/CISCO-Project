// API base: same-origin by default (unified deploy / dev proxy), overridable for a
// split deploy (frontend on Vercel, backend on a Hugging Face Space).
const BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

export const state = { demo: false }; // set true when no backend is reachable

async function req(path: string, opts?: RequestInit) {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

const NO_BACKEND = "No backend connected. This is a static snapshot — set VITE_API_BASE to a running backend (e.g. a Hugging Face Space) to run the pipeline and save reviews.";

export const api = {
  // read: fall back to the bundled snapshot so the dashboard is viewable with no backend
  async data() {
    try {
      const d = await req("/api/data");
      state.demo = false;
      return d;
    } catch {
      state.demo = true;
      return fetch("./demo-data.json").then((r) => r.json());
    }
  },
  run: (step: string, ids?: string[]) => {
    if (state.demo) return Promise.reject(new Error(NO_BACKEND));
    return req("/api/run", { method: "POST", body: JSON.stringify({ step, ids }) });
  },
  config: (c: Record<string, string>) => {
    if (state.demo) return Promise.reject(new Error(NO_BACKEND));
    return req("/api/config", { method: "POST", body: JSON.stringify(c) });
  },
  review: (r: Record<string, unknown>) => {
    if (state.demo) return Promise.reject(new Error(NO_BACKEND));
    return req("/api/review", { method: "POST", body: JSON.stringify(r) });
  },
};
