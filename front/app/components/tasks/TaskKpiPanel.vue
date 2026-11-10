<!-- Task analytics: overview KPIs, Employee KPI table, Created vs Completed chart, and the report
     (view in the UI · Excel · PDF). Everything is computed from the tasks the user may see. -->
<template>
  <div
    class="space-y-6"
    dir="rtl"
  >
    <div
      class="flex flex-wrap items-center gap-2"
      role="tablist"
    >
      <button
        v-for="t in TABS"
        :key="t.value"
        type="button"
        role="tab"
        class="rounded-full border px-4 py-1.5 text-sm font-medium transition-colors"
        :class="tab === t.value ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted'"
        :aria-selected="tab === t.value"
        @click="tab = t.value"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- ───────────── overview ───────────── -->
    <template v-if="tab === 'overview'">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card
          v-for="c in overviewCards"
          :key="c.label"
          class="gap-1 p-4 shadow-none"
        >
          <p class="text-sm text-muted-foreground">
            {{ c.label }}
          </p>
          <p
            class="text-2xl font-semibold"
            :class="c.tone"
          >
            {{ c.value }}
          </p>
          <p class="text-xs text-muted-foreground">
            {{ c.hint }}
          </p>
        </Card>
      </div>

      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <PrintableChart
          title="Created vs. Completed Work"
          class="gap-3 p-4 shadow-none"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 pl-16">
            <div>
              <h3 class="text-base font-semibold">
                Created vs. Completed Work
              </h3>
              <p class="text-xs text-muted-foreground">
                مقایسهٔ وظایف ایجادشده و تکمیل‌شده در هر ماه
              </p>
            </div>
            <div class="print-hide flex gap-1">
              <Button
                v-for="n in [3, 6, 12]"
                :key="n"
                size="sm"
                :variant="months === n ? 'default' : 'outline'"
                @click="months = n"
              >
                {{ toPersianDigits(n) }} ماه
              </Button>
            </div>
          </div>
          <TaskProductivityChart :points="monthly" />
        </PrintableChart>

        <PrintableChart
          title="Task Distribution"
          class="gap-4 p-4 shadow-none"
        >
          <h3 class="text-base font-semibold">
            توزیع وظایف بر اساس وضعیت
          </h3>
          <div class="space-y-3">
            <div
              v-for="s in statusRows"
              :key="s.key"
              class="space-y-1"
            >
              <div class="flex items-center justify-between text-sm">
                <span class="flex items-center gap-2"><i
                  class="inline-block size-2.5 rounded-full"
                  :style="{ background: s.color }"
                />{{ s.label }}</span>
                <span class="text-muted-foreground">{{ fa(s.count) }} · {{ fa(s.pct) }}٪</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  class="h-full rounded-full"
                  :style="{ width: `${s.pct}%`, background: s.color }"
                />
              </div>
            </div>
          </div>
          <h3 class="border-t pt-3 text-base font-semibold">
            توزیع بر اساس اولویت
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="p in priorityRows"
              :key="p.key"
              class="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2 text-sm"
            >
              <span class="flex items-center gap-2"><i
                class="inline-block size-2.5 rounded-full"
                :class="p.dot"
              />{{ p.label }}</span>
              <Badge variant="secondary">
                {{ fa(p.count) }}
              </Badge>
            </div>
          </div>
        </PrintableChart>
      </div>

      <PrintableChart
        title="Departments"
        class="gap-3 p-4 shadow-none"
      >
        <h3 class="pl-16 text-base font-semibold">
          عملکرد به تفکیک واحد
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="text-xs text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2 text-right font-medium">
                  واحد
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  کل
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  تکمیل
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  در انتظار
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  دارای تأخیر
                </th>
                <th class="px-3 py-2 text-center font-medium">
                  نرخ تکمیل
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in departmentRows"
                :key="d.id"
                class="border-b last:border-0"
              >
                <td class="px-3 py-2 font-medium">
                  {{ d.name }}
                </td>
                <td class="px-3 py-2 text-center">
                  {{ fa(d.kpi.assigned) }}
                </td>
                <td class="px-3 py-2 text-center">
                  {{ fa(d.kpi.completed) }}
                </td>
                <td class="px-3 py-2 text-center">
                  {{ fa(d.kpi.pending) }}
                </td>
                <td
                  class="px-3 py-2 text-center"
                  :class="d.kpi.overdue ? 'font-medium text-destructive' : ''"
                >
                  {{ fa(d.kpi.overdue) }}
                </td>
                <td class="px-3 py-2 text-center">
                  {{ fa(d.kpi.completionRate) }}٪
                </td>
              </tr>
              <tr v-if="!departmentRows.length">
                <td
                  colspan="6"
                  class="px-3 py-6 text-center text-muted-foreground"
                >
                  واحدی برای نمایش وجود ندارد.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PrintableChart>
    </template>

    <!-- ───────────── employee KPI ───────────── -->
    <template v-else-if="tab === 'employees'">
      <PrintableChart
        title="Employee KPI"
        class="gap-3 p-4 shadow-none"
      >
        <div class="flex flex-wrap items-center justify-between gap-2 pl-16">
          <div>
            <h3 class="text-base font-semibold">
              تحلیل عملکرد کارکنان (Employee KPI)
            </h3>
            <p class="text-xs text-muted-foreground">
              شاخص‌های هر کارمند بر اساس وظایف تخصیص‌یافته به او
            </p>
          </div>
          <Select v-model="sortKey">
            <SelectTrigger class="print-hide h-8 w-52">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="o in SORTS"
                :key="o.value"
                :value="o.value"
              >
                {{ o.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[56rem] text-sm">
            <thead class="text-xs text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2 text-right font-medium">
                  کارمند
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Total Assigned<br>کل تخصیص‌یافته
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Completed<br>تکمیل‌شده
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Pending<br>در انتظار
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Overdue<br>دارای تأخیر
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Completion Rate<br>نرخ تکمیل
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  On-Time<br>تکمیل به‌موقع
                </th>
                <th class="px-2 py-2 text-center font-medium">
                  Avg. Time<br>میانگین زمان
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  Task Distribution<br>توزیع وضعیت
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="e in employeeRows"
                :key="e.id"
                class="border-b last:border-0"
              >
                <td class="px-3 py-2.5 font-medium">
                  {{ e.name }}
                </td>
                <td class="px-2 py-2.5 text-center">
                  {{ fa(e.kpi.assigned) }}
                </td>
                <td class="px-2 py-2.5 text-center text-success">
                  {{ fa(e.kpi.completed) }}
                </td>
                <td class="px-2 py-2.5 text-center">
                  {{ fa(e.kpi.pending) }}
                </td>
                <td
                  class="px-2 py-2.5 text-center"
                  :class="e.kpi.overdue ? 'font-semibold text-destructive' : 'text-muted-foreground'"
                >
                  {{ fa(e.kpi.overdue) }}
                </td>
                <td class="px-2 py-2.5 text-center">
                  <div class="mx-auto w-20">
                    <span class="text-xs font-medium">{{ fa(e.kpi.completionRate) }}٪</span>
                    <div class="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        class="h-full rounded-full bg-primary"
                        :style="{ width: `${e.kpi.completionRate}%` }"
                      />
                    </div>
                  </div>
                </td>
                <td class="px-2 py-2.5 text-center">
                  {{ e.kpi.onTimeRate === null ? '—' : `${fa(e.kpi.onTimeRate)}٪` }}
                </td>
                <td class="px-2 py-2.5 text-center whitespace-nowrap">
                  {{ formatHours(e.kpi.avgCompletionHours) }}
                </td>
                <td class="px-3 py-2.5">
                  <div class="flex h-2.5 w-40 overflow-hidden rounded-full bg-muted">
                    <div
                      v-for="s in STATUS_ORDER"
                      :key="s.key"
                      :style="{ width: `${e.kpi.assigned ? (e.kpi.byStatus[s.key] / e.kpi.assigned) * 100 : 0}%`, background: s.color }"
                      :title="`${s.label}: ${fa(e.kpi.byStatus[s.key])}`"
                    />
                  </div>
                </td>
              </tr>
              <tr v-if="!employeeRows.length">
                <td
                  colspan="9"
                  class="px-3 py-6 text-center text-muted-foreground"
                >
                  هنوز وظیفه‌ای به کارمندی تخصیص داده نشده است.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="flex flex-wrap gap-x-4 gap-y-1 border-t pt-3 text-xs text-muted-foreground">
          <span
            v-for="s in STATUS_ORDER"
            :key="s.key"
            class="flex items-center gap-1.5"
          ><i
            class="inline-block size-2.5 rounded-sm"
            :style="{ background: s.color }"
          />{{ s.label }}</span>
          <span>· «به‌موقع» = تکمیل تا پایان روز موعد؛ «میانگین زمان» = از ایجاد تا تکمیل.</span>
        </div>
      </PrintableChart>

      <PrintableChart
        title="Employee completion"
        class="gap-3 p-4 shadow-none"
      >
        <h3 class="pl-16 text-base font-semibold">
          مقایسهٔ نرخ تکمیل کارکنان
        </h3>
        <div class="space-y-2.5">
          <div
            v-for="e in employeeRows"
            :key="`bar-${e.id}`"
            class="grid grid-cols-[9rem_1fr_3rem] items-center gap-3 text-sm"
          >
            <span class="truncate">{{ e.name }}</span>
            <div class="h-3 overflow-hidden rounded-full bg-muted">
              <div
                class="h-full rounded-full bg-success"
                :style="{ width: `${e.kpi.completionRate}%` }"
              />
            </div>
            <span class="text-left text-xs text-muted-foreground">{{ fa(e.kpi.completionRate) }}٪</span>
          </div>
        </div>
      </PrintableChart>
    </template>

    <!-- ───────────── report ───────────── -->
    <template v-else>
      <Card
        ref="reportCard"
        class="gap-4 p-4 shadow-none"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-base font-semibold">
              گزارش امور محوله
            </h3>
            <p class="text-xs text-muted-foreground">
              {{ fa(reportRows.length) }} مورد · تاریخ تهیه: {{ today }}
            </p>
          </div>
          <div class="print-hide flex flex-wrap gap-2">
            <Button
              variant="outline"
              class="gap-2"
              @click="emit('export-excel')"
            >
              <Icon
                name="lucide:file-spreadsheet"
                class="size-4"
              /> Excel
            </Button>
            <Button
              class="gap-2"
              @click="exportPdf"
            >
              <Icon
                name="lucide:file-down"
                class="size-4"
              /> PDF
            </Button>
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-4">
          <div
            v-for="c in reportSummary"
            :key="c.label"
            class="rounded-lg border bg-muted/20 p-3"
          >
            <p class="text-xs text-muted-foreground">
              {{ c.label }}
            </p>
            <p class="text-lg font-semibold">
              {{ c.value }}
            </p>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="text-xs text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2 text-right font-medium">
                  #
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  عنوان
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  واحد
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  مسئولان
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  وضعیت
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  اولویت
                </th>
                <th class="px-3 py-2 text-right font-medium">
                  موعد
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(r, i) in reportRows"
                :key="r.id"
                class="border-b align-top last:border-0"
              >
                <td class="px-3 py-2 text-muted-foreground">
                  {{ fa(i + 1) }}
                </td>
                <td
                  class="px-3 py-2 font-medium"
                  dir="auto"
                >
                  {{ r.title }}
                </td>
                <td class="px-3 py-2">
                  {{ r.project }}
                </td>
                <td class="px-3 py-2">
                  {{ r.assignees }}
                </td>
                <td class="px-3 py-2">
                  {{ r.status }}
                </td>
                <td class="px-3 py-2">
                  {{ r.priority }}
                </td>
                <td class="whitespace-nowrap px-3 py-2">
                  {{ r.due }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { TaskEntity } from '~/stores/taskWorkspace'
import TaskProductivityChart from '~/components/tasks/TaskProductivityChart.vue'
import { formatJalali, toPersianDigits, todayIso } from '~/utils/jalali'
import { formatHours, kpiFor, monthlyCreatedVsCompleted } from '~/utils/taskKpi'
import { printElement } from '~/utils/printElement'

const props = defineProps<{
  tasks: TaskEntity[]
  users: { id: string, name: string }[]
  projects: { id: string, name: string }[]
  assigneeNames: (t: TaskEntity) => string
  statusLabel: (status: string) => string
  dueText: (t: TaskEntity) => string
}>()
const emit = defineEmits<{ (e: 'export-excel'): void }>()

const TABS = [
  { value: 'overview', label: 'نمای کلی' },
  { value: 'employees', label: 'عملکرد کارکنان (KPI)' },
  { value: 'report', label: 'گزارش' },
] as const
const tab = ref<(typeof TABS)[number]['value']>('overview')
const months = ref(6)

const fa = (n: number) => toPersianDigits(Math.round(n))
const today = computed(() => toPersianDigits(formatJalali(todayIso())))
const live = computed(() => props.tasks.filter(t => !t.isDraft && !t.isArchived))
const total = computed(() => kpiFor(live.value))

const STATUS_ORDER = [
  { key: 'todo', label: 'انجام نشده', color: '#94a3b8' },
  { key: 'in-progress', label: 'در حال انجام', color: '#3b82f6' },
  { key: 'review', label: 'در انتظار تأیید', color: '#f59e0b' },
  { key: 'done', label: 'انجام شد', color: '#10b981' },
] as const

const overviewCards = computed(() => {
  const k = total.value
  return [
    { label: 'کل وظایف', value: fa(k.assigned), hint: 'بدون پیش‌نویس و بایگانی', tone: '' },
    { label: 'تکمیل‌شده', value: fa(k.completed), hint: `${fa(k.completionRate)}٪ از کل`, tone: 'text-success' },
    { label: 'در انتظار انجام', value: fa(k.pending), hint: 'انجام‌نشده، در حال انجام، در انتظار تأیید', tone: '' },
    { label: 'دارای تأخیر', value: fa(k.overdue), hint: 'موعد گذشته و هنوز باز', tone: k.overdue ? 'text-destructive' : '' },
    { label: 'نرخ تکمیل', value: `${fa(k.completionRate)}٪`, hint: 'تکمیل‌شده از کل وظایف', tone: 'text-primary' },
    { label: 'تکمیل به‌موقع', value: k.onTimeRate === null ? '—' : `${fa(k.onTimeRate)}٪`, hint: 'تکمیل تا پایان روز موعد', tone: '' },
    { label: 'میانگین زمان تکمیل', value: formatHours(k.avgCompletionHours), hint: 'از ایجاد تا تکمیل', tone: '' },
    { label: 'در معرض تأخیر', value: fa(live.value.filter(t => t.priority === 'urgent' && t.status !== 'done').length), hint: 'اولویت فوری و باز', tone: 'text-warning' },
  ]
})

const monthly = computed(() => monthlyCreatedVsCompleted(props.tasks, months.value))

const statusRows = computed(() => STATUS_ORDER.map(s => ({
  ...s,
  count: total.value.byStatus[s.key],
  pct: total.value.assigned ? Math.round((total.value.byStatus[s.key] / total.value.assigned) * 100) : 0,
})))
const priorityRows = computed(() => [
  { key: 'urgent', label: 'فوری', dot: 'bg-destructive' },
  { key: 'high', label: 'زیاد', dot: 'bg-primary' },
  { key: 'medium', label: 'متوسط', dot: 'bg-warning' },
  { key: 'low', label: 'کم', dot: 'bg-success' },
].map(p => ({ ...p, count: live.value.filter(t => t.priority === p.key).length })))

const departmentRows = computed(() => props.projects
  .map(p => ({ id: p.id, name: p.name, kpi: kpiFor(live.value.filter(t => t.projectId === p.id)) }))
  .filter(d => d.kpi.assigned > 0)
  .sort((a, b) => b.kpi.assigned - a.kpi.assigned))

const SORTS = [
  { value: 'assigned', label: 'بیشترین وظایف' },
  { value: 'completionRate', label: 'بالاترین نرخ تکمیل' },
  { value: 'overdue', label: 'بیشترین تأخیر' },
  { value: 'name', label: 'نام' },
] as const
const sortKey = ref<(typeof SORTS)[number]['value']>('assigned')
const employeeRows = computed(() => {
  const rows = props.users
    .map(u => ({ id: u.id, name: u.name, kpi: kpiFor(live.value.filter(t => t.assigneeIds.includes(u.id))) }))
    .filter(r => r.kpi.assigned > 0)
  const by = sortKey.value
  return rows.sort((a, b) => by === 'name' ? a.name.localeCompare(b.name, 'fa') : by === 'assigned' ? b.kpi.assigned - a.kpi.assigned : by === 'overdue' ? b.kpi.overdue - a.kpi.overdue : b.kpi.completionRate - a.kpi.completionRate)
})

const PRIORITY_FA: Record<string, string> = { low: 'کم', medium: 'متوسط', high: 'زیاد', urgent: 'فوری' }
const projectName = (id: string) => props.projects.find(p => p.id === id)?.name ?? 'عمومی'
const reportRows = computed(() => live.value.map(t => ({
  id: t.id,
  title: t.title,
  project: projectName(t.projectId),
  assignees: props.assigneeNames(t),
  status: props.statusLabel(t.status),
  priority: PRIORITY_FA[t.priority] ?? t.priority,
  due: props.dueText(t),
})))
const reportSummary = computed(() => [
  { label: 'کل', value: fa(total.value.assigned) },
  { label: 'تکمیل‌شده', value: fa(total.value.completed) },
  { label: 'دارای تأخیر', value: fa(total.value.overdue) },
  { label: 'نرخ تکمیل', value: `${fa(total.value.completionRate)}٪` },
])

const reportCard = ref<{ $el: HTMLElement } | null>(null)
const notify = useNotify()
function exportPdf() {
  notify.info('در پنجرهٔ چاپ، مقصد را «Save as PDF» انتخاب کنید.')
  printElement(reportCard.value?.$el, 'گزارش امور محوله')
}
</script>
