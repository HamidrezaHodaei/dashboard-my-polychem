<script setup lang="ts">
const store = useExpenseStore()
const notify = useNotify()

async function handleSubmit(payload: any) {
  await store.create(payload)
  notify.success('Expense created successfully.')
  navigateTo('/finance/purchases')
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Create expense</h1>
      <p class="mt-1 text-sm text-ink-700/60">Categorize and record business expenses</p>
    </div>
    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <ExpenseForm @submit="handleSubmit" @cancel="navigateTo('/finance/purchases')" />
    </div>
  </div>
</template>
