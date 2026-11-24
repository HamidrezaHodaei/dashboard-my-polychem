// One place that knows how a notification type looks (icon + colour) and which category it belongs to.
// Used by the bell popover and the notification centre; categories mirror the backend catalogue
// (backend/app/modules/notifications/catalog.py).

const ICONS: Record<string, string> = {
  MAIL: 'lucide:mail',
  TASK_ASSIGNED: 'lucide:clipboard-list',
  TASK_REFERRED: 'lucide:corner-up-left',
  TASK_MENTION: 'lucide:at-sign',
  TASK_DUE_SOON: 'lucide:alarm-clock',
  TASK_OVERDUE: 'lucide:alarm-clock-off',
  REVIEW_RESULT: 'lucide:badge-check',
  REVIEW_RESUBMITTED: 'lucide:rotate-ccw',
  CHANGE_REQUEST: 'lucide:file-pen-line',
  REVIEW_REQUEST: 'lucide:inbox',
  SAMPLE_SUBMITTED: 'lucide:flask-conical',
  SAMPLE_APPROVED: 'lucide:check-circle-2',
  SAMPLE_REJECTED: 'lucide:x-circle',
  SAMPLE_ON_HOLD: 'lucide:pause-circle',
  SAMPLE_DISPATCHED: 'lucide:truck',
  SAMPLE_DELIVERED: 'lucide:package-check',
  SAMPLE_REMIND_SHIP: 'lucide:package-open',
  SAMPLE_REMIND_DELIVER: 'lucide:truck',
  SAMPLE_REMIND_FOLLOWUP: 'lucide:phone-call',
  SAMPLE_FOLLOWUP_DUE: 'lucide:calendar-clock',
  SAMPLE_FEEDBACK: 'lucide:message-circle-heart',
  CUSTOMER_FOLLOWUP_DUE: 'lucide:phone-call',
  CUSTOMER_FOLLOWUP_OVERDUE: 'lucide:phone-missed',
  PURCHASE_NEW: 'lucide:shopping-cart',
  PURCHASE_RESUBMITTED: 'lucide:rotate-ccw',
  PURCHASE_RETURNED: 'lucide:corner-up-left',
  PURCHASE_VOID: 'lucide:x-circle',
  PURCHASE_STATUS: 'lucide:package-check',
  PURCHASE_APPROVAL: 'lucide:badge-check',
  PURCHASE_FINANCE: 'lucide:coins',
  PURCHASE_MANAGER_RETURN: 'lucide:corner-up-left',
  PURCHASE_PAID: 'lucide:coins',
}

export const notificationIcon = (type: string): string => ICONS[type] ?? (type.startsWith('LEAVE_') ? 'lucide:calendar-days' : 'lucide:bell')

export const notificationIconColor = (type: string): string => (
  type === 'TASK_OVERDUE' || type === 'CUSTOMER_FOLLOWUP_OVERDUE' || type === 'PURCHASE_VOID'
    ? 'text-destructive'
    : type === 'TASK_DUE_SOON' || type === 'CUSTOMER_FOLLOWUP_DUE' || type === 'PURCHASE_APPROVAL' ? 'text-amber-500' : 'text-primary'
)

export const NOTIFICATION_CATEGORIES = [
  { key: 'tasks', label: 'امور محوله' },
  { key: 'reminders', label: 'موعدها و یادآوری‌ها' },
  { key: 'purchases', label: 'درخواست‌های خرید' },
  { key: 'samples', label: 'درخواست نمونه' },
  { key: 'reviews', label: 'بررسی و تأیید' },
  { key: 'mail', label: 'مکاتبات' },
  { key: 'leave', label: 'مرخصی' },
  { key: 'other', label: 'سایر' },
] as const
