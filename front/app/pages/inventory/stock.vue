<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">موجودی کالا</h1>
        <p class="text-sm text-ink-faint">موجودی کالا در همه انبارها و محل‌های نگهداری.</p>
      </div>
      <WmsUiButton variant="primary" @click="openItemModal(null)">
        <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg></template>
        کالای جدید
      </WmsUiButton>
    </div>

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiInput v-model="filters.search" placeholder="جستجو بر اساس کد یا نام کالا..." class="w-64" />
        <WmsUiSelect v-model="filters.warehouseId" :options="warehouseOptions" placeholder="همه انبارها" class="w-48" />
        <WmsUiSelect v-model="filters.status" :options="statusOptions" placeholder="همه وضعیت‌ها" class="w-48" />
        <WmsUiButton v-if="hasFilters" variant="ghost" size="sm" @click="resetFilters">پاک کردن فیلترها</WmsUiButton>
        <span class="ml-auto text-xs text-ink-faint">{{ filtered.length }} رکورد</span>
      </div>

      <WmsUiTable :columns="columns" :rows="paged" :loading="inventoryStore.loading" row-key="id">
        <template #cell-itemCode="{ row }"><span class="data-code">{{ row.itemCode }}</span></template>
        <template #cell-availableQty="{ row }">
          <span class="font-medium tabular-nums">{{ row.availableQty }}</span>
          <span class="text-ink-faint"> {{ row.unitCode }}</span>
        </template>
        <template #cell-reservedQty="{ row }"><span class="tabular-nums text-ink-soft">{{ row.reservedQty }}</span></template>
        <template #cell-status="{ row }">
          <WmsUiBadge :tone="statusTone(row.stockStatus)">{{ statusLabel(row.stockStatus) }}</WmsUiBadge>
        </template>
        <template #actions="{ row }">
          <WmsUiDropdown align="right">
            <template #trigger>
              <button class="focus-ring rounded p-1 text-ink-faint hover:bg-steel-100 hover:text-ink dark:hover:bg-steel-800">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></svg>
              </button>
            </template>
            <WmsUiDropdownItem @click="openDetail(row)">مشاهده جزئیات</WmsUiDropdownItem>
            <WmsUiDropdownItem @click="openItemModal(row)">ویرایش کالا</WmsUiDropdownItem>
            <WmsUiDropdownItem @click="openAdjustment(row)">اصلاح موجودی</WmsUiDropdownItem>
            <WmsUiDropdownItem @click="openHistory(row)">تاریخچه گردش</WmsUiDropdownItem>
          </WmsUiDropdown>
        </template>
      </WmsUiTable>

      <WmsUiPagination v-model:page="page" :page-size="pageSize" :total="filtered.length" />
    </WmsUiCard>

    <!-- View details -->
    <WmsUiBaseModal v-model="detail.open" title="جزئیات کالا" :subtitle="detail.row?.itemCode" size="sm">
      <dl v-if="detail.row" class="space-y-3 text-sm">
        <div class="flex justify-between"><dt class="text-ink-faint">نام کالا</dt><dd class="font-medium text-ink">{{ detail.row.itemName }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">دسته‌بندی</dt><dd class="text-ink">{{ detail.row.categoryName }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">انبار</dt><dd class="text-ink">{{ detail.row.warehouseName }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">محل نگهداری</dt><dd class="data-code text-ink">{{ detail.row.locationCode }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">موجود</dt><dd class="font-medium text-ink">{{ detail.row.availableQty }} {{ detail.row.unitCode }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">رزروشده</dt><dd class="text-ink">{{ detail.row.reservedQty }} {{ detail.row.unitCode }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">حداقل موجودی</dt><dd class="text-ink">{{ detail.row.minStock }} {{ detail.row.unitCode }}</dd></div>
        <div class="flex justify-between"><dt class="text-ink-faint">وضعیت</dt><dd><WmsUiBadge :tone="statusTone(detail.row.stockStatus)">{{ statusLabel(detail.row.stockStatus) }}</WmsUiBadge></dd></div>
      </dl>
    </WmsUiBaseModal>

    <!-- Movement history -->
    <WmsUiBaseModal v-model="history.open" title="تاریخچه گردش" :subtitle="history.row?.itemCode" size="md">
      <WmsUiTable :columns="historyColumns" :rows="historyRows" row-key="id">
        <template #cell-type="{ row }"><WmsUiBadge :tone="useMovementMeta(row.type).tone">{{ useMovementMeta(row.type).label }}</WmsUiBadge></template>
        <template #cell-quantity="{ row }"><span :class="row.quantity < 0 ? 'text-danger' : 'text-success'">{{ row.quantity > 0 ? '+' : '' }}{{ row.quantity }}</span></template>
        <template #cell-date="{ row }">{{ formatDateTime(row.date) }}</template>
      </WmsUiTable>
    </WmsUiBaseModal>

    <WmsModalsStockAdjustmentModal v-model="adjustment.open" :row="adjustment.row" />
    <WmsModalsItemModal v-model="itemModal.open" :item="itemModal.item" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { InventoryRow, TableColumn, Item } from '~/types'

const inventoryStore = useInventoryStore()
const masterData = useMasterDataStore()
const movementStore = useMovementStore()

onMounted(() => {
  masterData.loadAll()
  inventoryStore.load()
  movementStore.load()
})

const filters = ref({ search: '', warehouseId: '', status: '' })
const hasFilters = computed(() => !!(filters.value.search || filters.value.warehouseId || filters.value.status))
function resetFilters() { filters.value = { search: '', warehouseId: '', status: '' } }

const warehouseOptions = computed(() => masterData.warehouses.map((w) => ({ label: w.name, value: w.id })))
const statusOptions = [
  { label: 'موجود', value: 'in_stock' },
  { label: 'موجودی کم', value: 'low_stock' },
  { label: 'ناموجود', value: 'out_of_stock' }
]

const filtered = computed(() => {
  return inventoryStore.rows.filter((r) => {
    const matchesSearch = !filters.value.search ||
      r.itemCode.toLowerCase().includes(filters.value.search.toLowerCase()) ||
      r.itemName.toLowerCase().includes(filters.value.search.toLowerCase())
    const matchesWarehouse = !filters.value.warehouseId || r.warehouseId === filters.value.warehouseId
    const matchesStatus = !filters.value.status || r.stockStatus === filters.value.status
    return matchesSearch && matchesWarehouse && matchesStatus
  })
})

const page = ref(1)
const pageSize = 8
watch(filtered, () => { page.value = 1 })
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))

const columns: TableColumn<InventoryRow>[] = [
  { key: 'itemCode', label: 'کد کالا' },
  { key: 'itemName', label: 'نام کالا' },
  { key: 'categoryName', label: 'دسته‌بندی' },
  { key: 'warehouseName', label: 'انبار' },
  { key: 'locationCode', label: 'محل نگهداری' },
  { key: 'availableQty', label: 'موجود', align: 'right' },
  { key: 'reservedQty', label: 'رزروشده', align: 'right' },
  { key: 'status', label: 'وضعیت' }
]

function statusTone(s: InventoryRow['stockStatus']) {
  return { in_stock: 'success', low_stock: 'warn', out_of_stock: 'danger' }[s] as any
}
function statusLabel(s: InventoryRow['stockStatus']) {
  return { in_stock: 'موجود', low_stock: 'موجودی کم', out_of_stock: 'ناموجود' }[s]
}

const detail = ref<{ open: boolean; row: InventoryRow | null }>({ open: false, row: null })
function openDetail(row: InventoryRow) { detail.value = { open: true, row } }

const adjustment = ref<{ open: boolean; row: InventoryRow | null }>({ open: false, row: null })
function openAdjustment(row: InventoryRow) { adjustment.value = { open: true, row } }

const history = ref<{ open: boolean; row: InventoryRow | null }>({ open: false, row: null })
function openHistory(row: InventoryRow) { history.value = { open: true, row } }
const historyRows = computed(() =>
  movementStore.movements.filter((m) => m.itemId === history.value.row?.itemId && m.warehouseId === history.value.row?.warehouseId)
)
const historyColumns: TableColumn[] = [
  { key: 'type', label: 'Type' },
  { key: 'quantity', label: 'Qty', align: 'right' },
  { key: 'reference', label: 'Reference' },
  { key: 'performedBy', label: 'By' },
  { key: 'date', label: 'Date' }
]

const itemModal = ref<{ open: boolean; item: Item | null }>({ open: false, item: null })
function openItemModal(row: InventoryRow | null) {
  const item = row ? masterData.items.find((i) => i.id === row.itemId) ?? null : null
  itemModal.value = { open: true, item }
}
</script>
