<script setup lang="ts">
const store = usePurchaseStore()
const notify = useNotify()

async function handleSubmit(payload: any) {
  await store.create(payload)
  notify.success('Purchase created successfully.')
  navigateTo('/finance/purchases')
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Create purchase</h1>
      <p class="mt-1 text-sm text-ink-700/60">Enter items, discount, and tax to calculate the final amount</p>
    </div>
    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <PurchaseForm @submit="handleSubmit" @cancel="navigateTo('/finance/purchases')" />
    </div>
  </div>
</template>
