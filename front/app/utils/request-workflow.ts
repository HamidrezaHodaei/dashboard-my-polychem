/**
 * The review workflow shared by logistics registrations, suppliers and customers
 * (server side: backend/app/core/request_workflow.py).
 *
 *  PENDING     در انتظار بررسی
 *  APPROVED    تأیید
 *  REJECTED    رد درخواست
 *  NEEDS_EDIT  نیازمند ویرایش یا تکمیل اطلاعات   (the manager's explanation is mandatory)
 *
 * The creator edits freely while the request is a draft or has been sent back; once it is
 * submitted ("ثبت نهایی") it is read-only for them and they can only send the manager a
 * written change request. What THIS user may do comes from `my_actions` on every record.
 */
export type RequestStatusKey = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NEEDS_EDIT' | 'SUSPENDED'
export type RequestReviewAction = 'APPROVE' | 'REJECT' | 'REQUEST_EDIT' | 'REOPEN' | 'SUSPEND'

export interface MyActions {
  can_edit: boolean
  can_finalize: boolean
  can_request_change: boolean
  can_review: boolean
}

export const REQUEST_STATUS_LABELS: Record<RequestStatusKey, string> = {
  PENDING: 'در انتظار بررسی',
  APPROVED: 'تأیید',
  REJECTED: 'رد درخواست',
  NEEDS_EDIT: 'نیازمند ویرایش یا تکمیل اطلاعات',
  SUSPENDED: 'تعلیق',
}

export const REQUEST_STATUS_VARIANT: Record<RequestStatusKey, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  PENDING: 'secondary',
  APPROVED: 'default',
  REJECTED: 'destructive',
  NEEDS_EDIT: 'outline',
  SUSPENDED: 'outline',
}

export const REQUEST_REVIEW_ACTIONS: Record<RequestReviewAction, { label: string, icon: string, noteRequired: boolean, hint?: string }> = {
  APPROVE: { label: 'تأیید', icon: 'lucide:badge-check', noteRequired: false },
  REJECT: { label: 'رد درخواست', icon: 'lucide:circle-x', noteRequired: true, hint: 'دلیل رد را بنویسید.' },
  REQUEST_EDIT: {
    label: 'نیازمند ویرایش یا تکمیل اطلاعات', icon: 'lucide:file-pen-line', noteRequired: true,
    hint: 'توضیح دهید چه چیزی باید اصلاح یا تکمیل شود؛ ثبت‌کننده همین متن را می‌بیند.',
  },
  REOPEN: { label: 'بازگرداندن به صف بررسی', icon: 'lucide:rotate-ccw', noteRequired: false },
  SUSPEND: { label: 'تعلیق', icon: 'lucide:pause-circle', noteRequired: true, hint: 'دلیل تعلیق را بنویسید.' },
}

/** Mirrors the server's transitions (core/request_workflow.py; SUSPEND exists for logistics only). */
export function requestReviewActionsFor(status: RequestStatusKey, opts: { allowSuspend?: boolean } = {}): RequestReviewAction[] {
  const base: Record<RequestStatusKey, RequestReviewAction[]> = {
    PENDING: ['APPROVE', 'REJECT', 'REQUEST_EDIT'],
    APPROVED: ['REQUEST_EDIT'],
    REJECTED: ['REOPEN'],
    NEEDS_EDIT: ['REJECT'],
    SUSPENDED: ['APPROVE'],
  }
  const list = [...base[status] ?? []]
  if (opts.allowSuspend && status === 'APPROVED') list.push('SUSPEND')
  return list
}

/** server error text -> Persian, for the three modules' workflow calls */
export function requestErrorMessage(err: unknown, fallback: string): string {
  const text = err instanceof Error ? err.message : ''
  if (/[\u0600-\u06FF]/.test(text)) return text
  if (/still a draft/i.test(text)) return 'این درخواست هنوز پیش‌نویس است و ثبت‌کننده آن را نهایی نکرده است.'
  if (/already submitted/i.test(text)) return 'این درخواست قبلاً ثبت نهایی شده است.'
  if (/written reason/i.test(text)) return 'برای این تصمیم نوشتن توضیح الزامی است.'
  if (/cannot (approve|reject|request_edit|reopen|suspend)/i.test(text)) return 'این تصمیم با وضعیت فعلی درخواست سازگار نیست.'
  if (/cannot request a change/i.test(text)) return 'برای این درخواست نمی‌توانید درخواست تغییر ثبت کنید.'
  if (/only the creator/i.test(text)) return 'فقط ثبت‌کننده‌ی درخواست می‌تواند آن را ثبت نهایی کند.'
  if (/missing permission|permission_denied/i.test(text)) return 'شما دسترسی لازم برای این کار را ندارید.'
  return fallback
}
