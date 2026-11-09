<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">انتقال بین انبارها</h1>
        <p class="text-sm text-ink-faint">انتقال موجودی بین انبارها همراه با اعتبارسنجی و ثبت سوابق.</p>
      </div>
      <WmsUiButton variant="primary" @click="modalOpen = true">
        <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg></template>
        انتقال جدید
      </WmsUiButton>
    </div>

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiSelect v-model="filters.status" :options="statusOptions" placeholder="همه وضعیت‌ها" class="w-48" />
        <WmsUiButton v-if="filters.status" variant="ghost" size="sm" @click="filters.status = ''">پاک کردن فیلترها</WmsUiButton>
        <span class="ml-auto text-xs text-ink-faint">{{ filtered.length }} انتقال</span>
      </div>

      <WmsUiTable :columns="columns" :rows="filtered" :loading="transferStore.loading" row-key="id">
        <template #cell-transferNumber="{ row }"><span class="data-code">{{ row.transferNumber }}</span></template>
        <template #cell-itemId="{ row }">
          <span class="data-code text-ink-soft">{{ masterData.itemByCode(row.itemId)?.code }}</span>
          <span class="ml-1.5 text-ink">{{ masterData.itemByCode(row.itemId)?.name }}</span>
        </template>
        <template #cell-route="{ row }">
          <span class="text-ink">{{ masterData.warehouseName(row.sourceWarehouseId) }}</span>
          <span class="mx-1.5 text-ink-faint">â†’</span>
          <span class="text-ink">{{ masterData.warehouseName(row.destinationWarehouseId) }}</span>
        </template>
        <template #cell-quantity="{ row }"><span class="font-medium tabular-nums">{{ row.quantity }}</span></template>
        <template #cell-date="{ row }">{{ formatDate(row.date) }}</template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="statusTone(row.status)">{{ titleCase(row.status) }}</WmsUiBadge></template>
      </WmsUiTable>
    </WmsUiCard>

    <WmsModalsWarehouseTransferModal v-model="modalOpen" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { WarehouseTransfer, TableColumn } from '~/types'

const masterData = useMasterDataStore()
const transferStore = useTransferStore()
const inventoryStore = useInventoryStore()
onMounted(() => { masterData.loadAll(); transferStore.load(); inventoryStore.load() })

const modalOpen = ref(false)
const filters = ref({ status: '' })

const statusOptions = [
  { label: 'در انتظار', value: 'pending' }, { label: 'در حال انتقال', value: 'in_transit' },
  { label: 'تکمیل‌شده', value: 'completed' }, { label: 'لغوشده', value: 'cancelled' }
]

const filtered = computed(() => transferStore.transfers.filter((t) => !filters.value.status || t.status === filters.value.status))

const columns: TableColumn<WmsWarehouseTransfer>[] = [
  { key: 'transferNumber', label: 'شماره انتقال' },
  { key: 'itemId', label: 'کالا' },
  { key: 'route', label: 'مسیر' },
  { key: 'quantity', label: 'تعداد', align: 'right' },
  { key: 'date', label: 'تاریخ' },
  { key: 'status', label: 'وضعیت' }
]

function statusTone(s: WarehouseTransfer['status']) {
  return { pending: 'warn', in_transit: 'info', completed: 'success', cancelled: 'danger' }[s] as any
}
</script>
