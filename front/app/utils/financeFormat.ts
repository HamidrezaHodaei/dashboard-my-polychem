/** Format a number with English thousands separators. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(Math.round(value))
}

export type CurrencyUnit = 'toman' | 'rial'

const unitLabel: Record<CurrencyUnit, string> = {
  toman: 'Toman',
  rial: 'Rial',
}

/** Format an amount with its currency unit label. */
export function formatCurrency(value: number, unit: CurrencyUnit = 'toman'): string {
  return `${formatNumber(value)} ${unitLabel[unit]}`
}

/** Format a signed amount for ledger displays (debit/credit), empty string for zero. */
export function formatLedgerAmount(value: number): string {
  if (!value) return '—'
  return formatNumber(Math.abs(value))
}

// ---- Minimal Gregorian -> Jalali (Shamsi) conversion ----------------------
// Self-contained so the UI can render Persian calendar dates without an
// external dependency. Swap for `date-fns-jalali` or `dayjs` + jalali plugin
// if richer calendar math (holidays, ranges) is needed later.

function div(a: number, b: number) {
  return Math.trunc(a / b)
}

export function gregorianToJalali(gy: number, gm: number, gd: number): [number, number, number] {
  const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
  let jy = gy <= 1600 ? 0 : 979
  gy -= gy <= 1600 ? 621 : 1600
  const gy2 = gm > 2 ? gy + 1 : gy
  let days =
    365 * gy +
    div(gy2 + 3, 4) -
    div(gy2 + 99, 100) +
    div(gy2 + 399, 400) -
    80 +
    gd +
    g_d_m[gm - 1]
  jy += 33 * div(days, 12053)
  days %= 12053
  jy += 4 * div(days, 1461)
  days %= 1461
  if (days > 365) {
    jy += div(days - 1, 365)
    days = (days - 1) % 365
  }
  const jm = days < 186 ? 1 + div(days, 31) : 7 + div(days - 186, 30)
  const jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30)
  return [jy, jm, jd]
}

const jalaliMonths = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

/** Convert any Latin digits in a value to Persian (Farsi) digits, for UI labels. */
export function toPersianDigits(value: number | string): string {
  const fa = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
  return String(value).replace(/[0-9]/g, d => fa[Number(d)]!)
}

/** Format an ISO date string using the English Gregorian calendar. */
export function formatJalaliDate(iso: string): string {
  const d = new Date(iso)
  return new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(d)
}

export function jalaliToGregorian(jy: number, jm: number, jd: number): [number, number, number] {
  let gy = jy <= 979 ? 621 : 1600
  jy -= jy <= 979 ? 0 : 979
  let days =
    365 * jy +
    div(jy, 33) * 8 +
    div(((jy % 33) + 3), 4) +
    78 +
    jd +
    (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186)
  gy += 400 * div(days, 146097)
  days %= 146097
  if (days > 36524) {
    gy += 100 * div(--days, 36524)
    days %= 36524
    if (days >= 365) days++
  }
  gy += 4 * div(days, 1461)
  days %= 1461
  if (days > 365) {
    gy += div(days - 1, 365)
    days = (days - 1) % 365
  }
  let gd = days + 1
  const salA = [0, 31, ((gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let gm = 0
  for (gm = 1; gm <= 12 && gd > salA[gm]; gm++) gd -= salA[gm]
  return [gy, gm, gd]
}

export function jalaliMonthLength(jy: number, jm: number): number {
  if (jm <= 6) return 31
  if (jm <= 11) return 30
  // esfand: leap year check via round-trip
  const [gy1] = jalaliToGregorian(jy + 1, 1, 1)
  const [gy0] = jalaliToGregorian(jy, 1, 1)
  return gy1 - gy0 === 1 && ((gy0 % 4 === 0 && gy0 % 100 !== 0) || gy0 % 400 === 0) ? 30 : 29
}

export { jalaliMonths }

/** Today's date as a jalali [year, month, day] tuple. */
export function todayJalali(): [number, number, number] {
  const now = new Date()
  return gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate())
}

/** Build an ISO date string (midday UTC to avoid TZ day-shift) from a jalali date. */
export function jalaliToIso(jy: number, jm: number, jd: number): string {
  const [gy, gm, gd] = jalaliToGregorian(jy, jm, jd)
  return new Date(Date.UTC(gy, gm - 1, gd, 12)).toISOString()
}
