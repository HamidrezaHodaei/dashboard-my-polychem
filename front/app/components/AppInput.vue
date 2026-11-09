<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: string | number
  label?: string
  type?: string
  placeholder?: string
  error?: string | null
  required?: boolean
}>(), { type: 'text' })

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm text-ink-800">
      {{ label }}<span v-if="required" class="text-debt-600"> *</span>
    </span>
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      class="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none transition-colors placeholder:text-ink-700/30 focus:ring-2"
      :class="error ? 'border-debt-600 focus:ring-debt-600/20' : 'border-paper-200 focus:border-gain-400 focus:ring-gain-400/20'"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    >
    <span v-if="error" class="mt-1 block text-xs text-debt-600">{{ error }}</span>
  </label>
</template>
