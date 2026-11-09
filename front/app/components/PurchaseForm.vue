<script setup lang="ts">
import type { Purchase, PurchaseItem } from '~/types/finance'
import { required, validate } from '~/utils/validators'
import { formatCurrency } from '~/utils/financeFormat'

const props = defineProps<{ initial?: Partial<Purchase> }>()
const emit = defineEmits<{ (e: 'submit', payload: Omit<Purchase, 'id' | 'invoiceNumber'>): void; (e: 'cancel'): void }>()

const partyStore = usePartyStore()
onMounted(() => partyStore.fetchAll())
const supplierOptions = computed(() => partyStore.items.filter((p) => p.type === 'supplier' || p.type === 'company').map((p) => ({ value: p.id, label: p.name })))

let itemSeq = 1
const form = reactive({
  supplierId: props.initial?.supplierId ?? '',
  date: props.initial?.date ?? new Date().toISOString(),
  items: (props.initial?.items ?? [{ id: `item-${itemSeq++}`, title: '', quantity: 1, unit: 'unit', unitPrice: 0 }]) as PurchaseItem[],
  discount: props.initial?.discount ?? 0,
  tax: props.initial?.tax ?? 0,
  paidAmount: props.initial?.paidAmount ?? 0,
  method: props.initial?.method ?? 'cash',
  description: props.initial?.description ?? '',
})

const methodOptions = [
  { value: 'cash', label: 'نقدی' }, { value: 'card', label: 'کارت' },
  { value: 'remittance', label: 'حواله' }, { value: 'bank_transfer', label: 'انتقال بانکی' }, { value: 'cheque', label: 'چک' },
]

const itemsTotal = computed(() => form.items.reduce((s, it) => s + it.quantity * it.unitPrice, 0))
const totalAmount = computed(() => Math.max(0, itemsTotal.value - form.discount + form.tax))
const remaining = computed(() => Math.max(0, totalAmount.value - form.paidAmount))
const status = computed<Purchase['status']>(() => remaining.value === 0 ? 'paid' : form.paidAmount === 0 ? 'unpaid' : 'partial')

function addItem() {
  form.items.push({ id: `item-${itemSeq++}`, title: '', quantity: 1, unit: 'unit', unitPrice: 0 })
}
function removeItem(id: string) {
  if (form.items.length > 1) form.items = form.items.filter((it) => it.id !== id)
}

const errors = reactive<Record<string, string | null>>({})
function validateForm() {
  errors.supplierId = validate(form.supplierId, [required('تأمین‌کننده')])
  errors.date = validate(form.date, [required('تاریخ')])
  return !Object.values(errors).some(Boolean) && form.items.every((it) => it.title)
}

function submit() {
  if (!validateForm()) return
  const supplier = partyStore.byId(form.supplierId)
  emit('submit', {
    supplierId: form.supplierId,
    supplierName: supplier?.name ?? '',
    date: form.date,
    items: form.items,
    discount: form.discount,
    tax: form.tax,
    totalAmount: totalAmount.value,
    paidAmount: form.paidAmount,
    remaining: remaining.value,
    status: status.value,
    method: form.method as Purchase['method'],
    description: form.description,
  })
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <AppSelect v-model="form.supplierId" label="تأمین‌کننده" required placeholder="انتخاب کنید" :options="supplierOptions" :error="errors.supplierId" />
      <AppDatePicker v-model="form.date" label="تاریخ خرید" required :error="errors.date" />
    </div>

    <div>
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-ink-800">اقلام خرید</span>
        <button type="button" class="text-xs font-medium text-gain-700 hover:underline" @click="addItem">+ افزودن کالا</button>
      </div>
      <div class="space-y-2">
        <div v-for="item in form.items" :key="item.id" class="grid grid-cols-12 items-center gap-2 rounded-lg border border-paper-200 p-2">
          <input v-model="item.title" placeholder="نام کالا" class="col-span-4 rounded-lg border border-paper-200 px-2 py-1.5 text-sm outline-none focus:border-gain-400">
          <input v-model.number="item.quantity" type="number" min="1" placeholder="تعداد" class="num col-span-2 rounded-lg border border-paper-200 px-2 py-1.5 text-sm outline-none focus:border-gain-400">
          <input v-model="item.unit" placeholder="واحد" class="col-span-2 rounded-lg border border-paper-200 px-2 py-1.5 text-sm outline-none focus:border-gain-400">
          <input v-model.number="item.unitPrice" type="number" min="0" placeholder="قیمت واحد" class="num col-span-3 rounded-lg border border-paper-200 px-2 py-1.5 text-sm outline-none focus:border-gain-400">
          <button type="button" class="col-span-1 rounded-lg p-1.5 text-debt-600/70 hover:bg-debt-50" @click="removeItem(item.id)">✕</button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <AppMoneyInput v-model="form.discount" label="تخفیف" />
      <AppMoneyInput v-model="form.tax" label="مالیات" />
      <AppMoneyInput v-model="form.paidAmount" label="مبلغ پرداخت‌شده" />
    </div>

    <div class="rounded-lg bg-paper-50 p-4 text-sm">
      <div class="flex justify-between py-1 text-ink-700/70"><span>جمع اقلام</span><span class="num">{{ formatCurrency(itemsTotal) }}</span></div>
      <div class="flex justify-between py-1 text-ink-700/70"><span>تخفیف</span><span class="num">- {{ formatCurrency(form.discount) }}</span></div>
      <div class="flex justify-between py-1 text-ink-700/70"><span>مالیات</span><span class="num">+ {{ formatCurrency(form.tax) }}</span></div>
      <div class="flex justify-between border-t border-paper-200 py-2 font-semibold text-ink-900"><span>مبلغ کل</span><span class="num">{{ formatCurrency(totalAmount) }}</span></div>
      <div class="flex justify-between py-1 text-debt-600"><span>مانده</span><span class="num">{{ formatCurrency(remaining) }}</span></div>
    </div>

    <AppSelect v-model="form.method" label="روش پرداخت" :options="methodOptions" />
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">توضیحات</span>
      <textarea v-model="form.description" rows="2" class="w-full rounded-lg border border-paper-200 bg-white px-3 py-2 text-sm outline-none focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20" />
    </label>

    <div class="flex justify-end gap-2 border-t border-paper-100 pt-4">
      <button type="button" class="rounded-lg border border-paper-200 px-4 py-2 text-sm font-medium text-ink-800 hover:bg-paper-50" @click="emit('cancel')">انصراف</button>
      <button type="submit" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700">ذخیره خرید</button>
    </div>
  </form>
</template>
