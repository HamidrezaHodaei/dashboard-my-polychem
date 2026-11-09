<script setup lang="ts">
import { formatNumber } from '~/utils/financeFormat'

interface Series {
  name: string
  color: string // tailwind hex
  values: number[]
}

const props = withDefaults(defineProps<{
  categories: string[]
  series: Series[]
  type?: 'bar' | 'line'
  height?: number
}>(), {
  type: 'bar',
  height: 220,
})

const width = 640
const paddingLeft = 44
const paddingBottom = 28
const paddingTop = 12
const chartWidth = width - paddingLeft - 12
const chartHeight = computed(() => props.height - paddingTop - paddingBottom)

const maxValue = computed(() => {
  const all = props.series.flatMap((s) => s.values)
  const max = Math.max(1, ...all)
  // round up to a "nice" number for gridlines
  const magnitude = 10 ** Math.floor(Math.log10(max))
  return Math.ceil(max / magnitude) * magnitude
})

const yTicks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(maxValue.value * f)))

const xFor = (i: number) => paddingLeft + (chartWidth / Math.max(1, props.categories.length - (props.type === 'line' ? 1 : 0))) * i
const yFor = (v: number) => paddingTop + chartHeight.value - (v / maxValue.value) * chartHeight.value

function linePath(values: number[]) {
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(v)}`).join(' ')
}

const groupWidth = computed(() => chartWidth / props.categories.length)
const barSlotWidth = computed(() => groupWidth.value * 0.62)

function barX(catIndex: number, seriesIndex: number, seriesCount: number) {
  const groupStart = paddingLeft + groupWidth.value * catIndex + (groupWidth.value - barSlotWidth.value) / 2
  const barW = barSlotWidth.value / seriesCount
  return groupStart + barW * seriesIndex
}
function barWidth(seriesCount: number) {
  return barSlotWidth.value / seriesCount - 4
}
</script>

<template>
  <div>
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" :style="{ height: `${height}px` }">
      <!-- gridlines -->
      <g v-for="tick in yTicks" :key="tick">
        <line :x1="paddingLeft" :x2="width - 12" :y1="yFor(tick)" :y2="yFor(tick)" stroke="#E2E6ED" stroke-width="1" />
        <text :x="paddingLeft - 8" :y="yFor(tick) + 4" text-anchor="end" font-size="10" fill="#334073" opacity="0.55" class="num">
          {{ formatNumber(tick, false) }}
        </text>
      </g>

      <!-- bars -->
      <template v-if="type === 'bar'">
        <g v-for="(cat, ci) in categories" :key="cat">
          <rect
            v-for="(s, si) in series"
            :key="s.name"
            :x="barX(ci, si, series.length)"
            :y="yFor(s.values[ci])"
            :width="barWidth(series.length)"
            :height="Math.max(0, yFor(0) - yFor(s.values[ci]))"
            :fill="s.color"
            rx="3"
          />
        </g>
      </template>

      <!-- lines -->
      <template v-else>
        <path
          v-for="s in series"
          :key="s.name"
          :d="linePath(s.values)"
          fill="none"
          :stroke="s.color"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <g v-for="s in series" :key="`${s.name}-dots`">
          <circle v-for="(v, i) in s.values" :key="i" :cx="xFor(i)" :cy="yFor(v)" r="3" :fill="s.color" />
        </g>
      </template>

      <!-- x labels -->
      <text
        v-for="(cat, ci) in categories"
        :key="cat"
        :x="type === 'line' ? xFor(ci) : paddingLeft + groupWidth * ci + groupWidth / 2"
        :y="height - 8"
        text-anchor="middle"
        font-size="10.5"
        fill="#334073"
        opacity="0.7"
      >
        {{ cat }}
      </text>
    </svg>

    <div class="mt-2 flex flex-wrap items-center justify-center gap-4">
      <div v-for="s in series" :key="s.name" class="flex items-center gap-1.5 text-xs text-ink-700/70">
        <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: s.color }" />
        {{ s.name }}
      </div>
    </div>
  </div>
</template>
