<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      section="مدیریت فروش و مشتریان"
      title="فروش‌ها"
      description="اسناد فروش و برگشت از فروش؛ هر سند به یک مشتری در بانک مشتریان متصل است."
      :action-label="access.canCreateSale.value ? 'ثبت فروش جدید' : undefined"
      @action="openCreate"
    />

    <CrmFilterBar show-search @apply="reload" />

    <CrmKpiCards v-if="store.analytics" :data="store.analytics" :loading="store.analyticsLoading" />

    <Card class="gap-0 overflow-hidden py-0 shadow-none">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b p-4">
        <p class="text-sm text-muted-foreground">{{ faNum(store.total) }} سند</p>
        <div class="flex flex-wrap gap-2">
          <Select v-model="store.sort" @update:model-value="reload">
            <SelectTrigger class="h-8 w-44"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="-date">جدیدترین تاریخ</SelectItem>
              <SelectItem value="date">قدیمی‌ترین تاریخ</SelectItem>
              <SelectItem value="-amount">بیشترین مبلغ</SelectItem>
              <SelectItem value="amount">کمترین مبلغ</SelectItem>
              <SelectItem value="-quantity_kg">بیشترین مقدار</SelectItem>
            </SelectContent>
          </Select>
          <ExportButtons v-if="access.canExportSale.value" :busy="exportBusy" :disabled="!store.total" @export="runExport" />
          <Button v-if="access.canPrintSale.value" variant="outline" size="sm" class="gap-2" :disabled="exporting || !store.total" @click="printReport">
            <Icon name="lucide:printer" class="size-4" /> چاپ
          </Button>
          <Button v-if="access.canCreateSale.value" variant="outline" size="sm" class="gap-2" @click="importOpen = true">
            <Icon name="lucide:file-up" class="size-4" /> ورود از اکسل
          </Button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <div v-if="store.salesLoading && !store.sales.length" class="p-8 text-center text-sm text-muted-foreground">در حال بارگذاری فروش‌ها...</div>
        <div v-else-if="store.salesError" class="p-8 text-center text-sm text-destructive">{{ store.salesError }}</div>
        <Table v-else-if="store.sales.length">
          <TableHeader>
            <TableRow>
              <TableHead>تاریخ</TableHead>
              <TableHead>مشتری</TableHead>
              <TableHead>گرید</TableHead>
              <TableHead>مقدار</TableHead>
              <TableHead>فی (ریال)</TableHead>
              <TableHead>مبلغ (ریال)</TableHead>
              <TableHead>نوع</TableHead>
              <TableHead>پرداخت</TableHead>
              <TableHead>ثبت‌کننده</TableHead>
              <TableHead class="text-right">عملیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="s in store.sales"
              :key="s.id"
              class="border-b border-slate-300/70 transition-colors odd:bg-white even:bg-slate-100 hover:bg-amber-100/70 dark:border-zinc-700 dark:odd:bg-zinc-900 dark:even:bg-zinc-800 dark:hover:bg-amber-300/15"
            >
              <TableCell class="whitespace-nowrap">{{ toPersianDigits(s.date) }}</TableCell>
              <TableCell>
                <p class="font-medium" dir="auto">{{ s.customer.name }}</p>
                <p v-if="s.customer.company" class="text-xs text-muted-foreground" dir="auto">{{ s.customer.company }}</p>
                <p v-if="s.customer.province" class="text-xs text-muted-foreground" dir="auto">{{ s.customer.province }}</p>
              </TableCell>
              <TableCell dir="auto">{{ s.product.name }}</TableCell>
              <TableCell class="whitespace-nowrap" :class="s.is_return ? 'text-destructive' : ''">{{ formatKg(s.net_quantity_kg) }}</TableCell>
              <TableCell class="whitespace-nowrap">{{ faNum(s.unit_price) }}</TableCell>
              <TableCell class="whitespace-nowrap font-medium" :class="s.is_return ? 'text-destructive' : ''">{{ faNum(s.net_amount) }}</TableCell>
              <TableCell>
                <Badge :variant="s.is_return ? 'destructive' : 'secondary'">{{ s.is_return ? 'برگشتی' : SALE_TYPE_LABELS[s.sale_type] }}</Badge>
                <p class="mt-1 text-xs text-muted-foreground">{{ SALE_STATUS_LABELS[s.status] }}</p>
              </TableCell>
              <TableCell class="text-sm">{{ s.payment_method?.name ?? '—' }}</TableCell>
              <TableCell class="text-sm">
                <p dir="auto">{{ s.created_by_name || '—' }}</p>
                <p v-if="s.created_at_display" class="whitespace-nowrap text-xs text-muted-foreground" dir="ltr">{{ toPersianDigits(s.created_at_display) }}</p>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button variant="ghost" size="icon" title="مشاهده" aria-label="مشاهده" @click="openDialog('view', s)">
                    <Icon name="lucide:eye" class="size-4" />
                  </Button>
                  <Button v-if="access.canUpdateSale.value" variant="ghost" size="icon" title="ویرایش" aria-label="ویرایش" @click="openDialog('edit', s)">
                    <Icon name="lucide:pencil" class="size-4" />
                  </Button>
                  <Button v-if="access.canDeleteSale.value" variant="ghost" size="icon" class="text-destructive" title="حذف" aria-label="حذف" @click="remove(s)">
                    <Icon name="lucide:trash-2" class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div v-else class="p-8 text-center text-sm text-muted-foreground">فروشی با این فیلترها پیدا نشد.</div>
      </div>

      <div v-if="store.total > store.perPage" class="flex items-center justify-between border-t p-4 text-sm text-muted-foreground">
        <span>صفحه {{ faNum(store.page) }} از {{ faNum(pageCount) }} &middot; مجموع {{ faNum(store.total) }} مورد</span>
        <div class="flex gap-2">
          <Button variant="outline" size="sm" :disabled="store.page <= 1 || store.salesLoading" @click="store.setPage(store.page - 1)">قبلی</Button>
          <Button variant="outline" size="sm" :disabled="store.page >= pageCount || store.salesLoading" @click="store.setPage(store.page + 1)">بعدی</Button>
        </div>
      </div>
    </Card>

    <CrmSaleDialog v-model:open="dialogOpen" :mode="dialogMode" :sale="selected" @saved="reload" />
    <CrmImportDialog v-model:open="importOpen" @imported="afterImport" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { SALE_STATUS_LABELS, SALE_TYPE_LABELS, escapeHtml, faNum, formatKg } from '~/utils/crm'
import { toPersianDigits } from '~/utils/jalali'
import type { CrmSale } from '~/stores/crm'

definePageMeta({ title: 'فروش‌ها' })

const store = useCrmStore()
const access = useCrmAccess()
const route = useRoute()
const notify = useNotify()
const { confirm } = useConfirm()

const pageCount = computed(() => Math.max(1, Math.ceil(store.total / store.perPage)))
const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit' | 'view'>('create')
const selected = ref<CrmSale | null>(null)
const importOpen = ref(false)
const exporting = ref(false)

function reload() {
  return Promise.all([store.loadSales(), store.loadAnalytics()])
}
function openCreate() {
  openDialog('create', null)
}
function openDialog(mode: 'create' | 'edit' | 'view', sale: CrmSale | null) {
  dialogMode.value = mode
  selected.value = sale
  dialogOpen.value = true
}
async function remove(s: CrmSale) {
  const ok = await confirm({
    title: 'حذف سند فروش', description: `سند ${s.customer.name} به تاریخ ${s.date} حذف شود؟`,
    confirmLabel: 'حذف', tone: 'danger',
  })
  if (!ok) return
  try {
    await store.deleteSale(s.id)
    notify.success('سند حذف شد')
    if (store.sales.length === 1 && store.page > 1) store.page -= 1
    await reload()
  }
  catch (err) {
    notify.error('حذف انجام نشد', err instanceof Error ? err.message : undefined)
  }
}
async function afterImport() {
  await Promise.all([reload(), store.loadCatalog(), store.loadOptions()])
}

/* ── export: ALL rows of the current filters (not just this page) ── */
const COLUMNS = ['تاریخ', 'مشتری', 'استان', 'گرید', 'مقدار (کیلوگرم)', 'فی (ریال)', 'مبلغ خالص (ریال)', 'نوع سند', 'نوع فروش', 'پرداخت', 'وضعیت', 'توضیحات', 'ثبت‌کننده', 'تاریخ و ساعت ثبت']
const toRow = (s: CrmSale) => [
  s.date, s.customer.label || s.customer.name, s.customer.province ?? '', s.product.name, s.net_quantity_kg, s.unit_price, s.net_amount,
  s.is_return ? 'برگشت از فروش' : 'فاکتور فروش', SALE_TYPE_LABELS[s.sale_type], s.payment_method?.name ?? '',
  SALE_STATUS_LABELS[s.status], s.description ?? '', s.created_by_name ?? '', s.created_at_display ?? '',
]
const exportBusy = ref<'' | 'xlsx' | 'docx'>('')
async function runExport(format: 'xlsx' | 'docx') {
  exportBusy.value = format
  try {
    await store.exportFile(format)
  }
  catch (err) {
    notify.error('خروجی گرفته نشد', err instanceof Error ? err.message : undefined)
  }
  finally {
    exportBusy.value = ''
  }
}
async function printReport() {
  exporting.value = true
  try {
    const rows = (await store.fetchAllSales()).map(toRow)
    const w = window.open('', '_blank')
    if (!w) { notify.warning('مرورگر پنجره چاپ را مسدود کرد'); return }
    const body = rows.map(r => `<tr>${r.map(c => `<td>${escapeHtml(typeof c === 'number' ? faNum(c) : String(c))}</td>`).join('')}</tr>`).join('')
    w.document.write(`<html dir="rtl" lang="fa"><head><meta charset="utf-8"><title>گزارش فروش</title>
      <style>body{font-family:Tahoma,sans-serif;font-size:11px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:4px 6px;text-align:right}th{background:#f3f4f6}</style></head>
      <body><h3>گزارش فروش</h3><table><thead><tr>${COLUMNS.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></body></html>`)
    w.document.close()
    w.focus()
    w.print()
  }
  catch {
    notify.error('چاپ انجام نشد')
  }
  finally {
    exporting.value = false
  }
}

onMounted(async () => {
  if (!access.canReadSales.value) return
  // Deep link from the customer bank: /crm/sales?customer_id=7
  const cid = Number(route.query.customer_id)
  if (cid > 0) {
    try { store.filters.customer = await store.customerById(cid) }
    catch { /* unknown id: ignore */ }
  }
  await Promise.all([store.loadOptions(), store.loadCatalog()])
  await reload()
})
</script>
