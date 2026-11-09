import type { MovementType, BadgeTone } from '~/types'

const meta: Record<MovementType, { label: string; tone: BadgeTone }> = {
  inbound: { label: 'ورودی', tone: 'success' },
  outbound: { label: 'خروجی', tone: 'info' },
  transfer: { label: 'انتقال', tone: 'amber' },
  adjustment: { label: 'اصلاح', tone: 'warn' },
  return: { label: 'مرجوعی', tone: 'success' },
  reservation: { label: 'رزرو', tone: 'neutral' },
  release: { label: 'آزادسازی', tone: 'neutral' }
}

export function useMovementMeta(type: MovementType) {
  return meta[type]
}
