<!-- Excel (SpreadsheetML .xls) import of sales. Customers are matched BY NAME against the customer
     bank on the server; rows whose customer is not in the bank are rejected (never auto-created),
     so the bank stays the single source of customers. A dry run previews before anything is saved. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle>ورود فروش از اکسل</DialogTitle>
        <DialogDescription>فایل خروجی نرم‌افزار حسابداری (XML Spreadsheet) را انتخاب کنید. مشتریان باید در بانک مشتریان ثبت شده باشند.</DialogDescription>
      </DialogHeader>

      <div class="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        <Input type="file" accept=".xls,.xml" :disabled="busy" @change="onFile" />
        <p v-if="parseError" class="text-sm text-destructive" role="alert">{{ parseError }}</p>

        <div v-if="rows.length" class="rounded-lg border p-4 text-sm">
          <p>{{ faNum(rows.length) }} ردیف در فایل خوانده شد.</p>
          <template v-if="preview">
            <p class="mt-1 text-green-700 dark:text-green-400">{{ faNum(preview.created) }} ردیف قابل ثبت است.</p>
            <p v-if="preview.rejected" class="mt-1 text-destructive">{{ faNum(preview.rejected) }} ردیف رد می‌شود:</p>
            <ul v-if="preview.errors.length" class="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs text-muted-foreground">
              <li v-for="e in preview.errors" :key="e.row" dir="auto">ردیف {{ faNum(e.row) }} — {{ e.customer }}: {{ messageFa(e.message) }}</li>
            </ul>
          </template>
        </div>
        <p v-if="resultText" class="text-sm font-medium">{{ resultText }}</p>
      </div>

      <DialogFooter class="gap-2 border-t bg-muted/30 px-6 py-4">
        <Button variant="outline" @click="emit('update:open', false)">بستن</Button>
        <Button v-if="rows.length && !preview" variant="secondary" :disabled="busy" @click="check">بررسی فایل</Button>
        <Button v-if="preview && preview.created" :disabled="busy" class="gap-2" @click="confirm">
          <Icon v-if="busy" name="lucide:loader-circle" class="size-4 animate-spin" />
          ثبت {{ faNum(preview.created) }} فروش
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { faNum } from '~/utils/crm'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [v: boolean], imported: [] }>()

const store = useCrmStore()
const rows = ref<Record<string, unknown>[]>([])
const preview = ref<Awaited<ReturnType<typeof store.importSales>> | null>(null)
const parseError = ref('')
const resultText = ref('')
const busy = ref(false)

watch(() => props.open, (v) => {
  if (v) { rows.value = []; preview.value = null; parseError.value = ''; resultText.value = '' }
})

const MESSAGES: Record<string, string> = {
  'Customer was not found in the customer bank.': 'مشتری در بانک مشتریان پیدا نشد.',
  'More than one customer in the bank has this name.': 'بیش از یک مشتری با این نام در بانک وجود دارد.',
  'Amount or unit price is required.': 'مبلغ یا فی الزامی است.',
}
const messageFa = (m: string) => MESSAGES[m] ?? m

const NS = 'urn:schemas-microsoft-com:office:spreadsheet'
const REQUIRED = ['نوع سند', 'تاريخ', 'مشتري', 'كالا/خدمت(2)', 'مقدار-اصلي', 'في به ارز پايه', 'خالص به ارز پايه']

function normalizePayment(raw: string): string | undefined {
  if (!raw) return undefined
  if (raw.includes('چک') || raw.includes('چك')) return 'چکی'
  if (raw.includes('حواله')) return 'حواله بانکی'
  if (raw.includes('اعتبار')) return 'اعتباری'
  if (raw.includes('نقد')) return 'نقدی'
  return undefined
}

function parseSpreadsheetML(xml: string): Record<string, unknown>[] {
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  const sheetRows = [...doc.getElementsByTagNameNS(NS, 'Row')]
  if (sheetRows.length < 2) throw new Error('فایل خالی است.')
  const cellsOf = (row: Element) => [...row.getElementsByTagNameNS(NS, 'Cell')].map((c) => {
    const d = c.getElementsByTagNameNS(NS, 'Data')[0]
    return (d?.textContent || '').trim()
  })
  const headers = cellsOf(sheetRows[0]!)
  const col = (name: string) => headers.indexOf(name)
  const missing = REQUIRED.filter(r => col(r) === -1)
  if (missing.length) throw new Error(`ستون‌های مورد نیاز یافت نشد: ${missing.join('، ')}`)

  const out: Record<string, unknown>[] = []
  for (const row of sheetRows.slice(1)) {
    const vals = cellsOf(row)
    const get = (name: string) => vals[col(name)] || ''
    const customer = get('مشتري')
    const date = get('تاريخ')
    if (!customer || !date) continue
    const docType = get('نوع سند')
    const isReturn = docType.includes('برگشت')
    const payment = normalizePayment(get('نوع فروش') || get('گروه مشتري'))
    out.push({
      customer,
      product: get('كالا/خدمت(2)') || 'نامشخص',
      quantity_kg: Math.abs(parseFloat(get('مقدار-اصلي')) || 0),
      unit_price: Math.abs(parseFloat(get('في به ارز پايه')) || 0),
      amount: Math.abs(parseFloat(get('خالص به ارز پايه')) || 0) || undefined,
      payment,
      date,
      document_type: isReturn ? 'RETURN' : 'INVOICE',
      status: 'COMPLETED',
      description: isReturn ? `برگشت از فروش — ${docType}` : undefined,
    })
  }
  if (!out.length) throw new Error('ردیف معتبری در فایل پیدا نشد.')
  return out
}

function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  rows.value = []
  preview.value = null
  resultText.value = ''
  parseError.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    try { rows.value = parseSpreadsheetML(String(ev.target?.result || '')) }
    catch (err) { parseError.value = err instanceof Error ? err.message : 'خواندن فایل ناموفق بود.' }
  }
  reader.readAsText(file)
}

const CHUNK = 500
async function run(dryRun: boolean) {
  busy.value = true
  try {
    let created = 0
    let rejected = 0
    const errors: { row: number, customer: string, message: string }[] = []
    for (let i = 0; i < rows.value.length; i += CHUNK) {
      const res = await store.importSales(rows.value.slice(i, i + CHUNK), dryRun)
      created += res.created
      rejected += res.rejected
      errors.push(...res.errors.map(e => ({ ...e, row: e.row + i })))
    }
    return { created, rejected, errors, dry_run: dryRun }
  }
  finally {
    busy.value = false
  }
}
async function check() {
  try { preview.value = await run(true) }
  catch (err) { parseError.value = err instanceof ApiError ? err.message : 'بررسی فایل انجام نشد.' }
}
async function confirm() {
  try {
    const res = await run(false)
    resultText.value = `${faNum(res.created)} فروش ثبت شد${res.rejected ? ` و ${faNum(res.rejected)} ردیف رد شد` : ''}.`
    preview.value = null
    rows.value = []
    emit('imported')
  }
  catch (err) { parseError.value = err instanceof ApiError ? err.message : 'ثبت انجام نشد.' }
}
</script>
