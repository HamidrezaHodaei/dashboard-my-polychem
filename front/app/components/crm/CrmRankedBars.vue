<!-- Ranked horizontal bars (customers, provinces, industries). Plain HTML so long Persian names
     stay readable; hover (title) shows the exact figure. -->
<template>
  <ul v-if="items.length" class="space-y-3">
    <li v-for="(r, i) in items" :key="r.name + i" :title="`${r.name}: ${format(r.value)}`">
      <div class="mb-1 flex items-center justify-between gap-3 text-sm">
        <span class="min-w-0 truncate" dir="auto">{{ r.name }}</span>
        <span class="shrink-0 font-medium" :class="r.value < 0 ? 'text-destructive' : ''" dir="auto">{{ format(r.value) }}</span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-muted" role="presentation">
        <div
          class="h-full rounded-full transition-[width] duration-500"
          :style="{ width: `${Math.max(2, (Math.abs(r.value) / max) * 100)}%`, background: r.value < 0 ? NEGATIVE_COLOR : colorAt(i) }"
        />
      </div>
    </li>
  </ul>
  <p v-else class="py-10 text-center text-sm text-muted-foreground">داده‌ای برای نمایش وجود ندارد.</p>
</template>

<script setup lang="ts">
import type { CrmGroupRow } from '~/stores/crm'
import { NEGATIVE_COLOR, colorAt, formatKg, formatRialCompact } from '~/utils/crm'

const props = defineProps<{ data: CrmGroupRow[], metric: 'amount' | 'quantity_kg' }>()
const items = computed(() => props.data.map(r => ({ name: r.name, value: r[props.metric] })))
const max = computed(() => Math.max(1, ...items.value.map(r => Math.abs(r.value))))
const format = (v: number) => (props.metric === 'amount' ? formatRialCompact(v) : formatKg(v))
</script>
