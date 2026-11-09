<!-- pages/crm/customers/index.vue  (route: /crm/customers) -->
<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      section="مدیریت فروش و مشتریان"
      title="مشتریان"
      description="پرونده‌ی مشتریان را بررسی کنید، وضعیت تجاری را پیگیری کنید یا مشتری جدیدی اضافه کنید."
      :action-label="store.canCreate ? 'افزودن مشتری' : undefined"
      @action="openCreate"
    />

    <div class="grid gap-4 sm:grid-cols-4">
      <AccessStat label="تعداد کل مشتریان" :value="store.stats?.total ?? store.total" icon="lucide:users" />
      <AccessStat label="پیگیری سررسیدشده" :value="store.stats?.follow_up_due ?? 0" icon="lucide:alarm-clock" />
      <AccessStat label="جذب‌شده و فعال" :value="acquiredCount" icon="lucide:badge-check" />
      <AccessStat label="از دست رفته" :value="store.stats?.by_commercial_status?.INACTIVE_LOST ?? 0" icon="lucide:ban" />
    </div>

    <Card class="overflow-hidden py-0 shadow-none">
      <div class="flex min-w-0 flex-col gap-3 border-b p-4">
        <div class="grid w-full min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div class="relative w-full min-w-0">
            <Icon name="lucide:search" class="absolute right-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              v-model="store.filters.search"
              dir="rtl"
              placeholder="جستجوی مشتری، محصول، شناسه یا شماره..."
              class="w-full min-w-0 pr-9 text-right"
              @keyup.enter="applyNow"
            />
          </div>

          <Select v-model="categoryModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="صنعت فعالیت" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه صنعت‌ها</SelectItem>
              <SelectItem v-for="c in store.categories" :key="c" :value="c">{{ c }}</SelectItem>
            </SelectContent>
          </Select>

          <Select v-if="subcategoryOptions.length" v-model="subcategoryModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="صنعت فرعی" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه صنعت‌های فرعی</SelectItem>
              <SelectItem v-for="c in subcategoryOptions" :key="c.id" :value="String(c.id)">{{ c.label }}</SelectItem>
            </SelectContent>
          </Select>

          <Select v-model="statusModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="وضعیت تجاری" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه وضعیت‌ها</SelectItem>
              <SelectItem v-for="o in commercialOptions" :key="o.value" :value="o.value">
                {{ o.label }}<template v-if="store.stats"> ({{ store.stats.by_commercial_status[o.value] ?? 0 }})</template>
              </SelectItem>
            </SelectContent>
          </Select>

          <Select v-model="provinceModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="استان" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه استان‌ها</SelectItem>
              <SelectItem v-for="l in store.locations" :key="l.province" :value="l.province">
                {{ l.province }} ({{ l.count }})
              </SelectItem>
            </SelectContent>
          </Select>

          <Select v-if="cityOptions.length" v-model="cityModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="شهر" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه شهرها</SelectItem>
              <SelectItem v-for="c in cityOptions" :key="c.city" :value="c.city">{{ c.city }} ({{ c.count }})</SelectItem>
            </SelectContent>
          </Select>

          <Select v-model="activityModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="نوع فعالیت" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه نوع‌های فعالیت</SelectItem>
              <SelectItem v-for="o in activityOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
            </SelectContent>
          </Select>

          <Select v-model="creditRatingModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="وضعیت اعتباری" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه وضعیت‌های اعتباری</SelectItem>
              <SelectItem v-for="o in creditRatingOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
            </SelectContent>
          </Select>

          <Select v-model="assigneeModel">
            <SelectTrigger class="w-full"><SelectValue placeholder="مسئول پیگیری" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه مسئول‌ها</SelectItem>
              <SelectItem value="none">بدون مسئول</SelectItem>
              <SelectItem v-for="u in store.assignees" :key="u.id" :value="String(u.id)">{{ u.full_name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="flex flex-wrap items-center justify-start gap-2">
          <Button
            :variant="store.filters.follow_up_due ? 'default' : 'outline'"
            class="gap-2"
            :aria-pressed="store.filters.follow_up_due"
            @click="store.filters.follow_up_due = !store.filters.follow_up_due"
          >
            <Icon name="lucide:alarm-clock" class="size-4" /> پیگیری سررسیدشده
          </Button>
          <Button variant="ghost" @click="resetAll">بازنشانی</Button>
          <Button v-if="store.canUpdate" variant="outline" class="gap-2" @click="categoriesOpen = true">
            <Icon name="lucide:tags" class="size-4" /> صنعت‌ها
          </Button>
          <Button v-if="store.canUpdate" variant="outline" class="gap-2" @click="optionsOpen = true">
            <Icon name="lucide:package" class="size-4" /> محصول و گرید
          </Button>
          <span v-if="store.loading && store.customers.length" class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Icon name="lucide:loader-circle" class="size-3.5 animate-spin" /> در حال جستجو...
          </span>
        </div>
      </div>

      <div class="overflow-x-auto">
        <div v-if="store.loading && !store.customers.length" class="p-8 text-center text-sm text-muted-foreground">
          در حال بارگذاری مشتریان...
        </div>
        <div v-else-if="store.loadError" class="p-8 text-center text-sm text-destructive">
          {{ store.loadError }}
        </div>
        <Table v-else-if="store.customers.length">
          <TableHeader>
            <TableRow>
              <TableHead>مشتری</TableHead>
              <TableHead>
                <button
                  type="button"
                  class="inline-flex items-center gap-1"
                  title="مرتب‌سازی بر اساس صنعت"
                  aria-label="مرتب‌سازی بر اساس صنعت"
                  @click="toggleIndustrySort"
                >
                  صنعت
                  <Icon
                    :name="industrySort === 'asc' ? 'lucide:arrow-up' : industrySort === 'desc' ? 'lucide:arrow-down' : 'lucide:arrow-up-down'"
                    class="size-3.5"
                    :class="industrySort === 'none' ? 'text-muted-foreground' : 'text-primary'"
                  />
                </button>
              </TableHead>
              <TableHead>موقعیت</TableHead>
              <TableHead>راه ارتباطی</TableHead>
              <TableHead>وضعیت تجاری</TableHead>
              <TableHead>مسئول پیگیری</TableHead>
              <TableHead>پیگیری بعدی</TableHead>
              <TableHead class="text-right">عملیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="c in store.customers"
              :key="c.id"
              class="border-b border-slate-300/70 transition-colors odd:bg-white even:bg-slate-100 hover:bg-amber-100/70 dark:border-zinc-700 dark:odd:bg-zinc-900 dark:even:bg-zinc-800 dark:hover:bg-amber-300/15"
            >
              <TableCell>
                <template v-if="c.customer_type !== 'LEGAL' && c.brand_name">
                  <p class="font-semibold" dir="auto">{{ c.brand_name }}</p>
                  <p class="text-sm text-muted-foreground" dir="auto">{{ c.display_name }}</p>
                </template>
                <template v-else>
                  <p class="font-medium" dir="auto">{{ c.display_name }}</p>
                  <p v-if="c.brand_name" class="text-xs text-muted-foreground" dir="auto">{{ c.brand_name }}</p>
                </template>
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-xs text-muted-foreground">{{ c.customer_type === 'LEGAL' ? 'شخص حقوقی' : 'شخص حقیقی' }}</span>
                  <Badge v-if="!c.is_finalized" variant="outline" class="h-5 px-1.5 text-[10px] font-normal">پیش‌نویس</Badge>
                  <Badge v-if="c.operational_status === 'INACTIVE'" variant="secondary" class="h-5 px-1.5 text-[10px] font-normal">غیرفعال</Badge>
                </div>
                <!-- Products that match the search text -->
                <div v-if="matchedProducts(c).length" class="mt-1 flex flex-wrap gap-1">
                  <Badge v-for="(p, i) in matchedProducts(c)" :key="i" variant="secondary" class="gap-1 font-normal" dir="auto">
                    <Icon name="lucide:package" class="size-3" /> {{ p }}
                  </Badge>
                </div>
              </TableCell>
              <TableCell>
                <!-- a customer can work in several industries -->
                <div v-if="industriesOf(c).length" class="space-y-1.5">
                  <div v-for="(ind, i) in industriesOf(c)" :key="i">
                    <Badge variant="outline" dir="auto">{{ ind.category }}</Badge>
                    <p v-if="ind.subcategory" class="mt-0.5 text-xs text-muted-foreground" dir="auto">{{ ind.subcategory }}</p>
                  </div>
                </div>
                <span v-else class="text-xs text-muted-foreground">—</span>
              </TableCell>
              <TableCell class="text-sm" dir="auto">
                {{ [c.factory_province, c.factory_city].filter(Boolean).join('، ') || '—' }}
              </TableCell>
              <TableCell class="text-sm">
                <template v-if="c.contacts?.length">
                  <p dir="auto">
                    {{ contactName(c.contacts[0]) }}
                    <span class="text-xs text-muted-foreground">· {{ c.contacts[0].position }}</span>
                  </p>
                  <p v-if="primaryNumber(c.contacts[0])" class="text-xs text-muted-foreground" dir="ltr">
                    {{ primaryNumber(c.contacts[0]) }}
                  </p>
                  <p v-if="c.contacts.length > 1" class="text-xs text-muted-foreground">و {{ c.contacts.length - 1 }} نفر دیگر</p>
                </template>
                <span v-else class="text-xs text-muted-foreground">—</span>
              </TableCell>
              <TableCell>
                <Select
                  :model-value="c.commercial_status"
                  :disabled="!store.canUpdate"
                  @update:model-value="v => setStatus(c, v as CommercialStatus)"
                >
                  <SelectTrigger class="h-8 w-52"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="o in commercialOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell class="text-sm" dir="auto">
                {{ c.assigned_to_name || '—' }}
              </TableCell>
              <TableCell class="text-sm">
                <span
                  v-if="c.next_follow_up_date"
                  :class="isOverdue(c) ? 'font-medium text-destructive' : ''"
                  dir="ltr"
                >{{ formatJalali(c.next_follow_up_date) }}</span>
                <span v-else class="text-xs text-muted-foreground">—</span>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button variant="ghost" size="icon" title="مشاهده جزئیات" aria-label="مشاهده جزئیات" @click="openView(c)">
                    <Icon name="lucide:eye" class="size-4" />
                  </Button>
                  <Button
                    v-if="crmAccess.canReadSales.value"
                    variant="ghost"
                    size="icon"
                    title="فروش‌های این مشتری"
                    aria-label="فروش‌های این مشتری"
                    @click="navigateTo({ path: '/crm/sales', query: { customer_id: c.id } })"
                  >
                    <Icon name="lucide:shopping-cart" class="size-4" />
                  </Button>
                  <Button v-if="store.canUpdate" variant="ghost" size="icon" title="ویرایش" aria-label="ویرایش" @click="openEdit(c)">
                    <Icon name="lucide:pencil" class="size-4" />
                  </Button>
                  <Button
                    v-if="store.canDelete"
                    variant="ghost"
                    size="icon"
                    class="text-destructive"
                    title="حذف"
                    aria-label="حذف"
                    @click="confirmDelete(c)"
                  >
                    <Icon name="lucide:trash-2" class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div v-else class="p-8 text-center text-sm text-muted-foreground">
          مشتری‌ای با این فیلترها پیدا نشد.
        </div>
      </div>

      <div
        v-if="store.total > store.perPage"
        class="flex items-center justify-between border-t p-4 text-sm text-muted-foreground"
      >
        <span>صفحه {{ store.page }} از {{ pageCount }} &middot; مجموع {{ store.total }} مورد</span>
        <div class="flex gap-2">
          <Button variant="outline" size="sm" :disabled="store.page <= 1 || store.loading" @click="store.setPage(store.page - 1)">
            قبلی
          </Button>
          <Button variant="outline" size="sm" :disabled="store.page >= pageCount || store.loading" @click="store.setPage(store.page + 1)">
            بعدی
          </Button>
        </div>
      </div>
    </Card>

    <!-- View details -->
    <Dialog v-model:open="viewOpen">
      <DialogContent class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
        <DialogHeader class="border-b px-6 py-4 text-right">
          <div class="flex flex-wrap items-center gap-2">
            <DialogTitle class="text-lg font-semibold" dir="auto">{{ viewing?.display_name }}</DialogTitle>
            <Badge variant="outline">{{ viewing?.customer_type === 'LEGAL' ? 'شخص حقوقی' : 'شخص حقیقی' }}</Badge>
            <Badge v-if="viewing" :variant="commercialBadgeVariant(viewing.commercial_status)">
              {{ statusLabel(viewing.commercial_status) }}
            </Badge>
            <Badge v-if="viewing?.operational_status === 'INACTIVE'" variant="secondary">غیرفعال</Badge>
            <Badge v-if="viewing" :variant="viewing.is_finalized ? 'default' : 'outline'">
              {{ viewing.is_finalized ? 'نهایی‌شده' : 'پیش‌نویس' }}
            </Badge>
          </div>
          <DialogDescription>
            {{ viewing?.created_by_name ? `تکمیل‌شده توسط ${viewing.created_by_name}` : 'پرونده‌ی مشتری' }}
            <template v-if="viewing?.registration_date"> · تاریخ ثبت: {{ formatJalali(viewing.registration_date) }}</template>
          </DialogDescription>
        </DialogHeader>

        <div v-if="viewing" class="flex-1 space-y-7 overflow-y-auto px-6 py-6 text-sm">
          <section class="space-y-3">
            <h3 class="font-semibold">اطلاعات پایه</h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div v-for="r in identityRows" :key="r.label">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto">{{ r.value || '—' }}</dd>
              </div>
            </dl>

            <div v-if="viewing.contacts?.length" class="space-y-3 pt-1">
              <p class="text-xs font-semibold text-muted-foreground">افراد تماس ({{ viewing.contacts.length }})</p>
              <div v-for="(p, i) in viewing.contacts" :key="i" class="rounded-xl border p-4">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <p class="font-medium" dir="auto">{{ contactName(p) }}</p>
                  <Badge variant="secondary" class="font-normal">{{ p.position }}</Badge>
                </div>
                <dl class="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-4">
                  <div><dt class="text-xs text-muted-foreground">ایمیل</dt><dd dir="ltr" class="text-left">{{ p.email || '—' }}</dd></div>
                  <div><dt class="text-xs text-muted-foreground">موبایل</dt><dd dir="ltr" class="text-left">{{ p.mobile || '—' }}</dd></div>
                  <div><dt class="text-xs text-muted-foreground">تلفن ثابت</dt><dd dir="ltr" class="text-left">{{ p.landline || '—' }}</dd></div>
                  <div v-if="p.birth_date"><dt class="text-xs text-muted-foreground">تاریخ تولد</dt><dd dir="ltr" class="text-left">{{ formatJalali(p.birth_date) }}</dd></div>
                </dl>
              </div>
            </div>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">نوع و مشخصات فعالیت</h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div v-for="r in activityRows" :key="r.label" :class="r.wide ? 'sm:col-span-2' : ''">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto">{{ r.value || '—' }}</dd>
              </div>
              <div class="sm:col-span-2">
                <dt class="mb-1 text-xs text-muted-foreground">نوع فعالیت</dt>
                <dd class="flex flex-wrap gap-1.5">
                  <Badge v-for="a in viewing.activity_types" :key="a" variant="secondary" class="font-normal">{{ activityLabel(a) }}</Badge>
                  <span v-if="!viewing.activity_types.length">—</span>
                </dd>
              </div>
            </dl>
            <div v-if="viewing.produced_products.length" class="space-y-2 pt-1">
              <p class="text-xs font-semibold text-muted-foreground">محصولات تولیدی ({{ viewing.produced_products.length }})</p>
              <ul class="grid gap-2 sm:grid-cols-2">
                <li v-for="(p, i) in viewing.produced_products" :key="i" class="flex items-center justify-between gap-2 rounded-lg border px-3 py-2">
                  <span class="font-medium" dir="auto">{{ p.name }}</span>
                  <span class="text-xs text-muted-foreground" dir="auto">{{ producedText(p) }}</span>
                </li>
              </ul>
            </div>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">
              محصولات مصرفی
              <span class="font-normal text-muted-foreground">({{ viewing.consumed_products.length }})</span>
            </h3>
            <div v-for="(p, i) in viewing.consumed_products" :key="i" class="rounded-xl border p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-medium" dir="auto">{{ p.name }}</p>
                <Badge v-if="p.grade_specs" variant="outline" class="font-normal" dir="auto">{{ p.grade_specs }}</Badge>
              </div>
              <dl class="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                <div><dt class="text-xs text-muted-foreground">مصرف ماهانه</dt><dd dir="auto">{{ fmtNum(p.monthly_consumption) }} {{ unitLabel(p.unit) }}</dd></div>
                <div><dt class="text-xs text-muted-foreground">مصرف سالانه</dt><dd dir="auto">{{ fmtNum(p.annual_consumption) }} {{ unitLabel(p.unit) }}</dd></div>
              </dl>
            </div>
            <div v-if="viewing.current_suppliers.length" class="space-y-2 pt-1">
              <p class="text-xs font-semibold text-muted-foreground">تأمین‌کنندگان فعلی</p>
              <ul class="space-y-2">
                <li v-for="(s, i) in viewing.current_suppliers" :key="i" class="rounded-lg border px-3 py-2">
                  <p class="font-medium" dir="auto">{{ s.name }}</p>
                  <div v-if="s.grades?.length" class="mt-1.5 flex flex-wrap gap-1.5">
                    <Badge v-for="(g, j) in s.grades" :key="j" variant="secondary" class="font-normal" dir="auto">
                      {{ g.grade ? `${g.product} — ${g.grade}` : g.product }}
                    </Badge>
                  </div>
                </li>
              </ul>
            </div>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">وضعیت و همکاری</h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div v-for="r in statusRows" :key="r.label">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto">{{ r.value || '—' }}</dd>
              </div>
            </dl>
            <div v-if="viewing.contact_log.length" class="space-y-2 pt-1">
              <p class="text-xs font-semibold text-muted-foreground">تماس‌ها ({{ viewing.contact_log.length }})</p>
              <ul class="space-y-1.5">
                <li v-for="(l, i) in viewing.contact_log" :key="i" class="flex items-baseline gap-3 rounded-lg border px-3 py-2">
                  <span class="shrink-0 text-xs text-muted-foreground" dir="ltr">{{ formatJalali(l.date) }}</span>
                  <span dir="auto">{{ l.note || '—' }}</span>
                </li>
              </ul>
            </div>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">اطلاعات خرید و شرایط تجاری</h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div v-for="r in termsRows" :key="r.label" :class="r.wide ? 'sm:col-span-2' : ''">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto">{{ r.value || '—' }}</dd>
              </div>
            </dl>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">پیگیری</h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div v-for="r in followRows" :key="r.label" :class="r.wide ? 'sm:col-span-2' : ''">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto" class="whitespace-pre-line">{{ r.value || '—' }}</dd>
              </div>
            </dl>
          </section>
        </div>

        <DialogFooter class="border-t bg-muted/30 px-6 py-4">
          <Button variant="outline" @click="viewOpen = false">بستن</Button>
          <Button v-if="store.canUpdate && viewing && !viewing.is_finalized" variant="outline" class="gap-2" @click="finalizeViewing">
            <Icon name="lucide:badge-check" class="size-4" /> ثبت نهایی
          </Button>
          <Button v-if="store.canUpdate && viewing" class="gap-2" @click="editFromView">
            <Icon name="lucide:pencil" class="size-4" /> ویرایش
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Add / edit wizard -->
    <CustomerFormWizard
      v-model:open="formOpen"
      :customer="editing"
      @saved="onSaved"
      @manage-categories="categoriesOpen = true"
    />

    <!-- Industry management -->
    <CustomerCategoriesDialog v-model:open="categoriesOpen" @changed="store.loadStats()" />
    <CustomerOptionsDialog v-model:open="optionsOpen" @changed="store.load()" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError } from '~/services/backendApi'
import type { CommercialStatus, CreditRating, Customer, CustomerContact, Industry, ProducedProduct } from '~/stores/customer'
import {
  ACTIVITY_LABELS, COMMERCIAL_STATUS_LABELS, CREDIT_RATING_LABELS, OPERATIONAL_LABELS, PAYMENT_LABELS, UNIT_LABELS,
  PURCHASE_LABELS, SOURCE_LABELS, commercialBadgeVariant,
} from '~/utils/customer-form'
import { formatJalali, todayIso } from '~/utils/jalali'

definePageMeta({ title: 'مشتریان' })
const crmAccess = useCrmAccess()

const store = useCustomerStore()

/* ── option lists (API labels first, built-in labels as a fallback) ── */
const toOptions = (labels: Record<string, string>) => Object.entries(labels).map(([value, label]) => ({ value, label }))
const commercialOptions = computed(() => store.options?.commercial_statuses ?? toOptions(COMMERCIAL_STATUS_LABELS))
const activityOptions = computed(() => store.options?.activity_types ?? toOptions(ACTIVITY_LABELS))
const creditRatingOptions = computed(() => store.options?.credit_ratings ?? toOptions(CREDIT_RATING_LABELS))
const statusLabel = (v: string) => commercialOptions.value.find(o => o.value === v)?.label ?? v
const activityLabel = (v: string) => activityOptions.value.find(o => o.value === v)?.label ?? v
const sourceLabel = (v: string) => store.options?.acquaintance_sources.find(o => o.value === v)?.label ?? SOURCE_LABELS[v as keyof typeof SOURCE_LABELS] ?? v
const ratingLabel = (v: string) => creditRatingOptions.value.find(o => o.value === v)?.label ?? v

const acquiredCount = computed(() => {
  const s = store.stats?.by_commercial_status
  return s ? (s.ACQUIRED ?? 0) + (s.REPEAT_ACTIVE ?? 0) : 0
})

/* ── live filtering ──
 * Typing in the search box filters after a short pause; every other filter applies
 * immediately. `appliedKey` remembers what the list already reflects so the Enter
 * key / reset button don't trigger a second identical request. */
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
watch(() => ({ ...store.filters }) as Record<string, unknown>, (now, old) => {
  if (JSON.stringify(now) === appliedKey) return
  clearTimeout(timer)
  const onlySearch = now.search !== old.search
    && Object.keys(now).every(k => k === 'search' || now[k] === old[k])
  timer = setTimeout(applyNow, onlySearch ? 350 : 0)
}, { deep: true })
onBeforeUnmount(() => clearTimeout(timer))

async function reloadReferenceData() {
  await Promise.all([store.loadStats(), store.loadLocations(), store.loadCategories(), store.loadCategoryItems()])
}
onMounted(async () => {
  await Promise.all([
    store.load(), store.loadOptions(), store.loadAssignees(), reloadReferenceData(),
  ])
  appliedKey = filterKey()
})

const pageCount = computed(() => Math.max(1, Math.ceil(store.total / store.perPage)))

/* ── filter models ── */
const categoryModel = computed({
  get: () => store.filters.category || 'all',
  set: (v: string) => {
    store.filters.category = v === 'all' ? '' : v
    store.filters.subcategory = '' // the old sub-category belonged to the previous industry
  },
})
// With a main industry chosen: its sub-industries. With none: all of them as "main / sub";
// picking one also sets the main industry (names can repeat across parents).
// A customer with several industries matches a filter through ANY of them.
const subcategoryOptions = computed(() => {
  const roots = store.categoryItems.filter(c => !c.parent_id)
  const nameOf = new Map(roots.map(r => [r.id, r.name]))
  const chosen = store.filters.category
  return store.categoryItems
    .filter(c => c.parent_id && (!chosen || nameOf.get(c.parent_id) === chosen))
    .map(c => ({ id: c.id, name: c.name, parent: nameOf.get(c.parent_id!) ?? '', label: chosen ? c.name : `${nameOf.get(c.parent_id!)} / ${c.name}` }))
})
const subcategoryModel = computed({
  get: () => {
    const sub = store.filters.subcategory
    if (!sub) return 'all'
    const hit = subcategoryOptions.value.find(o => o.name === sub && (!store.filters.category || o.parent === store.filters.category))
    return hit ? String(hit.id) : 'all'
  },
  set: (v: string) => {
    if (v === 'all') { store.filters.subcategory = ''; return }
    const hit = subcategoryOptions.value.find(o => String(o.id) === v)
    if (!hit) return
    store.filters.category = hit.parent
    store.filters.subcategory = hit.name
  },
})
const statusModel = computed({
  get: () => store.filters.commercial_status || 'all',
  set: (v: string) => { store.filters.commercial_status = v === 'all' ? '' : v as CommercialStatus },
})
const provinceModel = computed({
  get: () => store.filters.province || 'all',
  set: (v: string) => {
    store.filters.province = v === 'all' ? '' : v
    store.filters.city = '' // the old city belonged to the previous province
  },
})
const cityOptions = computed(() => store.locations.find(l => l.province === store.filters.province)?.cities ?? [])
const cityModel = computed({
  get: () => store.filters.city || 'all',
  set: (v: string) => { store.filters.city = v === 'all' ? '' : v },
})
const activityModel = computed({
  get: () => store.filters.activity_type || 'all',
  set: (v: string) => { store.filters.activity_type = v === 'all' ? '' : v as typeof store.filters.activity_type },
})
const creditRatingModel = computed({
  get: () => store.filters.credit_rating || 'all',
  set: (v: string) => { store.filters.credit_rating = v === 'all' ? '' : v as CreditRating },
})
const assigneeModel = computed({
  get: () => store.filters.assigned_to || 'all',
  set: (v: string) => { store.filters.assigned_to = v === 'all' ? '' : v },
})

// Column-header sort by industry: none -> A-Z -> Z-A -> none (the first industry of each customer).
const industrySort = computed(() =>
  store.filters.sort === 'category' ? 'asc' : store.filters.sort === '-category' ? 'desc' : 'none')
function toggleIndustrySort() {
  store.filters.sort = store.filters.sort === 'category' ? '-category'
    : store.filters.sort === '-category' ? '-created_at' : 'category'
}

// Products (produced or consumed) whose name contains the search text, shown under the customer's name.
function matchedProducts(c: Customer): string[] {
  const t = store.filters.search.trim().toLowerCase()
  if (!t) return []
  const names = [...(c.produced_products ?? []), ...(c.consumed_products ?? [])].map(p => p.name)
  return [...new Set(names.filter(n => n?.toLowerCase().includes(t)))].slice(0, 3)
}

const isOverdue = (c: Customer) =>
  !!c.next_follow_up_date && c.next_follow_up_date <= todayIso()
  && c.commercial_status !== 'INACTIVE_LOST' && c.operational_status === 'ACTIVE'

async function setStatus(c: Customer, status: CommercialStatus) {
  try {
    await store.setCommercialStatus(c.id, status)
    notify.success(`${c.display_name}: وضعیت به «${statusLabel(status)}» تغییر کرد.`)
    store.loadStats()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'به‌روزرسانی وضعیت انجام نشد.')
  }
}

/* ── industries (one or more per customer) ── */
function industriesOf(c: Customer): Industry[] {
  if (c.industries?.length) return c.industries
  // `category` / `subcategory` mirror the first industry (older records)
  const legacy = c as Customer & { category?: string | null, subcategory?: string | null }
  return legacy.category ? [{ category: legacy.category, subcategory: legacy.subcategory ?? null }] : []
}
const industryText = (i: Industry) => [i.category, i.subcategory].filter(Boolean).join(' / ')

/* ── contact persons ── */
const contactName = (c: Pick<CustomerContact, 'first_name' | 'last_name'>) => `${c.first_name} ${c.last_name}`.trim()
const primaryNumber = (c: CustomerContact) => c.mobile || c.landline || ''

/* ── view ── */
const fmtNum = (n: number | null | undefined) => (n === null || n === undefined ? '' : new Intl.NumberFormat('fa-IR').format(n))
const viewOpen = ref(false)
const viewing = ref<Customer | null>(null)
function openView(c: Customer) {
  viewing.value = c
  viewOpen.value = true
}
const unitLabel = (u?: string | null) => UNIT_LABELS[u === 'KG' ? 'KG' : 'TON']
function producedText(p: ProducedProduct) {
  if (p.amount === null || p.amount === undefined) return '—'
  return `${fmtNum(p.amount)} ${unitLabel(p.unit)} در سال`
}
type Row = { label: string, value: string | null | undefined, wide?: boolean }
const identityRows = computed<Row[]>(() => {
  const c = viewing.value
  if (!c) return []
  const own: Row[] = c.customer_type === 'LEGAL'
    ? [
        { label: 'نام شرکت', value: c.company_name },
        { label: 'شناسه ملی', value: c.company_national_id },
        { label: 'شماره ثبت', value: c.registration_number },
        { label: 'شناسه اقتصادی', value: c.economic_id },
        { label: 'تاریخ شروع فعالیت', value: formatJalali(c.activity_start_date) },
      ]
    : [
        { label: 'نام', value: c.first_name },
        { label: 'نام خانوادگی', value: c.last_name },
        { label: 'کد ملی', value: c.national_id },
        { label: 'نام شرکت یا برند', value: c.brand_name },
      ]
  const source = c.acquaintance_source
    ? (c.acquaintance_source === 'OTHER'
        ? `${sourceLabel('OTHER')}${c.acquaintance_source_other ? `: ${c.acquaintance_source_other}` : ''}`
        : sourceLabel(c.acquaintance_source))
    : ''
  return [
    ...own,
    { label: 'منبع آشنایی', value: source },
    { label: 'آدرس دفتر مرکزی', value: c.head_office_address },
    { label: 'کد پستی دفتر مرکزی', value: c.head_office_postal_code },
    { label: 'آدرس کارخانه', value: c.factory_address },
    { label: 'کد پستی کارخانه', value: c.factory_postal_code },
  ]
})
const activityRows = computed<Row[]>(() => {
  const c = viewing.value
  if (!c) return []
  return [
    { label: 'صنعت فعالیت', value: industriesOf(c).map(industryText).join('، '), wide: true },
    { label: 'استان', value: c.factory_province },
    { label: 'شهر', value: c.factory_city },
    { label: 'موقعیت', value: c.factory_location },
    { label: 'مختصات', value: c.latitude !== null && c.longitude !== null ? `${c.latitude}, ${c.longitude}` : '' },
    { label: 'تعداد خطوط تولید', value: fmtNum(c.production_lines_count) },
    { label: 'نام خطوط تولید', value: (c.production_line_names ?? []).filter(Boolean).join('، '), wide: true },
    { label: 'ظرفیت تولید کارخانه', value: c.production_capacity === null || c.production_capacity === undefined ? '' : `${fmtNum(c.production_capacity)} تن در سال` },
  ]
})
const statusRows = computed<Row[]>(() => {
  const c = viewing.value
  if (!c) return []
  return [
    { label: 'وضعیت تجاری', value: statusLabel(c.commercial_status) },
    { label: 'وضعیت عملیاتی', value: OPERATIONAL_LABELS[c.operational_status] },
    { label: 'مسئول پیگیری', value: c.assigned_to_name },
    { label: 'تاریخ اولین تماس', value: formatJalali(c.first_contact_date) },
    { label: 'تاریخ اولین خرید', value: formatJalali(c.first_purchase_date) },
    { label: 'تاریخ آخرین خرید', value: formatJalali(c.last_purchase_date) },
    ...(c.inactive_reason ? [{ label: 'دلیل غیرفعال شدن', value: c.inactive_reason, wide: true }] : []),
  ]
})
const paymentText = (c: Customer) => {
  if (!c.payment_type) return ''
  const credit = c.credit_other || (c.credit_months ? `${fmtNum(c.credit_months)} ماهه` : '')
  return [PAYMENT_LABELS[c.payment_type], credit].filter(Boolean).join(' — ')
}
const termsRows = computed<Row[]>(() => {
  const c = viewing.value
  if (!c) return []
  return [
    { label: 'شرایط پرداخت', value: paymentText(c) },
    { label: 'نحوه خرید', value: c.purchase_method ? PURCHASE_LABELS[c.purchase_method] : '' },
    { label: 'نوع تحویل', value: c.delivery_type },
    { label: 'محل تخلیه', value: c.unloading_location },
    { label: 'سقف اعتبار مصوب (ریال)', value: fmtNum(c.approved_credit_limit) },
    { label: 'وضعیت اعتباری', value: c.credit_rating ? ratingLabel(c.credit_rating) : '' },
    ...(c.payment_terms ? [{ label: 'توضیحات پرداخت', value: c.payment_terms, wide: true }] : []),
  ]
})
const followRows = computed<Row[]>(() => {
  const c = viewing.value
  if (!c) return []
  return [
    { label: 'تاریخ آخرین مذاکره', value: formatJalali(c.last_negotiation_date) },
    { label: 'تاریخ پیگیری بعدی', value: formatJalali(c.next_follow_up_date) },
    { label: 'نتیجه آخرین مذاکره', value: c.last_negotiation_result, wide: true },
    { label: 'اقدام بعدی', value: c.next_action, wide: true },
    { label: 'یادداشت‌های داخلی', value: c.internal_notes, wide: true },
  ]
})

async function finalizeViewing() {
  if (!viewing.value) return
  try {
    viewing.value = await store.finalizeCustomer(viewing.value.id)
    notify.success('پرونده‌ی مشتری نهایی شد.')
    store.loadStats()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ثبت نهایی انجام نشد.')
  }
}

/* ── add / edit ── */
const formOpen = ref(false)
const editing = ref<Customer | null>(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(c: Customer) {
  editing.value = c
  formOpen.value = true
}
function editFromView() {
  if (!viewing.value) return
  viewOpen.value = false
  openEdit(viewing.value)
}
async function onSaved() {
  await Promise.all([store.load(), reloadReferenceData()])
}

/* ── industries ── */
const categoriesOpen = ref(false)
const optionsOpen = ref(false)

/* ── delete ── */
async function confirmDelete(c: Customer) {
  if (!window.confirm(`مشتری «${c.display_name}» حذف شود؟ این کار از اینجا قابل بازگشت نیست.`)) return
  try {
    await store.removeCustomer(c.id)
    notify.success(`مشتری ${c.display_name} حذف شد.`)
    store.loadStats()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف مشتری انجام نشد.')
  }
}
</script>