<!-- <PurchasesBars :labels :series="[{name,color,values}]" /> : grouped vertical bars (HTML, RTL: the first period is on the right). -->
<template>
  <div dir="rtl">
    <div v-if="!labels.length" class="py-10 text-center text-sm text-muted-foreground">دادهٔ کافی برای نمایش وجود ندارد.</div>
    <template v-else>
      <div class="mb-3 flex flex-wrap gap-4 text-xs">
        <span v-for="s in series" :key="s.name" class="flex items-center gap-1.5">
          <span class="inline-block size-2.5 rounded-sm" :style="{ background: s.color }" />{{ s.name }}
        </span>
      </div>
      <div class="overflow-x-auto pb-1">
        <div class="flex h-44 items-end gap-2" :style="{ minWidth: `${labels.length * (series.length * 14 + 18)}px` }">
          <div v-for="(l, i) in labels" :key="l + i" class="flex h-full min-w-0 flex-1 flex-col justify-end">
            <div class="flex flex-1 items-end justify-center gap-0.5">
              <div
                v-for="s in series"
                :key="s.name"
                class="w-3 max-w-full rounded-t-sm transition-all"
                :style="{ height: `${barHeight(s.values[i])}%`, background: s.color, minHeight: s.values[i] ? '2px' : '0' }"
                :title="`${s.name} — ${l}: ${fmt(s.values[i])}`"
              />
            </div>
            <span class="mt-1 truncate text-center text-[10px] text-muted-foreground" :title="l">{{ l }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ labels: string[], series: { name: string, color: string, values: (number | null)[] }[], format?: (n: number | null) => string }>()
const max = computed(() => Math.max(0, ...props.series.flatMap(s => s.values.map(v => v ?? 0))))
const barHeight = (v: number | null) => (max.value && v ? Math.max(0, (v / max.value) * 100) : 0)
const fmt = (v: number | null) => (props.format ? props.format(v) : money(v))
</script>
