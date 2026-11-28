// Labels + types for the user-activity pages (login log, sessions, activity timeline).
// Nuxt auto-imports everything exported here.

/** What the page prints for a value the server never recorded -- never a guess. */
export const NOT_RECORDED = 'ثبت نشده'

export interface ActivityEvent {
  id: number
  at: string | null
  action: string
  module: string
  entity_type: string | null
  entity_id: number | null
  category: 'auth' | 'action'
  ip_address: string | null
  device_type: string | null
  os: string | null
  browser: string | null
  session_id: number | null
  reason: string | null
  changed_fields: string[]
  user?: { id: number, full_name: string, username: string }
}
export interface UserSessionRow {
  id: number
  status: 'active' | 'ended' | 'expired'
  ip_address: string | null
  device_type: string | null
  os: string | null
  browser: string | null
  login_at: string | null
  last_seen_at: string | null
  logout_at: string | null
  logout_reason: string | null
}

const ACTION_LABELS: Record<string, string> = {
  login_success: 'ورود به سامانه',
  login_failure: 'تلاش ناموفق برای ورود',
  logout: 'خروج از سامانه',
  avatar_changed: 'تغییر تصویر پروفایل',
  avatar_removed: 'حذف تصویر پروفایل',
  create: 'ایجاد',
  update: 'ویرایش',
  delete: 'حذف',
  read: 'مشاهده',
  send: 'ارسال',
  refer: 'ارجاع',
  resubmit: 'ارسال مجدد',
  import: 'درون‌ریزی',
  purge: 'حذف دائمی',
  assign: 'تخصیص',
  unassign: 'لغو تخصیص',
  set_assignees: 'تعیین مسئولان',
  assign_role: 'تخصیص نقش',
  revoke_role: 'لغو نقش',
  grant_permission: 'اعطای مجوز',
  revoke_permission: 'لغو مجوز',
  set_permissions: 'تنظیم مجوزها',
  delegate: 'تفویض',
  password_reset: 'تغییر رمز عبور',
  add_member: 'افزودن عضو',
  remove_member: 'حذف عضو',
  change_request: 'تغییر وضعیت درخواست',
  create_category: 'ایجاد دسته‌بندی',
  update_category: 'ویرایش دسته‌بندی',
  delete_category: 'حذف دسته‌بندی',
  create_option: 'ایجاد گزینه',
  update_option: 'ویرایش گزینه',
  delete_option: 'حذف گزینه',
  create_delivery_method: 'ایجاد روش ارسال',
  update_delivery_method: 'ویرایش روش ارسال',
  delete_delivery_method: 'حذف روش ارسال',
  update_sla: 'ویرایش زمان‌بندی (SLA)',
  set_unit_access: 'تنظیم دسترسی واحد',
  note_add: 'افزودن یادداشت',
  note_delete: 'حذف یادداشت',
  file_add: 'افزودن فایل',
  file_delete: 'حذف فایل',
  checklist_add: 'افزودن مورد چک‌لیست',
  checklist_update: 'ویرایش چک‌لیست',
  checklist_delete: 'حذف مورد چک‌لیست',
  recurrence_create: 'ایجاد تکرار',
}
const MODULE_LABELS: Record<string, string> = {
  auth: 'احراز هویت',
  core: 'مدیریت کاربران و ساختار',
  authz: 'مجوزها و دسترسی',
  tasks: 'وظایف',
  crm: 'مشتریان و فروش',
  logistics: 'لجستیک',
  procurement: 'تدارکات',
  correspondence: 'مکاتبات سازمانی',
  customers: 'مشتریان',
  suppliers: 'تأمین‌کنندگان',
  purchases: 'خرید',
  request_samples: 'درخواست نمونه',
}
const ENTITY_LABELS: Record<string, string> = {
  user: 'کاربر', role: 'نقش', team: 'تیم', department: 'دپارتمان', organization: 'سازمان',
  task: 'وظیفه', customer: 'مشتری', supplier: 'تأمین‌کننده', mail: 'نامه', thread: 'مکاتبه',
}
const DEVICE_LABELS: Record<string, string> = { desktop: 'رایانه', mobile: 'موبایل', tablet: 'تبلت' }
const LOGOUT_REASONS: Record<string, string> = {
  logout: 'خروج توسط کاربر',
  token_reuse: 'ابطال امنیتی نشست',
  revoked: 'ابطال توسط سامانه (مثلاً تغییر رمز)',
}

export const actionLabel = (a: string) => ACTION_LABELS[a] ?? a
export const moduleLabel = (m: string) => MODULE_LABELS[m] ?? m
export const entityLabel = (e: string | null) => (e ? (ENTITY_LABELS[e] ?? e) : '')
export const deviceLabel = (d: string | null) => (d ? (DEVICE_LABELS[d] ?? d) : '')
export const logoutReasonLabel = (r: string | null) => (r ? (LOGOUT_REASONS[r] ?? r) : '')
export const sessionStatusLabel = (s: UserSessionRow['status']) => ({ active: 'فعال', ended: 'خاتمه‌یافته', expired: 'منقضی‌شده' }[s])

/** "رایانه · Windows · Chrome" with only the parts that were recorded; '' when none was. */
export function describeClient(x: { device_type: string | null, os: string | null, browser: string | null }): string {
  return [deviceLabel(x.device_type), x.os, x.browser].filter(Boolean).join(' · ')
}
