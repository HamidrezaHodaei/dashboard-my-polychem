<script setup lang="ts">
import type { AccessStatus } from '~/composables/useAccessManagement'
const props = defineProps<{ status: AccessStatus }>()
const label = computed(() => props.status === 'active' ? 'فعال' : 'غیرفعال')
</script>

<template>
  <Badge :variant="status === 'active' ? 'success' : 'secondary'" class="gap-1.5">
    <span class="size-1.5 rounded-full bg-current" />
    {{ label }}
  </Badge>
</template>
