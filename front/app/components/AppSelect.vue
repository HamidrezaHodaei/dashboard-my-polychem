<script setup lang="ts">
interface Option { value: string; label: string }

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  options: Option[]
  placeholder?: string
  error?: string | null
  required?: boolean
}>(), {})

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm text-ink-800">
      {{ label }}<span v-if="required" class="text-debt-600"> *</span>
    </span>
    <select
      :value="modelValue"
      class="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none transition-colors focus:ring-2"
      :class="error ? 'border-debt-600 focus:ring-debt-600/20' : 'border-paper-200 focus:border-gain-400 focus:ring-gain-400/20'"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-if="placeholder" value="" disabled :selected="!modelValue">{{ placeholder }}</option>
      <option v-for="opt in options" :key="opt.value" :value="opt.value" :selected="opt.value === modelValue">
        {{ opt.label }}
      </option>
    </select>
    <span v-if="error" class="mt-1 block text-xs text-debt-600">{{ error }}</span>
  </label>
</template>
