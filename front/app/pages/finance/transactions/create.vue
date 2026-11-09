<script setup lang="ts">
import type { TransactionType } from '~/types/finance'

const route = useRoute()
const store = useTransactionStore()
const notify = useNotify()

const initialType = (route.query.type as TransactionType) || 'receipt'

async function handleSubmit(payload: any) {
  await store.create(payload)
  notify.success(payload.type === 'receipt' ? 'Receipt created successfully.' : 'Payment created successfully.')
  navigateTo('/finance/transactions')
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Create transaction</h1>
      <p class="mt-1 text-sm text-ink-700/60">Enter receipt or payment details</p>
    </div>
    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <TransactionForm :initial="{ type: initialType }" @submit="handleSubmit" @cancel="navigateTo('/finance/transactions')" />
    </div>
  </div>
</template>
