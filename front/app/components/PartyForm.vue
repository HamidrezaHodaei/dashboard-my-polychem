<script setup lang="ts">
import type { Party, PartyType } from '~/types/finance'
import { required, isPhone, isEmail, validate } from '~/utils/validators'

const props = defineProps<{ initial?: Partial<Party> }>()
const emit = defineEmits<{ (e: 'submit', payload: Omit<Party, 'id' | 'balance' | 'lastTransactionAt'>): void; (e: 'cancel'): void }>()

const form = reactive({
  name: props.initial?.name ?? '',
  type: (props.initial?.type ?? 'customer') as PartyType,
  phone: props.initial?.phone ?? '',
  mobile: props.initial?.mobile ?? '',
  nationalId: props.initial?.nationalId ?? '',
  economicCode: props.initial?.economicCode ?? '',
  address: props.initial?.address ?? '',
  city: props.initial?.city ?? '',
  email: props.initial?.email ?? '',
  description: props.initial?.description ?? '',
  isActive: props.initial?.isActive ?? true,
})

const typeOptions = [
  { value: 'customer', label: 'مشتری' },
  { value: 'supplier', label: 'تأمین‌کننده' },
  { value: 'person', label: 'شخص' },
  { value: 'company', label: 'شرکت' },
]

const errors = reactive<Record<string, string | null>>({})

function validateForm() {
  errors.name = validate(form.name, [required('نام')])
  errors.mobile = validate(form.mobile, [required('موبایل'), isPhone('موبایل')])
  errors.email = validate(form.email, [isEmail()])
  return !Object.values(errors).some(Boolean)
}

function submit() {
  if (!validateForm()) return
  emit('submit', { ...form })
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <AppInput v-model="form.name" label="نام / نام شرکت" required :error="errors.name" />
      <AppSelect v-model="form.type" label="نوع طرف‌حساب" required :options="typeOptions" />
      <AppInput v-model="form.phone" label="تلفن" />
      <AppInput v-model="form.mobile" label="موبایل" required :error="errors.mobile" />
      <AppInput v-model="form.nationalId" label="شناسه ملی" />
      <AppInput v-model="form.economicCode" label="کد اقتصادی" />
      <AppInput v-model="form.city" label="شهر" />
      <AppInput v-model="form.email" label="ایمیل" type="email" :error="errors.email" />
    </div>
    <AppInput v-model="form.address" label="نشانی" />
    <label class="block">
      <span class="mb-1.5 block text-sm text-ink-800">توضیحات</span>
      <textarea v-model="form.description" rows="3" class="w-full rounded-lg border border-paper-200 bg-white px-3 py-2 text-sm outline-none focus:border-gain-400 focus:ring-2 focus:ring-gain-400/20" />
    </label>
    <label class="flex items-center gap-2 text-sm text-ink-800">
      <input v-model="form.isActive" type="checkbox" class="h-4 w-4 rounded border-paper-200 text-gain-600 focus:ring-gain-400">
      طرف‌حساب فعال است
    </label>

    <div class="flex justify-end gap-2 border-t border-paper-100 pt-4">
      <button type="button" class="rounded-lg border border-paper-200 px-4 py-2 text-sm font-medium text-ink-800 hover:bg-paper-50" @click="emit('cancel')">
        انصراف
      </button>
      <button type="submit" class="rounded-lg bg-gain-600 px-4 py-2 text-sm font-medium text-white hover:bg-gain-700">
        ذخیره طرف‌حساب
      </button>
    </div>
  </form>
</template>
