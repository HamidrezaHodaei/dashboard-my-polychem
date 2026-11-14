<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="درخواست نمونه محصول (Request Sample)"
      description="ثبت و پیگیری درخواست نمونه: تأیید مدیر، ارسال، پیگیری مشتری، بازخورد و تبدیل به فروش."
      :action-label="store.canCreate ? 'ثبت درخواست جدید' : undefined"
      @action="openCreate"
    >
      <template #actions>
        <ExportButtons
          v-if="store.canExport"
          :busy="exporting"
          :disabled="!store.total"
          @export="runExport"
        />
      </template>
    </AccessPageHeader>

    <!-- filters -->
    <Card class="gap-4 p-4 shadow-none">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div class="relative md:col-span-2">
          <Icon
            name="lucide:search"
            class="absolute right-3 top-3 size-4 text-muted-foreground"
          />
          <Input
            v-model="store.filters.search"
            dir="rtl"
            class="pr-9 text-right"
            placeholder="جستجو: شناسه (شمارهٔ حواله)، مشتری، برند، محصول، گرید..."
          />
        </div>
        <Select v-model="statusModel">
          <SelectTrigger><SelectValue placeholder="وضعیت" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ وضعیت‌ها</SelectItem>
            <SelectItem v-for="s in STATUS_ORDER.filter(x => x !== 'NEW_REQUEST')" :key="s" :value="s">{{ STATUS_META[s].label }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="store.filters.priority">
          <SelectTrigger><SelectValue placeholder="اولویت" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ اولویت‌ها</SelectItem>
            <SelectItem v-for="(m, k) in PRIORITY_META" :key="k" :value="k">{{ m.label }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="store.filters.rep_id">
          <SelectTrigger><SelectValue placeholder="کارشناس فروش" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ کارشناسان</SelectItem>
            <SelectItem v-for="r in store.options.reps" :key="r.id" :value="String(r.id)">{{ r.name }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="store.filters.product">
          <SelectTrigger><SelectValue placeholder="محصول" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ محصولات</SelectItem>
            <SelectItem v-for="p in store.options.products" :key="p" :value="p">{{ p }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="store.filters.grade">
          <SelectTrigger><SelectValue placeholder="گرید" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ گریدها</SelectItem>
            <SelectItem v-for="g in store.options.grades" :key="g" :value="g">{{ g }}</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="store.filters.feedback">
          <SelectTrigger><SelectValue placeholder="بازخورد مشتری" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ بازخوردها</SelectItem>
            <SelectItem value="NONE">بدون بازخورد</SelectItem>
            <SelectItem v-for="(m, k) in FEEDBACK_META" :key="k" :value="k">{{ m.label }}</SelectItem>
          </SelectContent>
        </Select>
        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">از تاریخ ثبت</Label>
          <JalaliDateInput v-model="store.filters.date_from" />
        </div>
        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">تا تاریخ ثبت</Label>
          <JalaliDateInput v-model="store.filters.date_to" :invalid="!!rangeError" />
        </div>
        <div class="md:col-span-2">
          <Label class="text-xs text-muted-foreground">مشتری</Label>
          <CrmCustomerPicker
            :model-value="customerRef"
            clearable
            @update:model-value="onCustomer"
          />
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-4 border-t pt-3 text-sm">
        <label class="flex cursor-pointer items-center gap-2">
          <input v-model="store.filters.mine" type="checkbox" class="size-4 accent-primary"> درخواست‌های من
        </label>
        <label class="flex cursor-pointer items-center gap-2">
          <input v-model="store.filters.followup_overdue" type="checkbox" class="size-4 accent-primary"> پیگیری عقب‌افتاده
        </label>
        <p v-if="rangeError" class="text-xs text-destructive">{{ rangeError }}</p>
        <Button variant="ghost" size="sm" class="me-auto gap-1.5" @click="store.reset()">
          <Icon name="lucide:rotate-ccw" class="size-4" /> پاک‌کردن فیلترها
        </Button>
      </div>
    </Card>

    <!-- dashboard -->
    <RequestSampleAnalytics
      :data="store.analytics"
      :loading="store.analyticsLoading"
      :active-statuses="store.filters.statuses"
      @filter="s => store.setStatus(s && s.length === 1 ? s[0]! : null).then(() => { if (s && s.length > 1) { store.filters.statuses = s; store.apply() } })"
      @granularity="g => { store.granularity = g; store.loadAnalytics() }"
      @range="applyRangeKey"
    />

    <!-- table -->
    <Card class="gap-0 overflow-hidden p-0 shadow-none">
      <div class="flex items-center justify-between border-b px-4 py-3">
        <h2 class="text-base font-semibold">
          مدیریت درخواست‌ها
        </h2>
        <span class="text-xs text-muted-foreground">{{ toPersianDigits(store.total) }} درخواست</span>
      </div>

      <AppErrorState v-if="store.error" :message="store.error" @retry="store.load()" />
      <div v-else class="overflow-x-auto">
        <Table class="min-w-[64rem]">
          <TableHeader>
            <TableRow>
              <TableHead v-for="c in COLUMNS" :key="c.label" class="whitespace-nowrap">
                <button v-if="c.sort" type="button" class="flex items-center gap-1 hover:text-foreground" @click="store.setSort(c.sort)">
                  {{ c.label }}
                  <Icon
                    v-if="store.sort.replace('-', '') === c.sort"
                    :name="store.sort.startsWith('-') ? 'lucide:arrow-down' : 'lucide:arrow-up'"
                    class="size-3"
                  />
                </button>
                <template v-else>{{ c.label }}</template>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <template v-if="store.loading && !store.rows.length">
              <TableRow v-for="i in 6" :key="i">
                <TableCell v-for="c in COLUMNS" :key="c.label"><Skeleton class="h-5 w-full" /></TableCell>
              </TableRow>
            </template>
            <TableRow v-for="r in store.rows" :key="r.id" class="cursor-pointer" @click="navigateTo(`/crm/request-samples/${r.id}`)">
              <TableCell class="whitespace-nowrap font-medium" dir="ltr">
                {{ r.code }}
                <Icon v-if="r.parent_request_id" name="lucide:link" class="ms-1 inline size-3 text-muted-foreground" title="مرتبط با درخواست قبلی" />
              </TableCell>
              <TableCell>
                <p class="font-medium" dir="auto">{{ r.customer.name }}</p>
                <p v-if="r.customer.brand" class="text-xs text-muted-foreground" dir="auto">برند: {{ r.customer.brand }}</p>
              </TableCell>
              <TableCell dir="auto">{{ r.product || '—' }}<span v-if="r.items_count > 1" class="text-xs text-muted-foreground"> (+{{ toPersianDigits(r.items_count - 1) }})</span></TableCell>
              <TableCell dir="auto">{{ r.grade || '—' }}</TableCell>
              <TableCell class="whitespace-nowrap" dir="ltr">{{ r.quantity_label || '—' }}</TableCell>
              <TableCell class="whitespace-nowrap">{{ fmtDate(r.requested_date) }}</TableCell>
              <TableCell>{{ r.sales_rep.name || '—' }}</TableCell>
              <TableCell><RequestSampleStatusBadge :status="r.priority" kind="priority" /></TableCell>
              <TableCell>
                <RequestSampleStatusBadge :status="r.status" />
                <p v-if="r.followup_overdue" class="mt-1 text-[11px] font-medium text-destructive">پیگیری عقب‌افتاده</p>
              </TableCell>
              <TableCell>
                <RequestSampleStatusBadge v-if="r.feedback_status" :status="r.feedback_status" kind="feedback" />
                <span v-else class="text-xs text-muted-foreground">—</span>
              </TableCell>
              <TableCell @click.stop>
                <div class="flex items-center gap-0.5">
                  <Button variant="ghost" size="icon" title="مشاهده جزئیات" aria-label="مشاهده جزئیات" as-child>
                    <NuxtLink :to="`/crm/request-samples/${r.id}`"><Icon name="lucide:eye" class="size-4" /></NuxtLink>
                  </Button>
                  <Button v-if="r.my_actions.can_edit" variant="ghost" size="icon" title="ویرایش" aria-label="ویرایش" @click="openEdit(r.id)">
                    <Icon name="lucide:pencil" class="size-4" />
                  </Button>
                  <Button v-if="r.my_actions.can_follow_up" variant="ghost" size="icon" title="پیگیری" aria-label="پیگیری" as-child>
                    <NuxtLink :to="`/crm/request-samples/${r.id}?tab=followups`"><Icon name="lucide:phone-call" class="size-4" /></NuxtLink>
                  </Button>
                  <Button v-if="r.my_actions.can_delete" variant="ghost" size="icon" class="text-destructive hover:text-destructive" title="حذف" aria-label="حذف" @click="askDelete(r.id, r.code)">
                    <Icon name="lucide:trash-2" class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
            <TableRow v-if="!store.loading && !store.rows.length">
              <TableCell :colspan="COLUMNS.length" class="p-0">
                <AppEmptyState title="درخواستی پیدا نشد" />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <NumberedPagination :page="store.page" :page-size="store.perPage" :total="store.total" :loading="store.loading" @update:page="store.setPage" />
    </Card>

    <LazyRequestSampleFormWizard
      v-if="wizardLoaded"
      v-model:open="wizardOpen"
      :request-id="editingId"
      @saved="onSaved"
    />

  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { CrmCustomerRef } from '~/stores/crm'
import { FEEDBACK_META, PRIORITY_META, STATUS_META, STATUS_ORDER } from '~/utils/requestSample'
import { formatJalali, jalaliMonthLength, jalaliToIso, toPersianDigits } from '~/utils/jalali'
import { requestErrorMessage } from '~/utils/request-workflow'

usePageSeoMeta({ title: 'درخواست نمونه محصول' })

const store = useRequestSampleStore()
const notify = useNotify()
const route = useRoute()

const COLUMNS = [
  { label: 'شناسه', sort: 'id' }, { label: 'مشتری', sort: 'customer' }, { label: 'محصول' }, { label: 'گرید' },
  { label: 'مقدار نمونه' }, { label: 'تاریخ ثبت', sort: 'requested_date' }, { label: 'کارشناس فروش' },
  { label: 'اولویت', sort: 'priority' }, { label: 'وضعیت', sort: 'status' }, { label: 'بازخورد مشتری', sort: 'feedback' },
  { label: 'عملیات' },
] as { label: string, sort?: string }[]

const fmtDate = (iso: string) => toPersianDigits(formatJalali(iso))

/* filters: status select mirrors the single-status filter; every change refreshes table + dashboard */
const statusModel = computed({
  get: () => (store.filters.statuses.length === 1 ? store.filters.statuses[0]! : 'all'),
  set: (v: string) => { store.filters.statuses = v === 'all' ? [] : [v] },
})
const customerRef = computed<CrmCustomerRef | null>(() =>
  store.filters.customer_id ? { id: store.filters.customer_id, name: store.filters.customer_name, province: null, industry: null } : null)
function onCustomer(c: CrmCustomerRef | null) {
  store.filters.customer_id = c?.id ?? null
  store.filters.customer_name = c?.name ?? ''
}
const rangeError = computed(() =>
  store.filters.date_from && store.filters.date_to && store.filters.date_from > store.filters.date_to ? 'تاریخ شروع بعد از پایان است.' : '')

let timer: ReturnType<typeof setTimeout> | undefined
watch(() => JSON.stringify(store.filters), () => {
  if (rangeError.value) return
  clearTimeout(timer)
  timer = setTimeout(() => store.apply(), 350)
})

/** clicking a bar of the trend chart narrows the date range to that day / week / month */
function applyRangeKey(key: string) {
  if (/^\d{4}-\d{2}$/.test(key)) {
    const [jy, jm] = key.split('-').map(Number) as [number, number]
    store.filters.date_from = jalaliToIso(jy, jm, 1)
    store.filters.date_to = jalaliToIso(jy, jm, jalaliMonthLength(jy, jm))
  }
  else {
    store.filters.date_from = key
    const gran = store.analytics?.granularity
    const end = new Date(`${key}T00:00:00Z`)
    end.setUTCDate(end.getUTCDate() + (gran === 'week' ? 6 : 0))
    store.filters.date_to = end.toISOString().slice(0, 10)
  }
}

/* export */
const exporting = ref<'' | 'xlsx' | 'docx'>('')
async function runExport(format: 'xlsx' | 'docx') {
  exporting.value = format
  try { await store.exportFile(format) }
  catch (e) { notify.error(requestErrorMessage(e, 'دریافت خروجی انجام نشد.')) }
  finally { exporting.value = '' }
}

/* wizard */
const wizardLoaded = ref(false)
const wizardOpen = ref(false)
const editingId = ref<number | null>(null)
watch(wizardOpen, (v) => { if (v) wizardLoaded.value = true })
function openCreate() { editingId.value = null; wizardOpen.value = true }
function openEdit(id: number) { editingId.value = id; wizardOpen.value = true }
async function onSaved(id: number, submitted: boolean) {
  notify.success(submitted ? 'درخواست ثبت و برای تأیید ارسال شد.' : 'پیش‌نویس ذخیره شد.')
  await Promise.all([store.load(), store.loadAnalytics(), store.loadOptions()])
  if (submitted) await navigateTo(`/crm/request-samples/${id}`)
}

/* delete (the app-wide confirm host lives in app.vue) */
const { confirm } = useConfirm()
async function askDelete(id: number, code: string) {
  const ok = await confirm({ title: 'حذف درخواست', description: `درخواست ${code} حذف شود؟`, confirmLabel: 'حذف', tone: 'danger' })
  if (!ok) return
  try {
    await store.remove(id)
    notify.success('درخواست حذف شد.')
    await Promise.all([store.load(), store.loadAnalytics()])
  }
  catch (e) { notify.error(requestErrorMessage(e, 'حذف انجام نشد.')) }
}

onMounted(async () => {
  await Promise.all([store.loadOptions(), store.apply()])
  if (route.query.new && store.canCreate) openCreate()
})
</script>
