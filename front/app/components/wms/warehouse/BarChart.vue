<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" role="img" :aria-label="ariaLabel">
    <line
      v-for="g in 4" :key="g"
      :x1="padding" :x2="width - 8" :y1="chartTop + (g - 1) * (chartHeight / 3)" :y2="chartTop + (g - 1) * (chartHeight / 3)"
      stroke="currentColor" class="text-line" stroke-width="1"
    />
    <g v-for="(bar, i) in bars" :key="i">
      <rect
        :x="bar.x" :y="bar.y" :width="barWidth" :height="bar.h"
        rx="2" class="fill-amber-400 dark:fill-amber-500"
      />
      <text :x="bar.x + barWidth / 2" :y="height - 4" text-anchor="middle" class="fill-current text-ink-faint" font-size="9">
        {{ data[i].label }}
      </text>
    </g>
  </svg>
</template>

<script setup lang="ts">
const props = defineProps<{ data: { label: string; value: number }[]; ariaLabel?: string }>()

const width = 480
const height = 180
const padding = 8
const chartTop = 10
const chartHeight = height - 34

const maxVal = computed(() => Math.max(1, ...props.data.map((d) => d.value)))
const barWidth = computed(() => Math.min(36, (width - padding * 2) / props.data.length - 12))

const bars = computed(() =>
  props.data.map((d, i) => {
    const slot = (width - padding * 2) / props.data.length
    const h = (d.value / maxVal.value) * chartHeight
    return {
      x: padding + i * slot + (slot - barWidth.value) / 2,
      y: chartTop + chartHeight - h,
      h: Math.max(2, h)
    }
  })
)
</script>

