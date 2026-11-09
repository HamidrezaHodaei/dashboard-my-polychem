<script setup lang="ts">
import type { Purchase, Expense } from '~/types/finance'
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const purchaseStore = usePurchaseStore()
const expenseStore = useExpenseStore()
const notify = useNotify()
const { confirm } = useConfirm()

onMounted(() => { purchaseStore.fetchAll(); expenseStore.fetchAll() })

const activeTab = ref<'purchases' | 'expenses'>('purchases')
const search = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')
const page = ref(1)
const pageSize = 8

watch(activeTab, () => { page.value = 1; search.value = ''; statusFilter.value = ''; categoryFilter.value = '' })

const filteredPurchases = computed(() => purchaseStore.items.filter((p) => {
  if (search.value && !p.supplierName.includes(search.value) && !p.invoiceNumber.includes(search.value)) return false
  if (statusFilter.value && p.status !== statusFilter.value) return false
  return true
}))
const filteredExpenses = computed(() => expenseStore.items.filter((e) => {
  if (search.value && !e.title.includes(search.value)) return false
  if (categoryFilter.value && e.category !== categoryFilter.value) return false
  return true
}))

const pagedPurchases = computed(() => filteredPurchases.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const pagedExpenses = computed(() => filteredExpenses.value.slice((page.value - 1) * pageSize, page.value * pageSize))

const categoryLabel: Record<Expense['category'], string> = {
  salary: 'حقوق', rent: 'اجاره', transport: 'حمل و نقل', electricity: 'برق', water: 'آب', gas: 'گاز',
  internet: 'Internet', ads: 'Advertising', repairs: 'Repairs', equipment: 'Equipment', other: 'Other',
}
const statusLabel: Record<Purchase['status'], string> = { paid: 'Paid', partial: 'Partially paid', unpaid: 'Unpaid' }
const statusTone: Record<Purchase['status'], 'gain' | 'pending' | 'debt'> = { paid: 'gain', partial: 'pending', unpaid: 'debt' }

async function deletePurchase(p: Purchase) {
  const ok = await confirm(`Delete invoice “${p.invoiceNumber}”?`)
  if (!ok) return
  await purchaseStore.remove(p.id)
  notify.success('Purchase deleted.')
}
async function deleteExpense(e: Expense) {
  const ok = await confirm(`Delete expense “${e.title}”?`)
  if (!ok) return
  await expenseStore.remove(e.id)
  notify.success('Expense deleted.')
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink-900">Purchases and expenses</h1>
        <p class="mt-1 text-sm text-ink-700/60">Manage purchase invoices and ongoing business expenses</p>
      </div>
      <NuxtLink :to="activeTab === 'purchases' ? '/finance/purchases/create' : '/finance/expenses/create'" class="rounded-lg bg-gain-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-gain-700">
        {{ activeTab === 'purchases' ? '+ New purchase' : '+ New expense' }}
      </NuxtLink>
    </div>

    <div class="flex gap-1 border-b border-paper-200">
      <button class="border-b-2 px-3 py-2.5 text-sm font-medium" :class="activeTab === 'purchases' ? 'border-gain-600 text-gain-700' : 'border-transparent text-ink-700/60'" @click="activeTab = 'purchases'">Purchase invoices</button>
      <button class="border-b-2 px-3 py-2.5 text-sm font-medium" :class="activeTab === 'expenses' ? 'border-gain-600 text-gain-700' : 'border-transparent text-ink-700/60'" @click="activeTab = 'expenses'">Expenses</button>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppSearchInput v-model="search" placeholder="جستجو..." />
      <AppSelect v-if="activeTab === 'purchases'" v-model="statusFilter" placeholder="All statuses" class="w-40" :options="[{ value: 'paid', label: 'Paid' }, { value: 'partial', label: 'Partially paid' }, { value: 'unpaid', label: 'Unpaid' }]" />
      <AppSelect v-else v-model="categoryFilter" placeholder="همه دسته‌ها" class="w-44" :options="Object.entries(categoryLabel).map(([value, label]) => ({ value, label }))" />
    </div>

    <!-- Purchases tab -->
    <template v-if="activeTab === 'purchases'">
      <AppTableSkeleton v-if="purchaseStore.isLoading" :cols="7" />
      <AppErrorState v-else-if="purchaseStore.error" :message="purchaseStore.error" @retry="purchaseStore.fetchAll()" />
      <AppEmptyState v-else-if="!filteredPurchases.length" title="No purchase invoices have been recorded." action-label="Create purchase" @action="navigateTo('/finance/purchases/create')" />
      <template v-else>
        <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
          <table class="w-full min-w-[820px] text-right text-sm">
            <thead>
              <tr class="border-b border-paper-200 text-xs text-ink-700/60">
                <th class="px-4 py-3 font-medium">شماره فاکتور</th>
                <th class="px-4 py-3 font-medium">Date</th>
                <th class="px-4 py-3 font-medium">Supplier</th>
                <th class="px-4 py-3 font-medium">Amount</th>
                <th class="px-4 py-3 font-medium">Paid</th>
                <th class="px-4 py-3 font-medium">Remaining</th>
                <th class="px-4 py-3 font-medium">Status</th>
                <th class="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in pagedPurchases" :key="p.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
                <td class="px-4 py-3 text-ink-900">{{ p.invoiceNumber }}</td>
                <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(p.date) }}</td>
                <td class="px-4 py-3 text-ink-900">{{ p.supplierName }}</td>
                <td class="num px-4 py-3 font-medium">{{ formatCurrency(p.totalAmount) }}</td>
                <td class="num px-4 py-3 text-gain-700">{{ formatCurrency(p.paidAmount) }}</td>
                <td class="num px-4 py-3 text-debt-600">{{ formatCurrency(p.remaining) }}</td>
                <td class="px-4 py-3"><AppStatusBadge :label="statusLabel[p.status]" :tone="statusTone[p.status]" /></td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1">
                    <NuxtLink :to="`/finance/purchases/${p.id}`" class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100">
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke-linecap="round" stroke-linejoin="round" /><circle cx="12" cy="12" r="3" /></svg>
                    </NuxtLink>
                    <button class="rounded-lg p-1.5 text-debt-600/70 hover:bg-debt-50" @click="deletePurchase(p)">
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6h16z" stroke-linecap="round" stroke-linejoin="round" /></svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <AppPagination v-model:page="page" :page-size="pageSize" :total="filteredPurchases.length" />
      </template>
    </template>

    <!-- Expenses tab -->
    <template v-else>
      <AppTableSkeleton v-if="expenseStore.isLoading" :cols="6" />
      <AppEmptyState v-else-if="!filteredExpenses.length" title="No expenses have been recorded." action-label="Create expense" @action="navigateTo('/finance/expenses/create')" />
      <template v-else>
        <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
          <table class="w-full min-w-[700px] text-right text-sm">
            <thead>
              <tr class="border-b border-paper-200 text-xs text-ink-700/60">
                <th class="px-4 py-3 font-medium">عنوان</th>
                <th class="px-4 py-3 font-medium">دسته‌بندی</th>
                <th class="px-4 py-3 font-medium">Date</th>
                <th class="px-4 py-3 font-medium">Amount</th>
                <th class="px-4 py-3 font-medium">Payment method</th>
                <th class="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in pagedExpenses" :key="e.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
                <td class="px-4 py-3 text-ink-900">{{ e.title }}</td>
                <td class="px-4 py-3 text-ink-700/70">{{ categoryLabel[e.category] }}</td>
                <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(e.date) }}</td>
                <td class="num px-4 py-3 font-medium text-debt-600">{{ formatCurrency(e.amount) }}</td>
                <td class="px-4 py-3 text-ink-700/70">{{ e.method }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1">
                    <NuxtLink :to="`/finance/expenses/${e.id}`" class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100">
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke-linecap="round" stroke-linejoin="round" /><circle cx="12" cy="12" r="3" /></svg>
                    </NuxtLink>
                    <button class="rounded-lg p-1.5 text-debt-600/70 hover:bg-debt-50" @click="deleteExpense(e)">
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6h16z" stroke-linecap="round" stroke-linejoin="round" /></svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <AppPagination v-model:page="page" :page-size="pageSize" :total="filteredExpenses.length" />
      </template>
    </template>
  </div>
</template>
