<!-- source: https://inspira-ui.com/docs/components/text/number-ticker (cn repointed local) -->
<script setup lang="ts">
import { cn } from "@/lib/utils";
import { TransitionPresets, useElementVisibility, useMediaQuery, useTransition } from "@vueuse/core";
import { computed, ref, watch } from "vue";

const reduce = useMediaQuery("(prefers-reduced-motion: reduce)");

type TransitionsPresetsKeys = keyof typeof TransitionPresets;

interface NumberTickerProps {
  value?: number;
  direction?: "up" | "down";
  duration?: number;
  delay?: number;
  decimalPlaces?: number;
  class?: string;
  transition?: TransitionsPresetsKeys;
}

const props = withDefaults(defineProps<NumberTickerProps>(), {
  value: 0,
  direction: "up",
  delay: 0,
  duration: 1000,
  decimalPlaces: 0,
  transition: "easeOutCubic",
});

const spanRef = ref<HTMLSpanElement>();
const transitionValue = ref(props.direction === "down" ? props.value : 0);
const transitionOutput = useTransition(transitionValue, {
  delay: props.delay,
  duration: props.duration,
  transition: TransitionPresets[props.transition],
});

const output = computed(() => {
  const v = reduce.value ? props.value : transitionOutput.value;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: props.decimalPlaces,
    maximumFractionDigits: props.decimalPlaces,
  }).format(Number(Number(v).toFixed(props.decimalPlaces)));
});

const isInView = useElementVisibility(spanRef, { threshold: 0 });
const hasBeenInView = ref(false);
const stop = watch(
  isInView,
  (v) => {
    if (v && !hasBeenInView.value) {
      hasBeenInView.value = true;
      transitionValue.value = props.direction === "down" ? 0 : props.value;
      stop();
    }
  },
  { immediate: true },
);
watch(
  () => props.value,
  (n) => {
    if (hasBeenInView.value) transitionValue.value = props.direction === "down" ? 0 : n;
  },
);
</script>

<template>
  <span ref="spanRef" :class="cn('inline-block tabular-nums tracking-wider', props.class)">
    {{ output }}
  </span>
</template>
