<template>
  <button
    type="button"
    class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-ink hover:bg-steel-50 dark:hover:bg-steel-800"
    :class="danger ? 'text-danger hover:bg-danger-soft' : ''"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ danger?: boolean }>(), { danger: false })
</script>

