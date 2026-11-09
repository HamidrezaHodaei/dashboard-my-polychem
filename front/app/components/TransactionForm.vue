<script setup lang="ts">
import type { Transaction, TransactionType } from '~/types/finance'
import { required, isPositive, validate } from '~/utils/validators'

const props = defineProps<{ initial?: Partial<Transaction>; fixedType?: TransactionType }>()
const emit = defineEmits<{ (e: 'submit', payload: Omit<Transaction, 'id' | 'number' | 'status'>): void; (e: 'cancel'): void }>()

const partyStore = usePartyStore()
const accountStore = useAccountStore()
onMounted(() => { partyStore.fetchAll(); accountStore.fetchAll() })

const form = reactive({
  type: props.fixedType ?? props.initial?.type ?? 'receipt' as TransactionType,
  partyId: props.initial?.partyId ?? '',
  amount: props.initial?.amount ?? 0,
  date: props.initial?.date ?? new Date().toISOString(),
  method: props.initial?.method ?? 'cash',
  accountId: props.initial?.accountId ?? '',
  trackingCode: props.initial?.trackingCode ?? '',
  invoiceNumber: props.initial?.invoiceNumber ?? '',
  description: props.initial?.description ?? '',
})

const methodOptions = [
  { value: 'cash', label: 'نقدی' }, { value: 'card', label: 'کارت' },
  { value: 'remittance', label: 'حواله' }, { value: 'bank_transfer', label: 'انتقال بانکی' },
  { value: 'cheque', label: 'چک' },
]
const partyOptions = computed(() => partyStore.items.map((p) => ({ value: p.id, label: p.name })))
const accountOptions = computed(() => accountStore.items.map((a) => ({ value: a.id, label: a.name })))

const errors = reactive<Record<string, string | null>>({})
function validateForm() {
  errors.partyId = validate(form.partyId, [required('طرف‌حساب')])
  errors.amount = validate(form.amount, [required('مبلغ'), isPositive('مبلغ')])
  errors.accountId = validate(form.accountId, [required('حساب')])
  errors.date = validate(form.date, [required('تاریخ')])
  return !Object.values(errors).some(Boolean)
}

function submit() {
  if (!validateForm()) return
  const party = partyStore.byId(form.partyId)
  emit('submit', { ...form, partyName: party?.name ?? '' })
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div v-if="!fixedType" class="flex gap-2">
      <button
        v-for="t in [{ v: 'receipt', l: 'دریافت' }, { v: 'payment', l: 'پرداخت' }]" :key="t.v" type="button"
        class="flex-1 rounded-lg border py-2 text-sm font-medium"
        :class="form.type === t.v ? (t.v === 'receipt' ? 'border-gain-600 bg-gain-50 text-gain-700' : 'border-debt-600 bg-debt-50 text-debt-600') : 'border-paper-200 text-ink-700/60'"
        @click="form.type = t.v as TransactionType"
      >{{ t.l }}</button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <AppSelect v-model="form.partyId" label="طرف‌حساب" required placeholder="انتخاب کنید" :options="partyOptions" :error="errors.partyId" />
      <AppMoneyInput v-model="form.amount" label="مبلغ" required :error="errors.amount" />
      <AppDatePicker v-model="form.date" label="تاریخ" required :error="errors.date" />
      <AppSelect v-model="form.method" label="روش پرداخت" required :options="methodOptions" />
      <AppSelect v-model="form.accountId" :label="form.type === 'receipt' ? 'حساب مقصد' : 'حساب مبدأ'" required placeholder="انتخاب کنید" :options="accountOptions" :error="errors.accountId" />
      <AppInput v-model="form.trackingCode" label="شماره پیگیری" />
      <AppInput v-model="form.invoiceNumber" label="شماره فاکتور" />
    </div>
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">توضیحات</span>
      <textarea v-model="form.description" rows="2" class="w-full rounded-lg border border-paper-200 bg-white px-3 py-2 text-sm outline-none focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20" />
    </label>
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">پیوست</span>
      <input type="file" class="block w-full text-sm text-ink-700/70 file:me-3 file:rounded-lg file:border-0 file:bg-paper-100 file:px-3 file:py-1.5 file:text-xs">
    </label>

    <div class="flex justify-end gap-2 border-t border-paper-100 pt-4">
      <button type="button" class="rounded-lg border border-paper-200 px-4 py-2 text-sm font-medium text-ink-800 hover:bg-paper-50" @click="emit('cancel')">انصراف</button>
      <button type="submit" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700">ذخیره تراکنش</button>
    </div>
  </form>
</template>
