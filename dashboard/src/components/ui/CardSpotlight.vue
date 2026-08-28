<!-- source: https://inspira-ui.com/docs/components/cards/card-spotlight (cn repointed local) -->
<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import { cn } from "@/lib/utils";
import { computed, onMounted, ref } from "vue";

const props = withDefaults(
  defineProps<{
    class?: HTMLAttributes["class"];
    slotClass?: HTMLAttributes["class"];
    gradientSize?: number;
    gradientColor?: string;
    gradientOpacity?: number;
  }>(),
  { class: "", slotClass: "", gradientSize: 240, gradientColor: "#3b3b6b", gradientOpacity: 0.55 },
);

const mouseX = ref(-props.gradientSize * 10);
const mouseY = ref(-props.gradientSize * 10);

function handleMouseMove(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  mouseX.value = e.clientX - rect.left;
  mouseY.value = e.clientY - rect.top;
}
function handleMouseLeave() {
  mouseX.value = -props.gradientSize * 10;
  mouseY.value = -props.gradientSize * 10;
}
onMounted(() => {
  mouseX.value = -props.gradientSize * 10;
  mouseY.value = -props.gradientSize * 10;
});

const backgroundStyle = computed(
  () =>
    `radial-gradient(circle at ${mouseX.value}px ${mouseY.value}px, ${props.gradientColor} 0%, rgba(0,0,0,0) 70%)`,
);
</script>

<template>
  <div
    :class="
      cn(
        'group relative flex size-full overflow-hidden rounded-xl border bg-card text-card-foreground',
        $props.class,
      )
    "
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <div :class="cn('relative z-10 w-full', props.slotClass)">
      <slot />
    </div>
    <div
      class="pointer-events-none absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      :style="{ background: backgroundStyle, opacity: gradientOpacity }"
    />
  </div>
</template>
