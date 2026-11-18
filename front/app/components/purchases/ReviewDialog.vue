<!-- <PurchasesReviewDialog v-model:open :request="{id, request_no, review_status}" @saved="..." /> :
     the expert sets the review status of a request (pending / approved / rejected / needs revision).
     «نیازمند اصلاح» can be picked directly (a paper request may be recorded first and judged later); a rejected request stays in the records. -->
<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent dir="rtl">
      <DialogHeader><DialogTitle>تعیین وضعیت بررسی — {{ request?.request_no }}</DialogTitle></DialogHeader>
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="s in store.meta?.review_statuses" :key="s.value" type="button" class="rounded-lg border p-3 text-sm transition-colors hover:bg-muted"
            :class="status === s.value && 'border-primary bg-primary/5 font-semibold'" @click="status = s.value"
          >{{ s.label }}</button>
        </div>
        <PurchasesField :label="needsNote ? 'علت / موارد اصلاحی' : 'توضیح (اختیاری)'" :required="needsNote" :error="error">
          <Textarea v-model="note" rows="3" />
        </PurchasesField>
        <p v-if="status === 'REJECTED'" class="text-xs text-muted-foreground">درخواست ردشده از سوابق حذف نمی‌شود و در گزارش‌ها می‌ماند؛ تا تغییر وضعیت، قابل ویرایش نیست.</p>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">انصراف</Button>
        <Button :disabled="busy || status === request?.review_status && !needsNote" @click="save">ثبت وضعیت</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { PurchaseRequest } from '~/utils/purchase'

const props = defineProps<{ open: boolean, request: { id: number, request_no: string, review_status: string, review_note?: string | null } | null }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'saved', r: PurchaseRequest): void }>()
const store = usePurchasesStore()
const notify = useNotify()
const status = ref('PENDING_REVIEW')
const note = ref('')
const error = ref('')
const busy = ref(false)
const needsNote = computed(() => status.value === 'REJECTED' || status.value === 'NEEDS_REVISION')
watch(() => props.open, (o) => { if (o) { status.value = props.request?.review_status ?? 'PENDING_REVIEW'; note.value = props.request?.review_note ?? ''; error.value = '' } })

async function save() {
  if (!props.request) return
  busy.value = true
  error.value = ''
  try {
    const r = await store.setReview(props.request.id, status.value, note.value.trim())
    notify.success('وضعیت بررسی ثبت شد')
    emit('saved', r)
    emit('update:open', false)
  }
  catch (e) { error.value = e instanceof ApiError ? e.message : 'ثبت انجام نشد.' }
  finally { busy.value = false }
}
</script>
