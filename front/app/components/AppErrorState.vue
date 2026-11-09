<script setup lang="ts">
defineProps<{ message: string }>()
const emit = defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 rounded-xl border border-debt-600/20 bg-debt-50 py-14 text-center">
    <p class="text-sm text-debt-600">{{ message }}</p>
    <button class="rounded-lg bg-debt-600 px-4 py-2 text-sm font-medium text-white hover:bg-debt-700" @click="emit('retry')">
      تلاش مجدد
    </button>
  </div>
</template>
