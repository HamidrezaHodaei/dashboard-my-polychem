
<template>
  <Card class="gap-4 p-5 shadow-none">
    <div>
      <h2 class="font-semibold">
        {{ title }}
      </h2>
      <p class="mt-1 text-xs text-muted-foreground">
        داده‌های زنده از API فروش
      </p>
    </div>

    <div
      v-if="!hasData"
      class="flex h-48 items-center justify-center text-sm text-muted-foreground"
    >
      داده‌ای برای نمایش وجود ندارد
    </div>

    <div
      v-else
      class="flex h-48 items-end gap-2 border-b border-l px-2 pb-0 pt-6"
    >
      <div
        v-for="(value, index) in values"
        :key="index"
        class="group flex min-w-0 flex-1 flex-col items-center justify-end gap-2"
      >
        <div
          class="relative w-full max-w-12 rounded-t-md bg-primary/75 transition-all hover:bg-primary"
          :style="{ height: `${barHeight(value)}%` }"
        >
          <span
            class="pointer-events-none absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] opacity-0 transition-opacity group-hover:opacity-100"
          >
            {{ compact(value) }}
          </span>
        </div>

        <span class="max-w-full truncate text-[10px] text-muted-foreground">
          {{ labels[index] }}
        </span>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
const props = defineProps<{
  title: string
  values: number[]
  labels: string[]
}>()

const hasData = computed(() => props.values.some(value => value !== 0))

const maximum = computed(() => Math.max(...props.values.map(Math.abs), 1))

const barHeight = (value: number) =>
  Math.max(5, (Math.abs(value) / maximum.value) * 100)

const compact = (value: number) =>
  value >= 1_000_000_000
    ? `${(value / 1_000_000_000).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} میلیارد`
    : value >= 1_000_000
      ? `${(value / 1_000_000).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} میلیون`
      : value.toLocaleString('fa-IR')
</script>
