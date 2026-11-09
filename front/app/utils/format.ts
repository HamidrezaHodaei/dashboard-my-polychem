// `formatNumber` / `formatCurrency` live in `~/utils/financeFormat` only now --
// they used to be duplicated here, in financeFormat.ts and in index.ts, which
// made Nuxt's auto-import silently pick one and drop the other two (see the
// "Duplicated imports" build warnings). Any auto-imported call site (nothing
// here explicitly imported `~/utils/format` for these two) now resolves to
// financeFormat.ts's Toman/Rial-aware version instead of whichever file
// happened to win the race before.

export function formatDate(value: string): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: 'short', day: '2-digit' }).format(d)
}

export function formatDateTime(value: string): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
    year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit'
  }).format(d)
}

export function titleCase(value: string): string {
  const labels: Record<string, string> = {
    active: 'فعال',
    inactive: 'غیرفعال',
    draft: 'پیش‌نویس',
    pending: 'در انتظار',
    completed: 'تکمیل‌شده',
    cancelled: 'لغوشده',
    confirmed: 'تأییدشده',
  }
  const normalized = value.toLowerCase().replace(/_/g, ' ')
  return labels[normalized] ?? normalized.replace(/\b\w/g, (c) => c.toUpperCase())
}
