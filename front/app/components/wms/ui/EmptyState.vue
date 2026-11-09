<template>
  <div class="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
    <div class="mb-1 flex h-11 w-11 items-center justify-center rounded-full bg-steel-100 text-ink-faint dark:bg-steel-800">
      <slot name="icon">
        <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.75h16.5M3.75 9.75v9a1.5 1.5 0 001.5 1.5h13.5a1.5 1.5 0 001.5-1.5v-9M3.75 9.75l1.928-4.822A1.5 1.5 0 017.06 4h9.88a1.5 1.5 0 011.382.928L20.25 9.75" />
        </svg>
      </slot>
    </div>
    <p class="text-sm font-medium text-ink">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-sm text-ink-faint">{{ description }}</p>
    <div v-if="$slots.action" class="mt-2">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

