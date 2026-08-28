<!-- Monochrome animated backdrop: pitch black + drifting grid, soft grey glow, slow scanline. -->
<template>
  <div class="mbg" aria-hidden="true">
    <div class="mbg-grid" />
    <div class="mbg-glow mbg-glow-a" />
    <div class="mbg-glow mbg-glow-b" />
    <div class="mbg-scan" />
    <div class="mbg-vignette" />
  </div>
</template>

<style scoped>
.mbg {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  background: #000;
  pointer-events: none;
}

/* faint engineering grid that slowly pans */
.mbg-grid {
  position: absolute;
  inset: -2px;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 46px 46px;
  animation: mbg-pan 26s linear infinite;
}

/* soft grey light-sources drifting behind content */
.mbg-glow {
  position: absolute;
  width: 60vw;
  height: 60vw;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.5;
}
.mbg-glow-a {
  top: -20%;
  left: 8%;
  background: radial-gradient(circle, rgba(200, 200, 200, 0.09), transparent 60%);
  animation: mbg-float-a 34s ease-in-out infinite;
}
.mbg-glow-b {
  bottom: -25%;
  right: 4%;
  background: radial-gradient(circle, rgba(160, 160, 160, 0.07), transparent 60%);
  animation: mbg-float-b 42s ease-in-out infinite;
}

/* a thin scanline sweeping top -> bottom, like an oscilloscope */
.mbg-scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 180px;
  background: linear-gradient(to bottom, transparent, rgba(255, 255, 255, 0.05), transparent);
  animation: mbg-scan 9s linear infinite;
}

/* keep edges dark so content stays legible */
.mbg-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 90% at 50% 0%, transparent 55%, rgba(0, 0, 0, 0.75) 100%);
}

@keyframes mbg-pan {
  to { transform: translate(46px, 46px); }
}
@keyframes mbg-float-a {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(6%, 8%) scale(1.12); }
}
@keyframes mbg-float-b {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-7%, -6%) scale(1.1); }
}
@keyframes mbg-scan {
  0% { transform: translateY(-200px); }
  100% { transform: translateY(100vh); }
}

@media (prefers-reduced-motion: reduce) {
  .mbg-grid, .mbg-glow, .mbg-scan { animation: none; }
  .mbg-scan { display: none; }
}
</style>
