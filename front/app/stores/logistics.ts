import { defineStore } from 'pinia'
import { ApiError, apiFetch, apiFetchBlob, apiFetchPage } from '~/services/backendApi'
import type { FileRef } from '~/utils/supplier-form'
import type { MyActions } from '~/utils/request-workflow'
import type {
  ApplicantStatus, ApplicantType, AreaType, LogisticsReference, StepKey,
} from '~/utils/logistics-form'

/** Row as returned by the list endpoint (detail sections are only on GET /applicants/:id). */
export interface LogisticsApplicant {
  id: number
  applicant_type: ApplicantType
  status: ApplicantStatus
  display_name: string
  mobile: string
  is_active: boolean
  is_public_submission: boolean
  created_by_user_id: number | null
  created_by_name: string | null
  reviewed_by_user_id: number | null
  reviewed_at: string | null
  review_note: string | null
  is_finalized: boolean
  change_request_note: string | null
  change_requested_at: string | null
  /** what the signed-in user may do with this record */
  my_actions?: MyActions
  created_at: string
  updated_at: string
  area_type: AreaType | null
  // list-level summary
  province?: string
  city?: string
  vehicle_type?: string
  body_type?: string
  capacity_tons?: number
  // detail sections
  company_info?: Record<string, any>
  representative?: Record<string, any>
  identity?: Record<string, any>
  contact?: Record<string, any>
  vehicle?: Record<string, any>
  service_area?: {
    area_type: AreaType
    coverage: { province: string, all_cities: boolean, cities: string[] }[]
    origin_countries: string[]
    destination_countries: string[]
    permits: { type: string, number: string | null, expires_at: string | null, file: FileRef | null }[]
  }
}

export type ReviewAction = 'APPROVE' | 'REJECT' | 'SUSPEND' | 'REOPEN' | 'REQUEST_EDIT'

export interface LogisticsStats {
  total: number
  by_type_status: Partial<Record<ApplicantType, Record<ApplicantStatus, number>>>
  by_area_type: Record<AreaType, number>
}

export interface LogisticsFilters {
  search: string
  applicant_type: ApplicantType | ''
  status: ApplicantStatus | ''
  area_type: AreaType | ''
  province: string
  vehicle_type: string
}

const apiMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)
const ACTIONS = ['read', 'create', 'update', 'delete', 'review'] as const
type Action = typeof ACTIONS[number]

export const useLogisticsStore = defineStore('logistics', () => {
  const applicants = ref<LogisticsApplicant[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const loading = ref(false)
  const loadError = ref('')
  const stats = ref<LogisticsStats | null>(null)
  const reference = ref<LogisticsReference | null>(null)

  const filters = reactive<LogisticsFilters>({
    search: '', applicant_type: '', status: '', area_type: '', province: '', vehicle_type: '',
  })

  /* ── access levels ──
   * The server enforces `logistics.<company|driver>.<action>` per applicant type;
   * these helpers only decide what to SHOW, from the caller's effective permissions. */
  const can = (type: ApplicantType, action: Action) =>
    useAuthStore().hasPermission(`logistics.${type === 'COMPANY' ? 'company' : 'driver'}.${action}`)
  const types = computed<ApplicantType[]>(() => (['COMPANY', 'DRIVER'] as ApplicantType[]).filter(t => can(t, 'read')))
  const typesWith = (action: Action) => (['COMPANY', 'DRIVER'] as ApplicantType[]).filter(t => can(t, action))

  // Live search fires many requests; only the newest may write its result.
  let requestId = 0

  async function load() {
    const id = ++requestId
    loading.value = true
    loadError.value = ''
    try {
      const res = await apiFetchPage<LogisticsApplicant>('/logistics/applicants', {
        page: page.value,
        per_page: perPage.value,
        search: filters.search.trim() || undefined,
        applicant_type: filters.applicant_type || undefined,
        status: filters.status || undefined,
        area_type: filters.area_type || undefined,
        province: filters.applicant_type !== 'DRIVER' ? filters.province || undefined : undefined,
        vehicle_type: filters.applicant_type !== 'COMPANY' ? filters.vehicle_type || undefined : undefined,
        include_inactive: true,
      })
      if (id !== requestId) return
      applicants.value = res.items
      total.value = res.total
    }
    catch (err) {
      if (id !== requestId) return
      loadError.value = apiMessage(err, 'بارگذاری بانک اطلاعات لجستیک انجام نشد.')
      applicants.value = []
    }
    finally {
      if (id === requestId) loading.value = false
    }
  }

  async function loadStats() {
    try {
      stats.value = await apiFetch<LogisticsStats>('/logistics/stats')
    }
    catch {
      stats.value = null
    }
  }

  /** Catalog + provinces/cities for every select in the wizard (cached after the first call). */
  async function loadReference() {
    if (reference.value) return reference.value
    reference.value = await apiFetch<LogisticsReference>('/logistics/public/reference')
    return reference.value
  }

  const fetchOne = (id: number) => apiFetch<LogisticsApplicant>(`/logistics/applicants/${id}`)

  /** Same rules the final save applies, for ONE step (+ early duplicate detection). */
  const validateStep = (applicant_type: ApplicantType, step: StepKey, data: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>('/logistics/public/validate-step', {
      method: 'POST', body: { applicant_type, step, data },
    })

  /* ── permit scans ── */
  async function uploadFile(file: File): Promise<FileRef> {
    const fd = new FormData()
    fd.append('file', file) // no Content-Type header: the browser adds the multipart boundary
    return apiFetch<FileRef>('/logistics/public/files', { method: 'POST', body: fd })
  }
  async function downloadFile(ref: FileRef) {
    const blob = await apiFetchBlob(`/logistics/files/${ref.id}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = ref.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

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
    filters.applicant_type = ''
    filters.status = ''
    filters.area_type = ''
    filters.province = ''
    filters.vehicle_type = ''
    return applyFilters()
  }

  async function createApplicant(body: Record<string, unknown>) {
    const created = await apiFetch<LogisticsApplicant>('/logistics/applicants', { method: 'POST', body })
    await Promise.all([load(), loadStats()])
    return created
  }
  async function updateApplicant(id: number, body: Record<string, unknown>) {
    const updated = await apiFetch<LogisticsApplicant>(`/logistics/applicants/${id}`, { method: 'PATCH', body })
    await load()
    return updated
  }
  async function review(id: number, action: ReviewAction, note?: string) {
    const updated = await apiFetch<LogisticsApplicant>(`/logistics/applicants/${id}/review`, {
      method: 'POST', body: { action, note: note?.trim() || null },
    })
    const i = applicants.value.findIndex(a => a.id === id)
    if (i >= 0) applicants.value[i] = { ...applicants.value[i]!, ...updated }
    await loadStats()
    return updated
  }
  /** ثبت نهایی (draft) / ثبت مجدد (after a manager sent it back) */
  async function finalize(id: number) {
    const updated = await apiFetch<LogisticsApplicant>(`/logistics/applicants/${id}/finalize`, { method: 'POST' })
    const i = applicants.value.findIndex(a => a.id === id)
    if (i >= 0) applicants.value[i] = { ...applicants.value[i]!, ...updated }
    await loadStats()
    return updated
  }
  /** the creator of a submitted record asks the manager to allow a change */
  async function requestChange(id: number, reason: string) {
    const updated = await apiFetch<LogisticsApplicant>(`/logistics/applicants/${id}/request-change`, { method: 'POST', body: { reason } })
    const i = applicants.value.findIndex(a => a.id === id)
    if (i >= 0) applicants.value[i] = { ...applicants.value[i]!, ...updated }
    return updated
  }
  async function removeApplicant(id: number) {
    await apiFetch(`/logistics/applicants/${id}`, { method: 'DELETE' })
    applicants.value = applicants.value.filter(a => a.id !== id)
    total.value = Math.max(0, total.value - 1)
    await loadStats()
  }

  return {
    applicants, total, page, perPage, loading, loadError, filters, stats, reference,
    types, can, typesWith,
    load, loadStats, loadReference, fetchOne, validateStep, uploadFile, downloadFile,
    setPage, applyFilters, resetFilters, createApplicant, updateApplicant, review, finalize, requestChange, removeApplicant,
  }
})
