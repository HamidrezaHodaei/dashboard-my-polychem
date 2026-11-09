<script setup lang="ts">
import { formatCurrency } from '~/utils/financeFormat'
import { getPeriodRange, isWithinRange, periodOptions, type PeriodKey } from '~/utils/period'
import { profitLossMonthly } from '~/utils/mockData'

const txnStore = useTransactionStore()
const purchaseStore = usePurchaseStore()
const expenseStore = useExpenseStore()
onMounted(() => { txnStore.fetchAll(); purchaseStore.fetchAll(); expenseStore.fetchAll() })

const period = ref<PeriodKey>('month')
const customFrom = ref('')
const customTo = ref('')
const [from, to] = [computed(() => getPeriodRange(period.value, customFrom.value, customTo.value)[0]), computed(() => getPeriodRange(period.value, customFrom.value, customTo.value)[1])]

const revenue = computed(() => txnStore.items.filter((t) => t.type === 'receipt' && isWithinRange(t.date, from.value, to.value)).reduce((s, t) => s + t.amount, 0))
const totalPurchases = computed(() => purchaseStore.items.filter((p) => isWithinRange(p.date, from.value, to.value)).reduce((s, p) => s + p.totalAmount, 0))
const totalExpenses = computed(() => expenseStore.items.filter((e) => isWithinRange(e.date, from.value, to.value)).reduce((s, e) => s + e.amount, 0))
const grossProfit = computed(() => revenue.value - totalPurchases.value)
const netProfit = computed(() => grossProfit.value - totalExpenses.value)

const viewMode = ref<'cards' | 'table' | 'chart'>('cards')

const trendSeries = [
  { name: 'درآمد', color: '#334073', values: profitLossMonthly.map((p) => p.revenue) },
  { name: 'هزینه‌ها', color: '#C98A3E', values: profitLossMonthly.map((p) => p.expense) },
  { name: 'سود', color: '#1E7F6B', values: profitLossMonthly.map((p) => p.profit) },
]
const trendCategories = profitLossMonthly.map((p) => p.label)
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">گزارش سود و زیان</h1>
      <p class="mt-1 text-sm text-ink-700/60">مقایسه درآمد، خریدها و هزینه‌ها در بازه انتخاب‌شده</p>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppSelect v-model="period" class="w-40" :options="periodOptions" />
      <template v-if="period === 'custom'">
        <AppDatePicker v-model="customFrom" label="" />
        <AppDatePicker v-model="customTo" label="" />
      </template>
      <div class="me-auto flex gap-1 rounded-lg border border-paper-200 p-0.5 text-xs">
        <button class="rounded-md px-2.5 py-1" :class="viewMode === 'cards' ? 'bg-paper-100 text-ink-900' : 'text-ink-700/60'" @click="viewMode = 'cards'">کارت</button>
        <button class="rounded-md px-2.5 py-1" :class="viewMode === 'table' ? 'bg-paper-100 text-ink-900' : 'text-ink-700/60'" @click="viewMode = 'table'">جدول</button>
        <button class="rounded-md px-2.5 py-1" :class="viewMode === 'chart' ? 'bg-paper-100 text-ink-900' : 'text-ink-700/60'" @click="viewMode = 'chart'">نمودار</button>
      </div>
    </div>

    <div v-if="viewMode === 'cards'" class="grid grid-cols-2 gap-4 md:grid-cols-3">
      <StatCard label="مجموع درآمد" :value="revenue" tone="gain" />
      <StatCard label="مجموع خریدها" :value="totalPurchases" tone="debt" />
      <StatCard label="مجموع هزینه‌ها" :value="totalExpenses" tone="debt" />
      <StatCard label="سود ناخالص" :value="grossProfit" tone="neutral" />
      <StatCard label="سود خالص" :value="netProfit" :tone="netProfit >= 0 ? 'gain' : 'debt'" />
    </div>

    <div v-else-if="viewMode === 'table'" class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
      <table class="w-full text-right text-sm">
        <tbody>
          <tr class="border-b border-paper-100"><td class="px-4 py-3 text-ink-700/70">مجموع درآمد</td><td class="num px-4 py-3 text-left font-medium text-gain-700">{{ formatCurrency(revenue) }}</td></tr>
          <tr class="border-b border-paper-100"><td class="px-4 py-3 text-ink-700/70">مجموع خریدها</td><td class="num px-4 py-3 text-left font-medium text-debt-600">{{ formatCurrency(totalPurchases) }}</td></tr>
          <tr class="border-b border-paper-100"><td class="px-4 py-3 text-ink-700/70">سود ناخالص</td><td class="num px-4 py-3 text-left font-medium">{{ formatCurrency(grossProfit) }}</td></tr>
          <tr class="border-b border-paper-100"><td class="px-4 py-3 text-ink-700/70">مجموع هزینه‌ها</td><td class="num px-4 py-3 text-left font-medium text-debt-600">{{ formatCurrency(totalExpenses) }}</td></tr>
          <tr><td class="px-4 py-3 font-semibold text-ink-900">سود خالص</td><td class="num px-4 py-3 text-left font-bold" :class="netProfit >= 0 ? 'text-gain-700' : 'text-debt-600'">{{ formatCurrency(netProfit) }}</td></tr>
        </tbody>
      </table>
    </div>

    <div v-else class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
      <p class="mb-3 text-sm font-semibold text-ink-900">روند ۶ ماه اخیر</p>
      <FinancialChart type="line" :categories="trendCategories" :series="trendSeries" />
    </div>
  </div>
</template>
