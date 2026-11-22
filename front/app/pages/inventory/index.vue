<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="درخواست خرید"
      description="ثبت درخواست خرید کالا و پیگیری وضعیت هر درخواست و تک‌تک اقلام آن؛ از استعلام و پرداخت تا حمل و رسید انبار."
      section="انبار"
      :action-label="store.meta?.my_permissions.warehouse ? 'ثبت درخواست خرید' : undefined"
      @action="navigateTo('/inventory/new')"
    />
    <PurchasesFlowList base="/inventory" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
await store.loadMeta()
</script>
