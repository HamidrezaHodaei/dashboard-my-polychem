<template>
  <div>
    <div class="flex items-center gap-1 border-b border-line" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        role="tab"
        :aria-selected="modelValue === tab.value"
        class="focus-ring relative px-3.5 py-2 text-sm font-medium text-ink-soft transition-colors hover:text-ink"
        :class="modelValue === tab.value ? 'text-ink' : ''"
        @click="$emit('update:modelValue', tab.value)"
      >
        {{ tab.label }}
        <span
          class="absolute inset-x-0 -bottom-px h-0.5 rounded-full transition-colors"
          :class="modelValue === tab.value ? 'bg-amber-500' : 'bg-transparent'"
        />
      </button>
    </div>
    <div class="pt-4">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ tabs: { label: string; value: string }[]; modelValue: string }>()
defineEmits(['update:modelValue'])
</script>

