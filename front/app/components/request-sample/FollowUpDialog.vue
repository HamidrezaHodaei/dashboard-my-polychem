<!-- One routine follow-up with the customer (add or edit). The FINAL feedback has its own dialog. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="customer-wizard rs-rtl max-h-[92vh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader class="text-right">
        <DialogTitle>{{ editing ? 'ویرایش پیگیری' : 'ثبت پیگیری جدید' }}</DialogTitle>
        <DialogDescription>هر تماس، مکاتبه یا جلسه را ثبت کنید؛ نتیجهٔ نهایی مشتری جداگانه در «بازخورد نهایی» ثبت می‌شود.</DialogDescription>
      </DialogHeader>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1.5">
          <Label>تاریخ پیگیری <span class="text-destructive">*</span></Label>
          <JalaliDateInput v-model="f.followup_date" :max="todayIso()" :invalid="!!err.followup_date" />
          <p v-if="err.followup_date" class="text-xs text-destructive">{{ err.followup_date }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>روش پیگیری <span class="text-destructive">*</span></Label>
          <Select v-model="f.method">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem v-for="(l, k) in METHOD_LABELS" :key="k" :value="k">{{ l }}</SelectItem></SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>شخص مورد پیگیری</Label>
          <Input v-model="f.contact_person" dir="rtl" maxlength="200" list="rs-contacts" />
          <datalist id="rs-contacts"><option v-for="c in contacts" :key="c" :value="c" /></datalist>
        </div>
        <div class="space-y-1.5">
          <Label>کارشناس مسئول پیگیری</Label>
          <Select v-model="repModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="خودم" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="me">خودم</SelectItem>
              <SelectItem v-for="r in reps" :key="r.id" :value="String(r.id)">{{ r.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>نتیجهٔ پیگیری</Label>
          <Textarea v-model="f.result" rows="2" dir="rtl" />
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>پاسخ و توضیحات مشتری</Label>
          <Textarea v-model="f.customer_response" rows="2" dir="rtl" />
        </div>
        <div class="space-y-1.5">
          <Label>تاریخ پیگیری بعدی</Label>
          <JalaliDateInput v-model="f.next_followup_date" :min="f.followup_date || undefined" :invalid="!!err.next_followup_date" />
          <p v-if="err.next_followup_date" class="text-xs text-destructive">{{ err.next_followup_date }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>پیوست</Label>
          <Button type="button" variant="outline" class="w-full gap-2" @click="input?.click()">
            <Icon name="lucide:upload" class="size-4" />
            {{ pending.length ? `${toPersianDigits(pending.length)} فایل انتخاب شد` : 'بارگذاری فایل' }}
          </Button>
          <input ref="input" type="file" class="hidden" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" @change="onFiles">
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>یادداشت داخلی</Label>
          <Textarea v-model="f.internal_notes" rows="2" dir="rtl" />
        </div>
      </div>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :disabled="saving || uploading" @click="submit">{{ editing ? 'ذخیرهٔ تغییرات' : 'ثبت پیگیری' }}</Button>
        <Button variant="outline" :disabled="saving" @click="emit('update:open', false)">انصراف</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import type { SampleFollowUp } from '~/utils/requestSample'
import { METHOD_LABELS } from '~/utils/requestSample'
import { todayIso, toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ open: boolean, requestId: number, editing: SampleFollowUp | null, contacts: string[], reps: { id: number, name: string }[], saving?: boolean }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'submit', body: Record<string, unknown>): void }>()
const store = useRequestSampleStore()
const auth = useAuthStore()
const notify = useNotify()
const blank = () => ({ followup_date: todayIso(), method: 'PHONE', contact_person: '', result: '', customer_response: '', next_followup_date: '', responsible_user_id: null as number | null, internal_notes: '' })
const f = reactive(blank())
const err = reactive<Record<string, string>>({})
const pending = ref<File[]>([])
const uploading = ref(false)
const input = ref<HTMLInputElement | null>(null)
const repModel = computed({
  get: () => (f.responsible_user_id && f.responsible_user_id !== auth.user?.id ? String(f.responsible_user_id) : 'me'),
  set: (v: string) => { f.responsible_user_id = v === 'me' ? null : Number(v) },
})
watch(() => props.open, (v) => {
  if (!v) return
  const e = props.editing
  Object.assign(f, blank(), e ? {
    followup_date: e.followup_date, method: e.method, contact_person: e.contact_person ?? '', result: e.result ?? '',
    customer_response: e.customer_response ?? '', next_followup_date: e.next_followup_date ?? '',
    responsible_user_id: e.responsible.id, internal_notes: e.internal_notes ?? '',
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
  if (!f.followup_date) err.followup_date = 'تاریخ پیگیری الزامی است.'
  else if (f.followup_date > todayIso()) err.followup_date = 'تاریخ پیگیری نمی‌تواند در آینده باشد.'
  if (f.next_followup_date && f.next_followup_date < f.followup_date) err.next_followup_date = 'تاریخ بعدی قبل از این پیگیری است.'
  if (Object.keys(err).length) return
  uploading.value = true
  try { for (const file of pending.value) await store.uploadFile(file, 'FOLLOWUP', props.requestId) }
  catch { notify.error('بارگذاری فایل انجام نشد.'); uploading.value = false; return }
  uploading.value = false
  const nz = (s: string) => (s.trim() ? s.trim() : null)
  emit('submit', {
    followup_date: f.followup_date, method: f.method, contact_person: nz(f.contact_person), result: nz(f.result),
    customer_response: nz(f.customer_response), next_followup_date: f.next_followup_date || null,
    responsible_user_id: f.responsible_user_id, internal_notes: nz(f.internal_notes),
  })
}
</script>
