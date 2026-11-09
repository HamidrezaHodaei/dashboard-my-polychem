<template>
  <div class="rounded-md border border-line bg-paper-raised p-4">
    <div class="flex items-start justify-between">
      <p class="text-xs font-medium uppercase tracking-wide text-ink-faint">{{ label }}</p>
      <span class="flex h-7 w-7 items-center justify-center rounded" :class="iconBg">
        <span class="text-ink" v-html="icon" />
      </span>
    </div>
    <p class="mt-2.5 text-2xl font-semibold tabular-nums text-ink">{{ value }}</p>
    <p v-if="delta" class="mt-1 text-xs" :class="deltaPositive ? 'text-success' : 'text-danger'">
      {{ delta }}
    </p>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value: string
  icon: string
  tone?: 'neutral' | 'amber' | 'danger' | 'success'
  delta?: string
  deltaPositive?: boolean
}>(), { tone: 'neutral', deltaPositive: true })

const iconBg = computed(() => ({
  neutral: 'bg-steel-100 dark:bg-steel-800',
  amber: 'bg-amber-100 dark:bg-amber-900/40',
  danger: 'bg-danger-soft',
  success: 'bg-success-soft'
}[props.tone]))
</script>

