// Types + helpers of the correspondence module (مکاتبات). Nuxt auto-imports everything exported here.
export type MailFolder = 'inbox' | 'sent' | 'drafts' | 'spam' | 'trash' | 'archive'
export type MailLabel = 'urgent' | 'work' | 'finance' | 'meeting' | 'info'

export interface MailPerson {
  id: number
  full_name: string
  username: string
  email: string
  department: string | null
  avatar: string | null
  first_name?: string
  last_name?: string
}
export interface MailFile { id: string, name: string, size: number, content_type: string | null }
export interface MailMessage {
  id: number
  thread_id: number
  parent_id: number | null
  subject: string
  body: string
  is_draft: boolean
  sender_id: number
  to: number[]
  cc: number[]
  sent_at: string | null
  created_at: string
  is_mine: boolean
  attachments: MailFile[]
  folder: MailFolder | null
  is_read: boolean
  is_starred: boolean
}
export interface MailRow extends Omit<MailMessage, 'body'> {
  preview: string
  thread_count: number
  labels: MailLabel[]
  has_attachments: boolean
}
export interface MailThread {
  thread_id: number
  subject: string
  folder: MailFolder | null
  is_muted: boolean
  is_starred: boolean
  labels: MailLabel[]
  messages: MailMessage[]
  people: Record<string, MailPerson>
}
export interface MailMeta {
  access: { read: boolean, create: boolean, update: boolean, delete: boolean }
  can_manage_access: boolean
  labels: MailLabel[]
  limits: { max_files: number, max_file_mb: number, max_total_mb: number, allowed_extensions: string[] }
}

export const MAIL_FOLDERS: { id: MailFolder, label: string, icon: string }[] = [
  { id: 'inbox', label: 'صندوق دریافت', icon: 'lucide:inbox' },
  { id: 'drafts', label: 'پیش‌نویس‌ها', icon: 'lucide:file' },
  { id: 'sent', label: 'ارسال‌شده', icon: 'lucide:send' },
  { id: 'spam', label: 'هرزنامه', icon: 'lucide:archive-x' },
  { id: 'trash', label: 'سطل زباله', icon: 'lucide:trash-2' },
  { id: 'archive', label: 'بایگانی', icon: 'lucide:archive' },
]
// Labels are plain text tags: no per-label colours. Only «فوری» gets the theme's destructive tone,
// because urgency is the one label that carries meaning by itself.
export const MAIL_LABELS: { id: MailLabel, label: string, color: string }[] = [
  { id: 'urgent', label: 'فوری', color: 'text-destructive' },
  { id: 'work', label: 'کاری', color: '' },
  { id: 'finance', label: 'مالی', color: '' },
  { id: 'meeting', label: 'جلسه', color: '' },
  { id: 'info', label: 'اطلاع‌رسانی', color: '' },
]
export const labelStyle = (id: string) => MAIL_LABELS.find(l => l.id === id)

export const mailInitials = (name: string) => (name || '?').trim().split(/\s+/).map(p => p[0]).slice(0, 2).join('')

/**
 * List column: today -> "۱۴:۳۰", otherwise the Jalali date "۱۴۰۵/۰۹/۰۳" (Tehran time, like everywhere else).
 */
export function formatMailDate(iso: string | null): string {
  if (!iso) return ''
  const today = todayIso()
  return tehranDayKey(iso) === today ? formatTehranTime(iso) : formatTehranDate(iso)
}
/** Detail header: "۱۴۰۵/۰۹/۰۳ - ساعت ۱۴:۳۰". */
export function formatMailDateLong(iso: string | null): string {
  if (!iso) return ''
  return `${formatTehranDate(iso)} - ساعت ${formatTehranTime(iso)}`
}
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes.toLocaleString('fa-IR')} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString('fa-IR', { maximumFractionDigits: 0 })} KB`
  return `${(bytes / 1024 / 1024).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} MB`
}
