<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">ورودی انبار / رسید کالا</h1>
        <p class="text-sm text-ink-faint">ثبت و پیگیری کالاهای دریافتی از تأمین‌کنندگان.</p>
      </div>
      <WmsUiButton variant="primary" @click="modalOpen = true">
        <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg></template>
        ثبت رسید جدید
      </WmsUiButton>
    </div>

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiInput v-model="filters.search" placeholder="جستجوی شماره رسید..." class="w-64" />
        <WmsUiSelect v-model="filters.status" :options="statusOptions" placeholder="همه وضعیت‌ها" class="w-44" />
        <WmsUiButton v-if="filters.search || filters.status" variant="ghost" size="sm" @click="filters = { search: '', status: '' }">پاک کردن فیلترها</WmsUiButton>
        <span class="ml-auto text-xs text-ink-faint">{{ filtered.length }} رسید</span>
      </div>

      <WmsUiTable :columns="columns" :rows="filtered" :loading="inboundStore.loading" row-key="id">
        <template #cell-receiptNumber="{ row }"><span class="data-code">{{ row.receiptNumber }}</span></template>
        <template #cell-supplierId="{ row }">{{ masterData.supplierName(row.supplierId) }}</template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-date="{ row }">{{ formatDate(row.date) }}</template>
        <template #cell-items="{ row }">{{ row.lines.length }} ردیف</template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="statusTone(row.status)">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }">
          <WmsUiButton size="sm" variant="ghost" @click="detail = row">مشاهده</WmsUiButton>
        </template>
      </WmsUiTable>
    </WmsUiCard>

    <WmsUiBaseModal :model-value="!!detail" title="رسید کالا" :subtitle="detail?.receiptNumber" @update:model-value="detail = null">
      <div v-if="detail" class="space-y-4 text-sm">
        <div class="grid grid-cols-2 gap-3">
          <div><p class="text-ink-faint">تأمین‌کننده</p><p class="font-medium text-ink">{{ masterData.supplierName(detail.supplierId) }}</p></div>
          <div><p class="text-ink-faint">انبار</p><p class="font-medium text-ink">{{ masterData.warehouseName(detail.warehouseId) }}</p></div>
          <div><p class="text-ink-faint">تاریخ</p><p class="text-ink">{{ formatDate(detail.date) }}</p></div>
          <div><p class="text-ink-faint">ایجادکننده</p><p class="text-ink">{{ detail.createdBy }}</p></div>
        </div>
        <div>
          <p class="mb-1.5 font-medium text-ink">اقلام رسید</p>
          <ul class="divide-y divide-line rounded border border-line">
            <li v-for="line in detail.lines" :key="line.id" class="flex items-center justify-between px-3 py-2">
              <span class="data-code text-ink-soft">{{ masterData.itemByCode(line.itemId)?.code }}</span>
              <span class="flex-1 px-3 text-ink">{{ masterData.itemByCode(line.itemId)?.name }}</span>
              <span class="font-medium text-ink">{{ line.quantity }}</span>
            </li>
          </ul>
        </div>
      </div>
    </WmsUiBaseModal>

    <WmsModalsGoodsReceiptModal v-model="modalOpen" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { GoodsReceipt, TableColumn } from '~/types'

const masterData = useMasterDataStore()
const inboundStore = useInboundStore()
onMounted(() => { masterData.loadAll(); inboundStore.load() })

const modalOpen = ref(false)
const detail = ref<GoodsReceipt | null>(null)
const filters = ref({ search: '', status: '' })

const statusOptions = [
  { label: 'پیش‌نویس', value: 'draft' }, { label: 'در انتظار', value: 'pending' },
  { label: 'تکمیل‌شده', value: 'completed' }, { label: 'لغوشده', value: 'cancelled' }
]

const filtered = computed(() => inboundStore.receipts.filter((r) =>
  (!filters.value.search || r.receiptNumber.toLowerCase().includes(filters.value.search.toLowerCase())) &&
  (!filters.value.status || r.status === filters.value.status)
))

const columns: TableColumn<GoodsReceipt>[] = [
  { key: 'receiptNumber', label: 'شماره رسید' },
  { key: 'supplierId', label: 'تأمین‌کننده' },
  { key: 'warehouseId', label: 'انبار' },
  { key: 'date', label: 'تاریخ' },
  { key: 'items', label: 'اقلام' },
  { key: 'status', label: 'وضعیت' }
]

function statusTone(s: GoodsReceipt['status']) {
  return { draft: 'neutral', pending: 'warn', completed: 'success', cancelled: 'danger' }[s] as any
}
</script>
