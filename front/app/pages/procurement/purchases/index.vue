<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="گزارشات خرید"
      description="ثبت و مدیریت خریدهای واحد تدارکات و لجستیک و تحلیل عملکرد خرید بر اساس اطلاعات واقعی سامانه."
      section="تدارکات و لجستیک"
      :action-label="store.can('create') ? 'ثبت خرید جدید' : undefined"
      @action="navigateTo('/procurement/purchases/new')"
    >
      <template #actions>
        <template v-if="store.can('export')">
          <Button variant="outline" size="sm" class="gap-2" :disabled="!!busy" @click="exportExcel('all')">
            <Icon :name="busy === 'xlsx' ? 'lucide:loader-circle' : 'lucide:file-spreadsheet'" class="size-4" :class="busy === 'xlsx' && 'animate-spin'" />
            Excel (همه گزارش‌ها)
          </Button>
          <Button variant="outline" size="sm" class="gap-2" :disabled="!!busy" @click="printReport('overview')">
            <Icon :name="busy === 'pdf' ? 'lucide:loader-circle' : 'lucide:file-down'" class="size-4" :class="busy === 'pdf' && 'animate-spin'" />
            PDF / چاپ
          </Button>
        </template>
      </template>
    </AccessPageHeader>

    <!-- filters: one set drives KPIs, charts, groups, the table and every export -->
    <Card class="gap-4 p-4 shadow-none print-hide">
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <PurchasesField label="بازه زمانی (تاریخ ثبت)">
          <div class="flex flex-wrap gap-1">
            <button
              v-for="p in presets" :key="p.key" type="button"
              class="rounded-full border px-3 py-1 text-xs transition-colors hover:bg-muted"
              :class="preset === p.key && 'border-primary bg-primary text-primary-foreground hover:bg-primary'"
              @click="applyPreset(p.key)"
            >{{ p.label }}</button>
          </div>
        </PurchasesField>
        <PurchasesField label="از تاریخ"><JalaliDateInput v-model="store.filters.date_from" @update:model-value="customRange" /></PurchasesField>
        <PurchasesField label="تا تاریخ"><JalaliDateInput v-model="store.filters.date_to" @update:model-value="customRange" /></PurchasesField>
        <PurchasesField label="نمایش روند بر اساس">
          <select v-model="store.filters.granularity" :class="selectCls" @change="store.loadDashboard()">
            <option value="day">روزانه</option><option value="week">هفتگی</option><option value="month">ماهانه</option>
          </select>
        </PurchasesField>
        <PurchasesField label="گروه کالایی">
          <select v-model="store.filters.category_id" :class="selectCls" @change="refresh">
            <option value="">همه گروه‌ها</option>
            <option v-for="c in store.meta?.categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
          </select>
        </PurchasesField>
        <PurchasesField label="وضعیت خرید">
          <select v-model="store.filters.status" :class="selectCls" @change="refresh">
            <option value="">همه وضعیت‌ها</option>
            <option v-for="s in store.meta?.statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </PurchasesField>
        <PurchasesField label="نام تأمین‌کننده"><Input v-model="store.filters.supplier" placeholder="جستجو…" @input="debounced" /></PurchasesField>
        <PurchasesField label="شرکت یا واحد متقاضی">
          <Input v-model="store.filters.unit" list="purchase-units" placeholder="نام واحد…" @input="debounced" />
          <datalist id="purchase-units"><option v-for="u in store.meta?.requester_units" :key="u" :value="u" /></datalist>
        </PurchasesField>
        <PurchasesField label="شماره درخواست خرید"><Input v-model="store.filters.request_no" dir="ltr" class="text-right" placeholder="PR-1405-…" @input="debounced" /></PurchasesField>
        <PurchasesField label="نام کالا"><Input v-model="store.filters.item" placeholder="جستجو…" @input="debounced" /></PurchasesField>
      </div>
      <div class="flex justify-end"><Button variant="ghost" size="sm" class="gap-2" @click="reset"><Icon name="lucide:rotate-ccw" class="size-4" />پاک‌کردن فیلترها</Button></div>
    </Card>

    <p v-if="store.dashError" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ store.dashError }}</p>

    <!-- KPIs -->
    <div v-if="d" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <button v-for="k in kpiCards" :key="k.key" type="button" class="text-right" @click="showKpi(k.key)">
        <Card class="h-full gap-2 p-5 shadow-none transition-colors hover:border-primary/60" :class="store.kpi === k.key && 'border-primary ring-1 ring-primary'">
          <div class="flex items-center justify-between text-sm text-muted-foreground">
            <span>{{ k.label }}</span><Icon :name="k.icon" class="size-4 text-primary" />
          </div>
          <p class="text-2xl font-semibold" :class="k.negative && 'text-destructive'">{{ k.value }}</p>
          <p class="text-xs text-muted-foreground">{{ k.note }}</p>
          <p class="text-[11px] text-primary">مشاهده جزئیات ←</p>
        </Card>
      </button>
    </div>
    <div v-else-if="store.dashLoading" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"><Skeleton v-for="i in 6" :key="i" class="h-32 rounded-xl" /></div>

    <!-- charts -->
    <div v-if="d" class="grid gap-4 lg:grid-cols-2">
      <PrintableChart title="روند تعداد درخواست‌های خرید" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">روند تعداد درخواست‌های خرید</h3>
        <PurchasesBars :labels="labels" :series="[{ name: 'درخواست‌ها', color: '#6366f1', values: d.trend.map(t => t.requests) }]" :format="(n: number | null) => count(n)" />
      </PrintableChart>
      <PrintableChart title="روند هزینه‌های خرید" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">روند هزینه‌های خرید (خریدهای تکمیل‌شده)</h3>
        <PurchasesLine :labels="labels" :series="[{ name: 'هزینه', color: '#0ea5e9', values: d.trend.map(t => t.spent) }]" />
      </PrintableChart>
      <PrintableChart title="توزیع خرید بر اساس گروه کالایی" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">توزیع خرید بر اساس گروه کالایی</h3>
        <div v-if="!distribution.length" class="py-10 text-center text-sm text-muted-foreground">هنوز خریدی ثبت نشده است.</div>
        <ul v-else class="space-y-2">
          <li v-for="g in distribution" :key="g.name" class="space-y-1">
            <div class="flex justify-between text-xs"><span>{{ g.name }}</span><span class="text-muted-foreground">{{ count(g.requests) }} درخواست — {{ money(g.spent) }}</span></div>
            <div class="h-2 overflow-hidden rounded-full bg-muted"><div class="h-full rounded-full bg-primary" :style="{ width: `${g.pct}%` }" /></div>
          </li>
        </ul>
      </PrintableChart>
      <PrintableChart title="مقایسه هزینه برآوردی و نهایی" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">مقایسه هزینه برآوردی و هزینه نهایی (اقلام دارای هر دو قیمت)</h3>
        <PurchasesBars :labels="labels" :series="[{ name: 'برآوردی', color: '#f59e0b', values: d.trend.map(t => t.estimated) }, { name: 'نهایی', color: '#10b981', values: d.trend.map(t => t.final) }]" />
      </PrintableChart>
      <PrintableChart title="تحلیل میزان صرفه‌جویی" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">تحلیل صرفه‌جویی (فقط اقلام با قیمت مبنای تأییدشده)</h3>
        <PurchasesLine :labels="labels" :series="[{ name: 'صرفه‌جویی', color: '#10b981', values: d.trend.map(t => t.savings) }]" />
      </PrintableChart>
      <PrintableChart title="مقایسه عملکرد تأمین‌کنندگان" class="gap-3 p-5 shadow-none">
        <h3 class="text-sm font-semibold">مقایسه عملکرد تأمین‌کنندگان</h3>
        <div v-if="!d.suppliers.length" class="py-10 text-center text-sm text-muted-foreground">هنوز استعلامی ثبت نشده است.</div>
        <div v-else class="max-h-64 overflow-auto">
          <table class="w-full text-xs">
            <thead class="sticky top-0 bg-background text-muted-foreground"><tr>
              <th class="p-1.5 text-right">تأمین‌کننده</th><th class="p-1.5">استعلام</th><th class="p-1.5">انتخاب‌شده</th><th class="p-1.5">کمترین قیمت</th><th class="p-1.5">میانگین تحویل (روز)</th><th class="p-1.5">مبلغ خرید</th>
            </tr></thead>
            <tbody>
              <tr v-for="s in d.suppliers" :key="s.supplier_id ?? s.name" class="border-t text-center">
                <td class="p-1.5 text-right">{{ s.name }}</td><td>{{ count(s.inquiries) }}</td>
                <td>{{ count(s.selected) }}<span v-if="s.win_rate !== null" class="text-muted-foreground"> ({{ count(s.win_rate) }}٪)</span></td>
                <td>{{ s.compared ? `${count(s.cheapest)} از ${count(s.compared)}` : '—' }}</td><td>{{ count(s.avg_delivery_days) }}</td><td>{{ money(s.awarded) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </PrintableChart>
    </div>

    <!-- commodity groups (names come from the supplier bank's categories) -->
    <Card v-if="d" class="overflow-hidden py-0 shadow-none">
      <div class="flex items-center justify-between border-b p-4">
        <h3 class="font-semibold">تحلیل گروه‌های کالایی</h3>
        <div v-if="store.can('export')" class="flex gap-1.5">
          <Button variant="outline" size="sm" :disabled="!!busy" @click="exportExcel('groups')">Excel</Button>
          <Button variant="outline" size="sm" :disabled="!!busy" @click="printReport('groups')">PDF</Button>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-muted/50 text-muted-foreground"><tr>
            <th class="p-3 text-right">گروه کالایی</th><th class="p-3">کل درخواست‌ها</th><th class="p-3">تکمیل‌شده</th><th class="p-3">باز</th><th class="p-3">مجموع هزینه</th><th class="p-3">صرفه‌جویی</th>
          </tr></thead>
          <tbody>
            <tr v-for="g in d.groups" :key="g.category_id ?? g.name" class="cursor-pointer border-t text-center hover:bg-muted/40" @click="openGroup(g)">
              <td class="p-3 text-right font-medium">{{ g.name }}<Badge v-if="g.inactive" variant="outline" class="mr-2">غیرفعال</Badge></td>
              <td>{{ count(g.requests) }}</td><td>{{ count(g.completed) }}</td><td>{{ count(g.open) }}</td><td>{{ money(g.spent) }}</td>
              <td :class="g.savings !== null && g.savings < 0 && 'text-destructive'">{{ g.savings === null ? '—' : money(g.savings) }}</td>
            </tr>
            <tr v-if="!d.groups.length"><td colspan="6" class="p-6 text-center text-muted-foreground">گروه کالایی در سامانه تعریف نشده است.</td></tr>
          </tbody>
        </table>
      </div>
      <div v-if="group" class="border-t bg-muted/20 p-4">
        <div class="mb-2 flex items-center justify-between">
          <h4 class="text-sm font-semibold">درخواست‌های گروه «{{ group.name }}» ({{ count(groupTotal) }})</h4>
          <Button variant="ghost" size="sm" @click="group = null">بستن</Button>
        </div>
        <p v-if="groupLoading" class="py-4 text-center text-sm text-muted-foreground">در حال بارگذاری…</p>
        <table v-else class="w-full text-xs">
          <thead class="text-muted-foreground"><tr><th class="p-2 text-right">شماره</th><th class="p-2 text-right">موضوع</th><th class="p-2">وضعیت</th><th class="p-2">مبلغ نهایی</th><th class="p-2">صرفه‌جویی</th></tr></thead>
          <tbody>
            <tr v-for="r in groupRows" :key="r.id" class="cursor-pointer border-t text-center hover:bg-muted/40" @click="navigateTo(`/procurement/purchases/${r.id}`)">
              <td class="p-2 text-right" dir="ltr">{{ r.request_no }}</td><td class="p-2 text-right">{{ r.subject }}</td>
              <td><span class="rounded-full px-2 py-0.5" :class="statusTone[r.status]">{{ r.status_label }}</span></td><td>{{ money(r.final_amount) }}</td><td>{{ r.savings === null ? '—' : money(r.savings) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="groupTotal > groupRows.length" class="mt-2 text-xs text-muted-foreground">{{ count(groupRows.length) }} مورد اول نمایش داده شد؛ برای فهرست کامل از فیلتر «گروه کالایی» استفاده کنید.</p>
      </div>
    </Card>

    <!-- requests -->
    <Card ref="listCard" class="overflow-hidden py-0 shadow-none">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b p-4">
        <div>
          <h3 class="font-semibold">{{ store.kpi ? `جزئیات شاخص: ${kpiLabels[store.kpi]}` : 'فهرست درخواست‌های خرید' }}</h3>
          <p v-if="store.kpi && d" class="text-xs text-muted-foreground">{{ d.definitions[store.kpi] }}</p>
        </div>
        <div class="flex gap-1.5">
          <Button v-if="store.kpi" variant="ghost" size="sm" @click="showKpi('')">نمایش همه</Button>
          <template v-if="store.can('export')">
            <Button variant="outline" size="sm" :disabled="!!busy" @click="exportExcel('requests')">Excel ریز درخواست‌ها</Button>
            <Button variant="outline" size="sm" :disabled="!!busy" @click="printReport('requests')">PDF</Button>
          </template>
        </div>
      </div>
      <p v-if="store.listError" class="p-4 text-sm text-destructive">{{ store.listError }}</p>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-muted/50 text-muted-foreground"><tr>
            <th v-for="c in columns" :key="c.key" class="whitespace-nowrap p-3 text-right">
              <button v-if="c.sort" type="button" class="flex items-center gap-1 hover:text-foreground" @click="store.setSort(c.key)">
                {{ c.label }}<Icon v-if="store.sort === c.key" :name="store.direction === 'asc' ? 'lucide:arrow-up' : 'lucide:arrow-down'" class="size-3" />
              </button>
              <span v-else>{{ c.label }}</span>
            </th>
          </tr></thead>
          <tbody>
            <tr v-for="r in store.rows" :key="r.id" class="cursor-pointer border-t hover:bg-muted/40" @click="navigateTo(`/procurement/purchases/${r.id}`)">
              <td class="whitespace-nowrap p-3" dir="ltr">{{ r.request_no }}</td>
              <td class="p-3">{{ r.subject || '—' }}<div class="text-xs text-muted-foreground">{{ r.categories.join('، ') }}</div></td>
              <td class="p-3">{{ r.requester_unit || '—' }}</td>
              <td class="whitespace-nowrap p-3">{{ r.request_date_jalali }}</td>
              <td class="p-3"><span class="whitespace-nowrap rounded-full px-2 py-0.5 text-xs" :class="statusTone[r.status]">{{ r.status_label }}</span></td>
              <td v-if="store.kpi === 'next_month'" class="p-3">{{ money(r.forecast_amount) }}<div class="text-[11px] text-muted-foreground">{{ basisLabel[r.forecast_basis || ''] || 'بدون مبلغ' }}</div></td>
              <template v-else>
                <td class="p-3">{{ r.supplier_name || '—' }}</td>
                <td class="p-3">{{ money(r.final_amount ?? r.estimated_total ?? r.budget_amount) }}<div class="text-[11px] text-muted-foreground">{{ r.final_amount !== null ? 'نهایی' : r.estimated_total !== null ? 'برآورد' : r.budget_amount !== null ? 'بودجه' : '' }}</div></td>
                <td class="p-3" :class="r.savings !== null && r.savings < 0 && 'text-destructive'">{{ r.savings === null ? '—' : money(r.savings) }}</td>
              </template>
            </tr>
            <tr v-if="!store.rows.length && !store.listLoading"><td :colspan="columns.length" class="p-8 text-center text-muted-foreground">درخواستی با این فیلترها پیدا نشد.</td></tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t p-3 text-sm">
        <span class="text-muted-foreground">{{ count(store.total) }} درخواست</span>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="store.page <= 1" @click="store.setPage(store.page - 1)">قبلی</Button>
          <span>{{ count(store.page) }} / {{ count(pages) }}</span>
          <Button variant="outline" size="sm" :disabled="store.page >= pages" @click="store.setPage(store.page + 1)">بعدی</Button>
        </div>
      </div>
    </Card>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError, apiFetchPage } from '~/services/backendApi'
import { count, money, statusTone } from '~/utils/purchase'
import type { Dashboard, PurchaseRow } from '~/utils/purchase'

definePageMeta({ title: 'گزارشات خرید' })

const store = usePurchasesStore()
const notify = useNotify()
const d = computed(() => store.dashboard)
const busy = ref<'' | 'xlsx' | 'pdf'>('')
const listCard = ref<{ $el: HTMLElement } | null>(null)
const selectCls = 'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring'
const labels = computed(() => d.value?.trend.map(t => t.label) ?? [])
const pages = computed(() => Math.max(1, Math.ceil(store.total / store.perPage)))

/* ── period presets (Gregorian ISO bounds; the backend reads the registration date) ── */
const presets = [
  { key: 'week', label: 'هفته اخیر' }, { key: 'month', label: 'ماه اخیر' }, { key: 'quarter', label: 'سه‌ماهه' },
  { key: 'year', label: 'سال اخیر' }, { key: 'all', label: 'همه' },
]
const preset = ref('all')
const iso = (dt: Date) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
function applyPreset(key: string) {
  preset.value = key
  const to = new Date()
  const from = new Date()
  if (key === 'all') { store.filters.date_from = ''; store.filters.date_to = '' }
  else {
    from.setDate(to.getDate() - ({ week: 7, month: 30, quarter: 90, year: 365 } as Record<string, number>)[key]!)
    store.filters.date_from = iso(from)
    store.filters.date_to = iso(to)
    store.filters.granularity = key === 'week' ? 'day' : key === 'year' ? 'month' : key === 'month' ? 'week' : 'month'
  }
  refresh()
}
function customRange() { preset.value = 'custom'; debounced() }

let timer: ReturnType<typeof setTimeout> | undefined
const debounced = () => { clearTimeout(timer); timer = setTimeout(refresh, 350) }
const refresh = () => store.applyFilters()
const reset = () => { preset.value = 'all'; return store.resetFilters() }

/* ── KPI cards ── */
const kpiLabels: Record<string, string> = {
  total: 'تعداد کل درخواست‌های خرید', completed: 'خریدهای تکمیل‌شده', open: 'درخواست‌های باز و در حال انجام',
  spent: 'مجموع هزینه‌های انجام‌شده', savings: 'صرفه‌جویی محقق‌شده', next_month: 'بودجه پیش‌بینی‌شده ماه آینده',
}
const basisLabel: Record<string, string> = { selected_quote: 'قیمت توافقی', estimate: 'برآورد اقلام', budget: 'بودجهٔ درخواست' }
const kpiCards = computed(() => {
  const k = d.value!.kpis
  const nm = k.next_month
  return [
    { key: 'total', label: kpiLabels.total, icon: 'lucide:files', value: count(k.total.value), note: k.total.cancelled ? `${count(k.total.cancelled)} مورد لغوشده` : 'بدون پیش‌نویس‌ها' },
    { key: 'completed', label: kpiLabels.completed, icon: 'lucide:circle-check', value: count(k.completed.value), note: 'خرید انجام و کالا کامل تحویل‌شده' },
    { key: 'open', label: kpiLabels.open, icon: 'lucide:hourglass', value: count(k.open.value), note: 'در هر مرحله از گردش کار' },
    { key: 'spent', label: kpiLabels.spent, icon: 'lucide:wallet', value: money(k.spent.value), note: k.spent.extra_costs_included ? 'شامل هزینه‌های جانبی' : 'فقط اقلام فیلترشده' },
    {
      key: 'savings', label: kpiLabels.savings, icon: 'lucide:piggy-bank',
      value: k.savings.value === null ? 'محاسبه نشده' : money(k.savings.value), negative: (k.savings.value ?? 0) < 0,
      note: k.savings.items_total ? `بر اساس ${count(k.savings.items_counted)} از ${count(k.savings.items_total)} قلم؛ بقیه قیمت مبنای تأییدشده ندارند` : 'قیمت مبنای تأییدشده‌ای ثبت نشده است',
    },
    {
      key: 'next_month', label: `${kpiLabels.next_month} (${nm.month})`, icon: 'lucide:calendar-clock', value: money(nm.amount),
      note: `${count(nm.requests_count)} درخواست${nm.unpriced_count ? ` — ${count(nm.unpriced_count)} مورد بدون مبلغ` : ''}`,
    },
  ]
})
function showKpi(key: string) {
  store.kpi = store.kpi === key ? '' : key
  store.page = 1
  store.loadList()
  nextTick(() => listCard.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const columns = computed(() => [
  { key: 'request_no', label: 'شماره', sort: true }, { key: 'subject', label: 'موضوع', sort: true },
  { key: 'requester_unit', label: 'واحد متقاضی', sort: true }, { key: 'request_date', label: 'تاریخ ثبت', sort: true },
  { key: 'status', label: 'وضعیت', sort: true },
  ...(store.kpi === 'next_month'
    ? [{ key: 'forecast', label: 'مبلغ پیش‌بینی', sort: false }]
    : [{ key: 'supplier', label: 'تأمین‌کنندهٔ منتخب', sort: false }, { key: 'final_amount', label: 'مبلغ', sort: true }, { key: 'savings', label: 'صرفه‌جویی', sort: false }]),
])

/* ── group distribution + drill-down ── */
const distribution = computed(() => {
  const gs = (d.value?.groups ?? []).filter(g => g.requests > 0)
  const max = Math.max(1, ...gs.map(g => g.requests))
  return gs.map(g => ({ ...g, pct: (g.requests / max) * 100 }))
})
const group = ref<Dashboard['groups'][number] | null>(null)
const groupRows = ref<PurchaseRow[]>([])
const groupTotal = ref(0)
const groupLoading = ref(false)
async function openGroup(g: Dashboard['groups'][number]) {
  group.value = g
  groupRows.value = []
  groupLoading.value = true
  try {
    const res = await apiFetchPage<PurchaseRow>('/purchases', {
      date_from: store.filters.date_from || undefined, date_to: store.filters.date_to || undefined,
      status: store.filters.status || undefined, supplier: store.filters.supplier || undefined, unit: store.filters.unit || undefined,
      request_no: store.filters.request_no || undefined, item: store.filters.item || undefined,
      category_id: g.category_id ?? undefined, per_page: 50, sort: 'request_date', direction: 'desc', kpi: 'total',
    })
    groupRows.value = res.items
    groupTotal.value = res.total
  }
  catch (e) { notify.error('فهرست گروه بارگذاری نشد', e instanceof ApiError ? e.message : undefined) }
  finally { groupLoading.value = false }
}

/* ── exports (the same filters as the screen) ── */
async function exportExcel(kind: string) {
  busy.value = 'xlsx'
  try { await store.exportExcel(kind) }
  catch (e) { notify.error('خروجی Excel گرفته نشد', e instanceof ApiError ? e.message : undefined) }
  finally { busy.value = '' }
}
const esc = (s: unknown) => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!))
/** PDF = the browser's print dialog («Save as PDF»), the same convention as the other modules. */
async function printReport(kind: string) {
  busy.value = 'pdf'
  try {
    const r = await store.exportRows(kind)
    const w = window.open('', '_blank')
    if (!w) { notify.warning('مرورگر پنجره چاپ را مسدود کرد'); return }
    const body = r.rows.map(row => `<tr>${row.map(c => `<td>${esc(typeof c === 'number' ? count(c) : c)}</td>`).join('')}</tr>`).join('')
    w.document.write(`<html dir="rtl" lang="fa"><head><meta charset="utf-8"><title>${esc(r.title)}</title>
      <style>body{font-family:Tahoma,sans-serif;font-size:11px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:4px 6px;text-align:right}th{background:#f3f4f6}</style></head>
      <body><h3>${esc(r.title)}</h3><table><thead><tr>${r.headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></body></html>`)
    w.document.close()
    w.focus()
    w.print()
  }
  catch (e) { notify.error('چاپ انجام نشد', e instanceof ApiError ? e.message : undefined) }
  finally { busy.value = '' }
}

onMounted(async () => {
  await store.loadMeta().catch(() => {})
  await store.applyFilters()
})
</script>
