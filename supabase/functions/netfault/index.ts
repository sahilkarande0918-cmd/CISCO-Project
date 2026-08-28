// NetFault backend — Supabase Edge Function (Deno).
// Endpoints (matched by path suffix): GET /data, POST /run, POST /review, POST /config
// Case data + golden baseline are fetched from the GitHub repo (cached in memory).
import { createClient } from "jsr:@supabase/supabase-js@2";
import { diagnose } from "./rule.ts";

const RAW = "https://raw.githubusercontent.com/sahilkarande0918-cmd/CISCO-Project/main";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};
const json = (o: unknown, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { ...cors, "Content-Type": "application/json" } });

const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

const PROVIDERS: Record<string, [string, string]> = {
  gemini: ["https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.6-flash"],
  grok: ["https://api.x.ai/v1", "grok-2-latest"],
};
const FAULTS = ["duplicate_ip", "wrong_subnet_mask", "gateway_mismatch", "interface_down", "missing_vlan_assignment", "missing_route"];

let _bundle: { CASES: any[]; GOLDEN: any } | null = null;
async function getBundle() {
  if (_bundle) return _bundle;
  const cases = (await (await fetch(`${RAW}/cases/cases.json`)).json()).cases;
  const GOLDEN = await (await fetch(`${RAW}/topology/golden.json`)).json();
  const CASES = await Promise.all(cases.map(async (c: any) => ({
    id: c.id, symptom: c.symptom, fault_type: c.fault_type,
    evidence: await (await fetch(`${RAW}/${c.evidence_file}`)).text(),
  })));
  _bundle = { CASES, GOLDEN };
  return _bundle;
}

async function getConfig() {
  const { data } = await sb.from("app_config").select("*").eq("id", 1).maybeSingle();
  const provider = data?.provider || "gemini";
  const [base, defModel] = PROVIDERS[provider] || PROVIDERS.gemini;
  const model = data?.model || defModel;
  const key = data?.api_key || Deno.env.get("GEMINI_API_KEY") || Deno.env.get("AI_API_KEY") || "";
  return { provider, model, key, base };
}

const PROMPT = (symptom: string, evidence: string) =>
  `You are a network fault diagnosis assistant analysing Cisco Packet Tracer output.

Below is command output collected from one or more devices in a small enterprise
network (2 routers, a switch with VLANs 10/20/30, several PCs). Exactly ONE fault
has been injected. Identify it.

Reported symptom: ${symptom}

Evidence:
${evidence}

Respond with ONLY a JSON object, no prose, in exactly this shape:
{"fault_type": "<one of: ${FAULTS.join(", ")}>",
 "explanation": "<one or two sentences on what is wrong and why it causes the symptom>",
 "confidence": "<high|medium|low>",
 "recommended_fix": "<the specific Cisco IOS or PC config change to apply>"}`;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function aiDiagnose(evidence: string, symptom: string, cfg: any) {
  for (let t = 0; t < 4; t++) {
    const r = await fetch(`${cfg.base}/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${cfg.key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: cfg.model, temperature: 0, messages: [{ role: "user", content: PROMPT(symptom, evidence) }] }),
    });
    if (r.status === 429) { await sleep(3000 * (t + 1)); continue; } // rate limited — back off
    if (!r.ok) throw new Error(`AI ${r.status}: ${(await r.text()).slice(0, 160)}`);
    const text = (await r.json()).choices[0].message.content as string;
    const m = text.match(/\{[\s\S]*\}/);
    const d = m ? JSON.parse(m[0]) : { fault_type: "none", explanation: text, confidence: "low", recommended_fix: "" };
    return { ...d, model: cfg.model };
  }
  throw new Error("AI 429: rate limited after retries");
}

async function buildData() {
  const { CASES, GOLDEN } = await getBundle();
  const [aiRows, revRows, cfg] = await Promise.all([
    sb.from("ai_diagnoses").select("*"),
    sb.from("reviews").select("*"),
    getConfig(),
  ]);
  const ai: Record<string, any> = {};
  (aiRows.data || []).forEach((r: any) => (ai[r.case_id] = r));
  const rev: Record<string, any> = {};
  (revRows.data || []).forEach((r: any) => (rev[r.case_id] = r));

  const cases = CASES.map((c) => ({
    id: c.id, symptom: c.symptom, fault_type: c.fault_type, evidence: c.evidence,
    rule: diagnose(c.evidence, GOLDEN),
    ai: ai[c.id] ? { fault_type: ai[c.id].fault_type, explanation: ai[c.id].explanation, confidence: ai[c.id].confidence, recommended_fix: ai[c.id].recommended_fix, model: ai[c.id].model, engine: "ai", id: c.id } : null,
    review: rev[c.id] ? { id: c.id, decision: rev[c.id].decision, final_fault: rev[c.id].final_fault, note: rev[c.id].note, rule_fault: rev[c.id].rule_fault, ai_fault: rev[c.id].ai_fault, agree: rev[c.id].agree } : null,
  }));

  const n = cases.length;
  let ruleC = 0, aiC = 0, agree = 0;
  const disagreements: any[] = [];
  const decisions: Record<string, number> = {};
  const hasAi = Object.keys(ai).length > 0;
  for (const c of cases) {
    if (c.rule?.fault_type === c.fault_type) ruleC++;
    if (c.ai) {
      if (c.ai.fault_type === c.fault_type) aiC++;
      if (c.rule?.fault_type === c.ai.fault_type) agree++;
      else disagreements.push({ id: c.id, truth: c.fault_type, rule: c.rule?.fault_type, ai: c.ai.fault_type, human: c.review?.final_fault || "-" });
    }
    if (c.review) decisions[c.review.decision] = (decisions[c.review.decision] || 0) + 1;
  }
  const metrics = {
    cases: n,
    rule_accuracy: n ? +(ruleC / n).toFixed(3) : 0,
    ai_accuracy: hasAi ? +(aiC / n).toFixed(3) : null,
    agreement_rate: hasAi ? +(agree / n).toFixed(3) : null,
    disagreements, human_decisions: decisions,
  };
  return {
    metrics, cases,
    config: { provider: cfg.provider, model: cfg.model, key_set: !!cfg.key },
    status: { rule: true, ai: hasAi, review: Object.keys(rev).length > 0 },
  };
}

async function runStep(step: string) {
  const { CASES } = await getBundle();
  const lines: string[] = [];
  if (["generate", "all"].includes(step)) lines.push(`Cases loaded from repo: ${CASES.length}.`);
  if (["rule", "all", "metrics", "generate"].includes(step)) lines.push("Rule engine runs live on every load (deterministic).");
  if (["ai", "all"].includes(step)) {
    const cfg = await getConfig();
    if (!cfg.key) {
      lines.push("AI step skipped: no API key (set it in Settings).");
    } else {
      // throttle: small concurrent batches so we stay under the provider's per-minute limit
      const results: any[] = [];
      const B = 2;
      for (let i = 0; i < CASES.length; i += B) {
        const batch = await Promise.all(CASES.slice(i, i + B).map(async (c) => {
          try {
            const d = await aiDiagnose(c.evidence, c.symptom, cfg);
            return { case_id: c.id, fault_type: d.fault_type, explanation: d.explanation, confidence: d.confidence, recommended_fix: d.recommended_fix, model: d.model };
          } catch (e) {
            return { case_id: c.id, fault_type: "none", explanation: String(e), confidence: "low", recommended_fix: "", model: cfg.model };
          }
        }));
        results.push(...batch);
        if (i + B < CASES.length) await sleep(1500);
      }
      await sb.from("ai_diagnoses").upsert(results, { onConflict: "case_id" });
      results.forEach((r) => lines.push(`${r.case_id}: ${r.fault_type} (${r.confidence})`));
      lines.push(`Wrote ${results.length} AI diagnoses (provider=${cfg.provider}, model=${cfg.model}).`);
    }
  }
  return { ok: true, log: lines.join("\n"), data: await buildData() };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  const p = new URL(req.url).pathname;
  try {
    if (req.method === "GET" && p.endsWith("/data")) return json(await buildData());
    if (req.method === "POST" && p.endsWith("/run")) return json(await runStep((await req.json()).step || "all"));
    if (req.method === "POST" && p.endsWith("/review")) {
      const b = await req.json();
      await sb.from("reviews").upsert({
        case_id: b.id, decision: b.decision || "accepted", final_fault: b.final_fault || "",
        note: b.note || "", rule_fault: b.rule_fault || "", ai_fault: b.ai_fault || "", agree: !!b.agree,
      }, { onConflict: "case_id" });
      return json({ ok: true, data: await buildData() });
    }
    if (req.method === "POST" && p.endsWith("/config")) {
      const b = await req.json();
      const cur = (await sb.from("app_config").select("*").eq("id", 1).maybeSingle()).data || {};
      await sb.from("app_config").upsert({
        id: 1,
        provider: b.provider || cur.provider || "gemini",
        model: b.model || cur.model || null,
        api_key: b.api_key || cur.api_key || null,
      }, { onConflict: "id" });
      return json({ ok: true, config: (await buildData()).config });
    }
    return json({ error: "not found", path: p }, 404);
  } catch (e) {
    return json({ ok: false, error: String(e) }, 500);
  }
});
