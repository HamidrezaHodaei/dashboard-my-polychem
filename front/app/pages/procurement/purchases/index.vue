<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="گزارشات خرید"
      description="پیگیری درخواست‌های خرید، تأیید مدیر و گزارش زمان‌بندی تأمین؛ ثبت خرید جدید هم از همین‌جا انجام می‌شود."
      section="تدارکات و لجستیک"
      :action-label="canRegister ? 'ثبت خرید جدید' : undefined"
      @action="navigateTo('/procurement/purchases/new')"
    >
      <template #actions>
        <Button variant="outline" size="sm" @click="navigateTo('/procurement/purchases/legacy')">سوابق قبلی و خرید مستقیم</Button>
        <RowActions
          label="سایر عملیات"
          :actions="[
            { key: 'catalog', label: 'مدیریت کالاها', show: !!store.meta?.my_permissions.manage_catalog, to: '/procurement/purchases/products' },
          ]"
        />
      </template>
    </AccessPageHeader>

    <div class="flex flex-wrap gap-2" role="tablist" aria-label="بخش‌های گزارشات خرید">
      <button
        v-for="t in tabs"
        :key="t.value"
        type="button"
        role="tab"
        :aria-selected="tab === t.value"
        class="rounded-full border px-4 py-1.5 text-sm transition-colors hover:bg-muted"
        :class="tab === t.value && 'border-primary bg-primary/10 font-semibold'"
        @click="setTab(t.value)"
      >{{ t.label }}</button>
    </div>

    <PurchasesFlowList v-if="tab === 'cartable'" key="cartable" base="/procurement/purchases/flow" queue="open" />
    <PurchasesFlowList v-else-if="tab === 'manager'" key="manager" base="/procurement/purchases/flow" queue="manager" />
    <PurchasesFlowList v-else-if="tab === 'all'" key="all" base="/procurement/purchases/flow" />
    <PurchasesFlowReport v-else key="report" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
const legacy = usePurchasesStore()
const route = useRoute()
const router = useRouter()
await store.loadMeta()
const p = store.meta!.my_permissions
// «ثبت خرید جدید» used to be a separate button on the old-records page; it is the same registration wizard, now
// started from here (the only entry point).
const canRegister = legacy.can('create')
const tabs = [
  ...(p.procure || p.read ? [{ value: 'cartable', label: 'کارتابل تدارکات' }] : []),
  ...(p.manager ? [{ value: 'manager', label: 'تأیید مدیر' }] : []),
  ...(p.procure || p.read || p.manager ? [{ value: 'all', label: 'همهٔ درخواست‌ها' }] : []),
  { value: 'report', label: 'گزارش مدیریتی و تنظیمات' },
]
// the tab lives in the URL (?tab=) so it survives refresh and can be linked
const tab = ref(tabs.some(t => t.value === route.query.tab) ? String(route.query.tab) : tabs[0]!.value)
const setTab = (v: string) => { tab.value = v; router.replace({ query: { ...route.query, tab: v } }) }
</script>
