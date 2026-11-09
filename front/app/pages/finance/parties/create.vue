<script setup lang="ts">
const store = usePartyStore()
const notify = useNotify()

async function handleSubmit(payload: any) {
  await store.create(payload)
  notify.success('Party created successfully.')
  navigateTo('/finance/parties')
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Create party</h1>
      <p class="mt-1 text-sm text-ink-700/60">Enter customer, supplier, person, or company details</p>
    </div>
    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <PartyForm @submit="handleSubmit" @cancel="navigateTo('/finance/parties')" />
    </div>
  </div>
</template>
