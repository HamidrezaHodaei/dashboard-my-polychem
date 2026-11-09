import { markRaw } from 'vue'
import { toast } from 'vue-sonner'
import ToastCard from '@/components/notify/ToastCard.vue'

type Tone = 'success' | 'error' | 'warning' | 'info'

interface NotifyOptions {
  description?: string
  duration?: number
  action?: { label: string, onClick?: () => void }
}

type NotifyDetails = NotifyOptions | string

function show(tone: Tone, title: string, details: NotifyDetails = {}) {
  const opts = typeof details === 'string' ? { description: details } : details
  const id = crypto.randomUUID()
  toast.custom(markRaw(ToastCard), {
    id,
    duration: Infinity, // بسته شدن را خود کارت مدیریت می‌کند
    componentProps: { id, tone, title, ...opts },
  })
  return id
}

export function useNotify() {
  return {
    success: (title: string, details?: NotifyDetails) => show('success', title, details),
    error: (title: string, details?: NotifyDetails) => show('error', title, details),
    warning: (title: string, details?: NotifyDetails) => show('warning', title, details),
    info: (title: string, details?: NotifyDetails) => show('info', title, details),
  }
}