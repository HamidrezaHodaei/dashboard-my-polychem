<script setup lang="ts">
// /crm has no content of its own: send each user to the first CRM screen they may open.
definePageMeta({ title: 'مدیریت فروش و مشتریان' })
const auth = useAuthStore()
const target = ['crm_dashboard', 'customers', 'crm_sales', 'crm_settings']
  .map(k => auth.navigation.find(n => n.key === k)?.path)
  .find(Boolean)
await navigateTo(target ?? '/403', { replace: true })
</script>

<template>
  <div />
</template>
