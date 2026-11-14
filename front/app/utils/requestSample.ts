// Shared constants / types of the Request Sample (درخواست نمونه محصول) module.
export type SampleStatus =
  | 'DRAFT' | 'NEW_REQUEST' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'ON_HOLD'
  | 'DISPATCHED' | 'AWAITING_FEEDBACK' | 'COMPLETED' | 'CONVERTED' | 'CANCELLED'
export type SamplePriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT'
export type FeedbackStatus = 'ACCEPTED' | 'REJECTED' | 'ACCEPTED_WITH_CONDITIONS' | 'UNDER_EVALUATION' | 'NO_RESPONSE'
export type FollowUpMethod = 'PHONE' | 'EMAIL' | 'MEETING' | 'MESSAGE' | 'OTHER'

/** Coloured badge classes per status (same palette idea as the other CRM badges). */
export const STATUS_META: Record<SampleStatus, { label: string, en: string, cls: string, color: string }> = {
  DRAFT: { label: 'پیش‌نویس', en: 'Draft', cls: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-200', color: '#94a3b8' },
  NEW_REQUEST: { label: 'درخواست جدید', en: 'New Request', cls: 'bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-950 dark:text-sky-300', color: '#0ea5e9' },
  PENDING_APPROVAL: { label: 'در انتظار تأیید', en: 'Pending Approval', cls: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300', color: '#f59e0b' },
  APPROVED: { label: 'تأیید شده', en: 'Approved', cls: 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300', color: '#10b981' },
  REJECTED: { label: 'رد شده', en: 'Rejected', cls: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300', color: '#ef4444' },
  ON_HOLD: { label: 'متوقف', en: 'On Hold', cls: 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-300', color: '#f97316' },
  DISPATCHED: { label: 'ارسال شده', en: 'Dispatched', cls: 'bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-300', color: '#6366f1' },
  AWAITING_FEEDBACK: { label: 'در انتظار بازخورد', en: 'Awaiting Feedback', cls: 'bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-950 dark:text-violet-300', color: '#8b5cf6' },
  COMPLETED: { label: 'تکمیل شده', en: 'Completed', cls: 'bg-teal-100 text-teal-700 border-teal-200 dark:bg-teal-950 dark:text-teal-300', color: '#14b8a6' },
  CONVERTED: { label: 'تبدیل به فروش', en: 'Converted to Sales', cls: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-950 dark:text-green-300', color: '#22c55e' },
  CANCELLED: { label: 'لغو شده', en: 'Cancelled', cls: 'bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-300', color: '#71717a' },
}
export const STATUS_ORDER = Object.keys(STATUS_META) as SampleStatus[]

export const PRIORITY_META: Record<SamplePriority, { label: string, cls: string }> = {
  LOW: { label: 'کم', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  NORMAL: { label: 'عادی', cls: 'bg-blue-100 text-blue-700 border-blue-200' },
  HIGH: { label: 'زیاد', cls: 'bg-orange-100 text-orange-700 border-orange-200' },
  URGENT: { label: 'فوری', cls: 'bg-red-100 text-red-700 border-red-200' },
}
export const FEEDBACK_META: Record<FeedbackStatus, { label: string, cls: string, color: string }> = {
  ACCEPTED: { label: 'تأیید شد', cls: 'bg-emerald-100 text-emerald-700 border-emerald-200', color: '#10b981' },
  REJECTED: { label: 'تأیید نشد', cls: 'bg-red-100 text-red-700 border-red-200', color: '#ef4444' },
  ACCEPTED_WITH_CONDITIONS: { label: 'تأیید مشروط', cls: 'bg-amber-100 text-amber-800 border-amber-200', color: '#f59e0b' },
  UNDER_EVALUATION: { label: 'در حال بررسی', cls: 'bg-sky-100 text-sky-700 border-sky-200', color: '#0ea5e9' },
  NO_RESPONSE: { label: 'بدون پاسخ', cls: 'bg-slate-100 text-slate-600 border-slate-200', color: '#94a3b8' },
}
export const METHOD_LABELS: Record<FollowUpMethod, string> = {
  PHONE: 'تماس تلفنی', EMAIL: 'ایمیل', MEETING: 'جلسه', MESSAGE: 'پیام', OTHER: 'سایر',
}
export const METHOD_ICONS: Record<FollowUpMethod, string> = {
  PHONE: 'lucide:phone', EMAIL: 'lucide:mail', MEETING: 'lucide:users', MESSAGE: 'lucide:message-square', OTHER: 'lucide:more-horizontal',
}
export const UNIT_OPTIONS = [
  { value: 'kg', label: 'کیلوگرم (kg)' }, { value: 'g', label: 'گرم (g)' }, { value: 'ton', label: 'تن' },
  { value: 'liter', label: 'لیتر' }, { value: 'piece', label: 'عدد' },
]
export const DELIVERY_METHODS = ['پیک موتوری', 'تحویل حضوری', 'باربری', 'پست پیشتاز', 'حمل جاده‌ای (کامیون)', 'حمل هوایی', 'سایر']
export const FILE_KIND_LABELS: Record<string, string> = {
  TECHNICAL: 'مستندات فنی', DISPATCH: 'مدارک ارسال', FOLLOWUP: 'پیگیری', FEEDBACK: 'بازخورد', OTHER: 'سایر',
}
/** timeline action -> label + icon */
export const EVENT_META: Record<string, { label: string, icon: string }> = {
  created: { label: 'ایجاد درخواست', icon: 'lucide:file-plus' },
  updated: { label: 'ویرایش درخواست', icon: 'lucide:pencil' },
  submitted: { label: 'ثبت نهایی و ارسال برای تأیید', icon: 'lucide:send' },
  approved: { label: 'تأیید درخواست', icon: 'lucide:check-circle-2' },
  rejected: { label: 'رد درخواست', icon: 'lucide:x-circle' },
  on_hold: { label: 'توقف موقت', icon: 'lucide:pause-circle' },
  resumed: { label: 'ازسرگیری', icon: 'lucide:play-circle' },
  dispatch_added: { label: 'ثبت محموله', icon: 'lucide:package-plus' },
  dispatch_removed: { label: 'حذف محموله', icon: 'lucide:package-minus' },
  dispatched: { label: 'ارسال نمونه', icon: 'lucide:truck' },
  delivered: { label: 'دریافت نمونه توسط مشتری', icon: 'lucide:package-check' },
  awaiting_feedback: { label: 'در انتظار بازخورد مشتری', icon: 'lucide:hourglass' },
  followup_added: { label: 'ثبت پیگیری', icon: 'lucide:phone-call' },
  followup_updated: { label: 'ویرایش پیگیری', icon: 'lucide:pencil' },
  followup_removed: { label: 'حذف پیگیری', icon: 'lucide:trash-2' },
  feedback_recorded: { label: 'ثبت بازخورد نهایی مشتری', icon: 'lucide:message-circle-heart' },
  completed: { label: 'تکمیل درخواست', icon: 'lucide:badge-check' },
  converted: { label: 'تبدیل به فروش', icon: 'lucide:trending-up' },
  cancelled: { label: 'لغو درخواست', icon: 'lucide:ban' },
  file_added: { label: 'افزودن پیوست', icon: 'lucide:paperclip' },
  file_removed: { label: 'حذف پیوست', icon: 'lucide:paperclip' },
  new_request_raised: { label: 'ایجاد درخواست جدید مرتبط', icon: 'lucide:copy-plus' },
}

export interface SampleActions {
  can_edit: boolean, can_submit: boolean, can_approve: boolean, can_reject: boolean, can_hold: boolean,
  can_resume: boolean, can_dispatch: boolean, can_confirm_delivery: boolean, can_follow_up: boolean,
  can_feedback: boolean, can_complete: boolean, can_convert: boolean, can_cancel: boolean, can_delete: boolean,
  can_new_request: boolean, can_attach: boolean
}
export interface SampleCustomer {
  id: number, name: string, brand: string | null, province: string | null, city: string | null,
  company_name?: string | null, customer_type?: string, company_phone?: string | null, category?: string | null,
  contacts?: { name: string, position: string | null, mobile: string | null, landline: string | null }[]
}
export interface SampleRow {
  id: number, code: string, status: SampleStatus, priority: SamplePriority, customer: SampleCustomer,
  sales_rep: { id: number | null, name: string | null }, requested_date: string, required_delivery_date: string | null,
  dispatch_ref_number: string | null, product: string | null, grade: string | null, items_count: number,
  quantity_label: string, feedback_status: FeedbackStatus | null, parent_request_id: number | null,
  created_by_name: string | null, created_at: string | null, next_followup_date: string | null,
  followup_overdue: boolean, my_actions: SampleActions
}
export interface SampleItem {
  id?: number, product_name: string, grade: string | null,
  quantity: number | null, unit: string, number_of_samples: number,
  packaging: string | null, specifications: string | null
}
export interface SampleDispatch {
  id: number, dispatch_date: string, reference_number: string, delivery_method: string | null,
  tracking_number: string | null, carrier: string | null, shipped_quantity: number | null, unit: string,
  recipient_name: string | null, notes: string | null, created_by_name: string | null, created_at: string | null
}
export interface SampleFollowUp {
  id: number, followup_date: string, method: FollowUpMethod, contact_person: string | null, result: string | null,
  customer_response: string | null, next_followup_date: string | null, responsible: { id: number | null, name: string | null },
  internal_notes: string | null, created_by_name: string | null, created_by_user_id: number | null,
  created_at: string | null, overdue: boolean, can_edit: boolean
}
export interface SampleFile { id: string, name: string, size: number, kind: string, uploaded_at: string | null }
export interface SampleEvent {
  id: number, at: string, at_display: string | null, user_name: string | null, action: string,
  from_status: SampleStatus | null, to_status: SampleStatus | null, note: string | null, details: Record<string, unknown> | null
}
export interface SampleDetail extends SampleRow {
  purpose: string | null, technical_requirements: string | null, delivery_method: string | null,
  recipient_name: string | null, delivery_address: string | null, country: string | null, city: string | null,
  postal_code: string | null, delivery_instructions: string | null, internal_notes: string | null,
  reject_reason: string | null, hold_reason: string | null, cancel_reason: string | null,
  submitted_at: string | null, approved_at: string | null, first_dispatched_at: string | null, closed_at: string | null,
  delivered_at: string | null, delivery_received_by: string | null, delivery_note: string | null,
  items: SampleItem[], dispatches: SampleDispatch[], followups: SampleFollowUp[], files: SampleFile[], events: SampleEvent[],
  feedback: null | {
    status: FeedbackStatus, date: string | null, product_evaluation: string | null, technical_acceptance: boolean | null,
    customer_comments: string | null, rejection_reason: string | null, improvement_suggestions: string | null,
    evaluated_by: string | null, recorded_at: string | null
  },
  conversion: null | { sale_id: number | null, note: string | null, converted_at: string | null },
  parent?: { id: number, code: string } | null, children: { id: number, code: string, status: SampleStatus }[]
}
export interface SampleAnalytics {
  kpis: { total: number, pending: number, approved: number, dispatched: number, rejected: number, awaiting_feedback: number, converted: number, on_hold: number }
  trend: { key: string, label: string, count: number }[]
  granularity: 'day' | 'week' | 'month'
  status_distribution: { status: SampleStatus, count: number }[]
  top_products: { product: string, grade: string | null, requests: number, quantity_kg: number }[]
  sales_performance: { rep_id: number | null, name: string, requests: number, approved: number, rejected: number, dispatched: number, accepted: number, converted: number, approval_rate: number | null, conversion_rate: number | null }[]
  feedback: { counts: Record<string, number>, total: number, accepted_pct: number | null, rejected_pct: number | null, conditional_pct: number | null }
  conversion: { dispatched: number, converted: number, rate: number | null }
}
