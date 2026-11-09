import { defineStore } from 'pinia'
import type { MyActions, RequestReviewAction, RequestStatusKey } from '~/utils/request-workflow'
import { ApiError, apiFetch, apiFetchBlob, apiFetchPage } from '~/services/backendApi'
import type { FileRef, StoredFile } from '~/utils/supplier-form'

export type SupplierType = 'INDIVIDUAL' | 'LEGAL'
export type SupplierStatus = 'ACTIVE' | 'SEMI_ACTIVE' | 'INACTIVE'
export type SupplierQuality = 'EXCELLENT' | 'MEDIUM' | 'WEAK'

/** Flat phone list. Derived by the backend from `contacts`; kept for older records. */
export interface SupplierPhone { type: 'mobile' | 'landline', number: string }

/** One contact person. A person may have one mobile and one landline. */
export interface SupplierContact {
  first_name: string
  last_name: string
  position: string
  email: string | null
  mobile: string | null
  landline: string | null
}

export interface SupplierProduct {
  name: string
  specs?: string | null
  payment?: 'cash' | 'credit' | 'both' | null
  creditMonths?: number | null
  description?: string | null
  datasheet?: StoredFile | null
  image?: FileRef | null
}

/** A main category (parent_id === null) or a sub-category of one. */
export interface CategoryItem {
  id: number
  name: string
  parent_id: number | null
  is_active: boolean
  sort_order: number
  supplier_count: number
}

/** Public registration form: main category with its active sub-categories. */
export interface PublicCategoryNode { name: string, subcategories: string[] }

export interface Supplier {
  id: number
  supplier_type: SupplierType
  status: SupplierStatus
  quality: SupplierQuality | null
  display_name: string
  first_name: string | null
  last_name: string | null
  national_id: string | null
  /** نام برند یا مغازه — optional, individual suppliers only. */
  brand_name: string | null
  company_name: string | null
  company_national_id: string | null
  registration_number: string | null
  company_type: string | null
  established_date: string | null
  email: string | null
  website: string | null
  address: string | null
  postal_code: string | null
  category: string | null
  subcategory: string | null
  activity_type: string | null
  capacity: string | null
  experience: string | null
  contacts: SupplierContact[]
  phones: SupplierPhone[]
  products: SupplierProduct[]
  catalog_files: StoredFile[]
  /** Optional bank accounts; every field of a row may be null. */
  bank_accounts: {
    holder_name: string | null, bank_name: string | null, card_number: string | null,
    account_number: string | null, sheba: string | null
  }[]
  is_public_submission: boolean
  /** request workflow (core/request_workflow.py) */
  review_status: RequestStatusKey
  review_note: string | null
  is_finalized: boolean
  decided_at: string | null
  change_request_note: string | null
  change_requested_at: string | null
  my_actions?: MyActions
  is_active: boolean
  created_by_user_id: number | null
  created_by_name: string | null
  reviewed_by_user_id: number | null
  created_at: string
  updated_at: string
}

export interface SupplierFilters {
  search: string
  category: string
  subcategory: string
  status: SupplierStatus | ''
  quality: SupplierQuality | ''
  supplier_type: SupplierType | ''
}

const apiMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)

export const useSupplierStore = defineStore('suppliers', () => {
  const suppliers = ref<Supplier[]>([])
  const categories = ref<string[]>([])
  const categoryItems = ref<CategoryItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const loading = ref(false)
  const loadError = ref('')
  const canCreate = ref(true)
  const canUpdate = ref(true)
  const canDelete = ref(true)

  const filters = reactive<SupplierFilters>({
    search: '', category: '', subcategory: '', status: '', quality: '', supplier_type: '',
  })

  // Live search fires many requests in a row; only the newest one may write
  // its result, otherwise a slow old response could overwrite a newer one.
  let requestId = 0

  async function load() {
    const id = ++requestId
    loading.value = true
    loadError.value = ''
    try {
      const res = await apiFetchPage<Supplier>('/suppliers', {
        page: page.value,
        per_page: perPage.value,
        search: filters.search.trim() || undefined,
        category: filters.category || undefined,
        subcategory: filters.subcategory || undefined,
        status: filters.status || undefined,
        quality: filters.quality || undefined,
        supplier_type: filters.supplier_type || undefined,
        include_inactive: true,
      })
      if (id !== requestId) return
      suppliers.value = res.items
      total.value = res.total
    }
    catch (err) {
      if (id !== requestId) return
      if (err instanceof ApiError && err.status === 403) {
        canCreate.value = false
        canUpdate.value = false
        canDelete.value = false
      }
      loadError.value = apiMessage(err, 'Failed to load suppliers.')
      suppliers.value = []
    }
    finally {
      if (id === requestId) loading.value = false
    }
  }

  async function loadCategories() {
    try {
      categories.value = await apiFetch<string[]>('/suppliers/categories')
    }
    catch {
      categories.value = []
    }
  }

  /* ── admin-managed category list (Manage categories dialog) ── */
  async function loadCategoryItems() {
    categoryItems.value = await apiFetch<CategoryItem[]>('/suppliers/category-items')
  }
  /** `parentId` set → creates a sub-category under that main category. */
  const addCategory = (name: string, parentId: number | null = null) =>
    apiFetch<CategoryItem>('/suppliers/category-items', {
      method: 'POST',
      body: parentId ? { name, parent_id: parentId } : { name },
    })
  const updateCategory = (id: number, changes: Partial<Pick<CategoryItem, 'name' | 'is_active' | 'sort_order'>>) =>
    apiFetch<CategoryItem>(`/suppliers/category-items/${id}`, { method: 'PATCH', body: changes })
  const removeCategory = (id: number) =>
    apiFetch(`/suppliers/category-items/${id}`, { method: 'DELETE' })

  /** No login needed: the public registration form's select (main categories). */
  const loadPublicCategories = () => apiFetch<string[]>('/suppliers/categories/public')
  /** No login needed: main categories with their sub-categories. */
  const loadPublicCategoryTree = () => apiFetch<PublicCategoryNode[]>('/suppliers/categories/public-tree')

  /* ── files (catalog / datasheet) ── */
  async function uploadFile(file: File): Promise<FileRef> {
    const fd = new FormData()
    fd.append('file', file) // no Content-Type header: the browser adds the multipart boundary
    return apiFetch<FileRef>('/suppliers/files', { method: 'POST', body: fd })
  }
  async function uploadPublicFile(file: File): Promise<FileRef> {
    const fd = new FormData()
    fd.append('file', file)
    return apiFetch<FileRef>('/suppliers/files/public', { method: 'POST', body: fd })
  }
  // Downloads need the Authorization header, so a plain <a href> would 401.
  async function downloadFile(ref: FileRef) {
    const blob = await apiFetchBlob(`/suppliers/files/${ref.id}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = ref.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  /** Public registration form submit (no login). */
  const submitPublic = (body: Record<string, unknown>) =>
    apiFetch<Supplier>('/suppliers/public', { method: 'POST', body })

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
    filters.status = ''
    filters.quality = ''
    filters.supplier_type = ''
    return applyFilters()
  }

  async function review(id: number, changes: { status?: SupplierStatus, quality?: SupplierQuality | null }) {
    const updated = await apiFetch<Supplier>(`/suppliers/${id}`, { method: 'PATCH', body: changes })
    const i = suppliers.value.findIndex(s => s.id === id)
    if (i >= 0) suppliers.value[i] = updated
    return updated
  }

  async function updateSupplier(id: number, changes: Record<string, unknown>) {
    const updated = await apiFetch<Supplier>(`/suppliers/${id}`, { method: 'PATCH', body: changes })
    const i = suppliers.value.findIndex(s => s.id === id)
    if (i >= 0) suppliers.value[i] = updated
    return updated
  }

  /** ثبت نهایی (draft) / ثبت مجدد (after a manager sent it back) */
  async function finalizeSupplier(id: number) {
    return replace(await apiFetch<Supplier>(`/suppliers/${id}/finalize`, { method: 'POST' }))
  }
  /** the creator of a submitted request asks the manager to allow a change */
  async function requestChange(id: number, reason: string) {
    return replace(await apiFetch<Supplier>(`/suppliers/${id}/request-change`, { method: 'POST', body: { reason } }))
  }
  /** a manager decides: approve / reject / send back for edits (with a note) / reopen */
  async function decideRequest(id: number, action: RequestReviewAction, note: string) {
    return replace(await apiFetch<Supplier>(`/suppliers/${id}/review`, { method: 'POST', body: { action, note: note || null } }))
  }
  function replace(updated: Supplier) {
    const i = suppliers.value.findIndex(s => s.id === updated.id)
    if (i >= 0) suppliers.value[i] = updated
    return updated
  }

  async function createSupplier(body: Record<string, unknown>) {
    const created = await apiFetch<Supplier>('/suppliers', { method: 'POST', body })
    suppliers.value.unshift(created)
    total.value += 1
    if (created.category && !categories.value.includes(created.category)) categories.value.push(created.category)
    return created
  }

  async function removeSupplier(id: number) {
    await apiFetch(`/suppliers/${id}`, { method: 'DELETE' })
    suppliers.value = suppliers.value.filter(s => s.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  return {
    suppliers, categories, categoryItems, total, page, perPage, loading, loadError, filters,
    canCreate, canUpdate, canDelete,
    finalizeSupplier, requestChange, decideRequest,
    load, loadCategories, loadCategoryItems, addCategory, updateCategory, removeCategory,
    loadPublicCategories, loadPublicCategoryTree, uploadFile, uploadPublicFile, downloadFile, submitPublic,
    setPage, applyFilters, resetFilters,
    review, updateSupplier, createSupplier, removeSupplier,
  }
})