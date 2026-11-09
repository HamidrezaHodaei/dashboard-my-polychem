<script setup lang="ts">
import { formatCurrency } from '~/utils/financeFormat'
import { buildAccountLedger } from '~/utils/ledger'

const route = useRoute()
const id = route.params.id as string
const accountStore = useAccountStore()
const txnStore = useTransactionStore()
onMounted(() => { accountStore.fetchAll(); txnStore.fetchAll() })

const account = computed(() => accountStore.byId(id))
const ledger = computed(() => account.value ? buildAccountLedger(id, txnStore.items, account.value.openingBalance) : [])
const totalIn = computed(() => ledger.value.reduce((s, e) => s + e.debit, 0))
const totalOut = computed(() => ledger.value.reduce((s, e) => s + e.credit, 0))
</script>

<template>
  <div v-if="!account" class="py-16 text-center text-sm text-ink-700/50">Account not found.</div>
  <div v-else class="space-y-5">
    <h1 class="text-lg font-bold text-ink-900">Account ledger: {{ account.name }}</h1>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard label="Opening balance" :value="account.openingBalance" tone="neutral" />
      <StatCard label="Total deposits" :value="totalIn" tone="gain" />
      <StatCard label="Total withdrawals" :value="totalOut" tone="debt" />
      <StatCard label="Current balance" :value="account.currentBalance" tone="gain" />
    </div>

    <LedgerTable :entries="ledger" />
  </div>
</template>
