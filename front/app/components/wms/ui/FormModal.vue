<template>
  <WmsUiBaseModal :model-value="modelValue" :title="title" :subtitle="subtitle" :size="size" @update:model-value="$emit('update:modelValue', $event)">
    <slot />
    <template #footer>
      <WmsUiButton variant="ghost" :disabled="submitting" @click="$emit('update:modelValue', false)">Cancel</WmsUiButton>
      <WmsUiButton variant="primary" :loading="submitting" @click="$emit('submit')">{{ submitLabel }}</WmsUiButton>
    </template>
  </WmsUiBaseModal>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: boolean
  title: string
  subtitle?: string
  size?: 'sm' | 'md' | 'lg'
  submitLabel?: string
  submitting?: boolean
}>(), { size: 'md', submitLabel: 'Save', submitting: false })

defineEmits(['update:modelValue', 'submit'])
</script>

