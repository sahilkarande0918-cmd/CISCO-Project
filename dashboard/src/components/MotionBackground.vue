<!-- Warm light backdrop: drifting terracotta/pine glows + faint grid, parallaxed on scroll. -->
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useMediaQuery } from "@vueuse/core";

const reduce = useMediaQuery("(prefers-reduced-motion: reduce)");
const y = ref(0);
let raf = 0;
function onScroll() {
  if (raf) return;
  raf = requestAnimationFrame(() => {
    y.value = window.scrollY || 0;
    raf = 0;
  });
}
onMounted(() => {
  if (!reduce.value) window.addEventListener("scroll", onScroll, { passive: true });
});
onUnmounted(() => window.removeEventListener("scroll", onScroll));
</script>

<template>
  <div class="mbg" aria-hidden="true">
    <div class="grid" :style="{ transform: `translateY(${y * 0.04}px)` }" />
    <div class="blob a" :style="{ transform: `translate3d(0, ${y * -0.08}px, 0)` }" />
    <div class="blob b" :style="{ transform: `translate3d(0, ${y * 0.12}px, 0)` }" />
    <div class="blob c" :style="{ transform: `translate3d(0, ${y * -0.05}px, 0)` }" />
    <div class="grain" />
  </div>
</template>

<style scoped>
.mbg {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
  background: var(--color-paper);
}

/* faint ink grid */
.grid {
  position: absolute;
  inset: -60px;
  background-image:
    linear-gradient(color-mix(in oklch, var(--color-ink) 5%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in oklch, var(--color-ink) 5%, transparent) 1px, transparent 1px);
  background-size: 54px 54px;
}

/* soft coloured light sources */
.blob {
  position: absolute;
  width: 58vw;
  height: 58vw;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
  will-change: transform;
}
.blob.a {
  top: -18%;
  left: -8%;
  background: radial-gradient(circle, color-mix(in oklch, var(--color-accent) 42%, transparent), transparent 62%);
  animation: breathe-a 20s ease-in-out infinite;
}
.blob.b {
  top: 20%;
  right: -14%;
  background: radial-gradient(circle, color-mix(in oklch, var(--color-accent-2) 40%, transparent), transparent 62%);
  animation: breathe-b 26s ease-in-out infinite;
}
.blob.c {
  bottom: -22%;
  left: 24%;
  background: radial-gradient(circle, color-mix(in oklch, var(--color-warn) 34%, transparent), transparent 62%);
  animation: breathe-a 30s ease-in-out infinite;
}

/* very light film grain / paper texture via a fine dotted overlay */
.grain {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(color-mix(in oklch, var(--color-ink) 6%, transparent) 0.5px, transparent 0.6px);
  background-size: 3px 3px;
  opacity: 0.35;
}

/* breathing changes only opacity/filter so it never fights the parallax transform */
@keyframes breathe-a {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.72; }
}
@keyframes breathe-b {
  0%, 100% { opacity: 0.42; }
  50% { opacity: 0.64; }
}

@media (prefers-reduced-motion: reduce) {
  .blob { animation: none; }
}
</style>
