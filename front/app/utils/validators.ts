export type Validator = (value: unknown) => string | true

export const required = (label: string): Validator => (value) => {
  if (value === null || value === undefined || value === '') return `${label} الزامی است.`
  return true
}

export const isPositive = (label: string): Validator => (value) => {
  const n = Number(value)
  if (Number.isNaN(n)) return `${label} باید عدد باشد.`
  if (n < 0) return `${label} نمی‌تواند منفی باشد.`
  return true
}

export const isPhone = (label = 'شماره تماس'): Validator => (value) => {
  if (!value) return true
  const s = String(value).replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  if (!/^0\d{9,10}$/.test(s)) return `${label} معتبر نیست.`
  return true
}

export const isEmail = (label = 'ایمیل'): Validator => (value) => {
  if (!value) return true
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))) return `${label} معتبر نیست.`
  return true
}

/** Run a value through a list of validators; returns the first error or null. */
export function validate(value: unknown, validators: Validator[]): string | null {
  for (const v of validators) {
    const result = v(value)
    if (result !== true) return result
  }
  return null
}
