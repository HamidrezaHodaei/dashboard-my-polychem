<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">پیشخوان</h1>
        <p class="text-sm text-ink-faint">نمای لحظه‌ای موجودی و رسیدها و حواله‌های همه انبارها.</p>
      </div>
      <WmsUiButton variant="primary" to="/inventory/inbound">
        <template #icon>
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg>
        </template>
        ثبت رسید جدید
      </WmsUiButton>
    </div>

    <div v-if="loading">
      <WmsUiLoadingState label="در حال بارگذاری پیشخوان..." />
    </div>

    <template v-else>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <WmsWarehouseKpiCard label="تعداد کل کالاها" :value="formatNumber(kpis.totalItems)" tone="neutral" :icon="icons.box" />
        <WmsWarehouseKpiCard label="موجودی کل" :value="formatNumber(kpis.totalStock)" tone="neutral" :icon="icons.stack" />
        <WmsWarehouseKpiCard label="موجودی کم" :value="formatNumber(kpis.lowStock)" tone="amber" :icon="icons.alert" />
        <WmsWarehouseKpiCard label="ناموجود" :value="formatNumber(kpis.outOfStock)" tone="danger" :icon="icons.cross" />
        <WmsWarehouseKpiCard label="ورودی امروز" :value="formatNumber(kpis.todayInbound)" tone="success" :icon="icons.down" />
        <WmsWarehouseKpiCard label="خروجی امروز" :value="formatNumber(kpis.todayOutbound)" tone="neutral" :icon="icons.up" />
        <WmsWarehouseKpiCard label="انتقال‌های در انتظار" :value="formatNumber(kpis.pendingTransfers)" tone="amber" :icon="icons.transfer" />
        <WmsWarehouseKpiCard label="ارزش موجودی" :value="formatCurrency(kpis.stockValue)" tone="neutral" :icon="icons.value" />
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <WmsUiCard title="گردش‌ها (۷ مورد اخیر)" subtitle="مقدار جابه‌جایی بر اساس نوع گردش" class="lg:col-span-2">
          <WmsWarehouseBarChart :data="chartData" aria-label="نمودار حجم گردش موجودی" />
        </WmsUiCard>

        <WmsUiCard title="وضعیت انبارها" subtitle="انبارهای فعال">
          <ul class="space-y-3">
            <li v-for="w in masterData.activeWarehouses" :key="w.id" class="flex items-center justify-between text-sm">
              <span class="text-ink">{{ w.name }}</span>
              <span class="data-code text-ink-faint">{{ w.code }}</span>
            </li>
          </ul>
        </WmsUiCard>
      </div>

      <WmsUiCard title="گردش‌های اخیر موجودی" subtitle="آخرین تراکنش‌های موجودی در همه انبارها">
        <template #actions>
          <WmsUiButton size="sm" variant="ghost" to="/inventory/movements">مشاهده همه</WmsUiButton>
        </template>
        <WmsUiTable :columns="movementColumns" :rows="recentMovements" row-key="id">
          <template #cell-type="{ row }">
            <WmsUiBadge :tone="useMovementMeta(row.type).tone">{{ useMovementMeta(row.type).label }}</WmsUiBadge>
          </template>
          <template #cell-itemId="{ row }">
            <span class="data-code text-ink-soft">{{ masterData.itemByCode(row.itemId)?.code }}</span>
            <span class="ml-1.5 text-ink">{{ masterData.itemByCode(row.itemId)?.name }}</span>
          </template>
          <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
          <template #cell-quantity="{ row }">
            <span :class="row.quantity < 0 ? 'text-danger' : 'text-success'">{{ row.quantity > 0 ? '+' : '' }}{{ row.quantity }}</span>
          </template>
          <template #cell-date="{ row }">{{ formatDateTime(row.date) }}</template>
        </WmsUiTable>
      </WmsUiCard>
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { dashboardApi } from '~/services/api'

const masterData = useMasterDataStore()
const movementStore = useMovementStore()
const loading = ref(true)
const kpis = ref({
  totalItems: 0, totalStock: 0, lowStock: 0, outOfStock: 0,
  todayInbound: 0, todayOutbound: 0, pendingTransfers: 0, stockValue: 0
})

onMounted(async () => {
  await Promise.all([masterData.loadAll(), movementStore.load(), (async () => { kpis.value = await dashboardApi.kpis() })()])
  loading.value = false
})

const recentMovements = computed(() => movementStore.movements.slice(0, 6))

const movementColumns: import('~/types').TableColumn[] = [
  { key: 'type', label: 'نوع' },
  { key: 'itemId', label: 'کالا' },
  { key: 'warehouseId', label: 'انبار' },
  { key: 'quantity', label: 'تعداد', align: 'right' },
  { key: 'reference', label: 'مرجع' },
  { key: 'date', label: 'تاریخ' }
]

const chartData = computed(() => {
  const byType = new Map<import('~/types').MovementType, number>()
  for (const m of movementStore.movements) {
    byType.set(m.type, (byType.get(m.type) || 0) + Math.abs(m.quantity))
  }
  return [...byType].map(([type, value]) => ({ label: useMovementMeta(type).label, value }))
})

const icons = {
  box: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8l-9-5-9 5 9 5 9-5zm0 0v8l-9 5m9-13l-9 5m0 0L3 8m9 5v8M3 8v8l9 5"/></svg>',
  stack: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7l8-4 8 4-8 4-8-4zm0 5l8 4 8-4M4 17l8 4 8-4"/></svg>',
  alert: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a1 1 0 00.86 1.5h18.64a1 1 0 00.86-1.5L13.71 3.86a1 1 0 00-1.72 0z"/></svg>',
  cross: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" d="M9 9l6 6m0-6l-6 6"/></svg>',
  down: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m0 0l-5-5m5 5l5-5"/></svg>',
  up: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20V4m0 0l-5 5m5-5l5 5"/></svg>',
  transfer: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7h13l-3-3m3 3l-3 3M20 17H7l3 3m-3-3l3-3"/></svg>',
  value: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>'
}
</script>
