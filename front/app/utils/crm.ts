// Shared CRM helpers: number formatting (Persian digits), labels, chart palette.
// Dates are NOT parsed here: the UI keeps ISO ("2026-11-06") and the backend does all
// Jalali/Gregorian handling (app/utils/jalali.py::parse_date_input).

export const faNum = (n: number | string) => Number(n || 0).toLocaleString('fa-IR')

/** Full rial amount: «۱٬۲۳۴٬۰۰۰ ریال». */
export const formatRial = (n: number) => `${faNum(Math.round(n || 0))} ریال`

/** Compact rial for KPI cards / tooltips: «۱٫۲ میلیارد ریال». */
export function formatRialCompact(n: number): string {
  const abs = Math.abs(n || 0)
  const sign = (n || 0) < 0 ? '−' : ''
  if (abs >= 1e12) return `${sign}${faNum(Number((abs / 1e12).toFixed(2)))} تریلیون ریال`
  if (abs >= 1e9) return `${sign}${faNum(Number((abs / 1e9).toFixed(1)))} میلیارد ریال`
  if (abs >= 1e6) return `${sign}${faNum(Number((abs / 1e6).toFixed(1)))} میلیون ریال`
  if (abs >= 1e3) return `${sign}${faNum(Number((abs / 1e3).toFixed(0)))} هزار ریال`
  return `${sign}${faNum(Math.round(abs))} ریال`
}

/** Short axis label without a unit («۱٫۲ میلیارد» → «۱٫۲B» style is unreadable in Persian, so words). */
export function formatAxisRial(n: number): string {
  const abs = Math.abs(n || 0)
  const sign = (n || 0) < 0 ? '−' : ''
  if (abs >= 1e12) return `${sign}${faNum(Number((abs / 1e12).toFixed(1)))} تریلیون`
  if (abs >= 1e9) return `${sign}${faNum(Number((abs / 1e9).toFixed(1)))} میلیارد`
  if (abs >= 1e6) return `${sign}${faNum(Number((abs / 1e6).toFixed(0)))} میلیون`
  if (abs >= 1e3) return `${sign}${faNum(Number((abs / 1e3).toFixed(0)))} هزار`
  return `${sign}${faNum(Math.round(abs))}`
}

/** Quantities are stored in kilograms. */
export function formatKg(n: number): string {
  const abs = Math.abs(n || 0)
  const sign = (n || 0) < 0 ? '−' : ''
  if (abs >= 1e6) return `${sign}${faNum(Number((abs / 1e6).toFixed(2)))} هزار تن`
  if (abs >= 1e3) return `${sign}${faNum(Number((abs / 1e3).toFixed(1)))} تن`
  return `${sign}${faNum(Math.round(abs))} کیلوگرم`
}

/** Value + unit split in two, for labels printed ON a chart bar (number on top, small unit below).
 *  Kilograms are shown as real kilograms («۱۲۵٬۰۰۰ کیلوگرم»), never silently converted to tons;
 *  rials are shortened to words because the raw figure would not fit above a bar. */
export function chartLabelParts(n: number, metric: 'amount' | 'quantity_kg'): { num: string, unit: string } {
  const value = n || 0
  const sign = value < 0 ? '−' : ''
  const abs = Math.abs(value)
  if (metric === 'quantity_kg') return { num: `${sign}${faNum(Number(abs.toFixed(abs < 100 ? 1 : 0)))}`, unit: 'کیلوگرم' }
  if (abs >= 1e12) return { num: `${sign}${faNum(Number((abs / 1e12).toFixed(2)))}`, unit: 'تریلیون ریال' }
  if (abs >= 1e9) return { num: `${sign}${faNum(Number((abs / 1e9).toFixed(1)))}`, unit: 'میلیارد ریال' }
  if (abs >= 1e6) return { num: `${sign}${faNum(Number((abs / 1e6).toFixed(1)))}`, unit: 'میلیون ریال' }
  if (abs >= 1e3) return { num: `${sign}${faNum(Number((abs / 1e3).toFixed(0)))}`, unit: 'هزار ریال' }
  return { num: `${sign}${faNum(Math.round(abs))}`, unit: 'ریال' }
}

export const formatAxisKg = (n: number) => formatKg(n).replace(' کیلوگرم', ' کگ')

export const formatPercent = (part: number, total: number) =>
  total ? `${faNum(Number(((part / total) * 100).toFixed(1)))}٪` : '—'

/** Escape text going into tooltip HTML strings. */
export const escapeHtml = (s: string) =>
  s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;' }[c]!))

/** Series colours: brand yellow first, then hues that stay distinct in light and dark mode. */
export const CHART_COLORS = [
  '#ffcc05', '#3b82f6', '#10b981', '#f97316', '#8b5cf6', '#ec4899', '#14b8a6', '#ef4444', '#94a3b8',
]
export const NEGATIVE_COLOR = '#ef4444'
export const colorAt = (i: number) => CHART_COLORS[i % CHART_COLORS.length]!

export const SALE_TYPE_LABELS: Record<string, string> = { OFFICIAL: 'رسمی', UNOFFICIAL: 'غیررسمی' }
export const DOCUMENT_TYPE_LABELS: Record<string, string> = { INVOICE: 'فاکتور فروش', RETURN: 'برگشت از فروش' }
export const SALE_STATUS_LABELS: Record<string, string> = { PROCESSING: 'در حال پردازش', COMPLETED: 'تکمیل شده' }

export const PRESET_LABELS: Record<string, string> = {
  all: 'همه زمان‌ها',
  this_month: 'ماه جاری',
  last_1m: '۱ ماه اخیر',
  last_3m: '۳ ماه اخیر',
  last_6m: '۶ ماه اخیر',
  last_12m: '۱۲ ماه اخیر',
  this_year: 'سال جاری',
  custom: 'بازه دلخواه',
}
