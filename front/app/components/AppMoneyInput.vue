<script setup lang="ts">
import { formatNumber } from '~/utils/financeFormat'

const props = withDefaults(defineProps<{
  modelValue: number
  label?: string
  error?: string | null
  required?: boolean
  unit?: string
}>(), { unit: 'تومان' })

const emit = defineEmits<{ (e: 'update:modelValue', v: number): void }>()

const display = computed({
  get: () => (props.modelValue ? formatNumber(props.modelValue, false) : ''),
  set: () => {},
})

function onInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.replace(/[^\d]/g, '')
  emit('update:modelValue', raw ? Number(raw) : 0)
}
</script>

<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm text-ink-800">
      {{ label }}<span v-if="required" class="text-debt-600"> *</span>
    </span>
    <div class="relative">
      <input
        :value="display"
        inputmode="numeric"
        placeholder="۰"
        class="num w-full rounded-lg border bg-white px-3 py-2 pl-14 text-sm outline-none transition-colors focus:ring-2"
        :class="error ? 'border-debt-600 focus:ring-debt-600/20' : 'border-paper-200 focus:border-gain-400 focus:ring-gain-400/20'"
        @input="onInput"
      >
      <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-ink-700/50">{{ unit }}</span>
    </div>
    <span v-if="error" class="mt-1 block text-xs text-debt-600">{{ error }}</span>
  </label>
</template>
