<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { api, state as apiState } from "@/api";
import NumberTicker from "@/components/ui/NumberTicker.vue";
import BorderBeam from "@/components/ui/BorderBeam.vue";
import CardSpotlight from "@/components/ui/CardSpotlight.vue";
import ShimmerButton from "@/components/ui/ShimmerButton.vue";
import MotionBackground from "@/components/MotionBackground.vue";
import { IconNode, IconGear, IconPlay, IconClose, IconCheck, IconAlert } from "@/components/icons";

const FAULTS = [
  "duplicate_ip", "wrong_subnet_mask", "gateway_mismatch",
  "interface_down", "missing_vlan_assignment", "missing_route",
];

const reduced = useMediaQuery("(prefers-reduced-motion: reduce)");
const motion = computed(() => !reduced.value);

const data = ref<any>(null);
const loading = ref(true);
const running = ref("");
const log = ref("");
const showLog = ref(false);
const showSettings = ref(false);
const selected = ref<any>(null);
const editFault = ref("");
const note = ref("");
const cfg = ref({ provider: "gemini", model: "", api_key: "" });
const demo = ref(false);
const aiRunning = ref(false);
const aiDone = ref(0);
const aiTotal = ref(0);
const diagnosing = ref<Set<string>>(new Set());
const isDiag = (id: string) => diagnosing.value.has(id);

const metrics = computed<any>(() => data.value?.metrics ?? {});
const cases = computed<any[]>(() => data.value?.cases ?? []);
const conf = computed<any>(() => data.value?.config ?? {});
const n = computed(() => metrics.value.cases ?? cases.value.length ?? 0);
const rulePct = computed(() => Math.round((metrics.value.rule_accuracy ?? 0) * 100));
// AI + agreement are scored over the cases actually diagnosed (attempted),
// so pending cases (e.g. AI quota not yet run) don't drag the number down.
const aiValid = (c: any) => c.ai && c.ai.fault_type !== "error" && c.ai.fault_type !== "none";
const aiAttempted = computed(() => cases.value.filter(aiValid).length);
const aiCorrect = computed(() => cases.value.filter((c) => aiValid(c) && c.ai.fault_type === c.fault_type).length);
const aiPct = computed(() => (aiAttempted.value ? Math.round((aiCorrect.value / aiAttempted.value) * 100) : null));
const agreeCount = computed(() => cases.value.filter((c) => aiValid(c) && c.rule && c.rule.fault_type === c.ai.fault_type).length);
const agreePct = computed(() => (aiAttempted.value ? Math.round((agreeCount.value / aiAttempted.value) * 100) : null));
const conflicts = computed(() => aiAttempted.value - agreeCount.value);
const reviewed = computed(() => cases.value.filter((c) => c.review).length);
const reviewedPct = computed(() => (n.value ? Math.round((reviewed.value / n.value) * 100) : 0));
const disagreements = computed(() => conflicts.value);

const gauges = computed(() => [
  { label: "rule accuracy", val: rulePct.value, unit: "%", tone: "ok", sub: `${Math.round((rulePct.value / 100) * n.value)}/${n.value}` },
  { label: "ai accuracy", val: aiPct.value, unit: "%", tone: "accent", sub: aiPct.value == null ? "run step 3" : `${aiCorrect.value}/${aiAttempted.value}${aiAttempted.value < n.value ? " · " + (n.value - aiAttempted.value) + " pending" : ""}` },
  { label: "rule↔ai agreement", val: agreePct.value, unit: "%", tone: "accent", sub: agreePct.value == null ? "awaiting ai" : `${conflicts.value} conflicts / ${aiAttempted.value}` },
  { label: "human reviewed", val: reviewed.value, unit: "", tone: "warn", sub: `${reviewedPct.value}% of ${n.value}`, raw: reviewedPct.value },
]);

async function refresh() {
  data.value = await api.data();
  demo.value = apiState.demo;
  if (data.value?.config) {
    cfg.value.provider = data.value.config.provider;
    cfg.value.model = data.value.config.model;
  }
}
onMounted(async () => {
  try { await refresh(); } finally { loading.value = false; }
});

async function run(step: string) {
  if (step === "ai" || step === "all") return runAi(step);
  running.value = step;
  try {
    const res = await api.run(step);
    log.value = res.log || "(no output)";
    data.value = res.data;
    demo.value = apiState.demo;
    showLog.value = true;
  } catch (e: any) {
    log.value = "ERROR: " + e.message;
    showLog.value = true;
  } finally {
    running.value = "";
  }
}

// Diagnose case-by-case (small chunks) so the grid fills in live with progress.
async function runAi(step: string) {
  let targets = cases.value.filter((c) => !aiValid(c)).map((c) => c.id);
  if (!targets.length) targets = cases.value.map((c) => c.id); // all done -> refresh all
  running.value = step;
  aiRunning.value = true;
  aiTotal.value = targets.length;
  aiDone.value = 0;
  const logs: string[] = [];
  const CH = 2;
  try {
    for (let i = 0; i < targets.length; i += CH) {
      const chunk = targets.slice(i, i + CH);
      diagnosing.value = new Set(chunk);
      try {
        const res = await api.run("ai", chunk);
        data.value = res.data;
        demo.value = apiState.demo;
        if (res.log) logs.push(res.log);
      } catch (e: any) {
        logs.push("ERROR on " + chunk.join(", ") + ": " + e.message);
      }
      aiDone.value = Math.min(targets.length, i + chunk.length);
    }
    log.value = logs.join("\n") || "(no output)";
    showLog.value = true;
  } finally {
    diagnosing.value = new Set();
    aiRunning.value = false;
    running.value = "";
  }
}

async function saveConfig() {
  await api.config({ provider: cfg.value.provider, model: cfg.value.model, api_key: cfg.value.api_key });
  cfg.value.api_key = "";
  showSettings.value = false;
  await refresh();
}

const okc = (c: any, e: "rule" | "ai") => c[e] && c[e].fault_type === c.fault_type;

function openCase(c: any) {
  selected.value = c;
  editFault.value = c.ai?.fault_type || c.rule?.fault_type || FAULTS[0];
  note.value = c.review?.note || "";
}

async function review(decision: string) {
  const c = selected.value;
  const final =
    decision === "rejected" ? c.rule?.fault_type
      : decision === "edited" ? editFault.value
      : c.ai?.fault_type || c.rule?.fault_type;
  await api.review({
    id: c.id, decision, final_fault: final, note: note.value,
    rule_fault: c.rule?.fault_type || "", ai_fault: c.ai?.fault_type || "",
    agree: (c.rule?.fault_type || "") === (c.ai?.fault_type || ""),
  });
  await refresh();
  selected.value = cases.value.find((x) => x.id === c.id) || null;
}

const STEPS = [
  { key: "generate", n: "01", label: "generate cases", need: () => true },
  { key: "rule", n: "02", label: "rule engine", need: () => data.value?.status?.rule },
  { key: "ai", n: "03", label: "ai diagnosis", need: () => data.value?.status?.ai },
  { key: "metrics", n: "04", label: "metrics", need: () => true },
];
</script>

<template>
  <div>
    <MotionBackground />
    <!-- command bar -->
    <header class="sticky top-0 z-40 border-b bg-paper/85 backdrop-blur">
      <div class="mx-auto flex max-w-[1200px] items-center gap-3 px-5 py-3">
        <span class="grid size-8 place-items-center rounded-md border border-line-bright text-accent">
          <IconNode />
        </span>
        <div class="leading-none">
          <span class="font-display text-[19px] font-semibold tracking-tight text-ink">FaultLine</span>
          <span class="ml-1.5 font-mono text-[11px] text-faint">console</span>
        </div>
        <span class="mx-1 hidden text-line-bright sm:inline">/</span>
        <span class="hidden font-mono text-[11px] text-muted sm:inline">
          hybrid fault diagnosis · packet tracer
        </span>
        <div class="ml-auto flex items-center gap-2">
          <span class="flex items-center gap-2 rounded-md border border-line-bright bg-panel px-2.5 py-1.5 font-mono text-[11px]">
            <span class="size-1.5 rounded-full pulse"
              :class="conf.key_set ? 'bg-ok text-ok' : 'bg-bad text-bad'" />
            {{ conf.provider }}<span class="text-faint">·</span>{{ conf.key_set ? "key ok" : "no key" }}
          </span>
          <button
            class="grid size-[34px] place-items-center rounded-md border border-line-bright bg-panel text-muted transition hover:text-accent"
            @click="showSettings = !showSettings" aria-label="settings">
            <IconGear />
          </button>
        </div>
      </div>
    </header>

    <div v-if="demo" class="border-b border-warn/25 bg-warn/[0.07]">
      <div class="mx-auto flex max-w-[1200px] items-center gap-2 px-5 py-2 font-mono text-[11px] text-warn">
        <IconAlert /> read-only snapshot · no backend connected — deploy the API (Hugging Face Space) and set VITE_API_BASE for live runs
      </div>
    </div>

    <main class="mx-auto max-w-[1200px] px-5 pb-20">
      <!-- settings -->
      <transition name="fade">
        <div v-if="showSettings" class="mt-4 rounded-lg border bg-panel p-4">
          <div class="grid gap-3 md:grid-cols-4">
            <label class="text-sm">
              <span class="mb-1 block font-mono text-[11px] text-muted">provider</span>
              <select v-model="cfg.provider" class="w-full rounded-md border bg-panel-2 px-3 py-2 text-sm">
                <option value="gemini">gemini</option>
                <option value="grok">grok</option>
              </select>
            </label>
            <label class="text-sm">
              <span class="mb-1 block font-mono text-[11px] text-muted">model (optional)</span>
              <input v-model="cfg.model" placeholder="gemini-3.6-flash"
                class="w-full rounded-md border bg-panel-2 px-3 py-2 font-mono text-sm" />
            </label>
            <label class="text-sm md:col-span-2">
              <span class="mb-1 block font-mono text-[11px] text-muted">api key · held in server memory, never written to disk</span>
              <input v-model="cfg.api_key" type="password" placeholder="paste key…"
                class="w-full rounded-md border bg-panel-2 px-3 py-2 font-mono text-sm" />
            </label>
          </div>
          <div class="mt-3 flex justify-end">
            <button class="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink" @click="saveConfig">
              save config
            </button>
          </div>
        </div>
      </transition>

      <!-- title -->
      <section class="pt-10 pb-8">
        <h1 class="font-display max-w-3xl text-[2.1rem] leading-[1.08] font-medium tracking-tight md:text-[3.1rem]">
          Diagnose network faults with a rule engine and AI,
          <span class="text-accent">judged by a human.</span>
        </h1>
        <p class="mt-4 max-w-2xl text-[15px] text-muted">
          Two independent engines read the same Packet Tracer evidence. You adjudicate every call.
          Run the whole pipeline below — no terminal required.
        </p>
      </section>

      <!-- command deck -->
      <section class="ticked lift relative overflow-hidden rounded-lg border bg-panel p-4">
        <BorderBeam v-if="motion && running" :duration="6000" :border-width="1.5" />
        <div class="flex flex-wrap items-center gap-3">
          <ShimmerButton
            background="oklch(0.55 0.155 38)" shimmer-color="#fff3e6" border-radius="8px"
            class="border-white/20! disabled:opacity-60" @click="run('all')">
            <span class="flex items-center gap-2 text-sm font-semibold text-white">
              <span v-if="aiRunning" class="spinner" />
              <IconPlay v-else class="text-white" />
              {{ aiRunning ? `diagnosing… ${aiDone}/${aiTotal}` : "Run full pipeline" }}
            </span>
          </ShimmerButton>

          <div class="flex flex-wrap items-center gap-2">
            <button v-for="s in STEPS" :key="s.key" :disabled="!!running" @click="run(s.key)"
              class="group flex items-center gap-2 rounded-md border border-line-bright bg-panel-2 px-3 py-2 text-left transition hover:border-accent/60 disabled:opacity-50">
              <span class="font-mono text-[11px]"
                :class="running === s.key ? 'text-accent' : s.need() ? 'text-ok' : 'text-faint'">
                {{ running === s.key ? "··" : s.need() ? "✓" : s.n }}
              </span>
              <span class="text-[13px] text-ink/90">{{ s.label }}</span>
            </button>
          </div>

          <span class="ml-auto flex items-center gap-2 font-mono text-[11px] text-muted">
            <span class="size-1.5 rounded-full pulse" :class="running ? 'bg-accent text-accent' : 'bg-ok text-ok'" />
            {{ aiRunning ? `DIAGNOSING ${aiDone}/${aiTotal}` : running ? "PROCESSING" : "IDLE" }} · {{ n }} cases
          </span>
        </div>

        <!-- live progress bar with moving sheen -->
        <div v-if="aiRunning" class="mt-3">
          <div class="bar-sheen h-1.5 w-full overflow-hidden rounded-full bg-panel-2">
            <div class="h-full rounded-full bg-accent transition-all duration-300"
              :style="{ width: (aiTotal ? (aiDone / aiTotal) * 100 : 0) + '%' }" />
          </div>
        </div>
      </section>

      <!-- metrics instrument -->
      <section class="lift mt-4 grid grid-cols-2 divide-line overflow-hidden rounded-lg border bg-panel md:grid-cols-4 md:divide-x">
        <div v-for="(g, i) in gauges" :key="g.label"
          class="reveal border-t border-line px-5 py-5 md:border-t-0" :style="{ animationDelay: motion ? i * 60 + 'ms' : '0ms' }">
          <p class="font-mono text-[11px] tracking-wide text-muted">{{ g.label }}</p>
          <p class="mt-2 font-mono text-[34px] leading-none font-semibold"
            :class="{ 'text-ok': g.tone==='ok', 'text-accent': g.tone==='accent', 'text-warn': g.tone==='warn' }">
            <template v-if="g.val == null"><span class="text-faint">––</span></template>
            <template v-else><NumberTicker :value="g.val" />{{ g.unit }}</template>
          </p>
          <div class="mt-3 h-1 w-full overflow-hidden rounded-full bg-panel-2">
            <div class="h-full rounded-full transition-all duration-700"
              :class="{ 'bg-ok': g.tone==='ok', 'bg-accent': g.tone==='accent', 'bg-warn': g.tone==='warn' }"
              :style="{ width: (g.raw ?? g.val ?? 0) + '%' }" />
          </div>
          <p class="mt-2 font-mono text-[11px] text-faint">{{ g.sub }}</p>
        </div>
      </section>

      <!-- disagreement flag -->
      <div v-if="disagreements" class="mt-4 flex items-center gap-2 rounded-md border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-warn">
        <IconAlert /> {{ disagreements }} case(s) where the engines disagree — open them to adjudicate.
      </div>

      <!-- cases console -->
      <section class="mt-6">
        <div class="mb-2 flex items-baseline justify-between">
          <h2 class="font-mono text-[12px] tracking-wide text-muted">FAULT&nbsp;CASES</h2>
          <span class="font-mono text-[11px] text-faint">{{ reviewed }}/{{ n }} reviewed</span>
        </div>

        <div class="lift relative overflow-hidden rounded-lg border bg-panel">
          <div v-if="aiRunning" class="scanline" />
          <div class="hidden grid-cols-[70px_1fr_190px_190px_110px] gap-3 border-b bg-panel-2 px-4 py-2 font-mono text-[11px] text-faint md:grid">
            <span>case</span><span>symptom</span><span>rule engine</span><span>ai engine</span><span>review</span>
          </div>
          <div v-if="loading" class="px-4 py-10 text-center font-mono text-sm text-muted">loading…</div>
          <button v-for="(c, i) in cases" :key="c.id" @click="openCase(c)"
            class="reveal relative grid w-full grid-cols-1 gap-2 border-b border-line/70 px-4 py-3 text-left transition last:border-b-0 hover:bg-panel-2 md:grid-cols-[70px_1fr_190px_190px_110px] md:items-center md:gap-3"
            :class="{ 'diag-row': isDiag(c.id) }"
            :style="{ animationDelay: motion ? Math.min(i, 12) * 35 + 'ms' : '0ms' }">
            <span class="font-mono text-[12px] text-accent">{{ c.id.replace('case', '#') }}</span>
            <span class="truncate text-[13px] text-ink/90">{{ c.symptom }}</span>
            <span class="flex items-center gap-2">
              <span class="size-1.5 rounded-full" :class="c.rule ? (okc(c,'rule') ? 'bg-ok' : 'bg-bad') : 'bg-faint'" />
              <span class="font-mono text-[12px]">{{ c.rule?.fault_type ?? '—' }}</span>
            </span>
            <span class="flex items-center gap-2">
              <template v-if="isDiag(c.id)">
                <span class="size-1.5 rounded-full bg-accent pulse" />
                <span class="font-mono text-[12px] text-accent">diagnosing…</span>
              </template>
              <template v-else-if="!c.ai">
                <span class="size-1.5 rounded-full bg-faint" />
                <span class="font-mono text-[12px] text-faint">pending</span>
              </template>
              <template v-else-if="c.ai.fault_type === 'error' || c.ai.fault_type === 'none'">
                <span class="size-1.5 rounded-full bg-warn" />
                <span class="font-mono text-[12px] text-warn">n/a</span>
              </template>
              <template v-else>
                <span class="size-1.5 rounded-full" :class="okc(c,'ai') ? 'bg-ok' : 'bg-bad'" />
                <span class="font-mono text-[12px]">{{ c.ai.fault_type }}</span>
              </template>
            </span>
            <span>
              <span v-if="c.review" class="rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                :class="{
                  'bg-ok/15 text-ok': c.review.decision==='accepted',
                  'bg-accent/15 text-accent': c.review.decision==='edited',
                  'bg-warn/15 text-warn': c.review.decision==='rejected',
                }">{{ c.review.decision }}</span>
              <span v-else class="font-mono text-[11px] text-faint">pending</span>
            </span>
          </button>
        </div>
      </section>

      <!-- log -->
      <section v-if="log" class="mt-5">
        <button class="flex items-center gap-2 font-mono text-[12px] text-muted transition hover:text-accent" @click="showLog=!showLog">
          <span class="text-accent">{{ showLog ? '▾' : '▸' }}</span> pipeline_output.log
        </button>
        <pre v-if="showLog"
          class="mt-2 max-h-72 overflow-auto rounded-lg border bg-panel px-4 py-3 font-mono text-[11.5px] leading-relaxed text-muted">{{ log }}</pre>
      </section>

      <!-- footer -->
      <footer class="mt-24 border-t pt-8 pb-6">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p class="font-display text-xl text-ink">FaultLine</p>
            <p class="mt-1 text-[13px] text-muted">
              AI-assisted network fault diagnosis &amp; remediation · Cisco internship project
            </p>
          </div>
          <p class="font-mono text-[11px] text-faint">
            Sahil Karande · Avinash Borkar · Pranav Shripannavar
          </p>
        </div>
      </footer>
    </main>

    <!-- inspector -->
    <transition name="drawer">
      <div v-if="selected" class="fixed inset-0 z-50 flex justify-end bg-black/55" @click.self="selected=null">
        <CardSpotlight class="h-full w-full max-w-xl overflow-auto rounded-none border-l bg-panel! p-0" gradient-color="#efe3d2">
          <div class="border-b p-5">
            <div class="flex items-start justify-between gap-4">
              <div>
                <span class="font-mono text-[12px] text-accent">{{ selected.id.replace('case','#') }}</span>
                <h3 class="mt-1 text-lg leading-snug font-semibold">{{ selected.symptom }}</h3>
                <p class="mt-2 font-mono text-[11px] text-muted">
                  injected fault → <span class="text-ink">{{ selected.fault_type }}</span>
                </p>
              </div>
              <button class="grid size-8 place-items-center rounded-md border border-line-bright text-muted transition hover:text-accent"
                @click="selected=null"><IconClose /></button>
            </div>
          </div>

          <div class="grid gap-3 p-5 md:grid-cols-2">
            <div class="rounded-md border bg-panel-2 p-3">
              <div class="mb-1 flex items-center gap-2">
                <span class="size-1.5 rounded-full" :class="selected.rule ? (okc(selected,'rule')?'bg-ok':'bg-bad') : 'bg-faint'" />
                <p class="font-mono text-[11px] text-muted">rule engine</p>
              </div>
              <p class="font-mono text-sm">{{ selected.rule?.fault_type ?? '—' }}</p>
              <p class="mt-1 text-[12px] text-muted">{{ selected.rule?.recommended_fix }}</p>
            </div>
            <div class="rounded-md border bg-panel-2 p-3">
              <div class="mb-1 flex items-center gap-2">
                <span class="size-1.5 rounded-full" :class="selected.ai ? (okc(selected,'ai')?'bg-ok':'bg-bad') : 'bg-faint'" />
                <p class="font-mono text-[11px] text-muted">ai engine</p>
              </div>
              <p class="font-mono text-sm">{{ selected.ai?.fault_type ?? '—' }}</p>
              <p class="mt-1 text-[12px] text-muted">{{ selected.ai?.explanation }}</p>
              <p v-if="selected.ai?.recommended_fix" class="mt-1 text-[12px] text-faint">
                fix · {{ selected.ai.recommended_fix }}
              </p>
            </div>
          </div>

          <div class="px-5">
            <details class="rounded-md border bg-panel-2">
              <summary class="cursor-pointer px-3 py-2 font-mono text-[12px] text-muted select-none">▸ evidence capture</summary>
              <pre class="max-h-72 overflow-auto border-t px-3 py-3 font-mono text-[11px] leading-relaxed text-muted">{{ selected.evidence }}</pre>
            </details>
          </div>

          <!-- human review -->
          <div class="m-5 rounded-md border border-accent/25 bg-accent/[0.06] p-4">
            <p class="mb-3 flex items-center gap-2 font-mono text-[11px] tracking-wide text-accent">
              <span class="size-1.5 rounded-full bg-accent pulse" /> HUMAN REVIEW
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <button class="flex items-center gap-1.5 rounded-md bg-ok/15 px-3 py-1.5 text-sm text-ok transition hover:bg-ok/25"
                @click="review('accepted')"><IconCheck /> Accept AI</button>
              <div class="flex items-center overflow-hidden rounded-md border border-line-bright">
                <select v-model="editFault" class="bg-panel-2 px-2 py-1.5 font-mono text-[12px]">
                  <option v-for="f in FAULTS" :key="f" :value="f">{{ f }}</option>
                </select>
                <button class="bg-accent/15 px-3 py-1.5 text-sm text-accent transition hover:bg-accent/25" @click="review('edited')">Edit</button>
              </div>
              <button class="rounded-md bg-warn/15 px-3 py-1.5 text-sm text-warn transition hover:bg-warn/25" @click="review('rejected')">
                Reject → rule
              </button>
            </div>
            <input v-model="note" placeholder="note (optional)…"
              class="mt-3 w-full rounded-md border bg-panel-2 px-3 py-2 text-sm" />
            <p v-if="selected.review" class="mt-2 font-mono text-[11px] text-muted">
              logged · <span class="text-ink">{{ selected.review.decision }} → {{ selected.review.final_fault }}</span>
            </p>
          </div>
        </CardSpotlight>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-active :deep(.max-w-xl), .drawer-leave-active :deep(.max-w-xl) { transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1); }
.drawer-enter-from :deep(.max-w-xl), .drawer-leave-to :deep(.max-w-xl) { transform: translateX(100%); }
@media (prefers-reduced-motion: reduce) {
  .drawer-enter-active :deep(.max-w-xl), .drawer-leave-active :deep(.max-w-xl) { transition: none; }
}
</style>
