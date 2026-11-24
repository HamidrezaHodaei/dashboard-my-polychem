<script setup lang="ts">
import type { Party } from '~/types/finance'
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const store = usePartyStore()
const { items, isLoading, error } = storeToRefs(store)
const notify = useNotify()
const { confirm } = useConfirm()

onMounted(() => store.fetchAll())

const search = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 8
const selected = ref<string[]>([])

const typeLabel: Record<Party['type'], string> = { customer: 'مشتری', supplier: 'تأمین‌کننده', person: 'شخص', company: 'شرکت' }

const filtered = computed(() => items.value.filter((p) => {
  if (search.value && !p.name.includes(search.value) && !p.mobile.includes(search.value)) return false
  if (typeFilter.value && p.type !== typeFilter.value) return false
  if (statusFilter.value === 'active' && !p.isActive) return false
  if (statusFilter.value === 'inactive' && p.isActive) return false
  return true
}))

const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))

watch([search, typeFilter, statusFilter], () => { page.value = 1; selected.value = [] })

const allOnPageSelected = computed(() => paged.value.length > 0 && paged.value.every((p) => selected.value.includes(p.id)))
function toggleSelectAll() {
  if (allOnPageSelected.value) selected.value = selected.value.filter((id) => !paged.value.some((p) => p.id === id))
  else selected.value = [...new Set([...selected.value, ...paged.value.map((p) => p.id)])]
}

const isEditOpen = ref(false)
const editingParty = ref<Party | null>(null)
function openEdit(party: Party) { editingParty.value = party; isEditOpen.value = true }
async function handleEditSubmit(payload: any) {
  if (editingParty.value) {
    await store.update(editingParty.value.id, payload)
    notify.success('طرف‌حساب به‌روزرسانی شد.')
  }
  isEditOpen.value = false
}

async function handleDelete(party: Party) {
  const ok = await confirm(`«${party.name}» حذف شود؟`)
  if (!ok) return
  await store.remove(party.id)
  notify.success('طرف‌حساب حذف شد.')
}

async function handleBulkDelete() {
  const ok = await confirm(`${selected.value.length} طرف‌حساب انتخاب‌شده حذف شوند؟`)
  if (!ok) return
  for (const id of selected.value) await store.remove(id)
  notify.success('طرف‌حساب‌های انتخاب‌شده حذف شدند.')
  selected.value = []
}

function exportExcel() { notify.info('خروجی Excel آماده‌سازی شد.') }
function exportPdf() { notify.info('خروجی PDF آماده‌سازی شد.') }
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink-900">طرف‌حساب‌ها</h1>
        <p class="mt-1 text-sm text-ink-700/60">مدیریت مشتریان، تأمین‌کنندگان، اشخاص و شرکت‌ها</p>
      </div>
      <NuxtLink to="/finance/parties/create" class="rounded-lg bg-gain-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-gain-700">
        + طرف‌حساب جدید
      </NuxtLink>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppSearchInput v-model="search" placeholder="جستجو بر اساس نام یا موبایل..." />
      <AppSelect v-model="typeFilter" placeholder="همه انواع" class="w-40" :options="[
        { value: 'customer', label: 'مشتری' }, { value: 'supplier', label: 'تأمین‌کننده' },
        { value: 'person', label: 'شخص' }, { value: 'company', label: 'شرکت' },
      ]" />
      <AppSelect v-model="statusFilter" placeholder="All statuses" class="w-36" :options="[
        { value: 'active', label: 'فعال' }, { value: 'inactive', label: 'غیرفعال' },
      ]" />
      <div class="me-auto flex gap-2">
        <button v-if="selected.length" class="rounded-lg border border-debt-600/30 px-3 py-2 text-xs font-medium text-debt-600 hover:bg-debt-50" @click="handleBulkDelete">
          حذف گروهی ({{ selected.length }})
        </button>
        <button class="rounded-lg border border-paper-200 px-3 py-2 text-xs font-medium text-ink-700 hover:bg-paper-50" @click="exportExcel">خروجی Excel</button>
        <button class="rounded-lg border border-paper-200 px-3 py-2 text-xs font-medium text-ink-700 hover:bg-paper-50" @click="exportPdf">خروجی PDF</button>
      </div>
    </div>

    <AppTableSkeleton v-if="isLoading" :cols="7" />
    <AppErrorState v-else-if="error" :message="error" @retry="store.fetchAll()" />
    <AppEmptyState v-else-if="!filtered.length" title="طرف‌حسابی یافت نشد." action-label="ایجاد طرف‌حساب" @action="navigateTo('/finance/parties/create')" />

    <template v-else>
      <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
        <table class="w-full min-w-215 text-right text-sm">
          <thead>
            <tr class="border-b border-paper-200 text-xs text-ink-700/60">
              <th class="w-10 px-4 py-3"><input type="checkbox" :checked="allOnPageSelected" @change="toggleSelectAll"></th>
              <th class="px-4 py-3 font-medium">نام</th>
              <th class="px-4 py-3 font-medium">نوع</th>
              <th class="px-4 py-3 font-medium">شماره تماس</th>
              <th class="px-4 py-3 font-medium">مانده</th>
              <th class="px-4 py-3 font-medium">آخرین تراکنش</th>
              <th class="px-4 py-3 font-medium">وضعیت</th>
              <th class="col-actions px-4 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in paged" :key="p.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
              <td class="px-4 py-3"><input v-model="selected" type="checkbox" :value="p.id"></td>
              <td class="px-4 py-3 font-medium text-ink-900">{{ p.name }}</td>
              <td class="px-4 py-3 text-ink-700/70">{{ typeLabel[p.type] }}</td>
              <td class="num px-4 py-3 text-ink-700/70">{{ p.mobile }}</td>
              <td class="num px-4 py-3 font-medium" :class="p.balance > 0 ? 'text-debt-600' : p.balance < 0 ? 'text-gain-700' : 'text-ink-700/60'">
                {{ formatCurrency(Math.abs(p.balance)) }}
              </td>
              <td class="num px-4 py-3 text-ink-700/70">{{ p.lastTransactionAt ? formatJalaliDate(p.lastTransactionAt) : '—' }}</td>
              <td class="px-4 py-3"><AppStatusBadge :label="p.isActive ? 'فعال' : 'غیرفعال'" :tone="p.isActive ? 'gain' : 'neutral'" /></td>
              <td class="col-actions px-4 py-3">
                <div class="flex items-center justify-center">
                  <RowActions
                    :actions="[
                      { key: 'view', label: 'مشاهده', group: 0, to: `/finance/parties/${p.id}` },
                      { key: 'edit', label: 'ویرایش', group: 1, onSelect: () => openEdit(p) },
                      { key: 'delete', label: 'حذف', destructive: true, onSelect: () => handleDelete(p) },
                    ]"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AppPagination v-model:page="page" :page-size="pageSize" :total="filtered.length" />
    </template>

    <AppModal v-model="isEditOpen" title="ویرایش طرف‌حساب" size="lg">
      <PartyForm v-if="editingParty" :initial="editingParty" @submit="handleEditSubmit" @cancel="isEditOpen = false" />
    </AppModal>
  </div>
</template>
