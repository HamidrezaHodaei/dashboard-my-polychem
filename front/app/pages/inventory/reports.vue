<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">گزارش‌ها</h1>
        <p class="text-sm text-ink-faint">گزارش‌های عملیاتی موجودی، تراکنش‌ها و عملکرد انبار.</p>
      </div>
      <div class="flex gap-2">
        <WmsUiButton variant="outline" @click="exportCsv">
          <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" /></svg></template>
          خروجی CSV
        </WmsUiButton>
        <WmsUiButton variant="outline" @click="print">
          <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 9V3h12v6M6 18H4a1 1 0 01-1-1v-6a1 1 0 011-1h16a1 1 0 011 1v6a1 1 0 01-1 1h-2M6 14h12v7H6v-7z" /></svg></template>
          چاپ
        </WmsUiButton>
      </div>
    </div>

    <WmsUiTabs v-model="activeTab" :tabs="tabs" />

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiInput v-model="filters.from" type="date" label="" class="w-40" />
        <span class="text-ink-faint">تا</span>
        <WmsUiInput v-model="filters.to" type="date" label="" class="w-40" />
        <WmsUiSelect v-model="filters.warehouseId" :options="warehouseOptions" placeholder="همه انبارها" class="w-48" />
      </div>

      <!-- Inventory report -->
      <WmsUiTable v-if="activeTab === 'inventory'" :columns="inventoryColumns" :rows="inventoryRows" row-key="id">
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.stockStatus === 'in_stock' ? 'success' : row.stockStatus === 'low_stock' ? 'warn' : 'danger'">{{ titleCase(row.stockStatus) }}</WmsUiBadge></template>
      </WmsUiTable>

      <!-- Inbound report -->
      <WmsUiTable v-else-if="activeTab === 'inbound'" :columns="inboundColumns" :rows="inboundRows" row-key="id">
        <template #cell-supplierId="{ row }">{{ masterData.supplierName(row.supplierId) }}</template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-status="{ row }"><WmsUiBadge tone="neutral">{{ titleCase(row.status) }}</WmsUiBadge></template>
      </WmsUiTable>

      <!-- Outbound report -->
      <WmsUiTable v-else-if="activeTab === 'outbound'" :columns="outboundColumns" :rows="outboundRows" row-key="id">
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-status="{ row }"><WmsUiBadge tone="neutral">{{ titleCase(row.status) }}</WmsUiBadge></template>
      </WmsUiTable>

      <!-- Movements report -->
      <WmsUiTable v-else-if="activeTab === 'movements'" :columns="movementColumns" :rows="movementRows" row-key="id">
        <template #cell-type="{ row }"><WmsUiBadge :tone="useMovementMeta(row.type).tone">{{ useMovementMeta(row.type).label }}</WmsUiBadge></template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
      </WmsUiTable>

      <!-- Stock turnover -->
      <WmsUiTable v-else-if="activeTab === 'turnover'" :columns="turnoverColumns" :rows="turnoverRows" row-key="itemId">
        <template #cell-turnoverRate="{ row }">{{ row.turnoverRate.toFixed(2) }}x</template>
      </WmsUiTable>

      <!-- Warehouse performance -->
      <WmsUiTable v-else :columns="performanceColumns" :rows="performanceRows" row-key="warehouseId" />
    </WmsUiCard>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { TableColumn } from '~/types'

const masterData = useMasterDataStore()
const inventoryStore = useInventoryStore()
const inboundStore = useInboundStore()
const outboundStore = useOutboundStore()
const movementStore = useMovementStore()

onMounted(() => {
  masterData.loadAll()
  inventoryStore.load()
  inboundStore.load()
  outboundStore.load()
  movementStore.load()
})

const activeTab = ref('inventory')
const tabs = [
  { label: 'موجودی کالا', value: 'inventory' },
  { label: 'ورودی انبار', value: 'inbound' },
  { label: 'خروجی انبار', value: 'outbound' },
  { label: 'گردش موجودی', value: 'movements' },
  { label: 'گردش کالا', value: 'turnover' },
  { label: 'عملکرد انبار', value: 'performance' }
]

const filters = ref({ from: '', to: '', warehouseId: '' })
const warehouseOptions = computed(() => masterData.warehouses.map((w) => ({ label: w.name, value: w.id })))

function inRange(date: string) {
  if (filters.value.from && date < filters.value.from) return false
  if (filters.value.to && date > filters.value.to) return false
  return true
}

// ---- Inventory ----
const inventoryRows = computed(() => inventoryStore.rows.filter((r) => !filters.value.warehouseId || r.warehouseId === filters.value.warehouseId))
const inventoryColumns: TableColumn[] = [
  { key: 'itemCode', label: 'کد کالا' }, { key: 'itemName', label: 'کالا' },
  { key: 'warehouseName', label: 'انبار' }, { key: 'availableQty', label: 'موجود', align: 'right' },
  { key: 'reservedQty', label: 'رزروشده', align: 'right' }, { key: 'status', label: 'وضعیت' }
]

// ---- Inbound ----
const inboundRows = computed(() => inboundStore.receipts.filter((r) =>
  (!filters.value.warehouseId || r.warehouseId === filters.value.warehouseId) && inRange(r.date)))
const inboundColumns: TableColumn[] = [
  { key: 'receiptNumber', label: 'شماره رسید' }, { key: 'supplierId', label: 'تأمین‌کننده' },
  { key: 'warehouseId', label: 'انبار' }, { key: 'date', label: 'تاریخ', formatter: (r) => formatDate(r.date) },
  { key: 'status', label: 'وضعیت' }
]

// ---- Outbound ----
const outboundRows = computed(() => outboundStore.issues.filter((r) =>
  (!filters.value.warehouseId || r.warehouseId === filters.value.warehouseId) && inRange(r.date)))
const outboundColumns: TableColumn[] = [
  { key: 'issueNumber', label: 'شماره حواله' }, { key: 'destination', label: 'مقصد' },
  { key: 'warehouseId', label: 'انبار' }, { key: 'date', label: 'تاریخ', formatter: (r) => formatDate(r.date) },
  { key: 'status', label: 'وضعیت' }
]

// ---- Movements ----
const movementRows = computed(() => movementStore.movements.filter((m) =>
  (!filters.value.warehouseId || m.warehouseId === filters.value.warehouseId) && inRange(m.date.slice(0, 10))))
const movementColumns: TableColumn[] = [
  { key: 'type', label: 'نوع' }, { key: 'reference', label: 'مرجع' },
  { key: 'warehouseId', label: 'انبار' }, { key: 'quantity', label: 'تعداد', align: 'right' },
  { key: 'date', label: 'تاریخ', formatter: (r) => formatDateTime(r.date) }
]

// ---- Stock turnover (simplified: outbound qty / average stock) ----
const turnoverRows = computed(() => {
  return masterData.activeItems.map((item) => {
    const outboundQty = movementStore.movements
      .filter((m) => m.itemId === item.id && m.type === 'outbound')
      .reduce((sum, m) => sum + Math.abs(m.quantity), 0)
    const stockRec = inventoryStore.rows.find((r) => r.itemId === item.id)
    const avgStock = stockRec ? stockRec.availableQty || 1 : 1
    return { itemId: item.id, itemCode: item.code, itemName: item.name, outboundQty, avgStock, turnoverRate: outboundQty / avgStock }
  }).filter((r) => r.outboundQty > 0)
})
const turnoverColumns: TableColumn[] = [
  { key: 'itemCode', label: 'کد کالا' }, { key: 'itemName', label: 'کالا' },
  { key: 'outboundQty', label: 'تعداد ارسال‌شده', align: 'right' }, { key: 'avgStock', label: 'میانگین موجودی', align: 'right' },
  { key: 'turnoverRate', label: 'نرخ گردش', align: 'right' }
]

// ---- Warehouse performance ----
const performanceRows = computed(() => masterData.warehouses.map((w) => {
  const inboundCount = inboundStore.receipts.filter((r) => r.warehouseId === w.id).length
  const outboundCount = outboundStore.issues.filter((r) => r.warehouseId === w.id).length
  const stockItems = inventoryStore.rows.filter((r) => r.warehouseId === w.id)
  const lowStock = stockItems.filter((r) => r.stockStatus === 'low_stock' || r.stockStatus === 'out_of_stock').length
  return {
    warehouseId: w.id, warehouseName: w.name, inboundCount, outboundCount,
    itemCount: stockItems.length, lowStock
  }
}))
const performanceColumns: TableColumn[] = [
  { key: 'warehouseName', label: 'Warehouse' }, { key: 'itemCount', label: 'SKUs Stocked', align: 'right' },
  { key: 'inboundCount', label: 'Receipts', align: 'right' }, { key: 'outboundCount', label: 'Issues', align: 'right' },
  { key: 'lowStock', label: 'Low / Out of Stock', align: 'right' }
]

function currentColumnsAndRows() {
  const map: Record<string, [TableColumn[], any[]]> = {
    inventory: [inventoryColumns, inventoryRows.value],
    inbound: [inboundColumns, inboundRows.value],
    outbound: [outboundColumns, outboundRows.value],
    movements: [movementColumns, movementRows.value],
    turnover: [turnoverColumns, turnoverRows.value],
    performance: [performanceColumns, performanceRows.value]
  }
  return map[activeTab.value]
}

function exportCsv() {
  const [columns, rows] = currentColumnsAndRows()
  const header = columns.map((c) => c.label).join(',')
  const body = rows.map((row) => columns.map((c) => {
    const val = c.formatter ? c.formatter(row) : row[c.key]
    return `"${String(val ?? '').replace(/"/g, '""')}"`
  }).join(',')).join('\n')
  const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${activeTab.value}-report-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  useNotify().success('Export ready', `${activeTab.value} report downloaded as CSV.`)
}

function print() {
  window.print()
}
</script>
