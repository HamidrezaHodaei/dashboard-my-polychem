<!-- <PurchasesLine :labels :series /> : line chart (SVG). Handles negative values (savings can be < 0); time runs right-to-left. -->
<template>
  <div dir="rtl">
    <div v-if="!labels.length" class="py-10 text-center text-sm text-muted-foreground">دادهٔ کافی برای نمایش وجود ندارد.</div>
    <template v-else>
      <div class="mb-3 flex flex-wrap gap-4 text-xs">
        <span v-for="s in series" :key="s.name" class="flex items-center gap-1.5">
          <span class="inline-block h-0.5 w-4" :style="{ background: s.color }" />{{ s.name }}
        </span>
      </div>
      <svg :viewBox="`0 0 ${W} ${H}`" class="h-48 w-full" preserveAspectRatio="none" role="img">
        <line v-for="g in grid" :key="g.y" :x1="PAD" :x2="W - PAD" :y1="g.y" :y2="g.y" stroke="currentColor" class="text-border" stroke-width="1" vector-effect="non-scaling-stroke" />
        <line v-if="zeroY !== null" :x1="PAD" :x2="W - PAD" :y1="zeroY" :y2="zeroY" stroke="currentColor" class="text-muted-foreground" stroke-dasharray="4 3" vector-effect="non-scaling-stroke" />
        <g v-for="s in lines" :key="s.name">
          <polyline v-if="s.points.length > 1" :points="s.points.map(p => `${p.x},${p.y}`).join(' ')" fill="none" :stroke="s.color" stroke-width="2" vector-effect="non-scaling-stroke" />
          <circle v-for="p in s.points" :key="p.i" :cx="p.x" :cy="p.y" r="3" :fill="s.color">
            <title>{{ s.name }} — {{ labels[p.i] }}: {{ money(p.v) }}</title>
          </circle>
        </g>
      </svg>
      <div class="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>{{ labels[0] }}</span><span v-if="labels.length > 2">{{ labels[Math.floor(labels.length / 2)] }}</span><span>{{ labels[labels.length - 1] }}</span>
      </div>
      <p class="mt-1 text-[11px] text-muted-foreground">بیشینه: {{ money(hi) }}<template v-if="lo < 0"> — کمینه: {{ money(lo) }}</template></p>
    </template>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ labels: string[], series: { name: string, color: string, values: (number | null)[] }[] }>()
const W = 600
const H = 180
const PAD = 8
const all = computed(() => props.series.flatMap(s => s.values.filter((v): v is number => v !== null)))
const hi = computed(() => Math.max(0, ...all.value))
const lo = computed(() => Math.min(0, ...all.value))
const span = computed(() => (hi.value - lo.value) || 1)
const y = (v: number) => PAD + (1 - (v - lo.value) / span.value) * (H - 2 * PAD)
const x = (i: number) => (props.labels.length <= 1 ? W / 2 : W - PAD - (i * (W - 2 * PAD)) / (props.labels.length - 1)) // first period on the right
const zeroY = computed(() => (lo.value < 0 ? y(0) : null))
const grid = computed(() => [0, 0.25, 0.5, 0.75, 1].map(t => ({ y: PAD + t * (H - 2 * PAD) })))
const lines = computed(() => props.series.map(s => ({
  ...s, points: s.values.map((v, i) => (v === null ? null : { i, v, x: x(i), y: y(v) })).filter((p): p is { i: number, v: number, x: number, y: number } => p !== null),
})))
</script>
