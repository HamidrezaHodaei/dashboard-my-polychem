// Projects the FUTURE occurrences of recurring tasks (the server only creates a copy when its day
// arrives), so the calendar can show every upcoming repeat, in any month. Mirrors
// back/app/modules/tasks/recurrence.py (months / years are Jalali; a day past the end of a month
// is clamped, and the series returns to its anchor day afterwards).
import { isoToJalali, jalaliMonthLength, jalaliToIso } from '~/utils/jalali'

export type RecurrenceUnit = 'DAY' | 'WEEK' | 'MONTH' | 'YEAR'

function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number) as [number, number, number]
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10)
}

export function nextOccurrence(iso: string, unit: RecurrenceUnit, interval: number, anchorDay?: number): string {
  if (unit === 'DAY') return addDays(iso, interval)
  if (unit === 'WEEK') return addDays(iso, interval * 7)
  const j = isoToJalali(iso)!
  const months = unit === 'YEAR' ? interval * 12 : interval
  const total = j.jy * 12 + (j.jm - 1) + months
  const ny = Math.floor(total / 12)
  const nm = (total % 12) + 1
  return jalaliToIso(ny, nm, Math.min(anchorDay || j.jd, jalaliMonthLength(ny, nm)))
}

export interface RecurringTemplate {
  id: string
  dueDate: string
  recurrence: { unit: RecurrenceUnit, interval: number, end_date: string | null, next_date?: string | null } | null
}

/** Every not-yet-created occurrence of `task` that falls inside [from, to] (ISO dates, inclusive). */
export function projectOccurrences(task: RecurringTemplate, from: string, to: string): string[] {
  const r = task.recurrence
  if (!r) return []
  const anchor = isoToJalali(task.dueDate)?.jd
  let cur = r.next_date || ''
  if (!cur) return []
  const out: string[] = []
  for (let guard = 0; guard < 4000 && cur <= to; guard++) {
    if (r.end_date && cur > r.end_date) break
    if (cur >= from) out.push(cur)
    cur = nextOccurrence(cur, r.unit, r.interval || 1, anchor)
  }
  return out
}
