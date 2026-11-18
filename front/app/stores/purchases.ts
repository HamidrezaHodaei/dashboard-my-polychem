import { defineStore } from 'pinia'
import { apiDownload, apiFetch, apiFetchBlob, apiFetchPage } from '~/services/backendApi'
import type { CatalogProduct, Dashboard, DirectPurchase, PFile, PurchaseFilters, PurchaseMeta, PurchaseRequest, PurchaseRow, StepKey } from '~/utils/purchase'

const emptyFilters = (): PurchaseFilters => ({
  date_from: '', date_to: '', category_id: '', status: '', review_status: '', supplier: '', unit: '', request_no: '', item: '', granularity: 'month',
})

export const usePurchasesStore = defineStore('purchases', () => {
  const meta = ref<PurchaseMeta | null>(null)
  const filters = reactive<PurchaseFilters>(emptyFilters())
  const dashboard = ref<Dashboard | null>(null)
  const dashLoading = ref(false)
  const dashError = ref('')
  const rows = ref<PurchaseRow[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(15)
  const sort = ref('created_at')
  const direction = ref<'asc' | 'desc'>('desc')
  const kpi = ref('') // KPI whose details the list currently shows
  const directRows = ref<DirectPurchase[]>([])
  const directTotal = ref(0)
  const directPage = ref(1)
  const directLoading = ref(false)
  const listLoading = ref(false)
  const listError = ref('')

  const can = (a: keyof PurchaseMeta['my_permissions']) => useAuthStore().hasPermission(`procurement.purchase.${a}`)

  /** Every filter, as the query the backend understands (same for list, dashboard and exports). */
  function query(): Record<string, string | undefined> {
    const f = filters
    return {
      date_from: f.date_from || undefined, date_to: f.date_to || undefined, category_id: f.category_id || undefined,
      status: f.status || undefined, review_status: f.review_status || undefined, supplier: f.supplier.trim() || undefined, unit: f.unit.trim() || undefined,
      request_no: f.request_no.trim() || undefined, item: f.item.trim() || undefined, granularity: f.granularity,
    }
  }

  async function loadMeta() {
    if (!meta.value) meta.value = await apiFetch<PurchaseMeta>('/purchases/meta')
    return meta.value
  }

  let dashSeq = 0
  async function loadDashboard() {
    const id = ++dashSeq
    dashLoading.value = true
    dashError.value = ''
    try {
      const d = await apiFetch<Dashboard>('/purchases/dashboard', { query: query() })
      if (id === dashSeq) dashboard.value = d
    }
    catch (e: any) {
      if (id === dashSeq) dashError.value = e?.message || 'بارگذاری داشبورد انجام نشد.'
    }
    finally {
      if (id === dashSeq) dashLoading.value = false
    }
  }

  let listSeq = 0
  async function loadList() {
    const id = ++listSeq
    listLoading.value = true
    listError.value = ''
    try {
      const res = await apiFetchPage<PurchaseRow>('/purchases', {
        ...query(), page: page.value, per_page: perPage.value, sort: sort.value, direction: direction.value, kpi: kpi.value || undefined,
      })
      if (id !== listSeq) return
      rows.value = res.items
      total.value = res.total
    }
    catch (e: any) {
      if (id === listSeq) { listError.value = e?.message || 'بارگذاری فهرست انجام نشد.'; rows.value = [] }
    }
    finally {
      if (id === listSeq) listLoading.value = false
    }
  }

  async function loadDirect() {
    directLoading.value = true
    try {
      const res = await apiFetchPage<DirectPurchase>('/purchases/direct', { ...query(), page: directPage.value, per_page: 15, sort: 'purchase_date', direction: 'desc' })
      directRows.value = res.items
      directTotal.value = res.total
    }
    catch { directRows.value = [] }
    finally { directLoading.value = false }
  }
  const saveDirect = (body: Record<string, unknown>, id?: number) =>
    apiFetch<DirectPurchase>(id ? `/purchases/direct/${id}` : '/purchases/direct', { method: id ? 'PUT' : 'POST', body })
  const deleteDirect = (id: number) => apiFetch(`/purchases/direct/${id}`, { method: 'DELETE' })
  const setReview = (id: number, status: string, note: string) =>
    apiFetch<PurchaseRequest>(`/purchases/${id}/review`, { method: 'POST', body: { status, note: note || null } })

  /** A filter changed: everything (KPIs, charts, groups, both tables) is refreshed from the same filters. */
  function applyFilters() {
    page.value = 1
    directPage.value = 1
    return Promise.all([loadDashboard(), loadList(), loadDirect()])
  }
  function resetFilters() {
    Object.assign(filters, emptyFilters())
    kpi.value = ''
    return applyFilters()
  }
  function setSort(col: string) {
    if (sort.value === col) direction.value = direction.value === 'asc' ? 'desc' : 'asc'
    else { sort.value = col; direction.value = 'asc' }
    page.value = 1
    return loadList()
  }
  const setPage = (p: number) => { page.value = p; return loadList() }

  const fetchOne = (id: number) => apiFetch<PurchaseRequest>(`/purchases/${id}`)
  const create = (body: Record<string, unknown>) => apiFetch<PurchaseRequest>('/purchases', { method: 'POST', body })
  const saveStep = (id: number, step: StepKey, body: Record<string, unknown>) =>
    apiFetch<PurchaseRequest>(`/purchases/${id}/${step}`, { method: 'PUT', body })
  const action = (id: number, name: 'submit' | 'cancel' | 'send-back' | 'approve-reference' | 'send-to-finance', body?: Record<string, unknown>) =>
    apiFetch<PurchaseRequest>(`/purchases/${id}/${name}`, { method: 'POST', body })
  const remove = (id: number) => apiFetch(`/purchases/${id}`, { method: 'DELETE' })
  const searchSuppliers = (q: string) => apiFetch<{ id: number, name: string, category: string | null }[]>('/purchases/suppliers', { query: { q } })

  const searchProducts = (q: string, category_id?: number | null) =>
    apiFetch<CatalogProduct[]>('/purchases/products', { query: { q: q || undefined, category_id: category_id || undefined } })
  const searchUnits = (q: string) => apiFetch<string[]>('/purchases/units', { query: { q: q || undefined } })
  /** admin catalog */
  const listProducts = (query: Record<string, string | number | undefined>) => apiFetchPage<CatalogProduct>('/purchases/products', { ...query, include_inactive: 1 })
  const saveProduct = (body: Record<string, unknown>, id?: number) =>
    apiFetch<CatalogProduct>(id ? `/purchases/products/${id}` : '/purchases/products', { method: id ? 'PATCH' : 'POST', body })
  const deleteProduct = (id: number) => apiFetch(`/purchases/products/${id}`, { method: 'DELETE' })

  async function upload(file: File): Promise<PFile> {
    const fd = new FormData()
    fd.append('file', file)
    return apiFetch<PFile>('/purchases/files', { method: 'POST', body: fd })
  }
  async function downloadFile(ref: PFile) {
    const blob = await apiFetchBlob(`/purchases/files/${ref.id}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = ref.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  /** Excel of one report (or all six sheets) with the CURRENT filters. */
  const exportExcel = (kind: string) =>
    apiDownload('/purchases/export', { ...query(), kind, format: 'xlsx' }, `purchases-${kind}-${new Date().toISOString().slice(0, 10)}.xlsx`)
  /** Rows for the print / «Save as PDF» view. */
  const exportRows = (kind: string) =>
    apiFetch<{ title: string, headers: string[], rows: (string | number | null)[][], filters: Record<string, unknown> }>(
      '/purchases/export', { query: { ...query(), kind, format: 'json' } })

  return {
    directRows, directTotal, directPage, directLoading, loadDirect, saveDirect, deleteDirect, setReview,
    meta, filters, dashboard, dashLoading, dashError, rows, total, page, perPage, sort, direction, kpi, listLoading, listError,
    can, loadMeta, loadDashboard, loadList, applyFilters, resetFilters, setSort, setPage,
    fetchOne, create, saveStep, action, remove, searchSuppliers, searchProducts, searchUnits, listProducts, saveProduct, deleteProduct, upload, downloadFile, exportExcel, exportRows,
  }
})
