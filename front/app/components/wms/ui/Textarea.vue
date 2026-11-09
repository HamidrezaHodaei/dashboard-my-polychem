<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-sm font-medium text-ink">
      {{ label }}<span v-if="required" class="text-danger"> *</span>
    </span>
    <textarea
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      class="focus-ring w-full resize-none rounded border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder:text-ink-faint"
      :class="error ? 'border-danger' : ''"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    />
    <span v-if="error" class="mt-1 block text-xs text-danger">{{ error }}</span>
  </label>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  required?: boolean
  rows?: number
  error?: string
}>(), { required: false, rows: 3 })
defineEmits(['update:modelValue'])
</script>

