import { format } from 'date-fns'
import type { Period } from '~/types'

// `formatCurrency` used to be defined here too (USD-only, from the original
// dashboard template) but nothing explicitly imported it, and it was
// silently winning Nuxt's auto-import over `~/utils/financeFormat`'s
// Toman/Rial-aware version for every call site that doesn't explicitly
// import it. Removed in favor of the single definition in financeFormat.ts.

export function formatDateByPeriod(date: Date): Record<Period, string> {
  return {
    daily: format(date, 'd MMM'),
    weekly: format(date, 'd MMM'),
    monthly: format(date, 'MMM yyy'),
  }
}

export async function sleep(ms = 1000) {
  return await new Promise(function (resolve) {
    setTimeout(resolve, ms)
  })
}

export function getAvatarFallback(name: string) {
  return name
    .split(' ')
    .map(name => name.charAt(0))
    .join('')
    .substring(0, 2)
}

export function getFlag(countryCode: string) {
  const regex = /^[A-Z]{2}$/.test(countryCode)
  if (!countryCode || !regex) return
  return String.fromCodePoint(...countryCode.split('').map(char => 127397 + char.charCodeAt(0)))
}
