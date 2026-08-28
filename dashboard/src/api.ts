// API base: same-origin by default (unified deploy / dev proxy), overridable for a
// split deploy (frontend on Vercel, backend on a Hugging Face Space).
const BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

async function req(path: string, opts?: RequestInit) {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  data: () => req("/api/data"),
  run: (step: string) => req("/api/run", { method: "POST", body: JSON.stringify({ step }) }),
  config: (c: Record<string, string>) =>
    req("/api/config", { method: "POST", body: JSON.stringify(c) }),
  review: (r: Record<string, unknown>) =>
    req("/api/review", { method: "POST", body: JSON.stringify(r) }),
};
