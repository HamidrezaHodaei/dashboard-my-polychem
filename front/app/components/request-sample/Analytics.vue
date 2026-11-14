<!-- Request Sample dashboard: KPI cards + six interactive charts. Data comes from
     GET /crm/request-samples/analytics (the SAME filters as the table below). -->
<template>
  <div
    class="space-y-6"
    dir="rtl"
  >
    <!-- KPI cards: click one to filter the table to those requests -->
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      <button
        v-for="c in cards"
        :key="c.key"
        type="button"
        class="group rounded-xl border bg-card p-4 text-right shadow-none transition hover:border-primary/60 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :class="activeKey === c.key && 'border-primary ring-1 ring-primary/40'"
        :title="`نمایش ${c.label}`"
        @click="emit('filter', c.statuses)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs text-muted-foreground">{{ c.en }}</span>
          <span
            class="grid size-8 place-items-center rounded-lg"
            :style="{ background: `${c.color}1f`, color: c.color }"
          >
            <Icon
              :name="c.icon"
              class="size-4"
            />
          </span>
        </div>
        <p class="mt-2 text-2xl font-semibold tabular-nums">
          <span v-if="loading && !data">…</span>
          <template v-else>
            {{ fa(c.value) }}
          </template>
        </p>
        <p class="mt-0.5 text-sm text-foreground/80">
          {{ c.label }}
        </p>
      </button>
    </div>

    <div
      v-if="data && !data.kpis.total"
      class="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground"
    >
      در بازهٔ انتخابی درخواستی ثبت نشده است؛ نمودارها با ثبت اولین درخواست پر می‌شوند.
    </div>

    <template v-if="data && data.kpis.total">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <!-- 1. Request Trends -->
        <PrintableChart
          title="Request Trends"
          class="gap-3 p-5 shadow-none"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 pl-16">
            <div>
              <h3 class="text-base font-semibold">
                Request Trends · روند درخواست‌ها
              </h3>
              <p class="min-h-4 text-xs text-muted-foreground">
                <template v-if="hoverBar !== null && data.trend[hoverBar]">
                  {{ data.trend[hoverBar]!.label }}: <b class="text-foreground">{{ fa(data.trend[hoverBar]!.count) }}</b> درخواست
                </template>
                <template v-else>
                  تعداد درخواست‌های ثبت‌شده در هر بازه
                </template>
              </p>
            </div>
            <div class="print-hide flex gap-1">
              <Button
                v-for="g in GRANS"
                :key="g.value"
                size="sm"
                :variant="data.granularity === g.value ? 'default' : 'outline'"
                @click="emit('granularity', g.value)"
              >
                {{ g.label }}
              </Button>
            </div>
          </div>
          <div class="overflow-x-auto">
            <svg
              :viewBox="`0 0 ${trendW} 260`"
              :style="{ minWidth: `${Math.min(trendW, 900)}px` }"
              class="h-64 w-full"
              dir="ltr"
              role="img"
              aria-label="نمودار روند درخواست‌ها"
            >
              <g
                v-for="t in trendTicks"
                :key="t"
              >
                <line
                  x1="38"
                  :x2="trendW - 8"
                  :y1="ty(t)"
                  :y2="ty(t)"
                  stroke="currentColor"
                  stroke-opacity=".12"
                  stroke-dasharray="3 3"
                />
                <text
                  x="30"
                  :y="ty(t) + 3"
                  text-anchor="end"
                  font-size="10"
                  class="fill-muted-foreground"
                >{{ fa(t) }}</text>
              </g>
              <g
                v-for="(p, i) in data.trend"
                :key="p.key"
                class="cursor-pointer"
                @mouseenter="hoverBar = i"
                @mouseleave="hoverBar = null"
                @click="emit('range', p.key)"
              >
                <rect
                  :x="bx(i)"
                  y="14"
                  :width="bw + 8"
                  height="206"
                  fill="transparent"
                />
                <rect
                  :x="bx(i) + 4"
                  :y="ty(p.count)"
                  :width="bw"
                  :height="Math.max(2, 220 - ty(p.count))"
                  rx="4"
                  :fill="hoverBar === i ? '#f59e0b' : '#6366f1'"
                >
                  <title>{{ p.label }}: {{ fa(p.count) }}</title>
                </rect>
                <text
                  :x="bx(i) + 4 + bw / 2"
                  :y="ty(p.count) - 4"
                  text-anchor="middle"
                  font-size="10"
                  class="fill-foreground"
                >{{ fa(p.count) }}</text>
                <text
                  :x="bx(i) + 4 + bw / 2"
                  y="238"
                  text-anchor="middle"
                  font-size="9"
                  class="fill-muted-foreground"
                >{{ short(p.label) }}</text>
              </g>
            </svg>
          </div>
        </PrintableChart>

        <!-- 2. Request Status Distribution -->
        <PrintableChart
          title="Request Status Distribution"
          class="gap-3 p-5 shadow-none"
        >
          <h3 class="pl-16 text-base font-semibold">
            Status Distribution · توزیع وضعیت
          </h3>
          <div class="flex flex-wrap items-center justify-center gap-6">
            <svg
              viewBox="0 0 120 120"
              class="size-44"
              role="img"
              aria-label="توزیع وضعیت درخواست‌ها"
            >
              <circle
                v-for="(s, i) in donut"
                :key="s.status"
                cx="60"
                cy="60"
                r="42"
                fill="none"
                :stroke="s.color"
                :stroke-width="hoverSlice === i ? 22 : 18"
                :stroke-dasharray="`${s.len} ${CIRC - s.len}`"
                :stroke-dashoffset="-s.offset"
                transform="rotate(-90 60 60)"
                class="cursor-pointer transition-all"
                @mouseenter="hoverSlice = i"
                @mouseleave="hoverSlice = null"
                @click="emit('filter', [s.status])"
              >
                <title>{{ s.label }}: {{ fa(s.count) }}</title>
              </circle>
              <text
                x="60"
                y="57"
                text-anchor="middle"
                font-size="16"
                font-weight="700"
                class="fill-foreground"
              >{{ fa(hoverSlice !== null ? donut[hoverSlice]!.count : donutTotal) }}</text>
              <text
                x="60"
                y="72"
                text-anchor="middle"
                font-size="7"
                class="fill-muted-foreground"
              >{{ hoverSlice !== null ? donut[hoverSlice]!.label : 'کل درخواست' }}</text>
            </svg>
            <ul class="min-w-40 space-y-1.5 text-sm">
              <li
                v-for="(s, i) in donut"
                :key="s.status"
                class="flex cursor-pointer items-center justify-between gap-3 rounded px-1.5 py-0.5 hover:bg-muted/50"
                @mouseenter="hoverSlice = i"
                @mouseleave="hoverSlice = null"
                @click="emit('filter', [s.status])"
              >
                <span class="flex items-center gap-2"><i
                  class="size-2.5 rounded-full"
                  :style="{ background: s.color }"
                />{{ s.label }}</span>
                <span class="text-muted-foreground">{{ fa(s.count) }} · {{ fa(s.pct) }}٪</span>
              </li>
            </ul>
          </div>
        </PrintableChart>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- 3. Top Requested Products -->
        <PrintableChart
          title="Top Requested Products"
          class="gap-3 p-5 shadow-none"
        >
          <h3 class="pl-16 text-base font-semibold">
            Top Requested Products · پرتقاضاترین محصول و گرید
          </h3>
          <div class="space-y-3">
            <div
              v-for="(p, i) in data.top_products"
              :key="`${p.product}-${p.grade}`"
              class="space-y-1"
            >
              <div class="flex items-center justify-between gap-3 text-sm">
                <span class="min-w-0 truncate font-medium"><span class="text-muted-foreground">{{ fa(i + 1) }}.</span> {{ p.product }}<span v-if="p.grade"> · {{ p.grade }}</span></span>
                <span class="shrink-0 whitespace-nowrap text-xs text-muted-foreground">{{ fa(p.requests) }} درخواست<template v-if="p.quantity_kg"> · {{ fa(Math.round(p.quantity_kg)) }} kg</template></span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  class="h-full rounded-full bg-primary"
                  :style="{ width: `${(p.requests / topMax) * 100}%` }"
                />
              </div>
            </div>
            <p
              v-if="!data.top_products.length"
              class="py-6 text-center text-sm text-muted-foreground"
            >
              محصولی ثبت نشده است.
            </p>
          </div>
        </PrintableChart>

        <!-- 5. Customer Feedback Analysis + 6. Conversion -->
        <PrintableChart
          title="Customer Feedback Analysis"
          class="gap-4 p-5 shadow-none"
        >
          <h3 class="pl-16 text-base font-semibold">
            Customer Feedback · بازخورد مشتریان
          </h3>
          <div
            v-if="data.feedback.total"
            class="space-y-4"
          >
            <div class="flex h-4 overflow-hidden rounded-full bg-muted">
              <div
                v-for="f in feedbackBars"
                :key="f.key"
                :style="{ width: `${f.pct}%`, background: f.color }"
                :title="`${f.label}: ${fa(f.count)}`"
              />
            </div>
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="rounded-lg border bg-emerald-50 p-2 dark:bg-emerald-950/30">
                <p class="text-xl font-semibold text-emerald-700 dark:text-emerald-300">
                  {{ pct(data.feedback.accepted_pct) }}
                </p>
                <p class="text-xs text-muted-foreground">
                  تأیید شده
                </p>
              </div>
              <div class="rounded-lg border bg-amber-50 p-2 dark:bg-amber-950/30">
                <p class="text-xl font-semibold text-amber-700 dark:text-amber-300">
                  {{ pct(data.feedback.conditional_pct) }}
                </p>
                <p class="text-xs text-muted-foreground">
                  تأیید مشروط
                </p>
              </div>
              <div class="rounded-lg border bg-red-50 p-2 dark:bg-red-950/30">
                <p class="text-xl font-semibold text-red-700 dark:text-red-300">
                  {{ pct(data.feedback.rejected_pct) }}
                </p>
                <p class="text-xs text-muted-foreground">
                  تأیید نشده
                </p>
              </div>
            </div>
            <ul class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <li
                v-for="f in feedbackBars"
                :key="`l-${f.key}`"
                class="flex items-center justify-between"
              >
                <span class="flex items-center gap-1.5"><i
                  class="size-2 rounded-full"
                  :style="{ background: f.color }"
                />{{ f.label }}</span>
                <span>{{ fa(f.count) }}</span>
              </li>
            </ul>
          </div>
          <p
            v-else
            class="py-6 text-center text-sm text-muted-foreground"
          >
            هنوز بازخورد نهایی ثبت نشده است.
          </p>

          <div class="flex items-center gap-4 border-t pt-4">
            <svg
              viewBox="0 0 80 80"
              class="size-20 shrink-0"
              role="img"
              aria-label="نرخ تبدیل نمونه به فروش"
            >
              <circle
                cx="40"
                cy="40"
                r="30"
                fill="none"
                class="stroke-muted"
                stroke-width="9"
              />
              <circle
                cx="40"
                cy="40"
                r="30"
                fill="none"
                stroke="#22c55e"
                stroke-width="9"
                stroke-linecap="round"
                :stroke-dasharray="`${((data.conversion.rate ?? 0) / 100) * 188.5} 188.5`"
                transform="rotate(-90 40 40)"
              />
              <text
                x="40"
                y="44"
                text-anchor="middle"
                font-size="14"
                font-weight="700"
                class="fill-foreground"
              >{{ pct(data.conversion.rate) }}</text>
            </svg>
            <div>
              <h3 class="text-base font-semibold">
                Sample Conversion Rate · نرخ تبدیل نمونه به فروش
              </h3>
              <p class="text-xs text-muted-foreground">
                {{ fa(data.conversion.converted) }} تبدیل‌شده از {{ fa(data.conversion.dispatched) }} نمونهٔ ارسال‌شده
              </p>
            </div>
          </div>
        </PrintableChart>
      </div>

      <!-- 4. Sales Performance -->
      <PrintableChart
        title="Sales Performance"
        class="gap-3 p-5 shadow-none"
      >
        <h3 class="pl-16 text-base font-semibold">
          Sales Performance · عملکرد کارشناسان فروش
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[40rem] text-sm">
            <thead class="text-xs text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2 text-right font-medium">
                  کارشناس
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  درخواست‌ها
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  تأیید شده
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  نرخ تأیید
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  ارسال‌شده
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  تبدیل به فروش
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  نرخ تبدیل
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in data.sales_performance"
                :key="r.rep_id ?? 'x'"
                class="border-b last:border-0"
              >
                <td class="px-3 py-2.5 font-medium">
                  {{ r.name }}
                </td>
                <td class="px-3 py-2.5 text-center">
                  {{ fa(r.requests) }}
                </td>
                <td class="px-3 py-2.5 text-center">
                  {{ fa(r.approved) }}
                </td>
                <td class="px-3 py-2.5 text-center">
                  <div class="mx-auto w-20">
                    <span class="text-xs">{{ pct(r.approval_rate) }}</span>
                    <div class="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        class="h-full rounded-full bg-emerald-500"
                        :style="{ width: `${r.approval_rate ?? 0}%` }"
                      />
                    </div>
                  </div>
                </td>
                <td class="px-3 py-2.5 text-center">
                  {{ fa(r.dispatched) }}
                </td>
                <td class="px-3 py-2.5 text-center">
                  {{ fa(r.converted) }}
                </td>
                <td class="px-3 py-2.5 text-center">
                  <div class="mx-auto w-20">
                    <span class="text-xs">{{ pct(r.conversion_rate) }}</span>
                    <div class="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        class="h-full rounded-full bg-primary"
                        :style="{ width: `${r.conversion_rate ?? 0}%` }"
                      />
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PrintableChart>
    </template>
  </div>
</template>

<script setup lang="ts">
import { FEEDBACK_META, STATUS_META } from '~/utils/requestSample'
import type { SampleAnalytics, SampleStatus } from '~/utils/requestSample'
import { toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ data: SampleAnalytics | null, loading?: boolean, activeStatuses?: string[] }>()
const emit = defineEmits<{
  (e: 'filter', statuses: string[] | null): void
  (e: 'granularity', g: 'day' | 'week' | 'month'): void
  (e: 'range', key: string): void
}>()

const fa = (n: number) => toPersianDigits(Math.round(n))
const pct = (v: number | null) => (v === null ? '—' : `${fa(v)}٪`)
const GRANS = [{ value: 'day', label: 'روزانه' }, { value: 'week', label: 'هفتگی' }, { value: 'month', label: 'ماهانه' }] as const

const cards = computed(() => {
  const k = props.data?.kpis
  const v = (n?: number) => n ?? 0
  return [
    { key: 'total', en: 'Total Requests', label: 'کل درخواست‌ها', value: v(k?.total), icon: 'lucide:flask-conical', color: '#6366f1', statuses: null as string[] | null },
    { key: 'pending', en: 'Pending Requests', label: 'در انتظار تأیید', value: v(k?.pending), icon: 'lucide:hourglass', color: '#f59e0b', statuses: ['PENDING_APPROVAL'] },
    { key: 'approved', en: 'Approved Requests', label: 'تأیید شده', value: v(k?.approved), icon: 'lucide:check-circle-2', color: '#10b981', statuses: ['APPROVED'] },
    { key: 'dispatched', en: 'Samples Dispatched', label: 'نمونهٔ ارسال‌شده', value: v(k?.dispatched), icon: 'lucide:truck', color: '#0ea5e9', statuses: ['DISPATCHED', 'AWAITING_FEEDBACK', 'COMPLETED', 'CONVERTED'] },
    { key: 'rejected', en: 'Rejected Requests', label: 'رد شده', value: v(k?.rejected), icon: 'lucide:x-circle', color: '#ef4444', statuses: ['REJECTED'] },
    { key: 'awaiting', en: 'Awaiting Customer Feedback', label: 'در انتظار بازخورد', value: v(k?.awaiting_feedback), icon: 'lucide:message-circle-question', color: '#8b5cf6', statuses: ['AWAITING_FEEDBACK'] },
    { key: 'converted', en: 'Converted to Sales', label: 'تبدیل به فروش', value: v(k?.converted), icon: 'lucide:trending-up', color: '#22c55e', statuses: ['CONVERTED'] },
  ]
})
const activeKey = computed(() => {
  const a = [...(props.activeStatuses ?? [])].sort().join(',')
  return cards.value.find(c => (c.statuses ? [...c.statuses].sort().join(',') : '') === a)?.key ?? null
})

/* trend */
const hoverBar = ref<number | null>(null)
const bw = 26
const slot = computed(() => bw + 14)
const trendW = computed(() => Math.max(560, (props.data?.trend.length ?? 0) * slot.value + 56))
const bx = (i: number) => 44 + i * slot.value
const trendMax = computed(() => {
  const max = Math.max(1, ...(props.data?.trend.map(t => t.count) ?? [1]))
  const step = Math.max(1, Math.ceil(max / 4 / (max > 20 ? 5 : 1)) * (max > 20 ? 5 : 1))
  return Math.ceil(max / step) * step
})
const trendTicks = computed(() => {
  const step = Math.max(1, trendMax.value / 4)
  return Array.from({ length: 5 }, (_, i) => Math.round(i * step))
})
const ty = (v: number) => 220 - (v / trendMax.value) * 200
const short = (label: string) => (label.length > 10 ? `${label.slice(0, 9)}…` : label)

/* donut */
const hoverSlice = ref<number | null>(null)
const CIRC = 2 * Math.PI * 42
const donutTotal = computed(() => props.data?.status_distribution.reduce((s, x) => s + x.count, 0) ?? 0)
const donut = computed(() => {
  let offset = 0
  const total = donutTotal.value || 1
  return (props.data?.status_distribution ?? []).map((s) => {
    const len = (s.count / total) * CIRC
    const out = {
      status: s.status as SampleStatus, count: s.count, label: STATUS_META[s.status]?.label ?? s.status,
      color: STATUS_META[s.status]?.color ?? '#94a3b8', len, offset, pct: (s.count / total) * 100,
    }
    offset += len
    return out
  })
})

const topMax = computed(() => Math.max(1, ...(props.data?.top_products.map(p => p.requests) ?? [1])))
const feedbackBars = computed(() => {
  const f = props.data?.feedback
  if (!f?.total) return []
  return (Object.keys(FEEDBACK_META) as (keyof typeof FEEDBACK_META)[]).map(key => ({
    key, label: FEEDBACK_META[key].label, color: FEEDBACK_META[key].color, count: f.counts[key] ?? 0,
    pct: ((f.counts[key] ?? 0) / f.total) * 100,
  })).filter(x => x.count)
})
</script>
