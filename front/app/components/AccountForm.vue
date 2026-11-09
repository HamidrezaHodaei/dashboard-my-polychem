<script setup lang="ts">
import type { FinancialAccount } from '~/types/finance'
import { required, validate } from '~/utils/validators'

const props = defineProps<{ initial?: Partial<FinancialAccount> }>()
const emit = defineEmits<{ (e: 'submit', payload: Omit<FinancialAccount, 'id' | 'currentBalance'>): void; (e: 'cancel'): void }>()

const form = reactive({
  name: props.initial?.name ?? '',
  type: props.initial?.type ?? 'bank',
  accountNumber: props.initial?.accountNumber ?? '',
  openingBalance: props.initial?.openingBalance ?? 0,
  description: props.initial?.description ?? '',
  isActive: props.initial?.isActive ?? true,
})

const typeOptions = [
  { value: 'cash', label: 'نقدی' }, { value: 'bank', label: 'بانکی' },
  { value: 'card', label: 'کارت' }, { value: 'foreign_currency', label: 'ارز خارجی' },
]

const errors = reactive<Record<string, string | null>>({})
function validateForm() {
  errors.name = validate(form.name, [required('نام حساب')])
  return !Object.values(errors).some(Boolean)
}
function submit() {
  if (!validateForm()) return
  emit('submit', { ...form } as any)
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <AppInput v-model="form.name" label="نام حساب" required :error="errors.name" />
      <AppSelect v-model="form.type" label="نوع حساب" :options="typeOptions" />
      <AppInput v-model="form.accountNumber" label="شماره حساب" />
      <AppMoneyInput v-model="form.openingBalance" label="موجودی اولیه" />
    </div>
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">توضیحات</span>
      <textarea v-model="form.description" rows="2" class="w-full rounded-lg border border-paper-200 bg-white px-3 py-2 text-sm outline-none focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20" />
    </label>
    <label class="flex items-center gap-2 text-sm text-ink-800">
      <input v-model="form.isActive" type="checkbox" class="h-4 w-4 rounded border-paper-200 text-gain-600 focus:ring-gain-400">
      حساب فعال است
    </label>
    <div class="flex justify-end gap-2 border-t border-paper-100 pt-4">
      <button type="button" class="rounded-lg border border-paper-200 px-4 py-2 text-sm font-medium text-ink-800 hover:bg-paper-50" @click="emit('cancel')">انصراف</button>
      <button type="submit" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700">ذخیره حساب</button>
    </div>
  </form>
</template>
