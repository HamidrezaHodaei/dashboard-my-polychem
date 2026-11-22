<!-- <PurchasesFlowReport /> : management report — on-time KPIs per priority + (for settings holders) the allowed
     delivery time per priority and the pick lists of the request form. -->
<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-end gap-3">
      <PurchasesField label="از تاریخ"><JalaliDateInput v-model="f.date_from" /></PurchasesField>
      <PurchasesField label="تا تاریخ"><JalaliDateInput v-model="f.date_to" /></PurchasesField>
      <PurchasesField label="واحد متقاضی">
        <select v-model="f.unit" class="h-9 w-44 rounded-md border border-input bg-transparent px-3 text-sm"><option value="">همه</option><option v-for="u in meta?.units" :key="u" :value="u">{{ u }}</option></select>
      </PurchasesField>
      <PurchasesField label="اولویت">
        <select v-model="f.priority" class="h-9 w-36 rounded-md border border-input bg-transparent px-3 text-sm"><option value="">همه</option><option v-for="p in meta?.priorities" :key="p.value" :value="p.value">{{ p.label }}</option></select>
      </PurchasesField>
      <Button size="sm" :disabled="loading" @click="load">اعمال فیلتر</Button>
      <Button v-if="meta?.my_permissions.read && canExport" variant="outline" size="sm" class="gap-2" @click="store.exportKpi(query())"><Icon name="lucide:download" class="size-4" />خروجی Excel</Button>
    </div>
    <p v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</p>

    <template v-if="k">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <div v-for="c in cards" :key="c.label" class="rounded-xl border p-3"><div class="text-xs text-muted-foreground">{{ c.label }}</div><div class="mt-1 text-xl font-semibold" :class="c.tone">{{ c.value }}</div></div>
      </div>

      <div class="overflow-x-auto rounded-xl border">
        <table class="w-full min-w-[760px] text-sm">
          <thead class="bg-muted/50 text-xs text-muted-foreground"><tr>
            <th class="p-3 text-right">اولویت</th><th class="p-3">زمان مجاز</th><th class="p-3">تعداد اقلام</th><th class="p-3">درخواست‌ها</th><th class="p-3">تحویل در موعد</th><th class="p-3">تحویل با تأخیر</th><th class="p-3">دارای تأخیر (باز)</th><th class="p-3">درصد تحقق</th><th class="p-3">میانگین تأخیر</th>
          </tr></thead>
          <tbody>
            <tr v-for="p in k.by_priority" :key="p.priority" class="border-t text-center">
              <td class="p-3 text-right"><PurchasesFlowBadge kind="priority" :value="p.priority" :label="String(p.label)" /></td>
              <td class="p-3">{{ allowed(String(p.priority)) }}</td><td class="p-3">{{ p.items }}</td><td class="p-3">{{ p.requests }}</td>
              <td class="p-3 text-emerald-700">{{ p.delivered_on_time }}</td><td class="p-3 text-red-600">{{ p.delivered_late }}</td><td class="p-3 text-red-600">{{ p.open_overdue }}</td>
              <td class="p-3 font-semibold">{{ pct(p.attainment_pct as number | null) }}</td><td class="p-3">{{ fmtHours(p.avg_delay_hours as number) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="space-y-2">
        <h3 class="font-semibold">وضعیت زمان‌بندی اقلام <span class="text-xs font-normal text-muted-foreground">({{ k.rows.length }} از {{ k.rows_total }})</span></h3>
        <div class="overflow-x-auto rounded-xl border">
          <table class="w-full min-w-[900px] text-sm">
            <thead class="bg-muted/50 text-xs text-muted-foreground"><tr><th class="p-2 text-right">درخواست</th><th class="p-2 text-right">کالا</th><th class="p-2">اولویت</th><th class="p-2">وضعیت کالا</th><th class="p-2">موعد تحویل</th><th class="p-2">سپری‌شده</th><th class="p-2">باقی‌مانده</th><th class="p-2">تأخیر</th><th class="p-2">نتیجه</th></tr></thead>
            <tbody>
              <tr v-for="r in k.rows" :key="r.item_id" class="cursor-pointer border-t text-center hover:bg-muted/40" @click="navigateTo(`/procurement/purchases/flow/${r.request_id}`)">
                <td class="p-2 text-right" dir="ltr">{{ r.request_no }}</td><td class="p-2 text-right">{{ r.item_name }}</td>
                <td class="p-2">{{ r.priority_label }}</td><td class="p-2">{{ r.status_label }}</td><td class="p-2 text-xs">{{ r.deadline }}</td>
                <td class="p-2">{{ fmtHours(r.elapsed_hours) }}</td><td class="p-2">{{ r.remaining_hours === null ? '—' : fmtHours(r.remaining_hours) }}</td>
                <td class="p-2" :class="r.delay_hours > 0 && 'text-red-600'">{{ r.delay_hours > 0 ? fmtHours(r.delay_hours) : '—' }}</td>
                <td class="p-2"><span class="rounded-full px-2 py-0.5 text-xs" :class="STATE[r.state].tone">{{ STATE[r.state].label }}</span></td>
              </tr>
              <tr v-if="!k.rows.length"><td colspan="9" class="p-6 text-center text-muted-foreground">موردی پیدا نشد.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- settings (system admin) -->
    <section v-if="meta?.my_permissions.settings" class="space-y-6 rounded-xl border p-5">
      <h2 class="flex items-center gap-2 text-base font-semibold"><Icon name="lucide:settings-2" class="size-5" />تنظیمات</h2>
      <div class="space-y-3">
        <h3 class="text-sm font-semibold">زمان مجاز تأمین و تحویل هر اولویت</h3>
        <div v-for="r in sla" :key="r.priority" class="flex flex-wrap items-center gap-3">
          <span class="w-24 text-sm">{{ r.label }}</span>
          <Input v-model.number="r.amount" type="number" min="1" class="w-28" />
          <select v-model="r.unit" class="h-9 rounded-md border border-input bg-transparent px-3 text-sm"><option value="DAYS">روز</option><option value="HOURS">ساعت</option></select>
        </div>
        <p v-if="slaError" class="text-sm text-destructive">{{ slaError }}</p>
        <Button size="sm" :disabled="busy" @click="saveSla">ذخیرهٔ زمان‌ها</Button>
        <p class="text-xs text-muted-foreground">مبنای محاسبه، لحظهٔ ثبت درخواست و اولویت هر کالاست.</p>
      </div>
      <div class="grid gap-6 md:grid-cols-2">
        <div v-for="kind in KINDS" :key="kind.value" class="space-y-2">
          <h3 class="text-sm font-semibold">{{ kind.label }}</h3>
          <ul class="space-y-1">
            <li v-for="o in options.filter(x => x.kind === kind.value)" :key="o.id" class="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm" :class="!o.is_active && 'opacity-50'">
              <span class="flex-1">{{ o.label }}<span v-if="o.used_count" class="mr-2 text-xs text-muted-foreground">({{ o.used_count }} استفاده)</span></span>
              <button type="button" class="text-xs text-blue-700 dark:text-blue-300" @click="rename(o)">ویرایش</button>
              <button type="button" class="text-xs" @click="act(() => store.saveOption({ is_active: !o.is_active }, o.id))">{{ o.is_active ? 'غیرفعال' : 'فعال' }}</button>
              <button v-if="!o.used_count" type="button" class="text-xs text-destructive" @click="act(() => store.deleteOption(o.id))">حذف</button>
            </li>
          </ul>
          <div class="flex gap-2"><Input v-model="newLabel[kind.value]" :placeholder="`${kind.label} جدید…`" @keyup.enter="add(kind.value)" /><Button size="sm" variant="outline" @click="add(kind.value)">افزودن</Button></div>
        </div>
      </div>
      <p v-if="optError" class="text-sm text-destructive">{{ optError }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { FlowKpi } from '~/stores/purchaseFlow'

const store = usePurchaseFlowStore()
const auth = useAuthStore()
const notify = useNotify()
const meta = computed(() => store.meta)
await store.loadMeta()
const canExport = auth.hasPermission('procurement.purchase.export')
const f = reactive({ date_from: '', date_to: '', unit: '', priority: '' })
const k = ref<FlowKpi | null>(null)
const loading = ref(false)
const error = ref('')
const query = () => ({ date_from: f.date_from || undefined, date_to: f.date_to || undefined, unit: f.unit || undefined, priority: f.priority || undefined })
const STATE: Record<string, { label: string, tone: string }> = {
  ON_TIME: { label: 'تحویل در موعد', tone: 'bg-emerald-100 text-emerald-800' }, LATE: { label: 'تحویل با تأخیر', tone: 'bg-red-100 text-red-700' },
  OVERDUE: { label: 'دارای تأخیر', tone: 'bg-red-100 text-red-700' }, OPEN: { label: 'در مهلت', tone: 'bg-blue-100 text-blue-800' },
}
const pct = (v: number | null) => (v === null || v === undefined ? '—' : `${v.toLocaleString('en-US')}٪`)
const allowed = (p: string) => { const s = k.value?.sla.find(x => x.priority === p); return s ? `${s.amount} ${s.unit_label}` : '—' }
const cards = computed(() => {
  const o = k.value?.overall
  if (!o) return []
  return [
    { label: 'تعداد اقلام', value: o.items }, { label: 'تعداد درخواست‌ها', value: o.requests },
    { label: 'تحویل در موعد', value: o.delivered_on_time, tone: 'text-emerald-700' }, { label: 'تحویل با تأخیر', value: o.delivered_late, tone: 'text-red-600' },
    { label: 'دارای تأخیر (باز)', value: o.open_overdue, tone: 'text-red-600' }, { label: 'درصد تحقق زمان‌بندی تأمین', value: pct(o.attainment_pct) },
  ]
})
async function load() {
  loading.value = true
  error.value = ''
  try { k.value = await store.kpi(query()) }
  catch (e: any) { error.value = e?.message || 'بارگذاری گزارش انجام نشد.' }
  finally { loading.value = false }
}

// settings
const sla = ref<{ priority: string, label: string, amount: number, unit: string }[]>([])
const slaError = ref('')
const busy = ref(false)
const options = ref<Awaited<ReturnType<typeof store.options>>>([])
const optError = ref('')
const newLabel = reactive<Record<string, string>>({ UNIT: '', REQUEST_TYPE: '' })
const KINDS = [{ value: 'UNIT', label: 'واحدهای متقاضی' }, { value: 'REQUEST_TYPE', label: 'انواع درخواست' }]
async function loadSettings() {
  if (!meta.value?.my_permissions.settings) return
  sla.value = (meta.value.sla ?? []).map(s => ({ ...s }))
  options.value = await store.options()
}
async function saveSla() {
  busy.value = true
  slaError.value = ''
  try { await store.saveSla(sla.value.map(s => ({ priority: s.priority, amount: Number(s.amount), unit: s.unit }))); await store.loadMeta(true); notify.success('زمان‌های مجاز ذخیره شد'); await load() }
  catch (e) { slaError.value = e instanceof ApiError ? e.message : 'ذخیره انجام نشد.' }
  finally { busy.value = false }
}
async function act(fn: () => Promise<unknown>) {
  optError.value = ''
  try { await fn(); await store.loadMeta(true); options.value = await store.options() }
  catch (e) { optError.value = e instanceof ApiError ? e.message : 'عملیات انجام نشد.' }
}
const add = (kind: string) => newLabel[kind]?.trim() && act(async () => { await store.saveOption({ kind, label: newLabel[kind] }); newLabel[kind] = '' })
const rename = (o: { id: number, label: string }) => { const v = window.prompt('عنوان جدید', o.label); if (v && v.trim() && v !== o.label) act(() => store.saveOption({ label: v }, o.id)) }

onMounted(() => { load(); loadSettings() })
</script>
