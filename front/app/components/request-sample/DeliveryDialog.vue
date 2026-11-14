<!-- Confirm that the CUSTOMER received the sample (ارسال‌شده → تحویل شد). Starts the follow-up phase. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="customer-wizard rs-rtl max-h-[92vh] overflow-y-auto sm:max-w-lg">
      <DialogHeader class="text-right">
        <DialogTitle>تأیید دریافت نمونه توسط مشتری</DialogTitle>
        <DialogDescription>پس از ثبت، یادآوری روزانهٔ «تحویل نمونه» متوقف می‌شود و یادآوری پیگیری مشتری شروع می‌شود.</DialogDescription>
      </DialogHeader>
      <div class="grid gap-4">
        <div class="space-y-1.5">
          <Label>تاریخ دریافت <span class="text-destructive">*</span></Label>
          <JalaliDateInput v-model="f.delivered_date" :max="todayIso()" :invalid="!!err.delivered_date" />
          <p v-if="err.delivered_date" class="text-xs text-destructive">{{ err.delivered_date }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>نام دریافت‌کننده نزد مشتری</Label>
          <Input v-model="f.received_by" dir="rtl" maxlength="200" />
        </div>
        <div class="space-y-1.5">
          <Label>توضیحات</Label>
          <Textarea v-model="f.note" rows="2" dir="rtl" />
        </div>
      </div>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :disabled="saving" @click="submit">ثبت دریافت نمونه</Button>
        <Button variant="outline" :disabled="saving" @click="emit('update:open', false)">انصراف</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { todayIso } from '~/utils/jalali'

const props = defineProps<{ open: boolean, defaults?: { receivedBy?: string | null }, saving?: boolean }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'submit', body: Record<string, unknown>): void }>()
const blank = () => ({ delivered_date: todayIso(), received_by: '', note: '' })
const f = reactive(blank())
const err = reactive<Record<string, string>>({})

watch(() => props.open, (v) => {
  if (!v) return
  Object.assign(f, blank(), { received_by: props.defaults?.receivedBy ?? '' })
  Object.keys(err).forEach(k => delete err[k])
})
function submit() {
  Object.keys(err).forEach(k => delete err[k])
  if (!f.delivered_date) err.delivered_date = 'تاریخ دریافت الزامی است.'
  else if (f.delivered_date > todayIso()) err.delivered_date = 'تاریخ دریافت نمی‌تواند در آینده باشد.'
  if (Object.keys(err).length) return
  const nz = (s: string) => (s.trim() ? s.trim() : null)
  emit('submit', { delivered_date: f.delivered_date, received_by: nz(f.received_by), note: nz(f.note) })
}
</script>
