<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm font-medium text-ink">
      {{ label }}<span v-if="required" class="text-danger"> *</span>
    </span>
    <div class="relative">
      <span v-if="prefix" class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint text-sm">{{ prefix }}</span>
      <input
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        class="focus-ring h-9 w-full rounded border border-line bg-paper-raised px-3 text-sm text-ink placeholder:text-ink-faint disabled:cursor-not-allowed disabled:opacity-60"
        :class="[prefix ? 'pl-7' : '', error ? 'border-danger' : '', monospace ? 'font-mono' : '']"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <span v-if="error" class="mt-1 block text-xs text-danger">{{ error }}</span>
    <span v-else-if="hint" class="mt-1 block text-xs text-ink-faint">{{ hint }}</span>
  </label>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: string | number
  label?: string
  type?: string
  placeholder?: string
  required?: boolean
  disabled?: boolean
  error?: string
  hint?: string
  prefix?: string
  monospace?: boolean
}>(), {
  type: 'text',
  required: false,
  disabled: false,
  monospace: false
})
defineEmits(['update:modelValue'])
</script>

