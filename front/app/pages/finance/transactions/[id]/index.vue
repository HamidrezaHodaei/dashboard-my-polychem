<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const route = useRoute()
const id = route.params.id as string
const store = useTransactionStore()
const notify = useNotify()
const { confirm } = useConfirm()

onMounted(() => store.fetchAll())
const txn = computed(() => store.byId(id))
const isEditing = ref(false)

const methodLabel: Record<string, string> = { cash: 'Cash', card: 'Card', remittance: 'Remittance', bank_transfer: 'Bank transfer', cheque: 'Cheque' }

async function handleUpdate(payload: any) {
  await store.update(id, payload)
  isEditing.value = false
  notify.success('Transaction updated.')
}
async function handleDelete() {
  const ok = await confirm('Delete this transaction?')
  if (!ok) return
  await store.remove(id)
  notify.success('Transaction deleted.')
  navigateTo('/finance/transactions')
}
</script>

<template>
  <div v-if="!txn" class="py-16 text-center text-sm text-ink-700/50">Transaction not found.</div>
  <div v-else class="mx-auto max-w-2xl space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-ink-900">Transaction {{ txn.number }}</h1>
      <div class="flex gap-2">
        <button v-if="!isEditing" class="rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-800 hover:bg-paper-50" @click="isEditing = true">Edit</button>
        <button class="rounded-lg border border-debt-600/30 px-3 py-2 text-sm text-debt-600 hover:bg-debt-50" @click="handleDelete">Delete</button>
      </div>
    </div>

    <div v-if="!isEditing" class="grid grid-cols-1 gap-4 rounded-xl border border-paper-200 bg-white p-5 shadow-card sm:grid-cols-2">
      <div><p class="text-xs text-ink-700/50">Type</p><p class="mt-1 text-sm" :class="txn.type === 'receipt' ? 'text-gain-700' : 'text-debt-600'">{{ txn.type === 'receipt' ? 'Receipt' : 'Payment' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Party</p><p class="mt-1 text-sm text-ink-900">{{ txn.partyName }}</p></div>
      <div><p class="text-xs text-ink-700/50">Amount</p><p class="num mt-1 text-sm font-semibold text-ink-900">{{ formatCurrency(txn.amount) }}</p></div>
      <div><p class="text-xs text-ink-700/50">Date</p><p class="num mt-1 text-sm text-ink-900">{{ formatJalaliDate(txn.date) }}</p></div>
      <div><p class="text-xs text-ink-700/50">Payment method</p><p class="mt-1 text-sm text-ink-900">{{ methodLabel[txn.method] }}</p></div>
      <div><p class="text-xs text-ink-700/50">Tracking number</p><p class="num mt-1 text-sm text-ink-900">{{ txn.trackingCode || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Invoice number</p><p class="mt-1 text-sm text-ink-900">{{ txn.invoiceNumber || '—' }}</p></div>
      <div><p class="text-xs text-ink-700/50">Status</p><p class="mt-1"><AppStatusBadge :label="txn.status === 'confirmed' ? 'Confirmed' : 'Pending'" :tone="txn.status === 'confirmed' ? 'gain' : 'pending'" /></p></div>
      <div v-if="txn.description" class="sm:col-span-2"><p class="text-xs text-ink-700/50">Description</p><p class="mt-1 text-sm text-ink-900">{{ txn.description }}</p></div>
    </div>

    <div v-else class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <TransactionForm :initial="txn" @submit="handleUpdate" @cancel="isEditing = false" />
    </div>
  </div>
</template>
