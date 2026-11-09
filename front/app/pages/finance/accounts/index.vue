<script setup lang="ts">
import type { FinancialAccount } from '~/types/finance'
import { formatCurrency } from '~/utils/financeFormat'

const store = useAccountStore()
const { items, isLoading, error } = storeToRefs(store)
const notify = useNotify()
const { confirm } = useConfirm()

onMounted(() => store.fetchAll())

const typeLabel: Record<FinancialAccount['type'], string> = { cash: 'نقدی', bank: 'بانکی', card: 'کارت', foreign_currency: 'ارز خارجی' }

const isEditOpen = ref(false)
const editingAccount = ref<FinancialAccount | null>(null)
function openEdit(a: FinancialAccount) { editingAccount.value = a; isEditOpen.value = true }
async function handleEditSubmit(payload: any) {
  if (editingAccount.value) {
    await store.update(editingAccount.value.id, payload)
    notify.success('حساب به‌روزرسانی شد.')
  }
  isEditOpen.value = false
}
async function handleDelete(a: FinancialAccount) {
  const ok = await confirm(`حساب «${a.name}» حذف شود؟`)
  if (!ok) return
  await store.remove(a.id)
  notify.success('حساب حذف شد.')
}

const totalBalance = computed(() => items.value.filter((a) => a.isActive).reduce((s, a) => s + a.currentBalance, 0))
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink-900">حساب‌های مالی</h1>
        <p class="mt-1 text-sm text-ink-700/60">حساب‌های نقدی، بانکی، کارتی و ارزی</p>
      </div>
      <NuxtLink to="/finance/accounts/create" class="rounded-lg bg-gain-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-gain-700">+ حساب جدید</NuxtLink>
    </div>

    <StatCard label="نقدینگی کل (حساب‌های فعال)" :value="totalBalance" tone="gain" class="max-w-xs" />

    <AppTableSkeleton v-if="isLoading" :cols="5" />
    <AppErrorState v-else-if="error" :message="error" @retry="store.fetchAll()" />
    <AppEmptyState v-else-if="!items.length" title="هنوز حسابی ثبت نشده است." action-label="ایجاد حساب" @action="navigateTo('/finance/accounts/create')" />

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="a in items" :key="a.id" class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-sm font-semibold text-ink-900">{{ a.name }}</p>
            <p class="mt-0.5 text-xs text-ink-700/50">{{ typeLabel[a.type] }}<span v-if="a.accountNumber"> · {{ a.accountNumber }}</span></p>
          </div>
          <AppStatusBadge :label="a.isActive ? 'فعال' : 'غیرفعال'" :tone="a.isActive ? 'gain' : 'neutral'" />
        </div>
        <p class="num mt-4 text-xl font-bold text-ink-900">{{ formatCurrency(a.currentBalance) }}</p>
        <div class="mt-4 flex items-center gap-2 border-t border-paper-100 pt-3">
          <NuxtLink :to="`/finance/accounts/${a.id}`" class="flex-1 rounded-lg border border-paper-200 py-1.5 text-center text-xs font-medium text-ink-800 hover:bg-paper-50">مشاهده دفتر حساب</NuxtLink>
          <button class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100" @click="openEdit(a)">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.1 2.1 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </button>
          <button class="rounded-lg p-1.5 text-debt-600/70 hover:bg-debt-50" @click="handleDelete(a)">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6h16z" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </button>
        </div>
      </div>
    </div>

    <AppModal v-model="isEditOpen" title="ویرایش حساب">
      <AccountForm v-if="editingAccount" :initial="editingAccount" @submit="handleEditSubmit" @cancel="isEditOpen = false" />
    </AppModal>
  </div>
</template>
