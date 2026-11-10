<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="بانک اطلاعات لجستیک"
      description="شرکت‌های حمل‌ونقل و رانندگان ثبت‌شده را بررسی کنید یا متقاضی جدید اضافه کنید."
      :action-label="store.typesWith('create').length ? 'ثبت متقاضی جدید' : undefined"
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

    <div class="grid gap-4 sm:grid-cols-4">
      <AccessStat
        label="تعداد کل"
        :value="summary.total"
        icon="lucide:truck"
      />
      <AccessStat
        label="شرکت‌های حمل‌ونقل"
        :value="summary.company"
        icon="lucide:building-2"
      />
      <AccessStat
        label="رانندگان"
        :value="summary.driver"
        icon="lucide:user-round"
      />
      <AccessStat
        label="در انتظار بررسی"
        :value="summary.pending"
        icon="lucide:timer"
      />
    </div>

    <Card class="overflow-hidden py-0 shadow-none">
      <div class="flex min-w-0 flex-col gap-3 border-b p-4">
        <!-- applicant type tabs (only the types this user may read) -->
        <div
          class="flex flex-wrap gap-2"
          role="tablist"
          aria-label="نوع متقاضی"
        >
          <button
            v-for="t in typeTabs"
            :key="t.value"
            type="button"
            role="tab"
            class="rounded-full border px-4 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="store.filters.applicant_type === t.value ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted'"
            :aria-selected="store.filters.applicant_type === t.value"
            @click="setTypeFilter(t.value)"
          >
            {{ t.label }}
          </button>
        </div>

        <div class="grid w-full min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div class="relative w-full min-w-0 xl:col-span-2">
            <Icon
              name="lucide:search"
              class="absolute right-3 top-2.5 size-4 text-muted-foreground"
            />
            <Input
              v-model="store.filters.search"
              dir="rtl"
              placeholder="جستجوی نام، موبایل، کد ملی یا شناسه ملی..."
              class="w-full min-w-0 pr-9 text-right"
              @keyup.enter="applyNow"
            />
          </div>
          <Select v-model="statusModel">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="وضعیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه وضعیت‌ها
              </SelectItem>
              <SelectItem
                v-for="(label, code) in STATUS_LABELS"
                :key="code"
                :value="code"
              >
                {{ label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Select v-model="areaModel">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="محدوده فعالیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه محدوده‌ها
              </SelectItem>
              <SelectItem
                v-for="o in catalog?.area_types ?? []"
                :key="o.code"
                :value="o.code"
              >
                {{ o.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <!-- company-only filter -->
          <Select
            v-if="store.filters.applicant_type === 'COMPANY'"
            v-model="provinceModel"
          >
            <SelectTrigger class="w-full">
              <SelectValue placeholder="استان" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه استان‌ها
              </SelectItem>
              <SelectItem
                v-for="p in catalog?.provinces ?? []"
                :key="p.name"
                :value="p.name"
              >
                {{ p.name }}
              </SelectItem>
            </SelectContent>
          </Select>
          <!-- driver-only filter -->
          <Select
            v-else-if="store.filters.applicant_type === 'DRIVER'"
            v-model="vehicleModel"
          >
            <SelectTrigger class="w-full">
              <SelectValue placeholder="نوع خودرو" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه خودروها
              </SelectItem>
              <SelectItem
                v-for="o in catalog?.vehicle_types ?? []"
                :key="o.code"
                :value="o.code"
              >
                {{ o.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex flex-wrap items-center justify-start gap-2">
          <Button
            variant="ghost"
            @click="resetAll"
          >
            بازنشانی
          </Button>
          <span
            v-if="store.loading && store.applicants.length"
            class="flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            <Icon
              name="lucide:loader-circle"
              class="size-3.5 animate-spin"
            /> در حال جستجو...
          </span>
        </div>
      </div>

      <div class="overflow-x-auto">
        <div
          v-if="store.loading && !store.applicants.length"
          class="p-8 text-center text-sm text-muted-foreground"
        >
          در حال بارگذاری بانک اطلاعات لجستیک...
        </div>
        <div
          v-else-if="store.loadError"
          class="p-8 text-center text-sm text-destructive"
        >
          {{ store.loadError }}
        </div>
        <Table v-else-if="store.applicants.length">
          <TableHeader>
            <TableRow>
              <TableHead>متقاضی</TableHead>
              <TableHead>مشخصات</TableHead>
              <TableHead>محدوده فعالیت</TableHead>
              <TableHead>منبع ثبت</TableHead>
              <TableHead>وضعیت</TableHead>
              <TableHead class="text-right">
                عملیات
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="a in store.applicants"
              :key="a.id"
              class="border-b border-slate-300/70 transition-colors odd:bg-white even:bg-slate-100 hover:bg-amber-100/70 dark:border-zinc-700 dark:odd:bg-zinc-900 dark:even:bg-zinc-800 dark:hover:bg-amber-300/15"
            >
              <TableCell>
                <p
                  class="font-medium"
                  dir="auto"
                >
                  {{ a.display_name }}
                </p>
                <div class="mt-1 flex flex-wrap items-center gap-2">
                  <Badge variant="outline">
                    {{ TYPE_LABELS[a.applicant_type] }}
                  </Badge>
                  <span
                    class="text-xs text-muted-foreground"
                    dir="ltr"
                  >{{ a.mobile }}</span>
                </div>
              </TableCell>
              <TableCell class="text-sm">
                <template v-if="a.applicant_type === 'COMPANY'">
                  <p dir="auto">
                    {{ [a.province, a.city].filter(Boolean).join('، ') || '—' }}
                  </p>
                  <p class="text-xs text-muted-foreground">
                    دفتر فعالیت
                  </p>
                </template>
                <template v-else>
                  <p dir="auto">
                    {{ labelOf(catalog?.vehicle_types, a.vehicle_type) || '—' }}
                    <span class="text-xs text-muted-foreground">· {{ labelOf(catalog?.body_types, a.body_type) }}</span>
                  </p>
                  <p
                    v-if="a.capacity_tons != null"
                    class="text-xs text-muted-foreground"
                  >
                    ظرفیت {{ fmtTons(a.capacity_tons) }} تن
                  </p>
                </template>
              </TableCell>
              <TableCell>
                <Badge
                  v-if="a.area_type"
                  variant="secondary"
                >
                  {{ labelOf(catalog?.area_types, a.area_type) }}
                </Badge>
                <span
                  v-else
                  class="text-xs text-muted-foreground"
                >—</span>
              </TableCell>
              <TableCell>
                <Badge :variant="a.is_public_submission ? 'secondary' : 'outline'">
                  {{ a.is_public_submission ? 'فرم عمومی' : 'ثبت توسط کارمند' }}
                </Badge>
                <p
                  v-if="!a.is_public_submission && a.created_by_name"
                  class="mt-1 text-xs text-muted-foreground"
                  dir="auto"
                >
                  {{ a.created_by_name }}
                </p>
              </TableCell>
              <TableCell>
                <RequestStatusBadge
                  :status="a.status"
                  :draft="!a.is_finalized"
                  :change-requested="!!a.change_request_note"
                />
                <p
                  v-if="a.review_note && (a.status === 'REJECTED' || a.status === 'SUSPENDED' || a.status === 'NEEDS_EDIT')"
                  class="mt-1 max-w-48 truncate text-xs text-muted-foreground"
                  dir="auto"
                  :title="a.review_note"
                >
                  {{ a.review_note }}
                </p>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    title="مشاهده جزئیات"
                    aria-label="مشاهده جزئیات"
                    @click="openView(a)"
                  >
                    <Icon
                      name="lucide:eye"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="a.my_actions?.can_review && reviewActionsFor(a.status).length"
                    variant="ghost"
                    size="icon"
                    title="بررسی و تغییر وضعیت"
                    aria-label="بررسی و تغییر وضعیت"
                    @click="openReview(a)"
                  >
                    <Icon
                      name="lucide:shield-check"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="a.my_actions?.can_finalize"
                    variant="ghost"
                    size="icon"
                    :title="a.status === 'NEEDS_EDIT' ? 'ثبت مجدد (ارسال برای بررسی)' : 'ثبت نهایی'"
                    :aria-label="a.status === 'NEEDS_EDIT' ? 'ثبت مجدد' : 'ثبت نهایی'"
                    @click="finalizeRow(a)"
                  >
                    <Icon
                      name="lucide:send"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="a.my_actions?.can_request_change"
                    variant="ghost"
                    size="icon"
                    title="درخواست تغییر اطلاعات"
                    aria-label="درخواست تغییر اطلاعات"
                    @click="openChangeRequest(a)"
                  >
                    <Icon
                      name="lucide:file-pen-line"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="a.my_actions?.can_edit"
                    variant="ghost"
                    size="icon"
                    title="ویرایش"
                    aria-label="ویرایش"
                    @click="openEdit(a)"
                  >
                    <Icon
                      name="lucide:pencil"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="store.can(a.applicant_type, 'delete')"
                    variant="ghost"
                    size="icon"
                    class="text-destructive"
                    title="حذف"
                    aria-label="حذف"
                    @click="confirmDelete(a)"
                  >
                    <Icon
                      name="lucide:trash-2"
                      class="size-4"
                    />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div
          v-else
          class="p-8 text-center text-sm text-muted-foreground"
        >
          موردی با این فیلترها پیدا نشد.
        </div>
      </div>

      <NumberedPagination
        :page="store.page"
        :page-size="store.perPage"
        :total="store.total"
        :loading="store.loading"
        @update:page="store.setPage"
      />
    </Card>

    <!-- View details -->
    <Dialog v-model:open="viewOpen">
      <DialogContent class="fixed !inset-0 !left-0 !top-0 !h-dvh !max-h-none !w-screen !max-w-none !translate-x-0 !translate-y-0 flex flex-col gap-0 overflow-hidden !rounded-none border-0 p-0 sm:!max-w-none">
        <DialogHeader class="border-b px-6 py-4 text-right">
          <div class="flex flex-wrap items-center gap-2">
            <DialogTitle
              class="text-lg font-semibold"
              dir="auto"
            >
              {{ viewing?.display_name }}
            </DialogTitle>
            <Badge variant="outline">
              {{ viewing ? TYPE_LABELS[viewing.applicant_type] : '' }}
            </Badge>
            <RequestStatusBadge
              v-if="viewing"
              :status="viewing.status"
              :draft="!viewing.is_finalized"
              :change-requested="!!viewing.change_request_note"
            />
          </div>
          <DialogDescription>
            {{ viewing?.is_public_submission ? 'از طریق فرم عمومی ثبت‌نام ارسال شده است.' : viewing?.created_by_name ? `ثبت‌شده توسط ${viewing.created_by_name}.` : 'مستقیماً توسط کارمند ثبت شده است.' }}
          </DialogDescription>
        </DialogHeader>

        <RequestBanner
          v-if="viewing && !viewLoading"
          class="px-6 pt-4"
          :status="viewing.status"
          :note="viewing.review_note"
          :change-request-note="viewing.change_request_note"
        />
        <DetailNav :watch-key="viewing?.id" />
        <div
          v-if="viewLoading"
          class="p-10 text-center text-sm text-muted-foreground"
        >
          در حال بارگذاری...
        </div>
        <div
          v-else-if="viewing"
          class="detail-body flex-1 overflow-y-auto bg-muted/20 px-6 py-6 text-sm"
        >
          <section
            v-for="sec in viewSections"
            :key="sec.title"
            class="space-y-3"
          >
            <h3 class="font-semibold">
              {{ sec.title }}
            </h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div
                v-for="r in sec.rows"
                :key="r.label"
              >
                <dt class="text-xs text-muted-foreground">
                  {{ r.label }}
                </dt>
                <dd dir="auto">
                  {{ r.value || '—' }}
                </dd>
              </div>
            </dl>
          </section>

          <section
            v-if="viewing.service_area"
            class="space-y-3"
          >
            <h3 class="font-semibold">
              محدوده فعالیت
            </h3>
            <Badge variant="secondary">
              {{ labelOf(catalog?.area_types, viewing.service_area.area_type) }}
            </Badge>
            <ul
              v-if="viewing.service_area.coverage.length"
              class="space-y-1.5"
            >
              <li
                v-for="c in viewing.service_area.coverage"
                :key="c.province"
                dir="auto"
              >
                <span class="font-medium">{{ c.province }}</span>
                <span class="text-muted-foreground"> — {{ c.all_cities ? 'کل استان' : c.cities.join('، ') }}</span>
              </li>
            </ul>
            <dl
              v-if="viewing.service_area.area_type === 'INTERNATIONAL'"
              class="grid gap-x-6 gap-y-3 sm:grid-cols-2"
            >
              <div>
                <dt class="text-xs text-muted-foreground">
                  کشورهای مبدأ
                </dt>
                <dd>{{ countryNames(viewing.service_area.origin_countries) }}</dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  کشورهای مقصد
                </dt>
                <dd>{{ countryNames(viewing.service_area.destination_countries) }}</dd>
              </div>
            </dl>
            <ul
              v-if="viewing.service_area.permits.length"
              class="space-y-2"
            >
              <li
                v-for="p in viewing.service_area.permits"
                :key="p.type"
                class="flex flex-wrap items-center gap-2"
              >
                <span class="font-medium">{{ permitLabel(p.type) }}</span>
                <span
                  v-if="p.number"
                  class="text-xs text-muted-foreground"
                  dir="ltr"
                >{{ p.number }}</span>
                <span
                  v-if="p.expires_at"
                  class="text-xs text-muted-foreground"
                >· انقضا: {{ formatJalali(p.expires_at) }}</span>
                <Badge
                  v-if="p.file"
                  variant="secondary"
                  class="font-normal"
                >
                  <button
                    type="button"
                    class="inline-flex items-center gap-1.5 hover:underline"
                    @click="download(p.file)"
                  >
                    <Icon
                      name="lucide:download"
                      class="size-3.5"
                    />
                    <span dir="ltr">{{ p.file.name }}</span>
                  </button>
                </Badge>
              </li>
            </ul>
          </section>

          <section
            v-if="viewing.review_note"
            class="space-y-1"
          >
            <h3 class="font-semibold">
              یادداشت بررسی
            </h3>
            <p
              class="text-muted-foreground"
              dir="auto"
            >
              {{ viewing.review_note }}
            </p>
          </section>
        </div>

        <DialogFooter class="border-t bg-muted/30 px-6 py-4">
          <Button
            variant="outline"
            @click="viewOpen = false"
          >
            بستن
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_request_change"
            variant="outline"
            class="gap-2"
            @click="openChangeRequest(viewing)"
          >
            <Icon
              name="lucide:file-pen-line"
              class="size-4"
            /> درخواست تغییر اطلاعات
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_finalize"
            variant="outline"
            class="gap-2"
            @click="finalizeRow(viewing)"
          >
            <Icon
              name="lucide:send"
              class="size-4"
            /> {{ viewing.status === 'NEEDS_EDIT' ? 'ثبت مجدد' : 'ثبت نهایی' }}
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_edit"
            class="gap-2"
            @click="editFromView"
          >
            <Icon
              name="lucide:pencil"
              class="size-4"
            /> ویرایش
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Review: approve / reject / send back with a written explanation / reopen / suspend -->
    <RequestReviewDialog
      v-model:open="reviewOpen"
      :title="reviewing?.display_name ?? ''"
      :status="reviewing?.status ?? 'PENDING'"
      :change-request-note="reviewing?.change_request_note"
      allow-suspend
      :saving="reviewSaving"
      @submit="submitReview"
    />

    <!-- The creator of a submitted request asks the manager for a change -->
    <RequestChangeRequestDialog
      v-model:open="changeOpen"
      :title="changing?.display_name ?? ''"
      :saving="changeSaving"
      @submit="submitChangeRequest"
    />

    <!-- Add / edit wizard -->
    <LazyLogisticsFormWizard
      v-if="wizardLoaded"
      v-model:open="formOpen"
      :applicant="editing"
      @saved="onSaved"
    />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { LogisticsApplicant, ReviewAction } from '~/stores/logistics'
import type { FileRef } from '~/utils/supplier-form'
import { formatJalali } from '~/utils/jalali'
import { STATUS_LABELS, TYPE_LABELS, labelOf } from '~/utils/logistics-form'
import type { ApplicantStatus, ApplicantType, AreaType } from '~/utils/logistics-form'
import type { RequestReviewAction } from '~/utils/request-workflow'

definePageMeta({ title: 'بانک اطلاعات لجستیک' })

const notify = useNotify()
const store = useLogisticsStore()
const catalog = computed(() => store.reference)

/* ── live filtering (same behaviour as the suppliers page) ── */
let timer: ReturnType<typeof setTimeout> | undefined
let appliedKey = ''
const filterKey = () => JSON.stringify(store.filters)

function applyNow() {
  clearTimeout(timer)
  appliedKey = filterKey()
  store.applyFilters()
}
function resetAll() {
  clearTimeout(timer)
  store.resetFilters()
  appliedKey = filterKey()
}
watch(() => ({ ...store.filters }) as Record<string, any>, (now, old) => {
  if (JSON.stringify(now) === appliedKey) return
  clearTimeout(timer)
  const onlySearch = now.search !== old.search
    && ['applicant_type', 'status', 'area_type', 'province', 'vehicle_type'].every(k => now[k] === old[k])
  timer = setTimeout(applyNow, onlySearch ? 350 : 0)
}, { deep: true })
onBeforeUnmount(() => clearTimeout(timer))

onMounted(async () => {
  await Promise.all([store.load(), store.loadStats(), store.loadReference().catch(() => null)])
  appliedKey = filterKey()
  await openFromQuery()
})

/* ── a notification points here with ?open=<id>: show that request right away ── */
const route = useRoute()
async function openFromQuery() {
  const raw = Array.isArray(route.query.open) ? route.query.open[0] : route.query.open
  const id = Number(raw)
  if (!raw || !Number.isInteger(id) || id < 1) return
  try {
    await openView(await store.fetchOne(id))
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'این پرونده پیدا نشد یا اجازهٔ دیدن آن را ندارید.'))
  }
  finally {
    await navigateTo({ path: route.path, query: { ...route.query, open: undefined } }, { replace: true })
  }
}
watch(() => route.query.open, (v) => { if (v) openFromQuery() })


/* ── Excel / Word export of the current filters (needs the module's `export` permission) ── */
const exporting = ref<'' | 'xlsx' | 'docx'>('')
async function runExport(format: 'xlsx' | 'docx') {
  exporting.value = format
  try {
    await store.exportFile(format)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'دریافت خروجی انجام نشد.'))
  }
  finally {
    exporting.value = ''
  }
}
const pageCount = computed(() => Math.max(1, Math.ceil(store.total / store.perPage)))

/* ── tabs: only the applicant types this user may read ── */
const TAB_LABELS: Record<ApplicantType, string> = { COMPANY: 'شرکت‌های حمل‌ونقل', DRIVER: 'رانندگان' }
const typeTabs = computed(() => {
  const tabs: { value: ApplicantType | '', label: string }[] = store.types.map(t => ({ value: t, label: TAB_LABELS[t] }))
  return store.types.length > 1 ? [{ value: '' as const, label: 'همه' }, ...tabs] : tabs
})
function setTypeFilter(v: ApplicantType | '') {
  store.filters.applicant_type = v
  // filters that only exist for one type must not linger on the other
  store.filters.province = ''
  store.filters.vehicle_type = ''
}
// A user who may only read one type is pinned to it.
watch(() => store.types, (t) => {
  if (t.length === 1 && store.filters.applicant_type !== t[0]) setTypeFilter(t[0]!)
}, { immediate: true })

const statusModel = computed({
  get: () => store.filters.status || 'all',
  set: (v: string) => { store.filters.status = v === 'all' ? '' : v as ApplicantStatus },
})
const areaModel = computed({
  get: () => store.filters.area_type || 'all',
  set: (v: string) => { store.filters.area_type = v === 'all' ? '' : v as AreaType },
})
const provinceModel = computed({
  get: () => store.filters.province || 'all',
  set: (v: string) => { store.filters.province = v === 'all' ? '' : v },
})
const vehicleModel = computed({
  get: () => store.filters.vehicle_type || 'all',
  set: (v: string) => { store.filters.vehicle_type = v === 'all' ? '' : v },
})

/* ── stat cards (server totals when available) ── */
const summary = computed(() => {
  const s = store.stats
  const sum = (t: ApplicantType) => Object.values(s?.by_type_status?.[t] ?? {}).reduce((a, b) => a + b, 0)
  return {
    total: s?.total ?? store.total,
    company: sum('COMPANY'),
    driver: sum('DRIVER'),
    pending: (s?.by_type_status?.COMPANY?.PENDING ?? 0) + (s?.by_type_status?.DRIVER?.PENDING ?? 0),
  }
})

const fmtTons = (n: number) => n.toLocaleString('fa-IR', { maximumFractionDigits: 2 })

async function download(f: FileRef) {
  try {
    await store.downloadFile(f)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'بارگیری فایل انجام نشد.')
  }
}

/* ── view ── */
const viewOpen = ref(false)
const viewLoading = ref(false)
const viewing = ref<LogisticsApplicant | null>(null)

async function loadDetail(a: LogisticsApplicant) {
  try {
    return await store.fetchOne(a.id)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'بارگذاری جزئیات انجام نشد.')
    return null
  }
}
async function openView(a: LogisticsApplicant) {
  viewing.value = a
  viewOpen.value = true
  viewLoading.value = true
  const detail = await loadDetail(a)
  viewLoading.value = false
  if (detail) viewing.value = detail
  else viewOpen.value = false
}

const countryNames = (codes: string[]) => codes.map(c => labelOf(catalog.value?.countries, c)).join('، ') || '—'
const permitLabel = (code: string) => catalog.value?.permit_types.find(p => p.code === code)?.label ?? code

type Row = { label: string, value: string | null | undefined }
const viewSections = computed<{ title: string, rows: Row[] }[]>(() => {
  const a = viewing.value
  if (!a) return []
  const cat = catalog.value
  if (a.applicant_type === 'COMPANY') {
    const c = a.company_info ?? {}
    const r = a.representative ?? {}
    return [
      {
        title: 'اطلاعات شرکت',
        rows: [
          { label: 'نوع شخصیت', value: c.entity_type === 'LEGAL' ? 'حقوقی' : 'حقیقی' },
          ...(c.entity_type === 'LEGAL'
            ? [{ label: 'نام شرکت', value: c.company_name }, { label: 'شناسه ملی', value: c.national_id }]
            : [{ label: 'نام', value: c.first_name }, { label: 'نام خانوادگی', value: c.last_name }]),
          { label: 'استان', value: c.province },
          { label: 'شهر', value: c.city },
          { label: 'نشانی دفتر', value: c.office_address },
        ],
      },
      {
        title: 'نماینده و اطلاعات تماس',
        rows: [
          { label: 'نام و نام خانوادگی', value: `${r.first_name ?? ''} ${r.last_name ?? ''}`.trim() },
          { label: 'سمت', value: r.position === 'OTHER' ? r.position_other : labelOf(cat?.representative_positions, r.position) },
          { label: 'موبایل', value: r.mobile },
          { label: 'تلفن ثابت', value: r.landline },
        ],
      },
    ]
  }
  const i = a.identity ?? {}
  const c = a.contact ?? {}
  const v = a.vehicle ?? {}
  return [
    {
      title: 'اطلاعات هویتی و تماس',
      rows: [
        { label: 'نام', value: i.first_name },
        { label: 'نام خانوادگی', value: i.last_name },
        { label: 'کد ملی', value: i.national_code },
        { label: 'موبایل', value: c.mobile },
        { label: 'تلفن جایگزین', value: c.alt_phone },
      ],
    },
    {
      title: 'وسیله نقلیه و بارگیر',
      rows: [
        { label: 'نوع خودرو', value: v.vehicle_type === 'OTHER' ? v.vehicle_type_other : labelOf(cat?.vehicle_types, v.vehicle_type) },
        { label: 'نوع بارگیر', value: v.body_type === 'OTHER' ? v.body_type_other : labelOf(cat?.body_types, v.body_type) },
        { label: 'ظرفیت حمل', value: v.capacity_tons != null ? `${fmtTons(v.capacity_tons)} تن` : '' },
        {
          label: 'کالاهای قابل حمل',
          value: [
            ...(v.cargo_types ?? []).filter((x: string) => x !== 'OTHER').map((x: string) => labelOf(cat?.cargo_types, x)),
            ...((v.cargo_types ?? []).includes('OTHER') ? [v.cargo_type_other] : []),
          ].join('، '),
        },
      ],
    },
  ]
})

/* ── add / edit ── */
const formOpen = ref(false)
// the big wizard is downloaded only when it is first opened (keeps the list page fast to load)
const wizardLoaded = ref(false)
watch(formOpen, (v) => { if (v) wizardLoaded.value = true })
const editing = ref<LogisticsApplicant | null>(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
async function openEdit(a: LogisticsApplicant) {
  const detail = await loadDetail(a) // the list rows carry no section data
  if (!detail) return
  editing.value = detail
  formOpen.value = true
}
function editFromView() {
  if (!viewing.value) return
  viewOpen.value = false
  openEdit(viewing.value)
}
async function onSaved() {
  await Promise.all([store.load(), store.loadStats()])
}

/* ── review (managers) ── */
const reviewActionsFor = (status: ApplicantStatus) => requestReviewActionsFor(status, { allowSuspend: true })

const reviewOpen = ref(false)
const reviewing = ref<LogisticsApplicant | null>(null)
const reviewSaving = ref(false)

function openReview(a: LogisticsApplicant) {
  reviewing.value = a
  reviewOpen.value = true
}
async function submitReview(action: RequestReviewAction, note: string) {
  if (!reviewing.value) return
  reviewSaving.value = true
  try {
    await store.review(reviewing.value.id, action as ReviewAction, note)
    notify.success(`«${reviewing.value.display_name}»: وضعیت به‌روزرسانی شد.`)
    reviewOpen.value = false
    if (viewing.value?.id === reviewing.value.id) viewing.value = await store.fetchOne(reviewing.value.id)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ثبت تصمیم انجام نشد.'))
  }
  finally {
    reviewSaving.value = false
  }
}

/* ── ثبت نهایی / ثبت مجدد, and "request a change" (the creator) ── */
async function finalizeRow(a: LogisticsApplicant) {
  try {
    const resubmit = a.status === 'NEEDS_EDIT'
    await store.finalize(a.id)
    notify.success(resubmit ? 'درخواست دوباره برای بررسی ثبت شد.' : 'درخواست ثبت نهایی شد و در صف بررسی قرار گرفت.')
    if (viewing.value?.id === a.id) viewing.value = await store.fetchOne(a.id)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ثبت نهایی انجام نشد.'))
  }
}
const changeOpen = ref(false)
const changing = ref<LogisticsApplicant | null>(null)
const changeSaving = ref(false)
function openChangeRequest(a: LogisticsApplicant) {
  changing.value = a
  changeOpen.value = true
}
async function submitChangeRequest(reason: string) {
  if (!changing.value) return
  changeSaving.value = true
  try {
    await store.requestChange(changing.value.id, reason)
    notify.success('درخواست تغییر برای مدیر ارسال شد.')
    changeOpen.value = false
    if (viewing.value?.id === changing.value.id) viewing.value = await store.fetchOne(changing.value.id)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ارسال درخواست انجام نشد.'))
  }
  finally {
    changeSaving.value = false
  }
}

/* ── delete ── */
async function confirmDelete(a: LogisticsApplicant) {
  if (!window.confirm(`«${a.display_name}» حذف شود؟ این کار از اینجا قابل بازگشت نیست.`)) return
  try {
    await store.removeApplicant(a.id)
    notify.success(`${a.display_name} حذف شد.`)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'حذف انجام نشد.')
  }
}
</script>
