<script setup lang="ts">
import { formatCurrency } from '~/utils/financeFormat'

const store = useDashboardStore()
const { summary, cashFlow, profitLoss, recentTransactions, isLoading, error } = storeToRefs(store)

onMounted(() => store.fetchDashboard())

const cashFlowSeries = computed(() => [
  { name: 'دریافت‌ها', color: '#2E9E82', values: cashFlow.value.map((p) => p.receipts) },
  { name: 'پرداخت‌ها', color: '#C15A42', values: cashFlow.value.map((p) => p.payments) },
])
const cashFlowCategories = computed(() => cashFlow.value.map((p) => p.label))

const profitLossSeries = computed(() => [
  { name: 'درآمد', color: '#334073', values: profitLoss.value.map((p) => p.revenue) },
  { name: 'هزینه‌ها', color: '#C98A3E', values: profitLoss.value.map((p) => p.expense) },
  { name: 'سود', color: '#1E7F6B', values: profitLoss.value.map((p) => p.profit) },
])
const profitLossCategories = computed(() => profitLoss.value.map((p) => p.label))
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-bold text-ink-900">پیشخوان مالی</h1>
      <p class="mt-1 text-sm text-ink-700/60">خلاصه‌ای از جریان نقدی، تراکنش‌ها و سودآوری کسب‌وکار</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="isLoading" class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <div v-for="i in 8" :key="i" class="h-28 animate-pulse rounded-xl bg-paper-200" />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="rounded-xl border border-debt-600/20 bg-debt-50 p-6 text-center">
      <p class="text-sm text-debt-600">{{ error }}</p>
      <button class="mt-3 rounded-lg bg-debt-600 px-4 py-2 text-sm font-medium text-white" @click="store.fetchDashboard()">
        تلاش مجدد
      </button>
    </div>

    <template v-else-if="summary">
      <!-- KPI cards -->
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="موجودی نقدی" :value="summary.cashBalance" tone="neutral" icon="M3 7h18M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7M3 7l2-3h14l2 3M8 12h8" />
        <StatCard label="موجودی بانکی" :value="summary.bankBalance" tone="neutral" icon="M3 21h18M4 10h16M4 10l8-6 8 6M6 10v11M18 10v11M10 14v4M14 14v4" />
        <StatCard label="مجموع دریافت‌ها" :value="summary.totalReceipts" tone="gain" icon="M12 19V5M5 12l7-7 7 7" />
        <StatCard label="مجموع پرداخت‌ها" :value="summary.totalPayments" tone="debt" icon="M12 5v14M5 12l7 7 7-7" />
        <StatCard label="بدهی مشتریان" :value="summary.totalCustomerDebt" tone="pending" icon="M12 12a4 4 0 100-8 4 4 0 000 8zM6 20a6 6 0 0112 0" />
        <StatCard label="مجموع خریدها" :value="summary.totalPurchases" tone="neutral" icon="M6 2l1.5 4M18 2l-1.5 4M4 6h16l-1.5 12h-13L4 6z" />
        <StatCard label="مجموع هزینه‌ها" :value="summary.totalExpenses" tone="debt" icon="M4 20V10M10 20V4M16 20v-7M22 20H2" />
        <StatCard label="سود خالص" :value="summary.netProfit" tone="gain" icon="M13 2L3 14h7l-1 8 11-13h-7l1-7z" />
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-ink-900">جریان نقدی (هفتگی)</h2>
          </div>
          <FinancialChart type="bar" :categories="cashFlowCategories" :series="cashFlowSeries" />
        </div>

        <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-ink-900">روند سود و زیان (ماهانه)</h2>
          </div>
          <FinancialChart type="line" :categories="profitLossCategories" :series="profitLossSeries" />
        </div>
      </div>

      <!-- Recent transactions -->
      <div>
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-ink-900">تراکنش‌های اخیر</h2>
          <NuxtLink to="/finance/transactions" class="text-xs font-medium text-gain-700 hover:underline">مشاهده همه</NuxtLink>
        </div>
        <TransactionTable :transactions="recentTransactions" />
      </div>
    </template>
  </div>
</template>
