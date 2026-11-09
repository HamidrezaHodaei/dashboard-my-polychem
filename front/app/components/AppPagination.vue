<script setup lang="ts">
import { toPersianDigits } from '~/utils/financeFormat'

const props = defineProps<{ page: number; pageSize: number; total: number }>()
const emit = defineEmits<{ (e: 'update:page', v: number): void }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const rangeStart = computed(() => props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1)
const rangeEnd = computed(() => Math.min(props.total, props.page * props.pageSize))

function go(p: number) {
  if (p < 1 || p > totalPages.value) return
  emit('update:page', p)
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 px-1 py-3 text-sm text-ink-700/70">
    <span class="num">نمایش {{ toPersianDigits(rangeStart) }}–{{ toPersianDigits(rangeEnd) }} از {{ toPersianDigits(total) }}</span>
    <div class="flex items-center gap-1">
      <button class="rounded-lg border border-paper-200 p-1.5 disabled:opacity-30" :disabled="page <= 1" @click="go(page - 1)">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      <span class="num min-w-16 text-center">{{ toPersianDigits(page) }} از {{ toPersianDigits(totalPages) }}</span>
      <button class="rounded-lg border border-paper-200 p-1.5 disabled:opacity-30" :disabled="page >= totalPages" @click="go(page + 1)">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
    </div>
  </div>
</template>
