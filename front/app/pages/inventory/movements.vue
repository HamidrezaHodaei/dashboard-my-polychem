<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div>
      <h1 class="text-lg font-semibold text-ink">گردش موجودی</h1>
      <p class="text-sm text-ink-faint">گزارش کامل و قابل‌پیگیری همه تراکنش‌های موجودی.</p>
    </div>

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiSelect v-model="filters.type" :options="typeOptions" placeholder="همه انواع گردش" class="w-52" />
        <WmsUiSelect v-model="filters.warehouseId" :options="warehouseOptions" placeholder="همه انبارها" class="w-48" />
        <WmsUiButton v-if="filters.type || filters.warehouseId" variant="ghost" size="sm" @click="filters = { type: '', warehouseId: '' }">پاک کردن فیلترها</WmsUiButton>
        <span class="ml-auto text-xs text-ink-faint">{{ filtered.length }} گردش</span>
      </div>

      <WmsUiTable :columns="columns" :rows="paged" :loading="movementStore.loading" row-key="id">
        <template #cell-type="{ row }"><WmsUiBadge :tone="useMovementMeta(row.type).tone">{{ useMovementMeta(row.type).label }}</WmsUiBadge></template>
        <template #cell-itemId="{ row }">
          <span class="data-code text-ink-soft">{{ masterData.itemByCode(row.itemId)?.code }}</span>
          <span class="ml-1.5 text-ink">{{ masterData.itemByCode(row.itemId)?.name }}</span>
        </template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-quantity="{ row }"><span :class="row.quantity < 0 ? 'text-danger' : 'text-success'">{{ row.quantity > 0 ? '+' : '' }}{{ row.quantity }}</span></template>
        <template #cell-reference="{ row }"><span class="data-code text-ink-soft">{{ row.reference }}</span></template>
        <template #cell-date="{ row }">{{ formatDateTime(row.date) }}</template>
        <template #cell-performedBy="{ row }">
          <div>
            <p class="text-ink">{{ row.performedBy }}</p>
            <p v-if="row.reason" class="text-xs text-ink-faint">{{ row.reason }}</p>
          </div>
        </template>
      </WmsUiTable>

      <WmsUiPagination v-model:page="page" :page-size="pageSize" :total="filtered.length" />
    </WmsUiCard>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { StockMovement, TableColumn } from '~/types'

const masterData = useMasterDataStore()
const movementStore = useMovementStore()
onMounted(() => { masterData.loadAll(); movementStore.load() })

const filters = ref({ type: '', warehouseId: '' })
const typeOptions = [
  { label: 'ورودی', value: 'inbound' }, { label: 'خروجی', value: 'outbound' },
  { label: 'انتقال', value: 'transfer' }, { label: 'اصلاح', value: 'adjustment' },
  { label: 'مرجوعی', value: 'return' }, { label: 'رزرو', value: 'reservation' }, { label: 'آزادسازی', value: 'release' }
]
const warehouseOptions = computed(() => masterData.warehouses.map((w) => ({ label: w.name, value: w.id })))

const filtered = computed(() => movementStore.movements.filter((m) =>
  (!filters.value.type || m.type === filters.value.type) &&
  (!filters.value.warehouseId || m.warehouseId === filters.value.warehouseId)
))

const page = ref(1)
const pageSize = 10
watch(filtered, () => { page.value = 1 })
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))

const columns: TableColumn<StockMovement>[] = [
  { key: 'type', label: 'نوع' },
  { key: 'itemId', label: 'کالا' },
  { key: 'warehouseId', label: 'انبار' },
  { key: 'quantity', label: 'تعداد', align: 'right' },
  { key: 'reference', label: 'مرجع' },
  { key: 'date', label: 'تاریخ' },
  { key: 'performedBy', label: 'انجام‌دهنده' }
]
</script>
