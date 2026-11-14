// Request Sample (CRM) store: the list (filters / paging / sort), the dashboard analytics and every
// workflow call. The backend (services.py) enforces all permissions; `can*` only hides controls.
import { ApiError, apiDownload, apiFetch, apiFetchBlob, apiFetchPage } from '~/services/backendApi'
import type { SampleAnalytics, SampleDetail, SampleFile, SampleItem, SampleRow } from '~/utils/requestSample'

export interface SampleFilters {
  search: string
  statuses: string[]
  priority: string
  customer_id: number | null
  customer_name: string
  product: string
  grade: string
  rep_id: string
  feedback: string
  date_from: string
  date_to: string
  followup_overdue: boolean
  mine: boolean
}
const defaults = (): SampleFilters => ({
  search: '', statuses: [], priority: 'all', customer_id: null, customer_name: '', product: 'all', grade: 'all',
  rep_id: 'all', feedback: 'all', date_from: '', date_to: '', followup_overdue: false, mine: false,
})
const pick = (v: string) => (v && v !== 'all' ? v : undefined)

/** the editable shape of a request (same as the API's create / update body) */
export interface SamplePayload {
  customer_id: number
  sales_rep_user_id: number | null
  priority: string
  dispatch_ref_number: string | null
  required_delivery_date: string | null
  purpose: string | null
  technical_requirements: string | null
  delivery_method: string | null
  recipient_name: string | null
  delivery_address: string | null
  country: string | null
  city: string | null
  postal_code: string | null
  delivery_instructions: string | null
  internal_notes: string | null
  items: SampleItem[]
  file_ids: string[]
}

export const useRequestSampleStore = defineStore('requestSample', () => {
  const auth = useAuthStore()
  const has = (k: string) => computed(() => auth.hasPermission(`crm.request_sample.${k}`))
  const canRead = has('read')
  const canCreate = has('create')
  const canExport = has('export')

  const filters = reactive<SampleFilters>(defaults())
  const rows = ref<SampleRow[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(15)
  const sort = ref('-id')
  const loading = ref(false)
  const error = ref('')

  const analytics = ref<SampleAnalytics | null>(null)
  const analyticsLoading = ref(false)
  const granularity = ref<'day' | 'week' | 'month'>('month')
  const options = ref<{ reps: { id: number, name: string }[], products: string[], grades: string[] }>({ reps: [], products: [], grades: [] })

  function query(): Record<string, string | number | boolean | undefined> {
    return {
      search: filters.search.trim() || undefined,
      status: filters.statuses.length ? filters.statuses.join(',') : undefined,
      priority: pick(filters.priority),
      customer_id: filters.customer_id ?? undefined,
      product: pick(filters.product),
      grade: pick(filters.grade),
      rep_id: pick(filters.rep_id),
      feedback: pick(filters.feedback),
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      followup_overdue: filters.followup_overdue || undefined,
      mine: filters.mine || undefined,
    }
  }

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const res = await apiFetchPage<SampleRow>('/crm/request-samples', {
        ...query(), page: page.value, per_page: perPage.value, sort: sort.value,
      })
      rows.value = res.items
      total.value = res.total
    }
    catch (e) {
      error.value = e instanceof ApiError ? e.message : 'دریافت درخواست‌ها انجام نشد.'
    }
    finally {
      loading.value = false
    }
  }
  async function loadAnalytics() {
    analyticsLoading.value = true
    try {
      analytics.value = await apiFetch<SampleAnalytics>('/crm/request-samples/analytics', {
        query: { ...query(), granularity: granularity.value },
      })
    }
    catch {
      analytics.value = null
    }
    finally {
      analyticsLoading.value = false
    }
  }
  const loadOptions = async () => { options.value = await apiFetch('/crm/request-samples/options') }
  const loadReps = () => apiFetch<{ id: number, name: string }[]>('/crm/request-samples/reps')

  /** any filter change: back to page 1 and refresh the table AND the dashboard together */
  async function apply() {
    page.value = 1
    await Promise.all([load(), loadAnalytics()])
  }
  function setPage(p: number) {
    page.value = p
    load()
  }
  function setSort(key: string) {
    sort.value = sort.value === key ? `-${key}` : key
    page.value = 1
    load()
  }
  function reset() {
    Object.assign(filters, defaults())
    return apply()
  }
  function setStatus(status: string | null) {
    filters.statuses = status ? [status] : []
    return apply()
  }

  /* ── one request + workflow ── */
  const base = '/crm/request-samples'
  const get = (id: number) => apiFetch<SampleDetail>(`${base}/${id}`)
  const create = (body: SamplePayload) => apiFetch<SampleDetail>(base, { method: 'POST', body })
  const update = (id: number, body: SamplePayload) => apiFetch<SampleDetail>(`${base}/${id}`, { method: 'PUT', body })
  const remove = (id: number) => apiFetch(`${base}/${id}`, { method: 'DELETE' })
  const transition = (id: number, action: string, note?: string) =>
    apiFetch<SampleDetail>(`${base}/${id}/transition`, { method: 'POST', body: { action, note: note || null } })
  const newRequestFrom = (id: number) => apiFetch<SampleDetail>(`${base}/${id}/new-request`, { method: 'POST' })
  const addDispatch = (id: number, body: Record<string, unknown>) => apiFetch<SampleDetail>(`${base}/${id}/dispatches`, { method: 'POST', body })
  const confirmDelivery = (id: number, body: Record<string, unknown>) => apiFetch<SampleDetail>(`${base}/${id}/delivery`, { method: 'POST', body })
  const deleteDispatch = (id: number, did: number) => apiFetch<SampleDetail>(`${base}/${id}/dispatches/${did}`, { method: 'DELETE' })
  const addFollowUp = (id: number, body: Record<string, unknown>) => apiFetch<SampleDetail>(`${base}/${id}/followups`, { method: 'POST', body })
  const updateFollowUp = (id: number, fid: number, body: Record<string, unknown>) => apiFetch<SampleDetail>(`${base}/${id}/followups/${fid}`, { method: 'PUT', body })
  const deleteFollowUp = (id: number, fid: number) => apiFetch<SampleDetail>(`${base}/${id}/followups/${fid}`, { method: 'DELETE' })
  const setFeedback = (id: number, body: Record<string, unknown>) => apiFetch<SampleDetail>(`${base}/${id}/feedback`, { method: 'PUT', body })
  const convert = (id: number, note: string, sale_id: number | null) =>
    apiFetch<SampleDetail>(`${base}/${id}/convert`, { method: 'POST', body: { note: note || null, sale_id } })

  /* ── files ── */
  async function uploadFile(file: File, kind: string, requestId?: number): Promise<SampleFile> {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('kind', kind)
    return apiFetch<SampleFile>(requestId ? `${base}/${requestId}/files` : `${base}/files`, { method: 'POST', body: fd })
  }
  const deleteFile = (id: string) => apiFetch(`${base}/files/${id}`, { method: 'DELETE' })
  async function downloadFile(f: Pick<SampleFile, 'id' | 'name'>) {
    const blob = await apiFetchBlob(`${base}/files/${f.id}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = f.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }
  const fetchCustomer = (id: number) => apiFetch<Record<string, any>>(`/customers/${id}`)

  async function exportFile(format: 'xlsx' | 'docx') {
    await apiDownload(`${base}/export`, { ...query(), format }, `request-samples-${new Date().toISOString().slice(0, 10)}.${format}`)
  }

  return {
    filters, rows, total, page, perPage, sort, loading, error, analytics, analyticsLoading, granularity, options,
    canRead, canCreate, canExport,
    load, loadAnalytics, loadOptions, loadReps, apply, setPage, setSort, reset, setStatus,
    get, create, update, remove, transition, newRequestFrom, addDispatch, confirmDelivery, deleteDispatch, addFollowUp, updateFollowUp,
    deleteFollowUp, setFeedback, convert, uploadFile, deleteFile, downloadFile, fetchCustomer, exportFile,
  }
})
