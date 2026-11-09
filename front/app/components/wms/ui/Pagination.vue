<template>
  <div class="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
    <p class="text-ink-faint">
      Showing <span class="font-medium text-ink">{{ startRow }}â€“{{ endRow }}</span> of
      <span class="font-medium text-ink">{{ total }}</span>
    </p>
    <div class="flex items-center gap-1">
      <WmsUiButton size="sm" variant="ghost" :disabled="page <= 1" @click="$emit('update:page', page - 1)">Prev</WmsUiButton>
      <span class="px-2 text-ink-faint">Page {{ page }} of {{ totalPages }}</span>
      <WmsUiButton size="sm" variant="ghost" :disabled="page >= totalPages" @click="$emit('update:page', page + 1)">Next</WmsUiButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ page: number; pageSize: number; total: number }>()
defineEmits(['update:page'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const startRow = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const endRow = computed(() => Math.min(props.page * props.pageSize, props.total))
</script>

