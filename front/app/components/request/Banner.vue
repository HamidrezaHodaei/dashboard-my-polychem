<!-- /components/request/Banner.vue  → <RequestBanner :status :note :change-request-note /> -->
<!-- Explains, in the record's detail view, what the manager decided and why. -->
<template>
  <div
    v-if="status === 'NEEDS_EDIT' || (status === 'REJECTED' && note) || changeRequestNote"
    class="space-y-2 text-right"
    dir="rtl"
  >
    <div
      v-if="status === 'NEEDS_EDIT'"
      class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-right"
    >
      <p class="mb-1 flex items-center justify-end gap-1.5 font-semibold">
        <Icon
          name="lucide:file-pen-line"
          class="size-4"
        /> مدیر درخواست ویرایش یا تکمیل اطلاعات داده است
      </p>
      <p
        dir="auto"
        class="whitespace-pre-wrap"
      >
        {{ note || '—' }}
      </p>
    </div>
    <div
      v-else-if="status === 'REJECTED' && note"
      class="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-right"
    >
      <p class="mb-1 font-semibold text-right">
        دلیل رد درخواست
      </p>
      <p
        dir="auto"
        class="whitespace-pre-wrap"
      >
        {{ note }}
      </p>
    </div>
    <div
      v-if="changeRequestNote"
      class="rounded-lg border p-3 text-sm text-right"
    >
      <p class="mb-1 font-semibold text-right">
        درخواست تغییر اطلاعات
      </p>
      <p
        dir="auto"
        class="whitespace-pre-wrap"
      >
        {{ changeRequestNote }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RequestStatusKey } from '~/utils/request-workflow'

defineProps<{ status: RequestStatusKey, note?: string | null, changeRequestNote?: string | null }>()
</script>
