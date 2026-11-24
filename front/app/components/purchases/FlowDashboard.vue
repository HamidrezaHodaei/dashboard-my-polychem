<!-- <PurchasesFlowDashboard base="/inventory" /> : summary of the purchase requests -- where they are, what is late,
     what needs attention. Every number is a link to the list already filtered on it, so the dashboard is a
     starting point and not a dead end. Uses only the existing flow endpoints (/requests, /kpi); each block is
     optional: a block whose endpoint the user may not read is simply left out. -->
<template>
  <div class="space-y-6">
    <p v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</p>

    <!-- key figures -->
    <section aria-label="شاخص‌های اصلی" class="grid grid-cols-2 divide-x divide-x-reverse divide-y rounded-xl border sm:grid-cols-3 sm:divide-y-0 lg:grid-cols-5">
      <NuxtLink
        v-for="c in cells"
        :key="c.key"
        :to="c.to"
        class="p-4 transition-colors hover:bg-muted/40 focus-visible:outline-2 focus-visible:outline-ring"
      >
        <div class="text-xs text-muted-foreground">{{ c.label }}</div>
        <div class="mt-1 text-2xl font-semibold tabular-nums" :class="c.tone">{{ loading ? '…' : c.value }}</div>
      </NuxtLink>
    </section>

    <!-- status distribution -->
    <section class="space-y-3 rounded-xl border p-5">
      <div class="flex items-baseline justify-between gap-2">
        <h2 class="text-base font-semibold">وضعیت درخواست‌ها</h2>
        <span class="text-xs text-muted-foreground">{{ faNum(grandTotal) }} درخواست</span>
      </div>
      <div
        class="flex h-2.5 overflow-hidden rounded-full bg-muted"
        role="img"
        :aria-label="`توزیع وضعیت ${grandTotal} درخواست`"
      >
        <span v-for="s in nonEmpty" :key="s.value" :class="BAR[s.value] ?? 'bg-slate-400'" :style="{ width: `${(s.count / grandTotal) * 100}%` }" />
      </div>
      <ul class="grid gap-x-6 gap-y-1 sm:grid-cols-2">
        <li v-for="s in statuses" :key="s.value">
          <NuxtLink
            :to="{ path: base, query: { status: s.value } }"
            class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/50"
            :class="s.count === 0 && 'text-muted-foreground'"
          >
            <span class="size-2.5 shrink-0 rounded-full" :class="BAR[s.value] ?? 'bg-slate-400'" aria-hidden="true" />
            <span class="flex-1">{{ s.label }}</span>
            <span class="tabular-nums font-medium">{{ loading ? '…' : faNum(s.count) }}</span>
            <span class="w-10 text-left text-xs text-muted-foreground tabular-nums">{{ grandTotal && !loading ? `${faNum(Math.round((s.count / grandTotal) * 100))}٪` : '' }}</span>
          </NuxtLink>
        </li>
      </ul>
    </section>

    <div class="grid gap-6 lg:grid-cols-2">
      <!-- needs attention -->
      <section class="rounded-xl border">
        <header class="flex items-baseline justify-between border-b px-5 py-3">
          <h2 class="text-base font-semibold">نیازمند توجه</h2>
          <span class="text-xs text-muted-foreground">تأخیر یا رسید انبار ثبت‌نشده</span>
        </header>
        <ul v-if="attention.length" class="divide-y">
          <li v-for="r in attention" :key="r.id">
            <NuxtLink :to="`${base}/${r.id}`" class="flex items-center gap-3 px-5 py-3 text-sm transition-colors hover:bg-muted/40">
              <span class="font-semibold" dir="ltr">{{ r.request_no }}</span>
              <span class="flex-1 truncate text-muted-foreground">{{ r.requester_unit }}</span>
              <span v-if="r.overdue_items" class="text-xs text-red-600">{{ faNum(r.overdue_items) }} قلم با تأخیر</span>
              <span v-if="r.missing_receipts" class="text-xs text-orange-600">{{ faNum(r.missing_receipts) }} بدون رسید</span>
            </NuxtLink>
          </li>
        </ul>
        <p v-else class="px-5 py-8 text-center text-sm text-muted-foreground">{{ loading ? 'در حال بارگذاری…' : 'موردی نیازمند اقدام نیست.' }}</p>
      </section>

      <!-- latest requests -->
      <section class="rounded-xl border">
        <header class="flex items-baseline justify-between border-b px-5 py-3">
          <h2 class="text-base font-semibold">آخرین درخواست‌ها</h2>
          <NuxtLink :to="base" class="text-xs text-primary-content hover:underline">مشاهدهٔ همه</NuxtLink>
        </header>
        <ul v-if="latest.length" class="divide-y">
          <li v-for="r in latest" :key="r.id">
            <NuxtLink :to="`${base}/${r.id}`" class="flex items-center gap-3 px-5 py-3 text-sm transition-colors hover:bg-muted/40">
              <span class="font-semibold" dir="ltr">{{ r.request_no }}</span>
              <span class="flex-1 truncate text-muted-foreground">{{ r.requester_unit }} · {{ r.request_date_jalali }}</span>
              <PurchasesFlowBadge kind="request" :value="r.status" :label="r.status_label" />
            </NuxtLink>
          </li>
        </ul>
        <p v-else class="px-5 py-8 text-center text-sm text-muted-foreground">{{ loading ? 'در حال بارگذاری…' : 'هنوز درخواستی ثبت نشده است.' }}</p>
      </section>
    </div>

    <div class="flex justify-end">
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">به‌روزرسانی</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FlowRow } from '~/stores/purchaseFlow'

const props = withDefaults(defineProps<{ base?: string }>(), { base: '/inventory' })
const store = usePurchaseFlowStore()
await store.loadMeta()
const perms = store.meta!.my_permissions

const BAR: Record<string, string> = {
  UNDER_REVIEW: 'bg-slate-400', SOURCING: 'bg-blue-500', REFERRED_FINANCE: 'bg-violet-500', FOLLOW_UP: 'bg-amber-500',
  PARTIAL_DELIVERY: 'bg-teal-500', COMPLETED: 'bg-emerald-500', RETURNED: 'bg-orange-500', VOID: 'bg-red-500',
}
const faNum = (n: number | null | undefined) => (n === null || n === undefined ? '—' : Number(n).toLocaleString('fa-IR'))

const loading = ref(true)
const error = ref('')
const statuses = ref<{ value: string, label: string, count: number }[]>([])
const openTotal = ref(0)
const managerTotal = ref<number | null>(null)
const overdueItems = ref<number | null>(null)
const attention = ref<FlowRow[]>([])
const latest = ref<FlowRow[]>([])
const missingReceipts = ref(0)

const grandTotal = computed(() => statuses.value.reduce((n, s) => n + s.count, 0))
const nonEmpty = computed(() => statuses.value.filter(s => s.count > 0))

const cells = computed(() => [
  { key: 'all', label: 'کل درخواست‌ها', value: faNum(grandTotal.value), to: props.base, tone: '' },
  { key: 'open', label: 'در جریان', value: faNum(openTotal.value), to: { path: props.base, query: { queue: 'open' } }, tone: '' },
  ...(managerTotal.value !== null ? [{ key: 'manager', label: 'منتظر تأیید مدیر', value: faNum(managerTotal.value), to: props.base, tone: '' }] : []),
  ...(overdueItems.value !== null ? [{ key: 'overdue', label: 'اقلام دارای تأخیر', value: faNum(overdueItems.value), to: props.base, tone: overdueItems.value ? 'text-red-600' : '' }] : []),
  { key: 'receipt', label: 'بدون رسید انبار', value: faNum(missingReceipts.value), to: props.base, tone: missingReceipts.value ? 'text-orange-600' : '' },
])

let seq = 0
async function load() {
  const id = ++seq
  loading.value = true
  error.value = ''
  const metaStatuses = store.meta?.request_statuses ?? []
  const [counts, open, mgr, kpi, recent] = await Promise.allSettled([
    Promise.all(metaStatuses.map(s => store.list({ status: s.value, per_page: 1 }).then(r => r.total))),
    store.list({ queue: 'open', per_page: 50 }),
    perms.manager ? store.list({ queue: 'manager', per_page: 1 }) : Promise.resolve(null),
    perms.read ? store.kpi({}) : Promise.resolve(null),
    store.list({ per_page: 6 }),
  ])
  if (id !== seq) return
  if (counts.status === 'fulfilled') statuses.value = metaStatuses.map((s, i) => ({ ...s, count: counts.value[i] ?? 0 }))
  else error.value = 'بارگذاری آمار انجام نشد؛ دوباره تلاش کنید.'
  if (open.status === 'fulfilled') {
    openTotal.value = open.value.total
    attention.value = open.value.items.filter(r => r.overdue_items || r.missing_receipts).slice(0, 6)
    missingReceipts.value = open.value.items.filter(r => r.missing_receipts).length
  }
  managerTotal.value = mgr.status === 'fulfilled' && mgr.value ? mgr.value.total : null
  overdueItems.value = kpi.status === 'fulfilled' && kpi.value ? Number(kpi.value.overall.open_overdue ?? 0) : null
  if (recent.status === 'fulfilled') latest.value = recent.value.items
  loading.value = false
}
onMounted(load)
</script>
