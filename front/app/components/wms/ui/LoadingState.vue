<template>
  <div class="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
    <svg class="h-5 w-5 animate-spin text-ink-faint" viewBox="0 0 24 24" fill="none">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z" />
    </svg>
    <p class="text-sm text-ink-faint">{{ label }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loadingâ€¦' })
</script>

