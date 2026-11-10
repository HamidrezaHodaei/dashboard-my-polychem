import { defineStore } from 'pinia'
import { ApiError, apiDownload, apiFetch, apiFetchPage } from '~/services/backendApi'

export interface CrmCustomerRef { id: number, name: string, province: string | null, industry: string | null }
/** A product is an entry of the CUSTOMER BANK's product list -- CRM has no product table of its own. */
export interface CrmProduct { id: number, name: string, is_active: boolean }
export interface CrmPaymentMethod { id: number, name: string, is_active: boolean, sales_count: number }

export interface CrmSale {
  id: number
  customer: CrmCustomerRef
  product: { id: number, name: string }
  payment_method: { id: number, name: string } | null
  quantity_kg: number
  unit_price: number
  amount: number
  net_amount: number
  net_quantity_kg: number
  sale_type: 'OFFICIAL' | 'UNOFFICIAL'
  document_type: 'INVOICE' | 'RETURN'
  status: 'PROCESSING' | 'COMPLETED'
  is_return: boolean
  /** Jalali, 1405/08/15 */
  date: string
  date_iso: string
  jalali_year: number
  jalali_month: number
  description: string | null
  /** who registered the sale (a fixed text) and when -- Tehran time, ISO + ready-to-show Jalali "1405/08/18 14:32" */
  created_by_name: string | null
  created_at: string | null
  created_at_display: string | null
}

export interface CrmGroupRow { id: number | null, name: string, amount: number, quantity_kg: number }
export interface CrmMonthRow { year: number, month: number, label: string, short_label: string, amount: number, quantity_kg: number, count: number }
export interface CrmAnalytics {
  filters: Record<string, string | number | null>
  kpis: {
    net_amount: number, net_quantity_kg: number, document_count: number, invoice_count: number
    return_count: number, customer_count: number, avg_invoice: number
    top_customer: CrmGroupRow | null, top_product: CrmGroupRow | null
  }
  monthly: CrmMonthRow[]
  yearly: { year: number, amount: number, quantity_kg: number, count: number }[]
  by_product: CrmGroupRow[]
  by_product_quantity: CrmGroupRow[]
  by_customer: CrmGroupRow[]
  by_sale_type: CrmGroupRow[]
  by_payment: CrmGroupRow[]
  by_province: CrmGroupRow[]
  by_industry: CrmGroupRow[]
}

export interface CrmOptions { provinces: string[], industries: string[], years: number[], presets: string[] }

export type CrmPreset = 'all' | 'this_month' | 'last_1m' | 'last_3m' | 'last_6m' | 'last_12m' | 'this_year' | 'custom'

export interface CrmFilters {
  preset: CrmPreset
  /** ISO dates (YYYY-MM-DD) straight from <JalaliDateInput>; only used when preset === 'custom'. */
  date_from: string
  date_to: string
  year: string
  month: string
  customer: CrmCustomerRef | null
  product_id: string
  payment_method_id: string
  sale_type: string
  document_type: string
  status: string
  province: string
  industry: string
  search: string
}

const defaultFilters = (): CrmFilters => ({
  preset: 'all', date_from: '', date_to: '', year: 'all', month: 'all', customer: null, product_id: 'all',
  payment_method_id: 'all', sale_type: 'all', document_type: 'all', status: 'all', province: 'all',
  industry: 'all', search: '',
})

const apiMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)
const pick = (v: string) => (v && v !== 'all' ? v : undefined)

export const useCrmStore = defineStore('crm', () => {
  const filters = reactive<CrmFilters>(defaultFilters())

  const sales = ref<CrmSale[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const sort = ref('-date')
  const salesLoading = ref(false)
  const salesError = ref('')

  const analytics = ref<CrmAnalytics | null>(null)
  const analyticsLoading = ref(false)
  const analyticsError = ref('')

  const options = ref<CrmOptions>({ provinces: [], industries: [], years: [], presets: [] })
  const products = ref<CrmProduct[]>([])
  const paymentMethods = ref<CrmPaymentMethod[]>([])

  /** The ONE place filters become a query string: the table, the KPI cards and every chart use it,
   *  so they can never disagree. Dates go out as ISO; the server parses/validates them. */
  function filterQuery(): Record<string, string | number | undefined> {
    const custom = filters.preset === 'custom'
    return {
      preset: filters.preset !== 'all' && !custom ? filters.preset : undefined,
      date_from: custom && filters.date_from ? filters.date_from : undefined,
      date_to: custom && filters.date_to ? filters.date_to : undefined,
      year: pick(filters.year),
      month: pick(filters.month),
      customer_id: filters.customer?.id,
      product_id: pick(filters.product_id),
      payment_method_id: pick(filters.payment_method_id),
      sale_type: pick(filters.sale_type),
      document_type: pick(filters.document_type),
      status: pick(filters.status),
      province: pick(filters.province),
      industry: pick(filters.industry),
      search: filters.search.trim() || undefined,
    }
  }

  /** null when OK, otherwise a message to show next to the date fields (checked before any request). */
  function validateFilters(): string | null {
    if (filters.preset === 'custom' && filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
      return 'تاریخ شروع نباید بعد از تاریخ پایان باشد.'
    }
    return null
  }

  const activeFilterCount = computed(() => {
    const q = filterQuery()
    return Object.values(q).filter(v => v !== undefined).length
  })

  let salesRequest = 0
  async function loadSales() {
    const id = ++salesRequest
    salesLoading.value = true
    salesError.value = ''
    try {
      const res = await apiFetchPage<CrmSale>('/crm/sales', {
        ...filterQuery(), page: page.value, per_page: perPage.value, sort: sort.value,
      })
      if (id !== salesRequest) return
      sales.value = res.items
      total.value = res.total
    }
    catch (err) {
      if (id !== salesRequest) return
      sales.value = []
      total.value = 0
      salesError.value = apiMessage(err, 'بارگذاری فروش‌ها ناموفق بود.')
    }
    finally {
      if (id === salesRequest) salesLoading.value = false
    }
  }

  let analyticsRequest = 0
  async function loadAnalytics() {
    const id = ++analyticsRequest
    analyticsLoading.value = true
    analyticsError.value = ''
    try {
      const data = await apiFetch<CrmAnalytics>('/crm/analytics', { query: filterQuery() })
      if (id !== analyticsRequest) return
      analytics.value = data
    }
    catch (err) {
      if (id !== analyticsRequest) return
      analytics.value = null
      analyticsError.value = apiMessage(err, 'بارگذاری آمار ناموفق بود.')
    }
    finally {
      if (id === analyticsRequest) analyticsLoading.value = false
    }
  }

  function setPage(next: number) {
    page.value = next
    return loadSales()
  }
  function resetFilters() {
    Object.assign(filters, defaultFilters())
    page.value = 1
  }

  /* ── reference data: each swallows its own failure so a filter list never blocks the page ── */
  async function loadOptions() {
    try { options.value = await apiFetch<CrmOptions>('/crm/options') }
    catch { /* keep previous */ }
  }
  async function loadCatalog(includeInactive = false) {
    try {
      const [p, m] = await Promise.all([
        apiFetch<CrmProduct[]>('/crm/products', { query: { include_inactive: includeInactive || undefined } }),
        apiFetch<CrmPaymentMethod[]>('/crm/payment-methods', { query: { include_inactive: includeInactive || undefined } }),
      ])
      products.value = p
      paymentMethods.value = m
    }
    catch { /* keep previous */ }
  }

  /** Customers come from the customer bank (GET /crm/customers reads `customers`). */
  const searchCustomers = (search: string) =>
    apiFetch<CrmCustomerRef[]>('/crm/customers', { query: { search: search || undefined, limit: 15 } })
  async function customerById(id: number) {
    const rows = await apiFetch<CrmCustomerRef[]>('/crm/customers', { query: { id } })
    return rows[0] ?? null
  }

  /* ── sales CRUD ── */
  const createSale = (body: Record<string, unknown>) => apiFetch<CrmSale>('/crm/sales', { method: 'POST', body })
  const updateSale = (id: number, body: Record<string, unknown>) =>
    apiFetch<CrmSale>(`/crm/sales/${id}`, { method: 'PATCH', body })
  const deleteSale = (id: number) => apiFetch(`/crm/sales/${id}`, { method: 'DELETE' })
  const importSales = (rows: Record<string, unknown>[], dryRun: boolean) =>
    apiFetch<{ created: number, rejected: number, errors: { row: number, customer: string, message: string }[], dry_run: boolean }>(
      '/crm/sales/import', { method: 'POST', body: { rows, dry_run: dryRun } },
    )

  /** Excel / Word of every sale matching the CURRENT filters (server checks `crm.sale.export`). */
  async function exportFile(format: 'xlsx' | 'docx') {
    await apiDownload('/crm/sales/export', { ...filterQuery(), sort: sort.value, format }, `crm-sales-${new Date().toISOString().slice(0, 10)}.${format}`)
  }

  /** Every sale matching the CURRENT filters (for print), fetched page by page. */
  async function fetchAllSales(limit = 5000): Promise<CrmSale[]> {
    const out: CrmSale[] = []
    for (let p = 1; out.length < limit; p++) {
      const res = await apiFetchPage<CrmSale>('/crm/sales', { ...filterQuery(), page: p, per_page: 100, sort: sort.value })
      out.push(...res.items)
      if (out.length >= res.total || !res.items.length) break
    }
    return out
  }

  /* ── payment-method catalogue (products are managed in the customer bank, not here) ── */
  const savePaymentMethod = (body: Record<string, unknown>, id?: number) =>
    apiFetch<CrmPaymentMethod>(id ? `/crm/payment-methods/${id}` : '/crm/payment-methods', { method: id ? 'PATCH' : 'POST', body })
  /** `force` detaches the sales that use the method (the server refuses with 409 otherwise). */
  const removePaymentMethod = (id: number, force = false) =>
    apiFetch(`/crm/payment-methods/${id}`, { method: 'DELETE', query: force ? { force: 1 } : undefined })

  return {
    filters, sales, total, page, perPage, sort, salesLoading, salesError, analytics, analyticsLoading, analyticsError,
    options, products, paymentMethods, activeFilterCount,
    filterQuery, validateFilters, loadSales, loadAnalytics, setPage, resetFilters, loadOptions, loadCatalog,
    searchCustomers, customerById, createSale, updateSale, deleteSale, importSales, fetchAllSales, exportFile,
    savePaymentMethod, removePaymentMethod,
  }
})
