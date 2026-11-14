<!-- The customer's FINAL feedback -- one per request, separate from the routine follow-ups. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="customer-wizard rs-rtl max-h-[92vh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader class="text-right">
        <DialogTitle>ثبت بازخورد نهایی مشتری</DialogTitle>
        <DialogDescription>نتیجهٔ ارزیابی مشتری از نمونه. پیگیری‌های روزمره را در بخش «پیگیری‌ها» ثبت کنید.</DialogDescription>
      </DialogHeader>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1.5">
          <Label>نتیجهٔ بازخورد <span class="text-destructive">*</span></Label>
          <Select v-model="f.feedback_status">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem v-for="(m, k) in FEEDBACK_META" :key="k" :value="k">{{ m.label }}</SelectItem></SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>تاریخ دریافت بازخورد <span class="text-destructive">*</span></Label>
          <JalaliDateInput v-model="f.feedback_date" :max="todayIso()" :invalid="!!err.feedback_date" />
          <p v-if="err.feedback_date" class="text-xs text-destructive">{{ err.feedback_date }}</p>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>ارزیابی مشتری از محصول</Label>
          <Textarea v-model="f.product_evaluation" rows="2" dir="rtl" />
        </div>
        <div class="space-y-1.5">
          <Label>مشخصات فنی</Label>
          <Select v-model="techModel">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">نامشخص</SelectItem>
              <SelectItem value="yes">مورد تأیید است</SelectItem>
              <SelectItem value="no">مورد تأیید نیست</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>ثبت‌کنندهٔ ارزیابی</Label>
          <Input v-model="f.evaluated_by" dir="rtl" maxlength="200" placeholder="نام شخصِ ارزیاب نزد مشتری" />
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>توضیحات مشتری <span v-if="f.feedback_status === 'ACCEPTED_WITH_CONDITIONS'" class="text-destructive">* (شرایط مشتری)</span></Label>
          <Textarea v-model="f.customer_comments" rows="2" dir="rtl" :aria-invalid="!!err.customer_comments" />
          <p v-if="err.customer_comments" class="text-xs text-destructive">{{ err.customer_comments }}</p>
        </div>
        <div v-if="f.feedback_status === 'REJECTED'" class="space-y-1.5 sm:col-span-2">
          <Label>دلیل عدم تأیید <span class="text-destructive">*</span></Label>
          <Textarea v-model="f.rejection_reason" rows="2" dir="rtl" :aria-invalid="!!err.rejection_reason" />
          <p v-if="err.rejection_reason" class="text-xs text-destructive">{{ err.rejection_reason }}</p>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>پیشنهادهای مشتری برای اصلاح یا بهبود</Label>
          <Textarea v-model="f.improvement_suggestions" rows="2" dir="rtl" />
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>مستندات بازخورد</Label>
          <Button type="button" variant="outline" class="gap-2" @click="input?.click()">
            <Icon name="lucide:upload" class="size-4" />
            {{ pending.length ? `${toPersianDigits(pending.length)} فایل انتخاب شد` : 'بارگذاری فایل' }}
          </Button>
          <input ref="input" type="file" class="hidden" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" @change="onFiles">
        </div>
      </div>
      <p v-if="f.feedback_status === 'REJECTED'" class="rounded-lg bg-muted/40 p-2 text-xs text-muted-foreground">با «تأیید نشد» درخواست با همین نتیجه بسته می‌شود؛ برای نمونهٔ اصلاح‌شده می‌توانید یک درخواست جدید مرتبط ایجاد کنید.</p>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :disabled="saving || uploading" @click="submit">ثبت بازخورد</Button>
        <Button variant="outline" :disabled="saving" @click="emit('update:open', false)">انصراف</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import type { SampleDetail } from '~/utils/requestSample'
import { FEEDBACK_META } from '~/utils/requestSample'
import { todayIso, toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ open: boolean, requestId: number, current: SampleDetail['feedback'], saving?: boolean }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'submit', body: Record<string, unknown>): void }>()
const store = useRequestSampleStore()
const notify = useNotify()
const blank = () => ({ feedback_status: 'UNDER_EVALUATION', feedback_date: todayIso(), product_evaluation: '', technical_acceptance: null as boolean | null, customer_comments: '', rejection_reason: '', improvement_suggestions: '', evaluated_by: '' })
const f = reactive(blank())
const err = reactive<Record<string, string>>({})
const pending = ref<File[]>([])
const uploading = ref(false)
const input = ref<HTMLInputElement | null>(null)
const techModel = computed({
  get: () => (f.technical_acceptance === null ? 'none' : f.technical_acceptance ? 'yes' : 'no'),
  set: (v: string) => { f.technical_acceptance = v === 'none' ? null : v === 'yes' },
})
watch(() => props.open, (v) => {
  if (!v) return
  const c = props.current
  Object.assign(f, blank(), c ? {
    feedback_status: c.status, feedback_date: c.date ?? todayIso(), product_evaluation: c.product_evaluation ?? '',
    technical_acceptance: c.technical_acceptance, customer_comments: c.customer_comments ?? '',
    rejection_reason: c.rejection_reason ?? '', improvement_suggestions: c.improvement_suggestions ?? '', evaluated_by: c.evaluated_by ?? '',
  } : {})
  Object.keys(err).forEach(k => delete err[k])
  pending.value = []
})
const onFiles = (e: Event) => {
  const el = e.target as HTMLInputElement
  pending.value = [...pending.value, ...Array.from(el.files ?? [])]
  el.value = ''
}
async function submit() {
  Object.keys(err).forEach(k => delete err[k])
  if (!f.feedback_date) err.feedback_date = 'تاریخ بازخورد الزامی است.'
  else if (f.feedback_date > todayIso()) err.feedback_date = 'تاریخ بازخورد نمی‌تواند در آینده باشد.'
  if (f.feedback_status === 'REJECTED' && !f.rejection_reason.trim()) err.rejection_reason = 'دلیل عدم تأیید الزامی است.'
  if (f.feedback_status === 'ACCEPTED_WITH_CONDITIONS' && !f.customer_comments.trim()) err.customer_comments = 'شرایط مشتری را بنویسید.'
  if (Object.keys(err).length) return
  uploading.value = true
  try { for (const file of pending.value) await store.uploadFile(file, 'FEEDBACK', props.requestId) }
  catch { notify.error('بارگذاری فایل انجام نشد.'); uploading.value = false; return }
  uploading.value = false
  const nz = (s: string) => (s.trim() ? s.trim() : null)
  emit('submit', {
    feedback_status: f.feedback_status, feedback_date: f.feedback_date, product_evaluation: nz(f.product_evaluation),
    technical_acceptance: f.technical_acceptance, customer_comments: nz(f.customer_comments),
    rejection_reason: f.feedback_status === 'REJECTED' ? nz(f.rejection_reason) : null,
    improvement_suggestions: nz(f.improvement_suggestions), evaluated_by: nz(f.evaluated_by),
  })
}
</script>
