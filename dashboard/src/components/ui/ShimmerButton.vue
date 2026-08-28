<!-- source: https://inspira-ui.com/docs/components/buttons/shimmer-button (cn repointed local) -->
<script lang="ts" setup>
import { cn } from "@/lib/utils";
interface ShimmerButtonProps {
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  background?: string;
  class?: string;
}
withDefaults(defineProps<ShimmerButtonProps>(), {
  shimmerColor: "#ffffff",
  shimmerSize: "0.05em",
  shimmerDuration: "3s",
  borderRadius: "10px",
  background: "oklch(0.7 0.16 265)",
});
</script>

<template>
  <button
    :style="{
      '--spread': '90deg',
      '--shimmer-color': shimmerColor,
      '--radius': borderRadius,
      '--speed': shimmerDuration,
      '--cut': shimmerSize,
      '--bg': background,
    }"
    :class="
      cn(
        `group relative z-0 flex transform-gpu cursor-pointer items-center justify-center overflow-hidden [border-radius:var(--radius)] border border-white/10 px-5 py-2.5 whitespace-nowrap text-white transition-transform duration-300 ease-in-out [background:var(--bg)] active:translate-y-px`,
        $props.class,
      )
    "
  >
    <div class="absolute inset-0 -z-30 overflow-visible blur-[2px] [container-type:size]">
      <div class="animate-shimmer-slide absolute inset-0 aspect-square h-[100cqh] [mask:none]">
        <div
          class="animate-spin-around absolute -inset-full w-auto rotate-0 [translate:0_0] [background:conic-gradient(from_calc(270deg-(var(--spread)*0.5)),transparent_0,var(--shimmer-color)_var(--spread),transparent_var(--spread))]"
        />
      </div>
    </div>
    <slot />
    <div
      class="absolute size-full transform-gpu rounded-2xl px-4 py-1.5 text-sm font-medium shadow-[inset_0_-8px_10px_#ffffff1f] transition-all duration-300 ease-in-out group-hover:shadow-[inset_0_-6px_10px_#ffffff3f] group-active:shadow-[inset_0_-10px_10px_#ffffff3f]"
    />
    <div class="absolute inset-(--cut) -z-20 [border-radius:var(--radius)] [background:var(--bg)]" />
  </button>
</template>

<style scoped>
@keyframes shimmer-slide {
  to {
    transform: translate(calc(100cqw - 100%), 0);
  }
}
@keyframes spin-around {
  0% {
    transform: translateZ(0) rotate(0);
  }
  15%,
  35% {
    transform: translateZ(0) rotate(90deg);
  }
  65%,
  85% {
    transform: translateZ(0) rotate(270deg);
  }
  100% {
    transform: translateZ(0) rotate(360deg);
  }
}
.animate-shimmer-slide {
  animation: shimmer-slide var(--speed) ease-in-out infinite alternate;
}
.animate-spin-around {
  animation: spin-around calc(var(--speed) * 2) infinite linear;
}
</style>
