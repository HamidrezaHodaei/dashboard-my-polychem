<script setup lang="ts">
import { formatCurrency } from '~/utils/financeFormat'

type Tone = 'neutral' | 'gain' | 'pending' | 'debt'

const props = withDefaults(defineProps<{
  label: string
  value: number
  tone?: Tone
  icon?: string // svg path data
  hint?: string
}>(), {
  tone: 'neutral',
})

const toneClasses: Record<Tone, { bg: string; text: string }> = {
  neutral: { bg: 'bg-ink-900/5', text: 'text-ink-900' },
  gain: { bg: 'bg-gain-50', text: 'text-gain-700' },
  pending: { bg: 'bg-pending-50', text: 'text-pending-600' },
  debt: { bg: 'bg-debt-50', text: 'text-debt-600' },
}
</script>

<template>
  <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
    <div class="flex items-start justify-between gap-2">
      <p class="text-sm text-ink-700/70">{{ label }}</p>
      <div v-if="icon" class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="toneClasses[props.tone].bg">
        <svg class="h-4.5 w-4.5" :class="toneClasses[props.tone].text" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path :d="icon" />
        </svg>
      </div>
    </div>
    <p class="num mt-3 text-xl font-bold" :class="toneClasses[props.tone].text">{{ formatCurrency(value) }}</p>
    <p v-if="hint" class="mt-1 text-xs text-ink-700/50">{{ hint }}</p>
  </div>
</template>
