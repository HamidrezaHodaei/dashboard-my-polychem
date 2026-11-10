// Pure helpers behind the task analytics / Employee KPI screens.
import type { TaskEntity } from '~/stores/taskWorkspace'
import { JALALI_MONTHS, isoToJalali, todayIso } from '~/utils/jalali'

/** An ISO timestamp -> the calendar day in Tehran ("YYYY-MM-DD"). */
export function tehranDay(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Tehran' })
}

export interface Kpi {
  assigned: number
  completed: number
  pending: number
  overdue: number
  /** % of assigned tasks that are done */
  completionRate: number
  /** % of done tasks (that have a deadline) finished on or before it; null when none has a deadline */
  onTimeRate: number | null
  /** mean hours from creation to completion; null when nothing is done yet */
  avgCompletionHours: number | null
  byStatus: Record<'todo' | 'in-progress' | 'review' | 'done', number>
}

const live = (t: TaskEntity) => !t.isDraft && !t.isArchived

export function kpiFor(tasks: TaskEntity[], today = todayIso()): Kpi {
  const list = tasks.filter(live)
  const byStatus = { 'todo': 0, 'in-progress': 0, 'review': 0, 'done': 0 }
  for (const t of list) if (t.status in byStatus) byStatus[t.status as keyof typeof byStatus] += 1
  const done = list.filter(t => t.status === 'done')
  const withDue = done.filter(t => t.dueDate && t.completedAt)
  const onTime = withDue.filter(t => tehranDay(t.completedAt) <= t.dueDate).length
  const durations = done
    .filter(t => t.completedAt && t.createdAt)
    .map(t => (new Date(t.completedAt!).getTime() - new Date(t.createdAt).getTime()) / 36e5)
    .filter(h => h >= 0)
  return {
    assigned: list.length,
    completed: done.length,
    pending: list.length - done.length,
    overdue: list.filter(t => t.status !== 'done' && t.dueDate && t.dueDate < today).length,
    completionRate: list.length ? Math.round((done.length / list.length) * 100) : 0,
    onTimeRate: withDue.length ? Math.round((onTime / withDue.length) * 100) : null,
    avgCompletionHours: durations.length ? durations.reduce((a, b) => a + b, 0) / durations.length : null,
    byStatus,
  }
}

/** "۳ روز و ۴ ساعت" style text for a duration in hours. */
export function formatHours(h: number | null): string {
  if (h === null) return '—'
  if (h < 1) return 'کمتر از ۱ ساعت'
  if (h < 48) return `${Math.round(h)} ساعت`
  return `${(h / 24).toFixed(1)} روز`
}

export interface MonthPoint { key: string, label: string, created: number, completed: number }

/** Created vs completed tasks for the last `count` Jalali months (current month last). */
export function monthlyCreatedVsCompleted(tasks: TaskEntity[], count = 6, today = todayIso()): MonthPoint[] {
  const now = isoToJalali(today)!
  const months: MonthPoint[] = []
  for (let i = count - 1; i >= 0; i--) {
    const total = now.jy * 12 + (now.jm - 1) - i
    const jy = Math.floor(total / 12)
    const jm = (total % 12) + 1
    months.push({ key: `${jy}-${jm}`, label: JALALI_MONTHS[jm - 1]!, created: 0, completed: 0 })
  }
  const index = new Map(months.map(m => [m.key, m]))
  const bump = (iso: string | null | undefined, field: 'created' | 'completed') => {
    const j = isoToJalali(tehranDay(iso))
    if (j) {
      const m = index.get(`${j.jy}-${j.jm}`)
      if (m) m[field] += 1
    }
  }
  for (const t of tasks.filter(live)) {
    bump(t.createdAt, 'created')
    if (t.status === 'done') bump(t.completedAt, 'completed')
  }
  return months
}
