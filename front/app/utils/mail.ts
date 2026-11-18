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
export const MAIL_LABELS: { id: MailLabel, label: string, color: string }[] = [
  { id: 'urgent', label: 'فوری', color: 'bg-pink-500' },
  { id: 'work', label: 'کاری', color: 'bg-violet-500' },
  { id: 'finance', label: 'مالی', color: 'bg-lime-500' },
  { id: 'meeting', label: 'جلسه', color: 'bg-orange-500' },
  { id: 'info', label: 'اطلاع‌رسانی', color: 'bg-teal-500' },
]
export const labelStyle = (id: string) => MAIL_LABELS.find(l => l.id === id)

export const mailInitials = (name: string) => (name || '?').trim().split(/\s+/).map(p => p[0]).slice(0, 2).join('')

export function formatMailDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'هم‌اکنون'
  const sameDay = new Date().toDateString() === d.toDateString()
  if (sameDay) return d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('fa-IR', { month: 'long', day: 'numeric' })
}
export function formatMailDateLong(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }) : ''
}
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes.toLocaleString('fa-IR')} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString('fa-IR', { maximumFractionDigits: 0 })} KB`
  return `${(bytes / 1024 / 1024).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} MB`
}
