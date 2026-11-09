<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm font-medium text-ink">
      {{ label }}<span v-if="required" class="text-danger"> *</span>
    </span>
    <div class="relative">
      <select
        :value="modelValue"
        class="focus-ring h-9 w-full appearance-none rounded border border-line bg-paper-raised px-3 pr-8 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-60"
        :class="error ? 'border-danger' : ''"
        :disabled="disabled"
        @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <svg class="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
      </svg>
    </div>
    <span v-if="error" class="mt-1 block text-xs text-danger">{{ error }}</span>
  </label>
</template>

<script setup lang="ts">
import type { SelectOption } from '~/types'
withDefaults(defineProps<{
  modelValue: string
  options: SelectOption[]
  label?: string
  placeholder?: string
  required?: boolean
  disabled?: boolean
  error?: string
}>(), { required: false, disabled: false })
defineEmits(['update:modelValue'])
</script>

