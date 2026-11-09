<!-- /components/request/StatusBadge.vue  → <RequestStatusBadge :status="…" /> -->
<template>
  <span class="inline-flex flex-wrap items-center gap-1.5">
    <Badge :variant="REQUEST_STATUS_VARIANT[status] ?? 'secondary'">
      {{ REQUEST_STATUS_LABELS[status] ?? status }}
    </Badge>
    <Badge
      v-if="draft"
      variant="outline"
      class="font-normal"
    >
      پیش‌نویس
    </Badge>
    <Badge
      v-if="changeRequested"
      variant="outline"
      class="gap-1 border-amber-500/60 font-normal text-amber-600"
    >
      <Icon
        name="lucide:file-pen-line"
        class="size-3"
      /> درخواست تغییر
    </Badge>
  </span>
</template>

<script setup lang="ts">
import type { RequestStatusKey } from '~/utils/request-workflow'

withDefaults(defineProps<{
  status: RequestStatusKey
  /** not yet submitted ("ثبت نهایی" not pressed) */
  draft?: boolean
  /** the creator has asked the manager to allow a change */
  changeRequested?: boolean
}>(), { draft: false, changeRequested: false })
</script>
