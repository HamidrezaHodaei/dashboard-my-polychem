<!-- Record one shipment of the sample. A request can have several shipments. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="customer-wizard rs-rtl max-h-[92vh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader class="text-right">
        <DialogTitle>ثبت اطلاعات ارسال و اعلام «ارسال‌شده»</DialogTitle>
        <DialogDescription>پس از تحویل نمونه به واحد ارسال یا شرکت حمل‌ونقل، اطلاعات ارسال را ثبت کنید. اگر نمونه در چند محموله می‌رود، هر محموله را جدا ثبت کنید.</DialogDescription>
      </DialogHeader>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1.5">
          <Label>تاریخ ارسال <span class="text-destructive">*</span></Label>
          <JalaliDateInput v-model="f.dispatch_date" :max="todayIso()" :invalid="!!err.dispatch_date" />
          <p v-if="err.dispatch_date" class="text-xs text-destructive">{{ err.dispatch_date }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>شمارهٔ حوالهٔ ارسال <span class="text-destructive">*</span></Label>
          <Input v-model="f.reference_number" dir="rtl" maxlength="100" :aria-invalid="!!err.reference_number" />
          <p v-if="err.reference_number" class="text-xs text-destructive">{{ err.reference_number }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>روش ارسال</Label>
          <Select v-model="methodModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
            <SelectContent><SelectItem v-for="m in DELIVERY_METHODS" :key="m" :value="m">{{ m }}</SelectItem></SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>شرکت حمل‌کننده</Label>
          <Input v-model="f.carrier" dir="rtl" maxlength="200" />
        </div>
        <div class="space-y-1.5">
          <Label>کد رهگیری</Label>
          <Input v-model="f.tracking_number" dir="rtl" maxlength="100" />
        </div>
        <div class="space-y-1.5">
          <Label>نام تحویل‌گیرنده</Label>
          <Input v-model="f.recipient_name" dir="rtl" maxlength="200" />
        </div>
        <div class="space-y-1.5">
          <Label>مقدار واقعی ارسال‌شده</Label>
          <div class="flex gap-2">
            <Input v-model="f.shipped_quantity" dir="rtl" inputmode="decimal" class="text-right" :aria-invalid="!!err.shipped_quantity" />
            <Select v-model="f.unit">
              <SelectTrigger class="w-32 shrink-0"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem v-for="u in UNIT_OPTIONS" :key="u.value" :value="u.value">{{ u.label }}</SelectItem></SelectContent>
            </Select>
          </div>
          <p v-if="err.shipped_quantity" class="text-xs text-destructive">{{ err.shipped_quantity }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>مدارک ارسال</Label>
          <Button type="button" variant="outline" class="w-full gap-2" :disabled="uploading" @click="input?.click()">
            <Icon :name="uploading ? 'lucide:loader-circle' : 'lucide:upload'" class="size-4" :class="uploading && 'animate-spin'" />
            {{ pending.length ? `${toPersianDigits(pending.length)} فایل انتخاب شد` : 'بارگذاری فایل' }}
          </Button>
          <input ref="input" type="file" class="hidden" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" @change="onFiles">
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>توضیحات ارسال</Label>
          <Textarea v-model="f.notes" rows="2" dir="rtl" />
        </div>
        <label class="flex cursor-pointer items-start gap-2 text-sm sm:col-span-2">
          <input v-model="f.all_shipped" type="checkbox" class="mt-1 size-4 accent-primary">
          <span>نمونه به واحد ارسال / حمل‌کننده تحویل شد — وضعیت «ارسال‌شده» ثبت شود.<br><span class="text-xs text-muted-foreground">اگر هنوز محموله‌های دیگری باقی است تیک را بردارید؛ درخواست «تأیید شده» می‌ماند و یادآوری ارسال ادامه می‌یابد.</span></span>
        </label>
      </div>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :disabled="saving || uploading" @click="submit">ثبت ارسال</Button>
        <Button variant="outline" :disabled="saving" @click="emit('update:open', false)">انصراف</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { DELIVERY_METHODS, UNIT_OPTIONS } from '~/utils/requestSample'
import { todayIso, toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ open: boolean, requestId: number, defaults?: { reference?: string | null, recipient?: string | null, method?: string | null }, saving?: boolean }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'submit', body: Record<string, unknown>): void }>()
const store = useRequestSampleStore()
const notify = useNotify()
const blank = () => ({ dispatch_date: todayIso(), reference_number: '', delivery_method: '', tracking_number: '', carrier: '', shipped_quantity: '', unit: 'kg', recipient_name: '', notes: '', all_shipped: true })
const f = reactive(blank())
const err = reactive<Record<string, string>>({})
const pending = ref<File[]>([])
const uploading = ref(false)
const input = ref<HTMLInputElement | null>(null)
const methodModel = computed({ get: () => f.delivery_method || undefined, set: (v: string | undefined) => { f.delivery_method = v ?? '' } })

watch(() => props.open, (v) => {
  if (!v) return
  Object.assign(f, blank(), { reference_number: props.defaults?.reference ?? '', recipient_name: props.defaults?.recipient ?? '', delivery_method: props.defaults?.method ?? '' })
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
  if (!f.dispatch_date) err.dispatch_date = 'تاریخ ارسال الزامی است.'
  else if (f.dispatch_date > todayIso()) err.dispatch_date = 'تاریخ ارسال نمی‌تواند در آینده باشد.'
  if (!f.reference_number.trim()) err.reference_number = 'شمارهٔ حواله الزامی است.'
  const qty = f.shipped_quantity.trim() ? Number(f.shipped_quantity) : null
  if (qty !== null && (!Number.isFinite(qty) || qty < 0)) err.shipped_quantity = 'مقدار معتبر نیست.'
  if (Object.keys(err).length) return
  uploading.value = true
  try {
    for (const file of pending.value) await store.uploadFile(file, 'DISPATCH', props.requestId)
  }
  catch { notify.error('بارگذاری مدارک انجام نشد.'); uploading.value = false; return }
  uploading.value = false
  const nz = (s: string) => (s.trim() ? s.trim() : null)
  emit('submit', {
    dispatch_date: f.dispatch_date, reference_number: f.reference_number.trim(), delivery_method: nz(f.delivery_method),
    tracking_number: nz(f.tracking_number), carrier: nz(f.carrier), shipped_quantity: qty, unit: f.unit,
    recipient_name: nz(f.recipient_name), notes: nz(f.notes), all_shipped: f.all_shipped,
  })
}
</script>
