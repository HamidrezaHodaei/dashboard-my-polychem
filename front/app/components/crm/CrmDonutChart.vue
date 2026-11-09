<!-- Composition donut + a readable legend (name, value, share). Negative / zero rows (net returns)
     cannot be drawn as a slice, so they are listed in the legend only. -->
<template>
  <div class="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
    <div v-if="slices.length" class="shrink-0" dir="ltr">
      <VisSingleContainer :data="slices" :width="200" :height="200">
        <VisDonut
          :value="(d: Row) => d.value"
          :color="(_d: Row, i: number) => colorAt(i)"
          :arc-width="30"
          :pad-angle="0.02"
          :central-label="centralLabel"
          central-sub-label="مجموع"
        />
        <VisTooltip :triggers="{ [Donut.selectors.segment]: tooltip }" />
      </VisSingleContainer>
    </div>
    <p v-else class="w-full py-10 text-center text-sm text-muted-foreground">داده‌ای برای نمایش وجود ندارد.</p>

    <ul v-if="rows.length" class="w-full min-w-0 flex-1 space-y-1.5 text-sm">
      <li v-for="(r, i) in rows" :key="r.name + i" class="flex items-center gap-2" :title="`${r.name}: ${format(r.value)}`">
        <span class="size-2.5 shrink-0 rounded-full" :style="{ background: colorAt(i) }" />
        <span class="min-w-0 flex-1 truncate" dir="auto">{{ r.name }}</span>
        <span class="shrink-0 text-xs text-muted-foreground">{{ formatPercent(Math.max(r.value, 0), total) }}</span>
        <span class="shrink-0 font-medium" :class="r.value < 0 ? 'text-destructive' : ''" dir="auto">{{ format(r.value) }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { VisDonut, VisSingleContainer, VisTooltip } from '@unovis/vue'
import { Donut } from '@unovis/ts'
import type { CrmGroupRow } from '~/stores/crm'
import { colorAt, escapeHtml, formatKg, formatPercent, formatRial, formatRialCompact } from '~/utils/crm'

interface Row { name: string, value: number }

const props = defineProps<{ data: CrmGroupRow[], metric: 'amount' | 'quantity_kg' }>()

const rows = computed<Row[]>(() => props.data.map(r => ({ name: r.name, value: r[props.metric] })))
const slices = computed(() => rows.value.filter(r => r.value > 0))
const total = computed(() => slices.value.reduce((a, r) => a + r.value, 0))
const format = (v: number) => (props.metric === 'amount' ? formatRialCompact(v) : formatKg(v))
const centralLabel = computed(() => format(total.value))

function tooltip(d: { data: Row }) {
  const r = d.data
  const full = props.metric === 'amount' ? formatRial(r.value) : formatKg(r.value)
  return `<div dir="rtl" style="padding:.5rem .7rem;border-radius:.5rem;border:1px solid var(--border);background:var(--popover);color:var(--popover-foreground);box-shadow:0 4px 14px rgb(0 0 0/.12);font-size:.8rem;line-height:1.7">
    <div style="font-weight:600">${escapeHtml(r.name)}</div>
    <div>${full}</div>
    <div style="color:var(--muted-foreground)">${formatPercent(r.value, total.value)} از کل</div>
  </div>`
}
</script>
