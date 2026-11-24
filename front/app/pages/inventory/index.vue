<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="درخواست خرید"
      description="فهرست همهٔ درخواست‌ها و وضعیت اقلام هر کدام؛ برای مشاهدهٔ جزئیات روی ردیف بزنید."
      section="انبار"
      :action-label="store.meta?.my_permissions.warehouse ? 'ثبت درخواست خرید' : undefined"
      @action="navigateTo('/inventory/new')"
    />
    <PurchasesFlowList base="/inventory" sync-query />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
await store.loadMeta()
</script>
