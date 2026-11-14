import { defineStore } from 'pinia'
import type { MyActions, RequestReviewAction, RequestStatusKey } from '~/utils/request-workflow'
import { ApiError, apiDownload, apiFetch, apiFetchPage } from '~/services/backendApi'

export type CustomerType = 'INDIVIDUAL' | 'LEGAL'
export type CommercialStatus
  = | 'NO_ACTION' | 'MARKETING_NEGOTIATION' | 'SAMPLE_SENT' | 'AWAITING_SAMPLE_APPROVAL' | 'SALES_NEGOTIATION'
    | 'ACQUIRED' | 'REPEAT_ACTIVE' | 'INACTIVE_LOST' | 'POTENTIAL'
export type OperationalStatus = 'ACTIVE' | 'INACTIVE'
export type ActivityType = 'PRODUCER' | 'DISTRIBUTOR' | 'EXPORTER'
export type PurchaseMethod = 'OFFICIAL' | 'UNOFFICIAL' | 'BOTH'
export type AcquaintanceSource
  = | 'WEBSITE' | 'GOOGLE_SEARCH' | 'SOCIAL_MEDIA' | 'EXHIBITION' | 'CUSTOMER_REFERRAL' | 'PARTNER_REFERRAL'
    | 'INBOUND_CALL' | 'OUTBOUND_CALL' | 'FIELD_MARKETING' | 'TELEMARKETING' | 'EMAIL_CAMPAIGN' | 'MESSENGERS'
    | 'COMPANY_DATABASE' | 'PREVIOUS_CONNECTIONS' | 'OTHER'
export type PaymentType = 'CASH' | 'CREDIT' | 'CASH_CREDIT'
export type CreditRating = 'EXCELLENT' | 'GOOD' | 'AVERAGE' | 'WEAK' | 'BAD_DEBTOR' | 'NO_HISTORY' | 'NEEDS_REVIEW'
/** Unit of every produced / consumed amount (whole numbers). Default: TON. */
export type QuantityUnit = 'TON' | 'KG'
/** PRODUCED / CONSUMED are two independent pick-lists (produced vs consumed products); PRODUCT is the legacy shared one */
export type OptionKind = 'PRODUCED' | 'CONSUMED' | 'GRADE' | 'PRODUCT'

export interface OptionItem {
  id: number
  kind: OptionKind
  name: string
  is_active: boolean
  sort_order: number
}

export interface CustomerContact {
  first_name: string
  last_name: string
  position: string
  email: string | null
  mobile: string | null
  landline: string | null
  birth_date: string | null
}
/** Production is always PER YEAR. */
export interface ProducedProduct { name: string, amount: number | null, unit: QuantityUnit }
export interface ConsumedProduct {
  name: string
  grade_specs: string | null
  monthly_consumption: number
  annual_consumption: number
  unit: QuantityUnit
}
export interface SupplierGrade { product: string, grade: string | null }
export interface CurrentSupplier { name: string | null, supplier_id: number | null, grades?: SupplierGrade[] }
export interface ContactLogEntry { date: string, note: string | null }
export interface Industry { category: string, subcategory: string | null }

/** A main industry (parent_id === null) or a sub-category of one. */
export interface CategoryItem {
  id: number
  name: string
  parent_id: number | null
  is_active: boolean
  sort_order: number
  customer_count: number
}

export interface Option { value: string, label: string }
export interface CustomerOptions {
  customer_types: Option[]
  commercial_statuses: Option[]
  operational_statuses: Option[]
  activity_types: Option[]
  purchase_methods: Option[]
  payment_types: Option[]
  credit_months: number[]
  acquaintance_sources: Option[]
  credit_ratings: (Option & { description?: string })[]
  /** TON / KG */
  quantity_units: Option[]
  /** Fixed list for the contact "position" select (the panel adds "سایر" itself). */
  contact_positions: string[]
  /** Step 5 (commercial terms) applies to customers in these stages. */
  commercial_terms_statuses: CommercialStatus[]
}
export interface CustomerStats {
  total: number
  by_commercial_status: Record<string, number>
  by_operational_status: Record<string, number>
  follow_up_due: number
  unassigned: number
  not_finalized: number
  pending_review: number
}
export interface LocationNode { province: string, count: number, cities: { city: string, count: number }[] }
export interface AssignableUser { id: number, full_name: string }

export interface Customer {
  id: number
  display_name: string
  customer_type: CustomerType
  first_name: string | null
  last_name: string | null
  national_id: string | null
  /** نام شرکت یا برند -- individual customers only */
  brand_name: string | null
  company_name: string | null
  company_national_id: string | null
  registration_number: string | null
  economic_id: string | null
  activity_start_date: string | null
  contacts: CustomerContact[]
  head_office_address: string | null
  head_office_postal_code: string | null
  factory_address: string | null
  factory_postal_code: string | null
  acquaintance_source: AcquaintanceSource | null
  acquaintance_source_other: string | null
  industries: Industry[]
  /** first industry (kept for older clients) */
  category: string | null
  subcategory: string | null
  activity_types: ActivityType[]
  produced_products: ProducedProduct[]
  production_lines_count: number | null
  production_line_names: string[]
  /** units per line, parallel to production_line_names; production_lines_count is their sum */
  production_line_counts: number[]
  /** the company's own phone (legal customers) */
  company_phone: string | null
  /** tons per year: the sum of produced_products (computed by the server) */
  production_capacity: number | null
  factory_province: string | null
  factory_city: string | null
  factory_location: string | null
  latitude: number | null
  longitude: number | null
  consumed_products: ConsumedProduct[]
  current_suppliers: CurrentSupplier[]
  commercial_status: CommercialStatus
  operational_status: OperationalStatus
  contact_log: ContactLogEntry[]
  first_contact_date: string | null
  first_purchase_date: string | null
  last_purchase_date: string | null
  assigned_to_user_id: number | null
  assigned_to_name: string | null
  inactive_reason: string | null
  payment_type: PaymentType | null
  credit_months: number | null
  credit_other: string | null
  payment_terms: string | null
  purchase_method: PurchaseMethod | null
  delivery_type: string | null
  unloading_location: string | null
  approved_credit_limit: number | null
  credit_rating: CreditRating | null
  internal_notes: string | null
  last_negotiation_date: string | null
  last_negotiation_result: string | null
  next_action: string | null
  next_follow_up_date: string | null
  registration_date: string | null
  is_finalized: boolean
  finalized_at: string | null
  finalized_by_user_id: number | null
  /** request-review workflow (shared with suppliers / logistics) */
  review_status: RequestStatusKey
  review_note: string | null
  decided_at: string | null
  change_request_note: string | null
  change_requested_at: string | null
  my_actions?: MyActions
  is_active: boolean
  created_by_user_id: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface CustomerFilters {
  search: string
  category: string
  subcategory: string
  commercial_status: CommercialStatus | ''
  operational_status: OperationalStatus | ''
  customer_type: CustomerType | ''
  province: string
  city: string
  activity_type: ActivityType | ''
  credit_rating: CreditRating | ''
  /** request-review status ('' = all) */
  review_status: RequestStatusKey | ''
  assigned_to: string // '' | 'none' | user id
  follow_up_due: boolean
  /** '-created_at' (default, newest first) | 'category' | '-category' (by industry) | 'next_follow_up_date' ... */
  sort: string
}

const DEFAULT_SORT = '-created_at'
const apiMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)

export const useCustomerStore = defineStore('customers', () => {
  const customers = ref<Customer[]>([])
  const categories = ref<string[]>([])
  const categoryItems = ref<CategoryItem[]>([])
  const optionItems = ref<OptionItem[]>([])
  const options = ref<CustomerOptions | null>(null)
  const stats = ref<CustomerStats | null>(null)
  const locations = ref<LocationNode[]>([])
  const assignees = ref<AssignableUser[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const loading = ref(false)
  const loadError = ref('')
  // Derived from the signed-in user's real crm.customer.* permissions (the backend enforces the
  // same keys on every route) -- not from "did the last request 403".
  const auth = useAuthStore()
  const canCreate = computed(() => auth.hasPermission('crm.customer.create'))
  const canUpdate = computed(() => auth.hasPermission('crm.customer.update'))
  const canDelete = computed(() => auth.hasPermission('crm.customer.delete'))
  const canExport = computed(() => auth.hasPermission('crm.customer.export'))

  const filters = reactive<CustomerFilters>({
    search: '', category: '', subcategory: '', commercial_status: '', operational_status: '',
    customer_type: '', province: '', city: '', activity_type: '', credit_rating: '', assigned_to: '', review_status: '',
    follow_up_due: false, sort: DEFAULT_SORT,
  })

  // Live search fires many requests in a row; only the newest may write its result.
  let requestId = 0

  async function load() {
    const id = ++requestId
    loading.value = true
    loadError.value = ''
    try {
      const res = await apiFetchPage<Customer>('/customers', {
        page: page.value,
        per_page: perPage.value,
        search: filters.search.trim() || undefined,
        category: filters.category || undefined,
        subcategory: filters.subcategory || undefined,
        commercial_status: filters.commercial_status || undefined,
        operational_status: filters.operational_status || undefined,
        customer_type: filters.customer_type || undefined,
        province: filters.province || undefined,
        city: filters.city || undefined,
        activity_type: filters.activity_type || undefined,
        credit_rating: filters.credit_rating || undefined,
        review_status: filters.review_status || undefined,
        assigned_to: filters.assigned_to || undefined,
        follow_up_due: filters.follow_up_due || undefined,
        sort: filters.sort || DEFAULT_SORT,
        include_inactive: true,
      })
      if (id !== requestId) return
      customers.value = res.items
      total.value = res.total
    }
    catch (err) {
      if (id !== requestId) return
      loadError.value = apiMessage(err, 'Failed to load customers.')
      customers.value = []
    }
    finally {
      if (id === requestId) loading.value = false
    }
  }

  /* ── reference data (each swallows its own failure: a filter list must never block the page) ── */
  async function loadOptions() {
    try { options.value = await apiFetch<CustomerOptions>('/customers/options') }
    catch { /* keep previous */ }
  }
  async function loadStats() {
    try { stats.value = await apiFetch<CustomerStats>('/customers/stats') }
    catch { stats.value = null }
  }
  async function loadLocations() {
    try { locations.value = await apiFetch<LocationNode[]>('/customers/locations') }
    catch { locations.value = [] }
  }
  async function loadAssignees() {
    try { assignees.value = await apiFetch<AssignableUser[]>('/customers/assignable-users') }
    catch { assignees.value = [] }
  }
  async function loadCategories() {
    try { categories.value = await apiFetch<string[]>('/customers/categories') }
    catch { categories.value = [] }
  }

  /* ── admin-managed industry list (Manage categories dialog) ── */
  async function loadCategoryItems() {
    categoryItems.value = await apiFetch<CategoryItem[]>('/customers/category-items')
  }
  /** `forSamples` → read the lists through the request-sample permission (CONSUMED + GRADE only). */
  async function loadOptionItems(forSamples = false) {
    try { optionItems.value = await apiFetch<OptionItem[]>(forSamples ? '/crm/request-samples/option-items' : '/customers/option-items') }
    catch { optionItems.value = [] }
  }
  /** Rename / hide / reorder a product or grade name. A rename is also applied to existing customers by the server. */
  async function updateOptionItem(id: number, changes: Partial<Pick<OptionItem, 'name' | 'is_active' | 'sort_order'>>) {
    const updated = await apiFetch<OptionItem>(`/customers/option-items/${id}`, { method: 'PATCH', body: changes })
    const i = optionItems.value.findIndex(o => o.id === id)
    if (i >= 0) optionItems.value[i] = updated
    return updated
  }
  /** Removes the name from the pick-list only; customers already using it keep their value. */
  async function removeOptionItem(id: number) {
    await apiFetch(`/customers/option-items/${id}`, { method: 'DELETE' })
    optionItems.value = optionItems.value.filter(o => o.id !== id)
  }
  async function addOptionItem(kind: OptionKind, name: string) {
    const created = await apiFetch<OptionItem>('/customers/option-items', { method: 'POST', body: { kind, name } })
    optionItems.value.push(created)
    return created
  }
  /** `parentId` set → creates a sub-category under that main industry. */
  const addCategory = (name: string, parentId: number | null = null) =>
    apiFetch<CategoryItem>('/customers/category-items', {
      method: 'POST',
      body: parentId ? { name, parent_id: parentId } : { name },
    })
  const updateCategory = (id: number, changes: Partial<Pick<CategoryItem, 'name' | 'is_active' | 'sort_order'>>) =>
    apiFetch<CategoryItem>(`/customers/category-items/${id}`, { method: 'PATCH', body: changes })
  const removeCategory = (id: number) =>
    apiFetch(`/customers/category-items/${id}`, { method: 'DELETE' })

  function setPage(next: number) {
    page.value = next
    return load()
  }
  function applyFilters() {
    page.value = 1
    return load()
  }
  function resetFilters() {
    filters.search = ''
    filters.category = ''
    filters.subcategory = ''
    filters.commercial_status = ''
    filters.operational_status = ''
    filters.customer_type = ''
    filters.province = ''
    filters.city = ''
    filters.activity_type = ''
    filters.credit_rating = ''
    filters.review_status = ''
    filters.assigned_to = ''
    filters.follow_up_due = false
    filters.sort = DEFAULT_SORT
    return applyFilters()
  }

  function replaceInList(updated: Customer) {
    const i = customers.value.findIndex(c => c.id === updated.id)
    if (i >= 0) customers.value[i] = updated
  }

  async function updateCustomer(id: number, changes: Record<string, unknown>) {
    const updated = await apiFetch<Customer>(`/customers/${id}`, { method: 'PATCH', body: changes })
    replaceInList(updated)
    return updated
  }
  const setCommercialStatus = (id: number, commercial_status: CommercialStatus) =>
    updateCustomer(id, { commercial_status })

  async function createCustomer(body: Record<string, unknown>) {
    const created = await apiFetch<Customer>('/customers', { method: 'POST', body })
    customers.value.unshift(created)
    total.value += 1
    return created
  }
  async function finalizeCustomer(id: number) {
    const updated = await apiFetch<Customer>(`/customers/${id}/finalize`, { method: 'POST' })
    replaceInList(updated)
    return updated
  }
  /** the creator of a submitted request asks the manager to allow a change */
  async function requestChange(id: number, reason: string) {
    const updated = await apiFetch<Customer>(`/customers/${id}/request-change`, { method: 'POST', body: { reason } })
    replaceInList(updated)
    return updated
  }
  /** a manager decides: approve / reject / send back for edits (with a note) / reopen */
  async function decideRequest(id: number, action: RequestReviewAction, note: string) {
    const updated = await apiFetch<Customer>(`/customers/${id}/review`, { method: 'POST', body: { action, note: note || null } })
    replaceInList(updated)
    return updated
  }
  /** one file by id (e.g. when a notification points at a customer that is not on the current page) */
  const fetchOne = (id: number) => apiFetch<Customer>(`/customers/${id}`)
  /** Excel / Word of every customer matching the CURRENT filters (server checks `crm.customer.export`). */
  async function exportFile(format: 'xlsx' | 'docx') {
    await apiDownload('/customers/export', {
      format,
      search: filters.search.trim() || undefined,
      category: filters.category || undefined,
      subcategory: filters.subcategory || undefined,
      commercial_status: filters.commercial_status || undefined,
      operational_status: filters.operational_status || undefined,
      customer_type: filters.customer_type || undefined,
      province: filters.province || undefined,
      city: filters.city || undefined,
      activity_type: filters.activity_type || undefined,
      credit_rating: filters.credit_rating || undefined,
      review_status: filters.review_status || undefined,
      assigned_to: filters.assigned_to || undefined,
      follow_up_due: filters.follow_up_due || undefined,
      sort: filters.sort || DEFAULT_SORT,
      include_inactive: true,
    }, `customers-${new Date().toISOString().slice(0, 10)}.${format}`)
  }
  async function removeCustomer(id: number) {
    await apiFetch(`/customers/${id}`, { method: 'DELETE' })
    customers.value = customers.value.filter(c => c.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  return {
    customers, categories, categoryItems, optionItems, options, stats, locations, assignees,
    total, page, perPage, loading, loadError, filters, canCreate, canUpdate, canDelete, canExport, exportFile,
    load, loadOptions, loadStats, loadLocations, loadAssignees, loadCategories, loadCategoryItems,
    loadOptionItems, addOptionItem, updateOptionItem, removeOptionItem,
    addCategory, updateCategory, removeCategory,
    setPage, applyFilters, resetFilters,
    updateCustomer, setCommercialStatus, createCustomer, finalizeCustomer, requestChange, decideRequest, fetchOne, removeCustomer,
  }
})