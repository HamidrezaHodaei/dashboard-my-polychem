<template>
  <span class="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium" :class="toneClasses">
    <span class="h-1.5 w-1.5 rounded-full" :class="dotClasses" />
    <slot />
  </span>
</template>

<script setup lang="ts">
import type { BadgeTone } from '~/types'

const props = withDefaults(defineProps<{ tone?: BadgeTone }>(), { tone: 'neutral' })

const toneClasses = computed(() => ({
  neutral: 'bg-steel-100 text-steel-700 dark:bg-steel-800 dark:text-steel-200',
  success: 'bg-success-soft text-success',
  danger: 'bg-danger-soft text-danger',
  warn: 'bg-warn-soft text-warn',
  info: 'bg-info-soft text-info',
  amber: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
}[props.tone]))

const dotClasses = computed(() => ({
  neutral: 'bg-steel-400',
  success: 'bg-success',
  danger: 'bg-danger',
  warn: 'bg-warn',
  info: 'bg-info',
  amber: 'bg-amber-500'
}[props.tone]))
</script>

