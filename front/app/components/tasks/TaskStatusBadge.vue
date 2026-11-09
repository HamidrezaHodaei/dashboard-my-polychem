<template>
  <Badge :variant="variant">
    {{ label }}
  </Badge>
</template>

<script setup lang="ts">
import type { TaskStatus } from '~/stores/taskWorkspace'

const props = defineProps<{
  status: TaskStatus
}>()

const statusMap: Record<TaskStatus, string> = {
  todo: 'secondary',
  'in-progress': 'info',
  review: 'warning',
  done: 'success',
}

const labelMap: Record<TaskStatus, string> = {
  todo: 'در انتظار انجام',
  'in-progress': 'در حال انجام',
  review: 'درخواست تأیید تکمیل',
  done: 'انجام‌شده',
}

const variant = computed(() => statusMap[props.status])
const label = computed(() => labelMap[props.status])
</script>
