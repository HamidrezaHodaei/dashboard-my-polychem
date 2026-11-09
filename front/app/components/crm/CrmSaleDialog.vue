<!-- Create / edit / view one sale. The customer is chosen from the customer bank; the payload
     carries `customer_id`, never a name. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription>
          {{ readOnly ? 'جزئیات سند فروش' : 'مشتری از بانک مشتریان انتخاب می‌شود؛ مبلغ از حاصل‌ضرب مقدار در فی محاسبه می‌شود.' }}
        </DialogDescription>
      </DialogHeader>

      <div class="grid flex-1 gap-4 overflow-y-auto px-6 py-5 sm:grid-cols-2">
        <div class="space-y-1.5 sm:col-span-2">
          <Label>مشتری <span class="text-destructive">*</span></Label>
          <CrmCustomerPicker v-model="form.customer" :disabled="readOnly" :clearable="false" :invalid="!!errors.customer" />
          <p v-if="errors.customer" class="text-xs text-destructive">{{ errors.customer }}</p>
        </div>

        <div class="space-y-1.5">
          <Label>گرید <span class="text-destructive">*</span></Label>
          <Select v-model="form.product_id" :disabled="readOnly">
            <SelectTrigger class="w-full" :aria-invalid="!!errors.product_id"><SelectValue placeholder="انتخاب گرید" /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="p in productOptions" :key="p.id" :value="String(p.id)">{{ p.name }}</SelectItem>
            </SelectContent>
          </Select>
          <p class="text-xs text-muted-foreground">فهرست گریدها از بانک مشتریان خوانده می‌شود.</p>
          <p v-if="errors.product_id" class="text-xs text-destructive">{{ errors.product_id }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>نحوه پرداخت</Label>
          <Select v-model="form.payment_method_id" :disabled="readOnly">
            <SelectTrigger class="w-full"><SelectValue placeholder="نامشخص" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">نامشخص</SelectItem>
              <SelectItem v-for="m in store.paymentMethods" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-1.5">
          <Label>مقدار (کیلوگرم) <span class="text-destructive">*</span></Label>
          <Input v-model="form.quantity_kg" type="number" min="0" step="any" dir="ltr" class="text-right" :disabled="readOnly" :aria-invalid="!!errors.quantity_kg" />
          <p v-if="errors.quantity_kg" class="text-xs text-destructive">{{ errors.quantity_kg }}</p>
        </div>
        <div class="space-y-1.5">
          <Label>فی (ریال بر کیلوگرم) <span class="text-destructive">*</span></Label>
          <Input v-model="form.unit_price" type="number" min="0" step="any" dir="ltr" class="text-right" :disabled="readOnly" :aria-invalid="!!errors.unit_price" />
          <p v-if="errors.unit_price" class="text-xs text-destructive">{{ errors.unit_price }}</p>
        </div>

        <div class="space-y-1.5">
          <Label>تاریخ سند</Label>
          <JalaliDateInput v-model="form.date" :max="todayIso()" :disabled="readOnly" />
        </div>
        <div class="space-y-1.5">
          <Label>مبلغ محاسبه‌شده</Label>
          <div class="flex h-9 items-center rounded-md border bg-muted/40 px-3 text-sm font-medium" dir="auto">
            {{ formatRial(computedAmount) }}
          </div>
        </div>

        <div class="space-y-1.5">
          <Label>نوع سند</Label>
          <Select v-model="form.document_type" :disabled="readOnly">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="(l, k) in DOCUMENT_TYPE_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>نوع فروش</Label>
          <Select v-model="form.sale_type" :disabled="readOnly">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="(l, k) in SALE_TYPE_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>وضعیت</Label>
          <Select v-model="form.status" :disabled="readOnly">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="(l, k) in SALE_STATUS_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <Label>توضیحات</Label>
          <Textarea v-model="form.description" rows="3" dir="rtl" :disabled="readOnly" />
        </div>
        <p v-if="formError" class="text-sm text-destructive sm:col-span-2" role="alert">{{ formError }}</p>
      </div>

      <DialogFooter class="gap-2 border-t bg-muted/30 px-6 py-4">
        <Button variant="outline" @click="emit('update:open', false)">{{ readOnly ? 'بستن' : 'انصراف' }}</Button>
        <Button v-if="!readOnly" :disabled="saving" class="gap-2" @click="submit">
          <Icon v-if="saving" name="lucide:loader-circle" class="size-4 animate-spin" />
          {{ mode === 'edit' ? 'ذخیره تغییرات' : 'ثبت فروش' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { DOCUMENT_TYPE_LABELS, SALE_STATUS_LABELS, SALE_TYPE_LABELS, formatRial } from '~/utils/crm'
import { todayIso } from '~/utils/jalali'
import type { CrmCustomerRef, CrmSale } from '~/stores/crm'

const props = defineProps<{ open: boolean, mode: 'create' | 'edit' | 'view', sale: CrmSale | null }>()
const emit = defineEmits<{ 'update:open': [v: boolean], saved: [] }>()

const store = useCrmStore()
const notify = useNotify()

interface Form {
  customer: CrmCustomerRef | null
  product_id: string
  payment_method_id: string
  quantity_kg: string
  unit_price: string
  date: string
  document_type: string
  sale_type: string
  status: string
  description: string
}
const blank = (): Form => ({
  customer: null, product_id: '', payment_method_id: 'none', quantity_kg: '', unit_price: '', date: todayIso(),
  document_type: 'INVOICE', sale_type: 'OFFICIAL', status: 'PROCESSING', description: '',
})
const form = reactive<Form>(blank())
const errors = reactive<Record<string, string>>({})
const formError = ref('')
const saving = ref(false)

const readOnly = computed(() => props.mode === 'view')
// The product list is the customer bank's. A sale may still point at a product that was deactivated
// there afterwards -- keep it selectable so the form never shows an empty product for an old sale.
const productOptions = computed(() => {
  const list = store.products.map(p => ({ id: p.id, name: p.name }))
  const current = props.sale?.product
  return current && !list.some(p => p.id === current.id) ? [{ id: current.id, name: current.name }, ...list] : list
})
const title = computed(() => ({ create: 'ثبت فروش جدید', edit: 'ویرایش فروش', view: 'مشاهده فروش' })[props.mode])
const computedAmount = computed(() => Math.round(Number(form.quantity_kg || 0) * Number(form.unit_price || 0)))

watch(() => [props.open, props.sale], () => {
  if (!props.open) return
  Object.keys(errors).forEach(k => delete errors[k])
  formError.value = ''
  const s = props.sale
  Object.assign(form, s
    ? {
        customer: s.customer, product_id: String(s.product.id),
        payment_method_id: s.payment_method ? String(s.payment_method.id) : 'none',
        quantity_kg: String(s.quantity_kg), unit_price: String(s.unit_price), date: s.date_iso,
        document_type: s.document_type, sale_type: s.sale_type, status: s.status, description: s.description ?? '',
      }
    : blank())
}, { immediate: true })

function validate() {
  Object.keys(errors).forEach(k => delete errors[k])
  if (!form.customer) errors.customer = 'مشتری را از بانک مشتریان انتخاب کنید.'
  if (!form.product_id) errors.product_id = 'گرید را انتخاب کنید.'
  if (form.quantity_kg === '' || Number(form.quantity_kg) <= 0) errors.quantity_kg = 'مقدار باید بیشتر از صفر باشد.'
  if (form.unit_price === '' || Number(form.unit_price) <= 0) errors.unit_price = 'فی باید بیشتر از صفر باشد.'
  return Object.keys(errors).length === 0
}

async function submit() {
  formError.value = ''
  if (!validate()) return
  const body: Record<string, unknown> = {
    customer_id: form.customer!.id,
    product_id: Number(form.product_id),
    date: form.date || undefined,
    document_type: form.document_type,
    sale_type: form.sale_type,
    status: form.status,
    description: form.description.trim() || null,
  }
  // Quantity / price are sent when creating, or when edited: the server recomputes the amount
  // from them, so an untouched edit must not overwrite e.g. an imported net amount.
  const qty = Number(form.quantity_kg)
  const price = Number(form.unit_price)
  if (props.mode !== 'edit' || qty !== props.sale?.quantity_kg) body.quantity_kg = qty
  if (props.mode !== 'edit' || price !== props.sale?.unit_price) body.unit_price = price
  if (form.payment_method_id === 'none') {
    if (props.mode === 'edit') body.clear_payment_method = true
  }
  else {
    body.payment_method_id = Number(form.payment_method_id)
  }
  saving.value = true
  try {
    if (props.mode === 'edit' && props.sale) await store.updateSale(props.sale.id, body)
    else await store.createSale(body)
    notify.success(props.mode === 'edit' ? 'فروش ویرایش شد' : 'فروش ثبت شد')
    emit('saved')
    emit('update:open', false)
  }
  catch (err) {
    formError.value = err instanceof ApiError ? err.message : 'ذخیره انجام نشد.'
  }
  finally {
    saving.value = false
  }
}
</script>
