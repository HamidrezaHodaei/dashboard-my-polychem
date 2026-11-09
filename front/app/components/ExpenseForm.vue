<script setup lang="ts">
import type { Expense } from '~/types/finance'
import { required, isPositive, validate } from '~/utils/validators'

const props = defineProps<{ initial?: Partial<Expense> }>()
const emit = defineEmits<{ (e: 'submit', payload: Omit<Expense, 'id'>): void; (e: 'cancel'): void }>()

const partyStore = usePartyStore()
const accountStore = useAccountStore()
onMounted(() => { partyStore.fetchAll(); accountStore.fetchAll() })

const categoryOptions = [
  { value: 'salary', label: 'حقوق و دستمزد' }, { value: 'rent', label: 'اجاره' }, { value: 'transport', label: 'حمل‌ونقل' },
  { value: 'electricity', label: 'برق' }, { value: 'water', label: 'آب' }, { value: 'gas', label: 'گاز' },
  { value: 'internet', label: 'اینترنت' }, { value: 'ads', label: 'تبلیغات' }, { value: 'repairs', label: 'تعمیرات' },
  { value: 'equipment', label: 'تجهیزات' }, { value: 'other', label: 'سایر' },
]
const methodOptions = [
  { value: 'cash', label: 'نقدی' }, { value: 'card', label: 'کارت' },
  { value: 'remittance', label: 'حواله' }, { value: 'bank_transfer', label: 'انتقال بانکی' }, { value: 'cheque', label: 'چک' },
]

const form = reactive({
  title: props.initial?.title ?? '',
  category: props.initial?.category ?? 'other',
  amount: props.initial?.amount ?? 0,
  date: props.initial?.date ?? new Date().toISOString(),
  method: props.initial?.method ?? 'cash',
  accountId: props.initial?.accountId ?? '',
  partyId: props.initial?.partyId ?? '',
  description: props.initial?.description ?? '',
})

const accountOptions = computed(() => accountStore.items.map((a) => ({ value: a.id, label: a.name })))
const partyOptions = computed(() => partyStore.items.map((p) => ({ value: p.id, label: p.name })))

const errors = reactive<Record<string, string | null>>({})
function validateForm() {
  errors.title = validate(form.title, [required('عنوان')])
  errors.amount = validate(form.amount, [required('مبلغ'), isPositive('مبلغ')])
  errors.accountId = validate(form.accountId, [required('حساب')])
  return !Object.values(errors).some(Boolean)
}

function submit() {
  if (!validateForm()) return
  emit('submit', { ...form } as Omit<Expense, 'id'>)
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <AppInput v-model="form.title" label="عنوان" required :error="errors.title" />
      <AppSelect v-model="form.category" label="دسته‌بندی" required :options="categoryOptions" />
      <AppMoneyInput v-model="form.amount" label="مبلغ" required :error="errors.amount" />
      <AppDatePicker v-model="form.date" label="تاریخ" required />
      <AppSelect v-model="form.method" label="روش پرداخت" :options="methodOptions" />
      <AppSelect v-model="form.accountId" label="حساب" required placeholder="انتخاب کنید" :options="accountOptions" :error="errors.accountId" />
      <AppSelect v-model="form.partyId" label="طرف‌حساب (اختیاری)" placeholder="بدون طرف‌حساب" :options="partyOptions" />
    </div>
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">توضیحات</span>
      <textarea v-model="form.description" rows="2" class="w-full rounded-lg border border-paper-200 bg-white px-3 py-2 text-sm outline-none focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20" />
    </label>
    <div class="flex justify-end gap-2 border-t border-paper-100 pt-4">
      <button type="button" class="rounded-lg border border-paper-200 px-4 py-2 text-sm font-medium text-ink-800 hover:bg-paper-50" @click="emit('cancel')">انصراف</button>
      <button type="submit" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700">ذخیره هزینه</button>
    </div>
  </form>
</template>
