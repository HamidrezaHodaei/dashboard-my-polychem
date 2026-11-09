<!-- Monthly bar chart. `metric` switches rial / kg.
     * Every bar carries its own value ABOVE it (below it for a negative net month) -- nothing needs a
       hover to be read. Kilograms are printed as real kilograms.
     * The y-scale always contains zero and has head-room for the labels, so tall bars never push
       their number out of the chart and small / negative months are drawn to scale.
     * Many months: the chart keeps a minimum column width and scrolls sideways instead of squeezing.
     The native tooltip (title) still gives the full month detail for anyone who hovers. -->
<template>
  <div class="w-full overflow-x-auto pb-1" dir="ltr">
    <div class="flex" :style="{ minWidth: `${Math.max(data.length, 1) * columnMin}rem` }">
      <div class="relative flex-1">
        <!-- plot area -->
        <div class="relative" :style="{ height: `${PLOT_HEIGHT}px` }">
          <div
            v-for="g in gridLines"
            :key="g"
            class="absolute inset-x-0 border-t border-dashed border-border/60"
            :style="{ bottom: `${g}%` }"
          />
          <div class="absolute inset-x-0 border-t border-foreground/30" :style="{ bottom: `${zeroBottom}%` }" />

          <div class="absolute inset-0 flex">
            <div
              v-for="(row, i) in data"
              :key="`${row.year}-${row.month}`"
              class="relative flex-1"
              :title="tooltip(row)"
            >
              <!-- bar -->
              <div
                class="absolute left-1/2 w-[62%] max-w-14 -translate-x-1/2 transition-opacity hover:opacity-80"
                :class="rounded(values[i]!)"
                :style="barStyle(values[i]!)"
              />
              <!-- value label -->
              <div
                class="pointer-events-none absolute left-1/2 flex -translate-x-1/2 flex-col items-center text-center leading-tight"
                :style="labelStyle(values[i]!)"
              >
                <span class="text-[11px] font-semibold tabular-nums" :class="values[i]! < 0 ? 'text-destructive' : 'text-foreground'" dir="rtl">
                  {{ parts(values[i]!).num }}
                </span>
                <span class="whitespace-nowrap text-[9px] text-muted-foreground" dir="rtl">{{ parts(values[i]!).unit }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- month names -->
        <div class="flex border-t border-transparent pt-1.5">
          <div v-for="(row, i) in data" :key="`l-${row.year}-${row.month}`" class="min-w-0 flex-1 text-center" dir="rtl">
            <div class="truncate text-[11px] text-foreground/80">{{ row.short_label }}</div>
            <div v-if="showYear(i)" class="text-[10px] text-muted-foreground">{{ year(row.year) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CrmMonthRow } from '~/stores/crm'
import { CHART_COLORS, NEGATIVE_COLOR, chartLabelParts, faNum, formatKg, formatRial } from '~/utils/crm'

const props = defineProps<{ data: CrmMonthRow[], metric: 'amount' | 'quantity_kg' }>()

const PLOT_HEIGHT = 280
const LABEL_ROOM = 0.2 // share of the scale reserved above / below the tallest bar for its number

/** Minimum column width in rem -- full kilograms («۱۲٬۵۰۰٬۰۰۰») need more room than short rial words. */
const columnMin = computed(() => (props.metric === 'quantity_kg' ? 4.6 : 4))

const values = computed(() => props.data.map(d => Number(d[props.metric]) || 0))

// Scale: always includes 0, plus head-room on the side(s) that have bars so the labels fit.
const scale = computed(() => {
  const max = Math.max(0, ...values.value)
  const min = Math.min(0, ...values.value)
  const span = (max - min) || 1
  const top = max > 0 ? max + span * LABEL_ROOM : 0
  const bottom = min < 0 ? min - span * LABEL_ROOM : 0
  return { top, bottom, range: (top - bottom) || 1 }
})
const zeroBottom = computed(() => ((0 - scale.value.bottom) / scale.value.range) * 100)
const gridLines = computed(() => [25, 50, 75, 100].map(p => p).filter(p => Math.abs(p - zeroBottom.value) > 3))

function barStyle(v: number) {
  const h = (Math.abs(v) / scale.value.range) * 100
  const color = v < 0 ? NEGATIVE_COLOR : CHART_COLORS[0]
  // a month with a real value always gets a visible sliver
  const height = v === 0 ? 0 : Math.max(h, 0.8)
  return v >= 0
    ? { bottom: `${zeroBottom.value}%`, height: `${height}%`, background: color }
    : { top: `${100 - zeroBottom.value}%`, height: `${height}%`, background: color }
}
const rounded = (v: number) => (v >= 0 ? 'rounded-t-md' : 'rounded-b-md')

function labelStyle(v: number) {
  const h = (Math.abs(v) / scale.value.range) * 100
  return v >= 0
    ? { bottom: `calc(${zeroBottom.value + h}% + 3px)` }
    : { top: `calc(${100 - zeroBottom.value + h}% + 3px)` }
}

const parts = (v: number) => chartLabelParts(v, props.metric)

const year = (y: number) => faNum(y).replace(/٬/g, '')
// Show the year under the first month and wherever it changes (so a multi-year range is unambiguous).
const showYear = (i: number) => i === 0 || props.data[i - 1]?.year !== props.data[i]?.year

function tooltip(d: CrmMonthRow) {
  return `${d.label}\n${formatRial(d.amount)}\n${formatKg(d.quantity_kg)}\n${faNum(d.count)} سند`
}
</script>
