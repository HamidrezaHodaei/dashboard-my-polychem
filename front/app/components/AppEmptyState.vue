<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  actionLabel?: string
}>(), {})
const emit = defineEmits<{ (e: 'action'): void }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-paper-200 bg-white py-16 text-center">
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-paper-100">
      <svg class="h-6 w-6 text-ink-700/40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M9 13h6m-7 7h8a2 2 0 002-2V6a2 2 0 00-2-2H9a2 2 0 00-2 2v12a2 2 0 002 2z" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <p class="text-sm text-ink-700/60">{{ title }}</p>
    <button v-if="actionLabel" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>
