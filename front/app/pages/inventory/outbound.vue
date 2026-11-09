<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink">خروجی انبار / حواله کالا</h1>
        <p class="text-sm text-ink-faint">ثبت و پیگیری کالاهای خارج‌شده از انبار.</p>
      </div>
      <WmsUiButton variant="primary" @click="modalOpen = true">
        <template #icon><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg></template>
        ثبت حواله جدید
      </WmsUiButton>
    </div>

    <WmsUiCard :padded="false">
      <div class="flex flex-wrap items-center gap-2 border-b border-line p-4">
        <WmsUiInput v-model="filters.search" placeholder="جستجوی شماره حواله یا مقصد..." class="w-72" />
        <WmsUiSelect v-model="filters.status" :options="statusOptions" placeholder="همه وضعیت‌ها" class="w-44" />
        <WmsUiButton v-if="filters.search || filters.status" variant="ghost" size="sm" @click="filters = { search: '', status: '' }">پاک کردن فیلترها</WmsUiButton>
        <span class="ml-auto text-xs text-ink-faint">{{ filtered.length }} حواله</span>
      </div>

      <WmsUiTable :columns="columns" :rows="filtered" :loading="outboundStore.loading" row-key="id">
        <template #cell-issueNumber="{ row }"><span class="data-code">{{ row.issueNumber }}</span></template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-date="{ row }">{{ formatDate(row.date) }}</template>
        <template #cell-items="{ row }">{{ row.lines.length }} ردیف</template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="statusTone(row.status)">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }">
          <WmsUiButton size="sm" variant="ghost" @click="detail = row">مشاهده</WmsUiButton>
        </template>
      </WmsUiTable>
    </WmsUiCard>

    <WmsUiBaseModal :model-value="!!detail" title="حواله کالا" :subtitle="detail?.issueNumber" @update:model-value="detail = null">
      <div v-if="detail" class="space-y-4 text-sm">
        <div class="grid grid-cols-2 gap-3">
          <div><p class="text-ink-faint">مقصد</p><p class="font-medium text-ink">{{ detail.destination }}</p></div>
          <div><p class="text-ink-faint">درخواست‌کننده</p><p class="font-medium text-ink">{{ detail.requester }}</p></div>
          <div><p class="text-ink-faint">انبار</p><p class="text-ink">{{ masterData.warehouseName(detail.warehouseId) }}</p></div>
          <div><p class="text-ink-faint">تاریخ</p><p class="text-ink">{{ formatDate(detail.date) }}</p></div>
        </div>
        <div>
          <p class="mb-1.5 font-medium text-ink">اقلام حواله</p>
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

    <WmsModalsGoodsIssueModal v-model="modalOpen" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { GoodsIssue, TableColumn } from '~/types'

const masterData = useMasterDataStore()
const outboundStore = useOutboundStore()
const inventoryStore = useInventoryStore()
onMounted(() => { masterData.loadAll(); outboundStore.load(); inventoryStore.load() })

const modalOpen = ref(false)
const detail = ref<GoodsIssue | null>(null)
const filters = ref({ search: '', status: '' })

const statusOptions = [
  { label: 'در انتظار', value: 'pending' }, { label: 'تکمیل‌شده', value: 'completed' }, { label: 'لغوشده', value: 'cancelled' }
]

const filtered = computed(() => outboundStore.issues.filter((r) =>
  (!filters.value.search ||
    r.issueNumber.toLowerCase().includes(filters.value.search.toLowerCase()) ||
    r.destination.toLowerCase().includes(filters.value.search.toLowerCase())) &&
  (!filters.value.status || r.status === filters.value.status)
))

const columns: TableColumn<GoodsIssue>[] = [
  { key: 'issueNumber', label: 'شماره حواله' },
  { key: 'destination', label: 'مقصد' },
  { key: 'warehouseId', label: 'انبار' },
  { key: 'date', label: 'تاریخ' },
  { key: 'items', label: 'اقلام' },
  { key: 'status', label: 'وضعیت' }
]

function statusTone(s: GoodsIssue['status']) {
  return { draft: 'neutral', pending: 'warn', completed: 'success', cancelled: 'danger' }[s] as any
}
</script>
