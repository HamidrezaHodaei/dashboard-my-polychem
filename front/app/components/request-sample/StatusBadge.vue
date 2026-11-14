<!-- <RequestSampleStatusBadge status="APPROVED" /> | kind="priority" | kind="feedback" -->
<template>
  <span
    class="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium"
    :class="meta.cls"
  >
    <i
      v-if="kind === 'status'"
      class="size-1.5 rounded-full"
      :style="{ background: (meta as any).color }"
    />
    {{ meta.label }}
  </span>
</template>

<script setup lang="ts">
import { FEEDBACK_META, PRIORITY_META, STATUS_META } from '~/utils/requestSample'

const props = withDefaults(defineProps<{ status: string, kind?: 'status' | 'priority' | 'feedback' }>(), { kind: 'status' })
const meta = computed(() => {
  const table = props.kind === 'priority' ? PRIORITY_META : props.kind === 'feedback' ? FEEDBACK_META : STATUS_META
  return (table as Record<string, { label: string, cls: string }>)[props.status] ?? { label: props.status, cls: 'bg-muted' }
})
</script>
