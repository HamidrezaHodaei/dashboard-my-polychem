<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'
import { buildPartyLedger } from '~/utils/ledger'

const route = useRoute()
const id = route.params.id as string
const customerStore = useCustomerStore()
const txnStore = useTransactionStore()

onMounted(() => { customerStore.fetchAll(); txnStore.fetchAll() })

const customer = computed(() => customerStore.byId(id))
const payments = computed(() => txnStore.items.filter((t) => t.partyId === id && t.type === 'receipt'))
const ledger = computed(() => buildPartyLedger(id, txnStore.items))
const totalDebit = computed(() => ledger.value.reduce((s, e) => s + e.debit, 0))
const totalCredit = computed(() => ledger.value.reduce((s, e) => s + e.credit, 0))
const balance = computed(() => totalDebit.value - totalCredit.value)

const viewMode = ref<'timeline' | 'table'>('timeline')
</script>

<template>
  <div v-if="!customer" class="py-16 text-center text-sm text-ink-700/50">Customer not found.</div>
  <div v-else class="space-y-5">
    <div class="flex items-center gap-3">
      <div class="flex h-12 w-12 items-center justify-center rounded-full bg-ink-800 text-sm font-semibold text-white">{{ customer.name.slice(0, 2) }}</div>
      <div>
        <h1 class="text-lg font-bold text-ink-900">{{ customer.name }}</h1>
        <p class="text-sm text-ink-700/60">{{ customer.mobile }}</p>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard label="مجموع بدهکاری" :value="totalDebit" tone="debt" />
      <StatCard label="مجموع بستانکاری" :value="totalCredit" tone="gain" />
      <StatCard label="Outstanding balance" :value="Math.abs(balance)" :tone="balance > 0 ? 'debt' : 'gain'" />
      <StatCard :value="0" label="Last payment" tone="neutral" :hint="customer.lastTransactionAt ? formatJalaliDate(customer.lastTransactionAt) : 'Not recorded'" />
    </div>

    <div>
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-ink-900">Payment history</h2>
      </div>
      <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
        <table class="w-full min-w-[560px] text-right text-sm">
          <thead>
            <tr class="border-b border-paper-200 text-xs text-ink-700/60">
              <th class="px-4 py-3 font-medium">Date</th>
              <th class="px-4 py-3 font-medium">Amount</th>
              <th class="px-4 py-3 font-medium">Payment method</th>
              <th class="px-4 py-3 font-medium">شماره پیگیری</th>
              <th class="px-4 py-3 font-medium">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!payments.length"><td colspan="5" class="px-4 py-10 text-center text-ink-700/50">No payments have been recorded.</td></tr>
            <tr v-for="p in payments" :key="p.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
              <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(p.date) }}</td>
              <td class="num px-4 py-3 font-medium text-gain-700">{{ formatCurrency(p.amount) }}</td>
              <td class="px-4 py-3 text-ink-700/70">{{ p.method }}</td>
              <td class="num px-4 py-3 text-ink-700/70">{{ p.trackingCode || '—' }}</td>
              <td class="px-4 py-3 text-ink-700/70">{{ p.description || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-ink-900">Account ledger</h2>
        <div class="flex gap-1 rounded-lg border border-paper-200 p-0.5 text-xs">
          <button class="rounded-md px-2.5 py-1" :class="viewMode === 'timeline' ? 'bg-paper-100 text-ink-900' : 'text-ink-700/60'" @click="viewMode = 'timeline'">Timeline</button>
          <button class="rounded-md px-2.5 py-1" :class="viewMode === 'table' ? 'bg-paper-100 text-ink-900' : 'text-ink-700/60'" @click="viewMode = 'table'">جدول</button>
        </div>
      </div>

      <LedgerTable v-if="viewMode === 'table'" :entries="ledger" />
      <ol v-else class="relative space-y-5 border-e-2 border-paper-200 pe-5">
        <li v-if="!ledger.length" class="text-sm text-ink-700/50">No transactions have been recorded.</li>
        <li v-for="e in ledger" :key="e.id" class="relative">
          <span class="absolute -right-[27px] top-1 h-3 w-3 rounded-full" :class="e.debit ? 'bg-debt-600' : 'bg-gain-600'" />
          <p class="num text-xs text-ink-700/50">{{ formatJalaliDate(e.date) }}</p>
          <p class="text-sm text-ink-900">{{ e.description }}</p>
          <p class="num text-sm font-medium" :class="e.debit ? 'text-debt-600' : 'text-gain-700'">
            {{ e.debit ? '+ ' + formatCurrency(e.debit) : '- ' + formatCurrency(e.credit) }}
          </p>
        </li>
      </ol>
    </div>
  </div>
</template>
