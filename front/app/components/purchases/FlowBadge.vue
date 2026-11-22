<!-- <PurchasesFlowBadge kind="request|item|priority" :value :label /> : coloured status badge of the purchase flow. -->
<template>
  <span class="inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium" :class="tone">{{ label }}</span>
</template>

<script setup lang="ts">
const props = defineProps<{ kind: 'request' | 'item' | 'priority', value: string | null | undefined, label: string | null | undefined }>()
const tone = computed(() => (props.kind === 'request' ? REQUEST_TONE : props.kind === 'item' ? ITEM_TONE : PRIORITY_TONE)[props.value ?? ''] ?? 'bg-muted')
</script>
