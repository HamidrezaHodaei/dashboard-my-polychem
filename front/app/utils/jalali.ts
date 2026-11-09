/**
 * Jalali (Persian / Shamsi) calendar helpers -- no dependencies.
 * Nuxt auto-imports everything exported from `utils/`.
 *
 * The backend keeps dates as Gregorian ISO strings ("YYYY-MM-DD"); the UI
 * shows and edits them in Jalali. Conversion uses the well-known
 * jalaali-js algorithm (valid for Jalali years -61 .. 3177).
 */

const div = (a: number, b: number) => Math.trunc(a / b)
const mod = (a: number, b: number) => a - Math.trunc(a / b) * b

const BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]

export interface JalaliDate { jy: number, jm: number, jd: number }
export interface GregorianDate { gy: number, gm: number, gd: number }

function jalCal(jy: number, withoutLeap = false): { leap: number, gy: number, march: number } {
  const bl = BREAKS.length
  const gy = jy + 621
  let leapJ = -14
  let jp = BREAKS[0]!
  let jump = 0
  if (jy < jp || jy >= BREAKS[bl - 1]!) throw new Error(`Invalid Jalali year ${jy}`)
  for (let i = 1; i < bl; i++) {
    const jm = BREAKS[i]!
    jump = jm - jp
    if (jy < jm) break
    leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4)
    jp = jm
  }
  let n = jy - jp
  leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4)
  if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1
  const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150
  const march = 20 + leapJ - leapG
  if (withoutLeap) return { leap: 0, gy, march }
  if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33
  let leap = mod(mod(n + 1, 33) - 1, 4)
  if (leap === -1) leap = 4
  return { leap, gy, march }
}

function g2d(gy: number, gm: number, gd: number) {
  let d = div((gy + div(gm - 8, 6) + 100100) * 1461, 4) + div(153 * mod(gm + 9, 12) + 2, 5) + gd - 34840408
  d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752
  return d
}
function d2g(jdn: number): GregorianDate {
  let j = 4 * jdn + 139361631
  j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
  const i = div(mod(j, 1461), 4) * 5 + 308
  const gd = div(mod(i, 153), 5) + 1
  const gm = mod(div(i, 153), 12) + 1
  const gy = div(j, 1461) - 100100 + div(8 - gm, 6)
  return { gy, gm, gd }
}
function j2d(jy: number, jm: number, jd: number) {
  const r = jalCal(jy, true)
  return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1
}
function d2j(jdn: number): JalaliDate {
  const gy = d2g(jdn).gy
  let jy = gy - 621
  const r = jalCal(jy)
  const jdn1f = g2d(gy, 3, r.march)
  let k = jdn - jdn1f
  if (k >= 0) {
    if (k <= 185) return { jy, jm: 1 + div(k, 31), jd: mod(k, 31) + 1 }
    k -= 186
  }
  else {
    jy -= 1
    k += 179
    if (r.leap === 1) k += 1
  }
  return { jy, jm: 7 + div(k, 30), jd: mod(k, 30) + 1 }
}

export const toJalali = (gy: number, gm: number, gd: number): JalaliDate => d2j(g2d(gy, gm, gd))
export const toGregorian = (jy: number, jm: number, jd: number): GregorianDate => d2g(j2d(jy, jm, jd))

export const isJalaliLeap = (jy: number) => jalCal(jy).leap === 0
export function jalaliMonthLength(jy: number, jm: number) {
  if (jm <= 6) return 31
  if (jm <= 11) return 30
  return isJalaliLeap(jy) ? 30 : 29
}
/** 0 = Saturday … 6 = Friday (Persian week order) for a Jalali date. */
export function jalaliWeekday(jy: number, jm: number, jd: number) {
  const { gy, gm, gd } = toGregorian(jy, jm, jd)
  return (new Date(gy, gm - 1, gd).getDay() + 1) % 7
}

export const JALALI_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
export const JALALI_WEEKDAYS = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']

const pad = (n: number) => String(n).padStart(2, '0')

/** "2025-03-21" -> {jy,jm,jd}, or null if blank/invalid. */
export function isoToJalali(iso: string | null | undefined): JalaliDate | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '')
  if (!m) return null
  try {
    return toJalali(Number(m[1]), Number(m[2]), Number(m[3]))
  }
  catch {
    return null
  }
}
/** Jalali -> Gregorian ISO "YYYY-MM-DD". */
export function jalaliToIso(jy: number, jm: number, jd: number) {
  const { gy, gm, gd } = toGregorian(jy, jm, jd)
  return `${gy}-${pad(gm)}-${pad(gd)}`
}

const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
export const toPersianDigits = (s: string | number) => String(s).replace(/\d/g, d => FA_DIGITS[Number(d)]!)

/** Display form, e.g. "۱۴۰۴/۰۱/۰۱"; '' when blank, the raw text when it isn't an ISO date. */
export function formatJalali(iso: string | null | undefined): string {
  if (!iso) return ''
  const j = isoToJalali(iso)
  return j ? toPersianDigits(`${j.jy}/${pad(j.jm)}/${pad(j.jd)}`) : iso
}

/** Parses typed "1404/01/01" (Persian/Arabic digits, "/" "-" "." accepted) -> ISO, or null. */
export function parseJalaliInput(text: string): string | null {
  const latin = text
    .replace(/[۰-۹]/g, d => String(FA_DIGITS.indexOf(d)))
    .replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)))
    .trim()
  const m = /^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$/.exec(latin)
  if (!m) return null
  const jy = Number(m[1]); const jm = Number(m[2]); const jd = Number(m[3])
  if (jy < 1 || jm < 1 || jm > 12 || jd < 1) return null
  try {
    if (jd > jalaliMonthLength(jy, jm)) return null
    return jalaliToIso(jy, jm, jd)
  }
  catch {
    return null
  }
}

/** Every date and time in the app is Tehran time (UTC+03:30; Iran has no DST since 2022). */
export const TEHRAN_TZ = 'Asia/Tehran'

/** Today's calendar date in Tehran as "YYYY-MM-DD" -- NOT the browser's local day. */
export function todayIso() {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: TEHRAN_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
    .formatToParts(new Date())
  const get = (t: string) => parts.find(p => p.type === t)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}`
}

/**
 * A server timestamp (ISO, UTC -- the API always sends an offset; a bare value is read as UTC)
 * -> Jalali date + 24h time in Tehran, Persian digits: "۱۴۰۵/۰۸/۰۹ ۱۴:۳۰".
 */
export function formatTehranDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
  if (Number.isNaN(d.getTime())) return ''
  const f = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    timeZone: TEHRAN_TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(d)
  const g = (t: string) => f.find(p => p.type === t)?.value ?? ''
  return toPersianDigits(`${g('year')}/${g('month')}/${g('day')} ${g('hour')}:${g('minute')}`)
}

/** "YYYY-MM-DD" + optional "HH:MM" -> "۱۴۰۵/۰۸/۰۹ - ساعت ۰۹:۳۰". */
export function formatDueDateTime(date: string | null | undefined, time?: string | null): string {
  if (!date) return ''
  const day = formatJalali(date)
  return time ? `${day} - ساعت ${toPersianDigits(time.slice(0, 5))}` : day
}

/** Persian month + year for a Jalali position, e.g. "آبان ۱۴۰۵". */
export const jalaliMonthTitle = (jy: number, jm: number) => `${JALALI_MONTHS[jm - 1]} ${toPersianDigits(jy)}`