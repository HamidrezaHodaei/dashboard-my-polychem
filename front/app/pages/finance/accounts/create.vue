<script setup lang="ts">
const store = useAccountStore()
const notify = useNotify()

async function handleSubmit(payload: any) {
  await store.create(payload)
  notify.success('Account created successfully.')
  navigateTo('/finance/accounts')
}
</script>

<template>
  <div class="mx-auto max-w-xl space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Create financial account</h1>
      <p class="mt-1 text-sm text-ink-700/60">Create a cash, bank, card, or foreign currency account</p>
    </div>
    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <AccountForm @submit="handleSubmit" @cancel="navigateTo('/finance/accounts')" />
    </div>
  </div>
</template>
