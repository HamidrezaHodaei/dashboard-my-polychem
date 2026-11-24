<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="داشبورد درخواست خرید"
      description="وضعیت درخواست‌های خرید در یک نگاه؛ هر عدد شما را به فهرست مربوط می‌برد."
      section="انبار"
      :action-label="store.meta?.my_permissions.warehouse ? 'ثبت درخواست خرید' : undefined"
      @action="navigateTo('/inventory/new')"
    />
    <PurchasesFlowDashboard base="/inventory" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
await store.loadMeta()
</script>
