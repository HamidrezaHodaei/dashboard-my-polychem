// Types + helpers of the Purchase Reports module (گزارشات خرید). Nuxt auto-imports everything exported here.
import type { MyActions } from '~/utils/request-workflow'

export type PurchaseStatus = 'DRAFT' | 'ENTERING' | 'AWAITING_INQUIRY' | 'INQUIRING' | 'AWAITING_SELECTION'
  | 'PURCHASING' | 'SENT_TO_FINANCE' | 'AWAITING_DELIVERY' | 'COMPLETED' | 'CANCELLED' | 'NEEDS_REVISION'

export type ReviewStatus = 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'NEEDS_REVISION'
export interface Opt { value: string, label: string }
export interface PurchaseMeta {
  categories: { id: number, name: string }[]
  units: string[]
  requester_units: string[]
  statuses: Opt[]
  priorities: Opt[]
  review_statuses: Opt[]
  delivery_statuses: Opt[]
  reference_sources: Opt[]
  selection_reasons: Opt[]
  steps: Opt[]
  max_inquiries: number
  currency: 'IRR'
  my_permissions: Record<'read' | 'create' | 'update' | 'delete' | 'approve' | 'export' | 'manage_catalog', boolean>
}
export interface PFile { id: string, name: string, size: number }

export interface PurchaseItem {
  id?: number
  product_id: number | null
  product_code: string | null
  category_id: number | null
  category_name?: string
  name: string
  specs: string | null
  brand_model: string | null
  quantity: number | null
  unit: string
  estimated_unit_price: number | null
  estimated_total?: number | null
  reference_unit_price: number | null
  reference_source: string | null
  reference_note: string | null
  reference_item_id: number | null
  reference_approved?: boolean
  final_unit_price?: number | null
  purchased_quantity?: number | null
  final_total?: number | null
  savings?: number | null
}
export interface PurchaseInquiry {
  id: number
  supplier_id: number | null
  supplier_name: string
  received_date: string | null
  received_date_jalali: string | null
  validity_days: number | null
  delivery_days: number | null
  payment_terms: string | null
  extra_costs: number | null
  total_price: number
  lines_complete: boolean
  is_lowest: boolean
  is_selected: boolean
  note: string | null
  file: PFile | null
  lines: { item_id: number, unit_price: number }[]
}
export interface PurchaseEvent {
  id: number, kind: string, kind_label: string, step_label: string | null, from_label: string | null
  to_label: string | null, note: string | null, user_name: string | null, at: string | null
}
export interface PurchaseRequest {
  id: number
  request_no: string
  status: PurchaseStatus
  status_label: string
  status_note: string | null
  review_status: ReviewStatus
  review_label: string
  review_note: string | null
  reviewed_at: string | null
  reviewed_by_name: string | null
  pipeline_status: PurchaseStatus
  sent_to_finance_at: string | null
  current_step: number
  requester_unit: string | null
  requester_name: string | null
  request_date: string | null
  request_date_jalali: string | null
  subject: string | null
  priority: string
  priority_label: string
  reason: string | null
  description: string | null
  budget_amount: number | null
  estimated_total: number | null
  required_date: string | null
  required_date_jalali: string | null
  delivery_location: string | null
  budget_files: PFile[]
  inquiry_shortfall_reason: string | null
  inquiries_finalized: boolean
  selected_inquiry_id: number | null
  selection_reasons: string[]
  selection_reason_labels: string[]
  selection_note: string | null
  purchase_date: string | null
  final_extra_costs: number | null
  final_amount: number | null
  delivery_status: string
  delivery_label: string
  completion_note: string | null
  final_files: PFile[]
  savings: number | null
  items: (PurchaseItem & { id: number })[]
  inquiries: PurchaseInquiry[]
  events: PurchaseEvent[]
  my_actions: MyActions & Record<string, boolean>
  creator_name: string | null
  updated_at: string | null
}
export interface PurchaseRow {
  id: number, request_no: string, status: PurchaseStatus, status_label: string, priority: string, priority_label: string
  review_status: ReviewStatus, review_label: string, review_note: string | null
  requester_unit: string | null, requester_name: string | null, subject: string | null
  request_date_jalali: string | null, required_date_jalali: string | null
  budget_amount: number | null, estimated_total: number | null, final_amount: number | null, savings: number | null
  supplier_name: string | null, categories: string[], items_count: number, current_step: number
  forecast_amount?: number | null, forecast_basis?: string | null
}
export interface PurchaseFilters {
  date_from: string, date_to: string, category_id: string, status: string, review_status: string, supplier: string,
  unit: string, request_no: string, item: string, granularity: 'day' | 'week' | 'month'
}
export interface Dashboard {
  definitions: Record<string, string>
  kpis: {
    total: { value: number, cancelled: number }
    completed: { value: number }
    open: { value: number }
    spent: { value: number, requests_amount: number, direct_amount: number, extra_costs_included: boolean }
    direct: { value: number, amount: number }
    savings: { value: number | null, items_counted: number, items_total: number, items_without_reference: number }
    next_month: {
      month: string, amount: number, requests_count: number, unpriced_count: number
      from_jalali: string, to_jalali: string
      basis: Record<'selected_quote' | 'estimate' | 'budget', { count: number, amount: number }>
    }
  }
  status_counts: { status: string, label: string, count: number }[]
  review_counts: { status: ReviewStatus, label: string, count: number }[]
  groups: { category_id: number | null, name: string, inactive: boolean, requests: number, completed: number, open: number, spent: number, requests_spent: number, direct_count: number, direct_spent: number, savings: number | null, savings_items: number }[]
  trend: { label: string, requests: number, spent: number, estimated: number, final: number, direct_spent: number, savings: number | null }[]
  suppliers: { supplier_id: number | null, name: string, inquiries: number, selected: number, cheapest: number, compared: number, awarded: number, win_rate: number | null, cheapest_rate: number | null, avg_delivery_days: number | null, direct_count: number, direct_amount: number }[]
}

/** Every price in the module is in Iranian rial: 1500000000 -> «1,500,000,000 ریال» ('—' for no value).
 *  Only the display is formatted; the number sent to / stored by the backend is the plain value. */
export const money = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : `${Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })} ریال`
/** the same without the unit, for a column whose header already says ریال */
export const rialNumber = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
export const count = (v: number | null | undefined) => (v === null || v === undefined ? '—' : Number(v).toLocaleString('fa-IR'))

export const statusTone: Record<PurchaseStatus, string> = {
  DRAFT: 'bg-muted text-muted-foreground',
  ENTERING: 'bg-sky-100 text-sky-800',
  AWAITING_INQUIRY: 'bg-amber-100 text-amber-800',
  INQUIRING: 'bg-amber-100 text-amber-800',
  AWAITING_SELECTION: 'bg-orange-100 text-orange-800',
  PURCHASING: 'bg-indigo-100 text-indigo-800',
  SENT_TO_FINANCE: 'bg-cyan-100 text-cyan-800',
  AWAITING_DELIVERY: 'bg-violet-100 text-violet-800',
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  CANCELLED: 'bg-rose-100 text-rose-800',
  NEEDS_REVISION: 'bg-red-100 text-red-800',
}

export const WIZARD_STEPS = [
  { key: 'basic', title: 'اطلاعات اولیه' },
  { key: 'items', title: 'اقلام کالا' },
  { key: 'budget', title: 'بودجه و برآورد' },
  { key: 'inquiries', title: 'استعلام قیمت' },
  { key: 'selection', title: 'انتخاب تأمین‌کننده' },
  { key: 'result', title: 'نتیجه خرید' },
] as const
export type StepKey = typeof WIZARD_STEPS[number]['key']

/** `{ 'items.0.name': 'message' }` from an ApiError's `details` (backend field paths). */
export function fieldErrors(details: unknown): Record<string, string> {
  const out: Record<string, string> = {}
  if (Array.isArray(details)) {
    for (const d of details as { field?: string, message?: string }[]) {
      if (d?.field && d.message && !out[d.field]) out[d.field] = d.message
    }
  }
  return out
}

/** Life-cycle shown by the stepper (right to left). `stageOf` says which one a status belongs to. */
export const LIFECYCLE = [
  { key: 'entry', label: 'ثبت اطلاعات' },
  { key: 'inquiry', label: 'در حال استعلام' },
  { key: 'selection', label: 'انتخاب تأمین‌کننده' },
  { key: 'purchase', label: 'انجام خرید' },
  { key: 'finance', label: 'ارسال به مالی' },
  { key: 'delivery', label: 'در حال تحویل و حمل' },
  { key: 'done', label: 'پایان‌یافته' },
] as const

export function stageOf(status: PurchaseStatus): number {
  switch (status) {
    case 'AWAITING_INQUIRY': case 'INQUIRING': return 1
    case 'AWAITING_SELECTION': return 2
    case 'PURCHASING': return 3
    case 'SENT_TO_FINANCE': return 4
    case 'AWAITING_DELIVERY': return 5
    case 'COMPLETED': return 6
    default: return 0 // DRAFT, ENTERING (cancelled / revision use the request's pipeline_status instead)
  }
}

export interface CatalogProduct { id: number, name: string, code: string | null, category_id: number | null, category_name: string | null, is_active: boolean, used_count?: number }

export const reviewTone: Record<ReviewStatus, string> = {
  PENDING_REVIEW: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-emerald-100 text-emerald-800',
  REJECTED: 'bg-rose-100 text-rose-800',
  NEEDS_REVISION: 'bg-orange-100 text-orange-800',
}

export interface DirectPurchase {
  id: number, doc_no: string, purchase_date: string, purchase_date_jalali: string, title: string, description: string | null
  category_id: number | null, category_name: string | null, supplier_id: number | null, supplier_name: string
  amount: number, usage_place: string, creator_name: string | null
}
