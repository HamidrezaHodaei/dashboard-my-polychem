<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'
import { buildPartyLedger } from '~/utils/ledger'

const route = useRoute()
const partyId = route.params.id as string

const partyStore = usePartyStore()
const txnStore = useTransactionStore()
const purchaseStore = usePurchaseStore()

onMounted(async () => {
  await Promise.all([partyStore.fetchAll(), txnStore.fetchAll(), purchaseStore.fetchAll()])
})

const party = computed(() => partyStore.byId(partyId))
const typeLabel: Record<string, string> = { customer: 'Customer', supplier: 'Supplier', person: 'Person', company: 'Company' }

const partyTransactions = computed(() => txnStore.items.filter((t) => t.partyId === partyId))
const partyPurchases = computed(() => purchaseStore.items.filter((p) => p.supplierId === partyId))
const ledger = computed(() => buildPartyLedger(partyId, txnStore.items, purchaseStore.items))

const totalDebit = computed(() => ledger.value.reduce((s, e) => s + e.debit, 0))
const totalCredit = computed(() => ledger.value.reduce((s, e) => s + e.credit, 0))
const balance = computed(() => totalDebit.value - totalCredit.value)

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'ledger', label: 'Ledger' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'purchases', label: 'Purchases' },
]
const activeTab = ref('overview')
</script>

<template>
  <div v-if="!party" class="py-16 text-center text-sm text-ink-700/50">Party not found.</div>
  <div v-else class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="flex h-12 w-12 items-center justify-center rounded-full bg-ink-800 text-sm font-semibold text-white">
          {{ party.name.slice(0, 2) }}
        </div>
        <div>
          <h1 class="text-lg font-bold text-ink-900">{{ party.name }}</h1>
          <p class="text-sm text-ink-700/60">{{ typeLabel[party.type] }} · {{ party.mobile }}</p>
        </div>
      </div>
      <AppStatusBadge :label="party.isActive ? 'Active' : 'Inactive'" :tone="party.isActive ? 'gain' : 'neutral'" />
    </div>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard label="Account balance" :value="Math.abs(balance)" :tone="balance >= 0 ? 'debt' : 'gain'" />
      <StatCard label="Total debits" :value="totalDebit" tone="debt" />
      <StatCard label="Total credits" :value="totalCredit" tone="gain" />
      <StatCard
        label="Last transaction"
        :value="0"
        tone="neutral"
        :hint="party.lastTransactionAt ? formatJalaliDate(party.lastTransactionAt) : 'No transactions'"
      />
    </div>

    <div class="flex gap-1 border-b border-paper-200">
      <button
        v-for="tab in tabs" :key="tab.key"
        class="border-b-2 px-3 py-2.5 text-sm font-medium transition-colors"
        :class="activeTab === tab.key ? 'border-gain-600 text-gain-700' : 'border-transparent text-ink-700/60 hover:text-ink-900'"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'overview'" class="grid grid-cols-1 gap-4 rounded-xl border border-paper-200 bg-white p-5 shadow-card sm:grid-cols-2">
      <div><p class="text-xs text-ink-700/50">Phone</p><p class="mt-1 num text-sm text-ink-900">{{ party.phone || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Mobile</p><p class="mt-1 num text-sm text-ink-900">{{ party.mobile }}</p></div>
      <div><p class="text-xs text-ink-700/50">National ID</p><p class="mt-1 num text-sm text-ink-900">{{ party.nationalId || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Economic code</p><p class="mt-1 num text-sm text-ink-900">{{ party.economicCode || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">City</p><p class="mt-1 text-sm text-ink-900">{{ party.city || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Email</p><p class="mt-1 text-sm text-ink-900">{{ party.email || '—' }}</p></div>
      <div class="sm:col-span-2"><p class="text-xs text-ink-700/50">Address</p><p class="mt-1 text-sm text-ink-900">{{ party.address || '—' }}</p></div>
      <div v-if="party.description" class="sm:col-span-2"><p class="text-xs text-ink-700/50">Description</p><p class="mt-1 text-sm text-ink-900">{{ party.description }}</p></div>
    </div>

    <LedgerTable v-else-if="activeTab === 'ledger'" :entries="ledger" />

    <TransactionTable v-else-if="activeTab === 'transactions'" :transactions="partyTransactions" />

    <div v-else-if="activeTab === 'purchases'" class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
      <table class="w-full min-w-150 text-right text-sm">
        <thead>
          <tr class="border-b border-paper-200 text-xs text-ink-700/60">
            <th class="px-4 py-3 font-medium">Invoice number</th>
            <th class="px-4 py-3 font-medium">Date</th>
            <th class="px-4 py-3 font-medium">Amount</th>
            <th class="px-4 py-3 font-medium">Remaining</th>
            <th class="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!partyPurchases.length"><td colspan="5" class="px-4 py-10 text-center text-ink-700/50">No purchases have been recorded.</td></tr>
          <tr v-for="p in partyPurchases" :key="p.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
            <td class="px-4 py-3 text-ink-900">{{ p.invoiceNumber }}</td>
            <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(p.date) }}</td>
            <td class="num px-4 py-3">{{ formatCurrency(p.totalAmount) }}</td>
            <td class="num px-4 py-3">{{ formatCurrency(p.remaining) }}</td>
            <td class="px-4 py-3">
              <AppStatusBadge
                :label="p.status === 'paid' ? 'Paid' : p.status === 'partial' ? 'Partially paid' : 'Unpaid'"
                :tone="p.status === 'paid' ? 'gain' : p.status === 'partial' ? 'pending' : 'debt'"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
