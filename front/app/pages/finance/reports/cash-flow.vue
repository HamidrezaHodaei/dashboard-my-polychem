<script setup lang="ts">
import { formatCurrency } from '~/utils/financeFormat'
import { getPeriodRange, isWithinRange, periodOptions, type PeriodKey } from '~/utils/period'
import { cashFlowWeekly } from '~/utils/mockData'

const accountStore = useAccountStore()
const txnStore = useTransactionStore()
onMounted(() => { accountStore.fetchAll(); txnStore.fetchAll() })

const period = ref<PeriodKey>('month')
const customFrom = ref('')
const customTo = ref('')
const from = computed(() => getPeriodRange(period.value, customFrom.value, customTo.value)[0])
const to = computed(() => getPeriodRange(period.value, customFrom.value, customTo.value)[1])

const cashAccounts = computed(() => accountStore.items.filter((a) => a.type === 'cash'))
const bankAccounts = computed(() => accountStore.items.filter((a) => a.type === 'bank' || a.type === 'card'))

const cashBalance = computed(() => cashAccounts.value.reduce((s, a) => s + a.currentBalance, 0))
const bankBalance = computed(() => bankAccounts.value.reduce((s, a) => s + a.currentBalance, 0))
const totalLiquidity = computed(() => cashBalance.value + bankBalance.value)

function sumFor(accounts: { id: string }[], type: 'receipt' | 'payment') {
  const ids = new Set(accounts.map((a) => a.id))
  return txnStore.items
    .filter((t) => ids.has(t.accountId) && t.type === type && isWithinRange(t.date, from.value, to.value))
    .reduce((s, t) => s + t.amount, 0)
}
const cashIn = computed(() => sumFor(cashAccounts.value, 'receipt'))
const cashOut = computed(() => sumFor(cashAccounts.value, 'payment'))
const bankIn = computed(() => sumFor(bankAccounts.value, 'receipt'))
const bankOut = computed(() => sumFor(bankAccounts.value, 'payment'))

const chartSeries = [
  { name: 'Receipts', color: '#2E9E82', values: cashFlowWeekly.map((p) => p.receipts) },
  { name: 'Payments', color: '#C15A42', values: cashFlowWeekly.map((p) => p.payments) },
]
const chartCategories = cashFlowWeekly.map((p) => p.label)
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Cash flow report</h1>
      <p class="mt-1 text-sm text-ink-700/60">Cash, bank, and total liquidity for the selected period</p>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppSelect v-model="period" class="w-40" :options="periodOptions" />
      <template v-if="period === 'custom'">
        <AppDatePicker v-model="customFrom" label="" />
        <AppDatePicker v-model="customTo" label="" />
      </template>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
        <p class="text-sm font-semibold text-ink-900">Cash</p>
        <p class="num mt-2 text-lg font-bold text-ink-900">{{ formatCurrency(cashBalance) }}</p>
        <div class="mt-3 space-y-1 text-xs text-ink-700/60">
          <div class="flex justify-between"><span>Total receipts</span><span class="num text-gain-700">{{ formatCurrency(cashIn) }}</span></div>
          <div class="flex justify-between"><span>Total payments</span><span class="num text-debt-600">{{ formatCurrency(cashOut) }}</span></div>
        </div>
      </div>
      <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
        <p class="text-sm font-semibold text-ink-900">Bank</p>
        <p class="num mt-2 text-lg font-bold text-ink-900">{{ formatCurrency(bankBalance) }}</p>
        <div class="mt-3 space-y-1 text-xs text-ink-700/60">
          <div class="flex justify-between"><span>Total deposits</span><span class="num text-gain-700">{{ formatCurrency(bankIn) }}</span></div>
          <div class="flex justify-between"><span>Total withdrawals</span><span class="num text-debt-600">{{ formatCurrency(bankOut) }}</span></div>
        </div>
      </div>
      <div class="rounded-xl border border-gain-600/20 bg-gain-50 p-4 shadow-card">
        <p class="text-sm font-semibold text-gain-700">کل نقدینگی</p>
        <p class="num mt-2 text-xl font-bold text-gain-700">{{ formatCurrency(totalLiquidity) }}</p>
        <p class="mt-3 text-xs text-gain-700/70">Cash balance + bank balance</p>
      </div>
    </div>

    <div class="rounded-xl border border-paper-200 bg-white p-4 shadow-card">
      <p class="mb-3 text-sm font-semibold text-ink-900">نمودار جریان نقدینگی (هفتگی)</p>
      <FinancialChart type="bar" :categories="chartCategories" :series="chartSeries" />
    </div>
  </div>
</template>
