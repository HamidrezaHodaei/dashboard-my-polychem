<script setup lang="ts">
import type { Transaction } from '~/types/finance'
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const store = useTransactionStore()
const { items, isLoading, error } = storeToRefs(store)
const notify = useNotify()
const { confirm } = useConfirm()

onMounted(() => store.fetchAll())

const search = ref('')
const isFilterOpen = ref(false)
const filters = reactive({ type: '', method: '', partyId: '', dateFrom: '', dateTo: '', minAmount: 0, maxAmount: 0 })
const page = ref(1)
const pageSize = 8

const methodLabel: Record<Transaction['method'], string> = { cash: 'نقدی', card: 'کارت', remittance: 'حواله', bank_transfer: 'انتقال بانکی', cheque: 'چک' }

const partyStore = usePartyStore()
onMounted(() => partyStore.fetchAll())
const partyOptions = computed(() => partyStore.items.map((p) => ({ value: p.id, label: p.name })))

const activeFilterCount = computed(() => Object.values(filters).filter((v) => v).length)

const filtered = computed(() => items.value.filter((t) => {
  if (search.value && !t.partyName.includes(search.value) && !t.number.includes(search.value)) return false
  if (filters.type && t.type !== filters.type) return false
  if (filters.method && t.method !== filters.method) return false
  if (filters.partyId && t.partyId !== filters.partyId) return false
  if (filters.dateFrom && new Date(t.date) < new Date(filters.dateFrom)) return false
  if (filters.dateTo && new Date(t.date) > new Date(filters.dateTo)) return false
  if (filters.minAmount && t.amount < filters.minAmount) return false
  if (filters.maxAmount && t.amount > filters.maxAmount) return false
  return true
}))

const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch([search, filters], () => { page.value = 1 })

function resetFilters() {
  filters.type = ''; filters.method = ''; filters.partyId = ''
  filters.dateFrom = ''; filters.dateTo = ''; filters.minAmount = 0; filters.maxAmount = 0
}

async function handleDelete(t: Transaction) {
  const ok = await confirm(`تراکنش «${t.number}» حذف شود؟`)
  if (!ok) return
  await store.remove(t.id)
  notify.success('تراکنش حذف شد.')
}
function exportExcel() { notify.info('خروجی Excel آماده است.') }
function exportPdf() { notify.info('خروجی PDF آماده است.') }
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink-900">دریافت‌ها و پرداخت‌ها</h1>
        <p class="mt-1 text-sm text-ink-700/60">ایجاد و مدیریت تراکنش‌های مالی</p>
      </div>
      <div class="flex gap-2">
        <NuxtLink to="/finance/transactions/create?type=receipt" class="rounded-lg bg-gain-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-gain-700">+ دریافت جدید</NuxtLink>
        <NuxtLink to="/finance/transactions/create?type=payment" class="rounded-lg bg-debt-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-debt-700">+ پرداخت جدید</NuxtLink>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppSearchInput v-model="search" placeholder="جستجو بر اساس طرف‌حساب یا شماره..." />
      <button class="relative rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-700 hover:bg-paper-50" @click="isFilterOpen = true">
        فیلترها
        <span v-if="activeFilterCount" class="num absolute -left-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-gain-600 text-[10px] text-white">{{ activeFilterCount }}</span>
      </button>
      <div class="me-auto flex gap-2">
        <button class="rounded-lg border border-paper-200 px-3 py-2 text-xs font-medium text-ink-700 hover:bg-paper-50" @click="exportExcel">خروجی Excel</button>
        <button class="rounded-lg border border-paper-200 px-3 py-2 text-xs font-medium text-ink-700 hover:bg-paper-50" @click="exportPdf">خروجی PDF</button>
      </div>
    </div>

    <AppTableSkeleton v-if="isLoading" :cols="7" />
    <AppErrorState v-else-if="error" :message="error" @retry="store.fetchAll()" />
    <AppEmptyState v-else-if="!filtered.length" title="هنوز تراکنشی ثبت نشده است." action-label="ایجاد تراکنش" @action="navigateTo('/finance/transactions/create')" />

    <template v-else>
      <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
        <table class="w-full min-w-225 text-right text-sm">
          <thead>
            <tr class="border-b border-paper-200 text-xs text-ink-700/60">
              <th class="px-4 py-3 font-medium">شماره</th>
              <th class="px-4 py-3 font-medium">تاریخ</th>
              <th class="px-4 py-3 font-medium">نوع</th>
              <th class="px-4 py-3 font-medium">طرف‌حساب</th>
              <th class="px-4 py-3 font-medium">مبلغ</th>
              <th class="px-4 py-3 font-medium">روش پرداخت</th>
              <th class="px-4 py-3 font-medium">وضعیت</th>
              <th class="px-4 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in paged" :key="t.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
              <td class="num px-4 py-3 text-ink-700/70">{{ t.number }}</td>
              <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(t.date) }}</td>
              <td class="px-4 py-3">
                <span class="text-xs font-medium" :class="t.type === 'receipt' ? 'text-gain-700' : 'text-debt-600'">{{ t.type === 'receipt' ? 'دریافت' : 'پرداخت' }}</span>
              </td>
              <td class="px-4 py-3 text-ink-900">{{ t.partyName }}</td>
              <td class="num px-4 py-3 font-medium text-ink-900">{{ formatCurrency(t.amount) }}</td>
              <td class="px-4 py-3 text-ink-700/70">{{ methodLabel[t.method] }}</td>
              <td class="px-4 py-3">
                <AppStatusBadge :label="t.status === 'confirmed' ? 'تأییدشده' : t.status === 'pending' ? 'در انتظار' : 'لغوشده'" :tone="t.status === 'confirmed' ? 'gain' : t.status === 'pending' ? 'pending' : 'debt'" />
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <NuxtLink :to="`/finance/transactions/${t.id}`" class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100"> 
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke-linecap="round" stroke-linejoin="round" /><circle cx="12" cy="12" r="3" /></svg>
                  </NuxtLink>
                  <button class="rounded-lg p-1.5 text-debt-600/70 hover:bg-debt-50" @click="handleDelete(t)">
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6h16z" stroke-linecap="round" stroke-linejoin="round" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AppPagination v-model:page="page" :page-size="pageSize" :total="filtered.length" />
    </template>

    <AppDrawer v-model="isFilterOpen" title="فیلترهای تراکنش">
      <div class="space-y-4">
        <AppSelect v-model="filters.type" label="نوع تراکنش" placeholder="همه" :options="[{ value: 'receipt', label: 'دریافت' }, { value: 'payment', label: 'پرداخت' }]" />
        <AppSelect v-model="filters.partyId" label="طرف‌حساب" placeholder="همه" :options="partyOptions" />
        <AppSelect v-model="filters.method" label="روش پرداخت" placeholder="همه" :options="[{ value: 'cash', label: 'نقدی' }, { value: 'card', label: 'کارت' }, { value: 'remittance', label: 'حواله' }, { value: 'bank_transfer', label: 'انتقال بانکی' }, { value: 'cheque', label: 'چک' }]" />
        <AppDatePicker v-model="filters.dateFrom" label="از تاریخ" />
        <AppDatePicker v-model="filters.dateTo" label="تا تاریخ" />
        <AppMoneyInput v-model="filters.minAmount" label="حداقل مبلغ" />
        <AppMoneyInput v-model="filters.maxAmount" label="حداکثر مبلغ" />
      </div>
      <template #footer>
        <div class="flex gap-2">
          <button class="flex-1 rounded-lg border border-paper-200 py-2.5 text-sm font-medium text-ink-800" @click="resetFilters">پاک کردن</button>
          <button class="flex-1 rounded-lg bg-gain-600 py-2.5 text-sm font-medium text-white" @click="isFilterOpen = false">اعمال فیلترها</button>
        </div>
      </template>
    </AppDrawer>
  </div>
</template>
