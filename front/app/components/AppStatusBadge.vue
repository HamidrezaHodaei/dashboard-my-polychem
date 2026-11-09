<script setup lang="ts">
type Tone = 'gain' | 'pending' | 'debt' | 'neutral'
withDefaults(defineProps<{ label: string; tone?: Tone }>(), { tone: 'neutral' })
const toneClass: Record<Tone, string> = {
  gain: 'bg-gain-50 text-gain-700',
  pending: 'bg-pending-50 text-pending-600',
  debt: 'bg-debt-50 text-debt-600',
  neutral: 'bg-paper-100 text-ink-700/70',
}
</script>

<template>
  <span class="rounded-full px-2.5 py-1 text-xs font-medium" :class="toneClass[tone]">{{ label }}</span>
</template>
