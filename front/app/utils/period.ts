export type PeriodKey = 'today' | 'week' | 'month' | 'quarter' | 'year' | 'custom'

export const periodOptions: { value: PeriodKey; label: string }[] = [
  { value: 'today', label: 'امروز' },
  { value: 'week', label: 'این هفته' },
  { value: 'month', label: 'این ماه' },
  { value: 'quarter', label: 'این فصل' },
  { value: 'year', label: 'امسال' },
  { value: 'custom', label: 'بازه سفارشی' },
]

/** Returns [from, to] Date bounds for a named period, anchored to now. */
export function getPeriodRange(key: PeriodKey, customFrom?: string, customTo?: string): [Date, Date] {
  const now = new Date()
  const to = now
  let from = new Date(now)

  switch (key) {
    case 'today':
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      break
    case 'week':
      from = new Date(now)
      from.setDate(now.getDate() - 7)
      break
    case 'month':
      from = new Date(now.getFullYear(), now.getMonth(), 1)
      break
    case 'quarter':
      from = new Date(now)
      from.setMonth(now.getMonth() - 3)
      break
    case 'year':
      from = new Date(now.getFullYear(), 0, 1)
      break
    case 'custom':
      return [customFrom ? new Date(customFrom) : new Date(0), customTo ? new Date(customTo) : now]
  }
  return [from, to]
}

export function isWithinRange(dateIso: string, from: Date, to: Date): boolean {
  const d = new Date(dateIso).getTime()
  return d >= from.getTime() && d <= to.getTime()
}
