const TEHRAN_TZ_NOTIF = 'Asia/Tehran'

// LRI / PDI: isolate a run of digits so the bidi algorithm cannot flip the date and the time
// around each other inside right-to-left text ("۱۴۰۵/۰۸/۱۶ - ساعت ۱۷:۳۴" stays in that order).
const LRI = '\u2066'
const PDI = '\u2069'

function parseServerDate(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
}

/** "۱۴۰۵/۰۸/۱۶ - ساعت ۱۷:۳۴" (Tehran time), safe to drop into RTL text. */
export function formatNotificationDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = parseServerDate(iso)
  if (Number.isNaN(d.getTime())) return ''
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    timeZone: TEHRAN_TZ_NOTIF, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(d)
  const g = (t: string) => parts.find(p => p.type === t)?.value ?? ''
  const date = toPersianDigits(`${g('year')}/${g('month')}/${g('day')}`)
  const time = toPersianDigits(`${g('hour')}:${g('minute')}`)
  return `${LRI}${date}${PDI} - ساعت ${LRI}${time}${PDI}`
}

/** "همین حالا / ۵ دقیقه پیش / ۳ ساعت پیش / ۲ روز پیش", then the full Jalali date. */
export function formatNotificationTime(iso: string): string {
  const diff = Date.now() - parseServerDate(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'همین حالا'
  if (minutes < 60) return `${LRI}${toPersianDigits(minutes)}${PDI} دقیقه پیش`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${LRI}${toPersianDigits(hours)}${PDI} ساعت پیش`
  const days = Math.floor(hours / 24)
  return days < 7 ? `${LRI}${toPersianDigits(days)}${PDI} روز پیش` : formatNotificationDateTime(iso)
}
