<script setup lang="ts">
const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string }>(), {
  placeholder: 'جستجو...',
})
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <div class="relative w-full sm:w-64">
    <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-700/40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.35-4.35" stroke-linecap="round" />
    </svg>
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      class="w-full rounded-lg border border-paper-200 bg-white py-2 pr-9 pl-3 text-sm outline-none placeholder:text-ink-700/40 focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    >
  </div>
</template>
