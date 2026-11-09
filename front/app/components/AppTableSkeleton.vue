<script setup lang="ts">
withDefaults(defineProps<{ rows?: number; cols?: number }>(), { rows: 6, cols: 5 })
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-paper-200 bg-white">
    <div v-for="r in rows" :key="r" class="flex gap-4 border-b border-paper-100 px-4 py-3.5 last:border-0">
      <div v-for="c in cols" :key="c" class="h-4 flex-1 animate-pulse rounded bg-paper-200" />
    </div>
  </div>
</template>
