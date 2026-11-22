// Types + helpers of the item-based purchase flow (warehouse → procurement → manager → finance → delivery).
import type { PFile } from '~/utils/purchase'

export type FlowStatus = 'UNDER_REVIEW' | 'SOURCING' | 'REFERRED_FINANCE' | 'FOLLOW_UP' | 'PARTIAL_DELIVERY' | 'COMPLETED' | 'RETURNED' | 'VOID'
export type FlowItemStatus = 'PENDING' | 'INQUIRY' | 'AWAITING_APPROVAL' | 'IN_FINANCE' | 'PAID' | 'SHIPPING' | 'DELIVERED' | 'CANCELLED'
export interface FlowOpt { value: string, label: string }

export interface FlowMeta {
  units: string[]
  request_types: string[]
  categories: { id: number, name: string }[]
  request_statuses: FlowOpt[]
  item_statuses: FlowOpt[]
  priorities: FlowOpt[]
  supply_places: FlowOpt[]
  subjects: FlowOpt[]
  pay_methods: FlowOpt[]
  sla: { priority: string, label: string, amount: number, unit: 'DAYS' | 'HOURS' }[]
  my_permissions: Record<'read' | 'warehouse' | 'procure' | 'manager' | 'finance' | 'settings' | 'manage_catalog', boolean>
  today: string
}

export interface FlowTiming {
  deadline: string
  allowed: number
  allowed_unit: 'DAYS' | 'HOURS'
  elapsed_hours: number
  remaining_hours: number | null
  delay_hours: number
  delivered: boolean
  on_time: boolean | null
  overdue: boolean
}
export interface FlowQuote {
  id: number
  supplier_id: number | null
  supplier_name: string
  unit_price: number
  total_price: number
  received_date: string | null
  received_date_jalali: string | null
  validity_days: number | null
  delivery_days: number | null
  payment_method: 'CASH' | 'CHEQUE' | null
  payment_method_label: string | null
  payment_terms: string | null
  note: string | null
  file: PFile | null
  is_lowest: boolean
  is_selected: boolean
}
export interface FlowPayment {
  method: 'CASH' | 'CHEQUE'
  method_label: string
  amount: number | null
  paid_date_jalali: string | null
  payment_ref: string | null
  receipt_file: PFile | null
  cheque_file: PFile | null
  cheque_no: string | null
  cheque_amount: number | null
  cheque_issue_date_jalali: string | null
  cheque_due_date_jalali: string | null
  cheque_bank: string | null
  cheque_payee: string | null
  note: string | null
  recorded_by_name: string | null
  recorded_at: string | null
}
export interface FlowItem {
  id: number
  product_id: number | null
  product_code: string | null
  name: string
  category_id: number | null
  category_name: string
  unit: string
  quantity: number
  current_stock: number | null
  reorder_point: number | null
  request_type: string | null
  purchase_subject: string | null
  purchase_subject_label: string | null
  priority: string | null
  priority_label: string | null
  status: FlowItemStatus
  status_label: string
  status_note: string | null
  supply_place: string | null
  supply_place_label: string | null
  quotes_count: number
  approved_at: string | null
  approved_by_name: string | null
  manager_note: string | null
  paid_at: string | null
  shipped_at: string | null
  delivered_at: string | null
  has_payment: boolean
  receipt: PFile | null
  receipt_missing: boolean
  timing: FlowTiming | null
  can: Record<'set_supply_place' | 'edit_quotes' | 'submit_to_manager' | 'decide' | 'pay' | 'ship' | 'deliver' | 'upload_receipt' | 'cancel', boolean>
  quotes?: FlowQuote[]
  selected_quote_id?: number | null
  selected_total?: number | null
  payment_method?: string | null
  payment?: FlowPayment | null
}
export interface FlowEvent {
  id: number
  scope: 'ITEM' | 'REQUEST'
  item_name: string | null
  from_label: string | null
  to_label: string | null
  note: string | null
  user_name: string | null
  at: string | null
}
export interface FlowRequest {
  id: number
  request_no: string
  status: FlowStatus
  status_label: string
  status_note: string | null
  requester_unit: string
  requester_name: string
  request_date: string
  request_date_jalali: string
  required_date: string
  required_date_jalali: string
  submitted_at: string | null
  creator_name: string | null
  items_count: number
  counts: Record<FlowItemStatus, number>
  awaiting_manager: number
  in_finance: number
  missing_receipts: number
  overdue_items: number
  items: FlowItem[]
  events?: FlowEvent[]
  my_actions: Record<string, boolean>
}

export const REQUEST_TONE: Record<string, string> = {
  UNDER_REVIEW: 'bg-slate-100 text-slate-700', SOURCING: 'bg-blue-100 text-blue-800', REFERRED_FINANCE: 'bg-violet-100 text-violet-800',
  FOLLOW_UP: 'bg-amber-100 text-amber-800', PARTIAL_DELIVERY: 'bg-teal-100 text-teal-800', COMPLETED: 'bg-emerald-100 text-emerald-800',
  RETURNED: 'bg-orange-100 text-orange-800', VOID: 'bg-red-100 text-red-700',
}
export const ITEM_TONE: Record<string, string> = {
  PENDING: 'bg-slate-100 text-slate-700', INQUIRY: 'bg-blue-100 text-blue-800', AWAITING_APPROVAL: 'bg-yellow-100 text-yellow-800',
  IN_FINANCE: 'bg-violet-100 text-violet-800', PAID: 'bg-emerald-100 text-emerald-800', SHIPPING: 'bg-sky-100 text-sky-800',
  DELIVERED: 'bg-green-200 text-green-900', CANCELLED: 'bg-red-100 text-red-700',
}
export const PRIORITY_TONE: Record<string, string> = { NORMAL: 'bg-slate-100 text-slate-700', URGENT: 'bg-amber-100 text-amber-800', EMERGENCY: 'bg-red-100 text-red-700' }

/** 52 → «۲ روز و ۴ ساعت» (negative = the time is over). */
export function fmtHours(h: number | null | undefined): string {
  if (h === null || h === undefined) return '—'
  const abs = Math.abs(h)
  const d = Math.floor(abs / 24)
  const hh = Math.round(abs - d * 24)
  const text = d ? (hh ? `${d} روز و ${hh} ساعت` : `${d} روز`) : `${hh} ساعت`
  return h < 0 ? `${text} گذشته` : text
}
export const fmtMoney = (n: number | null | undefined) => (n === null || n === undefined ? '—' : `${Number(n).toLocaleString('en-US')} ریال`)
