<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="گزارشات خرید"
      description="کارتابل تدارکات، تأیید مدیر و گزارش مدیریتی زمان‌بندی تأمین؛ هر کالا در یک درخواست چندقلمی مسیر مستقل خودش را طی می‌کند."
      section="تدارکات و لجستیک"
    >
      <template #actions>
        <Button v-if="store.meta?.my_permissions.manage_catalog" variant="outline" size="sm" class="gap-2" @click="navigateTo('/procurement/purchases/products')"><Icon name="lucide:package-search" class="size-4" />مدیریت کالاها</Button>
        <Button variant="outline" size="sm" class="gap-2" @click="navigateTo('/procurement/purchases/legacy')"><Icon name="lucide:archive" class="size-4" />سوابق نسخهٔ قبلی و خریدهای مستقیم</Button>
      </template>
    </AccessPageHeader>

    <div class="flex flex-wrap gap-2">
      <button v-for="t in tabs" :key="t.value" type="button" class="rounded-full border px-4 py-1.5 text-sm transition-colors hover:bg-muted" :class="tab === t.value && 'border-primary bg-primary/10 font-semibold'" @click="tab = t.value">{{ t.label }}</button>
    </div>

    <PurchasesFlowList v-if="tab === 'cartable'" key="cartable" base="/procurement/purchases/flow" queue="open" />
    <PurchasesFlowList v-else-if="tab === 'manager'" key="manager" base="/procurement/purchases/flow" queue="manager" />
    <PurchasesFlowList v-else-if="tab === 'all'" key="all" base="/procurement/purchases/flow" />
    <PurchasesFlowReport v-else key="report" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
await store.loadMeta()
const p = store.meta!.my_permissions
const tabs = [
  ...(p.procure || p.read ? [{ value: 'cartable', label: 'کارتابل تدارکات' }] : []),
  ...(p.manager ? [{ value: 'manager', label: 'تأیید مدیر' }] : []),
  ...(p.procure || p.read || p.manager ? [{ value: 'all', label: 'همهٔ درخواست‌ها' }] : []),
  { value: 'report', label: 'گزارش مدیریتی و تنظیمات' },
]
const tab = ref(tabs[0]!.value)
</script>
