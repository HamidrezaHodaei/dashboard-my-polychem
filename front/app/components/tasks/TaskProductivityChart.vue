<!-- Created vs completed work per Jalali month (grouped bars, numeric Y axis, values on the bars).
     Used as "Monthly Productivity Overview" on the dashboard and "Created vs. Completed Work" in analytics. -->
<template>
  <div class="w-full">
    <div
      class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground"
      dir="rtl"
    >
      <span class="flex items-center gap-1.5"><i
        class="inline-block size-2.5 rounded-sm"
        :style="{ background: CREATED }"
      /> ایجاد‌شده</span>
      <span class="flex items-center gap-1.5"><i
        class="inline-block size-2.5 rounded-sm"
        :style="{ background: COMPLETED }"
      /> تکمیل‌شده</span>
      <span class="flex items-center gap-1.5"><i
        class="inline-block h-0.5 w-4"
        :style="{ background: RATE }"
      /> نرخ بهره‌وری (٪ تکمیل از ایجاد)</span>
    </div>

    <div
      v-if="!hasData"
      class="flex h-48 items-center justify-center text-sm text-muted-foreground"
    >
      هنوز داده‌ای برای این بازه ثبت نشده است.
    </div>
    <svg
      v-else
      :viewBox="`0 0 ${W} ${H}`"
      class="h-auto w-full"
      dir="ltr"
      role="img"
      aria-label="نمودار ایجاد و تکمیل وظایف به تفکیک ماه"
    >
      <!-- grid + Y axis -->
      <g
        v-for="t in ticks"
        :key="t"
      >
        <line
          :x1="PAD_L"
          :x2="W - PAD_R"
          :y1="y(t)"
          :y2="y(t)"
          stroke="currentColor"
          stroke-opacity="0.12"
          stroke-dasharray="3 3"
        />
        <text
          :x="PAD_L - 8"
          :y="y(t) + 3"
          text-anchor="end"
          class="fill-muted-foreground"
          font-size="10"
        >{{ fa(t) }}</text>
      </g>
      <line
        :x1="PAD_L"
        :x2="PAD_L"
        :y1="PAD_T"
        :y2="H - PAD_B"
        stroke="currentColor"
        stroke-opacity="0.3"
      />

      <!-- bars -->
      <g
        v-for="(m, i) in points"
        :key="m.key"
      >
        <rect
          :x="groupX(i)"
          :y="y(m.created)"
          :width="barW"
          :height="Math.max(0, H - PAD_B - y(m.created))"
          :fill="CREATED"
          rx="3"
        >
          <title>{{ m.label }}: {{ fa(m.created) }} ایجاد‌شده</title>
        </rect>
        <rect
          :x="groupX(i) + barW + 3"
          :y="y(m.completed)"
          :width="barW"
          :height="Math.max(0, H - PAD_B - y(m.completed))"
          :fill="COMPLETED"
          rx="3"
        >
          <title>{{ m.label }}: {{ fa(m.completed) }} تکمیل‌شده</title>
        </rect>
        <text
          :x="groupX(i) + barW / 2"
          :y="y(m.created) - 4"
          text-anchor="middle"
          font-size="10"
          class="fill-foreground"
        >{{ m.created ? fa(m.created) : '' }}</text>
        <text
          :x="groupX(i) + barW * 1.5 + 3"
          :y="y(m.completed) - 4"
          text-anchor="middle"
          font-size="10"
          class="fill-foreground"
        >{{ m.completed ? fa(m.completed) : '' }}</text>
        <text
          :x="groupX(i) + barW + 1.5"
          :y="H - PAD_B + 16"
          text-anchor="middle"
          font-size="11"
          class="fill-foreground/80"
        >{{ m.label }}</text>
      </g>

      <!-- productivity-rate line (0-100 % on its own scale, right edge) -->
      <polyline
        v-if="ratePoints.length > 1"
        :points="ratePoints.map(p => `${p.x},${p.y}`).join(' ')"
        fill="none"
        :stroke="RATE"
        stroke-width="2"
        stroke-linejoin="round"
      />
      <g
        v-for="p in ratePoints"
        :key="p.key"
      >
        <circle
          :cx="p.x"
          :cy="p.y"
          r="3.5"
          :fill="RATE"
        >
          <title>{{ p.label }}: {{ fa(p.rate) }}٪</title>
        </circle>
      </g>
      <g
        v-for="t in [0, 50, 100]"
        :key="`r${t}`"
      >
        <text
          :x="W - PAD_R + 6"
          :y="yRate(t) + 3"
          font-size="10"
          class="fill-muted-foreground"
        >{{ fa(t) }}٪</text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import type { MonthPoint } from '~/utils/taskKpi'
import { toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ points: MonthPoint[] }>()

const CREATED = '#3b82f6'
const COMPLETED = '#10b981'
const RATE = '#f59e0b'
const W = 640
const H = 280
const PAD_L = 40
const PAD_R = 44
const PAD_T = 22
const PAD_B = 30

const fa = (n: number) => toPersianDigits(Math.round(n))
const hasData = computed(() => props.points.some(p => p.created || p.completed))

/** nice Y maximum + ticks (always whole numbers: these are task counts) */
const niceMax = computed(() => {
  const max = Math.max(1, ...props.points.flatMap(p => [p.created, p.completed]))
  const raw = max / 4
  const pow = 10 ** Math.floor(Math.log10(raw))
  const f = raw / pow
  const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow)
  return { step, top: Math.ceil(max / step) * step }
})
const ticks = computed(() => {
  const out: number[] = []
  for (let v = 0; v <= niceMax.value.top; v += niceMax.value.step) out.push(v)
  return out
})
const plotH = H - PAD_T - PAD_B
const y = (v: number) => PAD_T + plotH - (v / niceMax.value.top) * plotH
const yRate = (pct: number) => PAD_T + plotH - (pct / 100) * plotH

const slot = computed(() => (W - PAD_L - PAD_R) / Math.max(props.points.length, 1))
const barW = computed(() => Math.min(26, (slot.value - 16) / 2))
const groupX = (i: number) => PAD_L + slot.value * i + (slot.value - (barW.value * 2 + 3)) / 2

const ratePoints = computed(() =>
  props.points
    .map((p, i) => ({
      key: p.key,
      label: p.label,
      rate: p.created ? Math.min(100, (p.completed / p.created) * 100) : (p.completed ? 100 : 0),
      x: groupX(i) + barW.value + 1.5,
      y: 0,
    }))
    .filter((_, i) => props.points[i]!.created || props.points[i]!.completed)
    .map(p => ({ ...p, y: yRate(p.rate) })),
)
</script>
