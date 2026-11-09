<template>
  <Badge :variant="variant">
    {{ label }}
  </Badge>
</template>

<script setup lang="ts">
import type { TaskPriority } from '~/stores/taskWorkspace'

const props = defineProps<{
  priority: TaskPriority
}>()

const priorityMap: Record<TaskPriority, string> = {
  low: 'secondary',
  medium: 'warning',
  high: 'info',
  urgent: 'destructive',
}

const labelMap: Record<TaskPriority, string> = {
  low: 'کم',
  medium: 'متوسط',
  high: 'زیاد',
  urgent: 'فوری',
}

const variant = computed(() => priorityMap[props.priority])
const label = computed(() => labelMap[props.priority])
</script>
