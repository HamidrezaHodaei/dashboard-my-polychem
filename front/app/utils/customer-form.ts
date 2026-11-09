/**
 * Shared form logic for the admin customer wizard (create + edit) -- CRM module.
 * Nuxt auto-imports everything exported from `utils/`.
 *
 * Mirrors the backend rules in app/modules/customers/schemas.py so people get an
 * instant, per-step message; the server enforces the same rules.
 * Dates are Gregorian ISO strings ('YYYY-MM-DD' or ''); the UI shows them in
 * Jalali through <JalaliDateInput>.
 */
import { toLatinDigits } from '~/utils/supplier-form'
import type {
  AcquaintanceSource, ActivityType, CommercialStatus, CreditRating, Customer, OperationalStatus, PaymentType,
  PurchaseMethod, QuantityUnit,
} from '~/stores/customer'

export const IRAN_PROVINCES = [
  'آذربایجان شرقی', 'آذربایجان غربی', 'اردبیل', 'اصفهان', 'البرز', 'ایلام', 'بوشهر', 'تهران',
  'چهارمحال و بختیاری', 'خراسان جنوبی', 'خراسان رضوی', 'خراسان شمالی', 'خوزستان', 'زنجان', 'سمنان',
  'سیستان و بلوچستان', 'فارس', 'قزوین', 'قم', 'کردستان', 'کرمان', 'کرمانشاه', 'کهگیلویه و بویراحمد',
  'گلستان', 'گیلان', 'لرستان', 'مازندران', 'مرکزی', 'هرمزگان', 'همدان', 'یزد',
]

/** Fallback labels (the page prefers the API's /options so they never drift). */
export const COMMERCIAL_STATUS_LABELS: Record<CommercialStatus, string> = {
  NO_ACTION: 'بدون اقدام',
  MARKETING_NEGOTIATION: 'در حال مذاکره و بازاریابی',
  SAMPLE_SENT: 'ارسال نمونه',
  AWAITING_SAMPLE_APPROVAL: 'منتظر تایید نمونه',
  SALES_NEGOTIATION: 'در حال مذاکره فروش',
  ACQUIRED: 'مشتری جذب شده',
  REPEAT_ACTIVE: 'مشتری تکرار شونده - فعال',
  INACTIVE_LOST: 'غیرفعال - از دست رفته',
  POTENTIAL: 'بالقوه',
}
export const OPERATIONAL_LABELS: Record<OperationalStatus, string> = { ACTIVE: 'فعال', INACTIVE: 'غیرفعال' }
export const ACTIVITY_LABELS: Record<ActivityType, string> = {
  PRODUCER: 'تولید کننده', DISTRIBUTOR: 'توزیع کننده', EXPORTER: 'صادر کننده',
}
export const PURCHASE_LABELS: Record<PurchaseMethod, string> = { OFFICIAL: 'رسمی', UNOFFICIAL: 'غیر رسمی', BOTH: 'هر دو' }
export const PERIOD_LABELS = { MONTHLY: 'ماهانه', YEARLY: 'سالانه' } as const

/** Unit of every produced / consumed amount (whole numbers). TON is the default. */
export const UNIT_LABELS: Record<QuantityUnit, string> = { TON: 'تن', KG: 'کیلوگرم' }
export const normalizeUnit = (v: unknown): QuantityUnit => (v === 'KG' ? 'KG' : 'TON')

/** سمت افراد تماس -- a fixed list plus "سایر" (free text). Keep in sync with the API's /options. */
export const CONTACT_POSITIONS = [
  'مالک / مؤسس',
  'سهام‌دار',
  'مدیرعامل',
  'رئیس هیئت‌مدیره',
  'عضو هیئت‌مدیره',
  'مدیر مالی',
  'حسابدار',
  'مدیر بازرگانی',
  'مدیر فروش',
  'مدیر خرید و تدارکات',
  'کارشناس مالی',
  'کارشناس خرید',
  'کارشناس فروش',
  'نماینده قانونی',
  'صاحب امضای مجاز',
  'تصمیم‌گیرنده خرید',
  'تأییدکننده سفارش',
  'تأییدکننده پرداخت',
  'مشاور',
  'انباردار',
  'کمک‌انباردار',
  'کارشناس انبار',
]
export const POSITION_OTHER = '__other__'

/** منبع آشنایی با مشتری ('OTHER' comes with a free-text description). */
export const SOURCE_LABELS: Record<AcquaintanceSource, string> = {
  WEBSITE: 'وب‌سایت شرکت',
  GOOGLE_SEARCH: 'جست‌وجوی گوگل',
  SOCIAL_MEDIA: 'شبکه‌های اجتماعی',
  EXHIBITION: 'نمایشگاه و همایش',
  CUSTOMER_REFERRAL: 'معرفی مشتریان دیگر',
  PARTNER_REFERRAL: 'معرفی همکاران و ارتباطات تجاری',
  INBOUND_CALL: 'تماس ورودی مشتری',
  OUTBOUND_CALL: 'تماس خروجی شرکت',
  FIELD_MARKETING: 'بازاریابی حضوری',
  TELEMARKETING: 'بازاریابی تلفنی',
  EMAIL_CAMPAIGN: 'ایمیل تبلیغاتی',
  MESSENGERS: 'پیام‌رسان‌ها',
  COMPANY_DATABASE: 'بانک اطلاعاتی شرکت',
  PREVIOUS_CONNECTIONS: 'ارتباطات قبلی',
  OTHER: 'سایر',
}
/** شرایط پرداخت. Credit types ask for a duration of 1-12 months or a free-text "other". */
export const PAYMENT_LABELS: Record<PaymentType, string> = { CASH: 'نقدی', CREDIT: 'اعتباری', CASH_CREDIT: 'نقدی - اعتباری' }
export const CREDIT_MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
export const isCreditPayment = (t: PaymentType | '') => t === 'CREDIT' || t === 'CASH_CREDIT'
/** وضعیت اعتباری مشتری. */
export const CREDIT_RATING_LABELS: Record<CreditRating, string> = {
  EXCELLENT: 'عالی — پرداخت منظم و به‌موقع',
  GOOD: 'خوب — تأخیرهای جزئی و محدود',
  AVERAGE: 'متوسط — تأخیرهای تکرارشونده',
  WEAK: 'ضعیف — تأخیرهای طولانی در پرداخت',
  BAD_DEBTOR: 'بدحساب — بدهی معوق قابل‌توجه یا عدم پایبندی به تعهدات',
  NO_HISTORY: 'فاقد سابقه اعتباری — هنوز معامله اعتباری نداشته است',
  NEEDS_REVIEW: 'نیازمند بررسی — اطلاعات کافی برای ارزیابی وجود ندارد',
}

/** نوع تحویل. The two fixed choices are stored as their label; "other" is a free-text value. */
export type DeliveryChoice = '' | 'CUSTOMER_FACTORY' | 'SELLER_FACTORY' | 'OTHER'
export const DELIVERY_LABELS: Record<Exclude<DeliveryChoice, '' | 'OTHER'>, string> = {
  CUSTOMER_FACTORY: 'درب کارخانه مشتری',
  SELLER_FACTORY: 'درب کارخانه فروشنده',
}

/** Colour hint per pipeline stage (Badge variants only, so it works with any theme). */
export function commercialBadgeVariant(s: CommercialStatus): 'default' | 'secondary' | 'outline' | 'destructive' {
  if (s === 'ACQUIRED' || s === 'REPEAT_ACTIVE') return 'default'
  if (s === 'INACTIVE_LOST') return 'destructive'
  if (s === 'NO_ACTION' || s === 'POTENTIAL') return 'outline'
  return 'secondary'
}

/* ───────────── form state ───────────── */
export interface CustomerContactForm {
  first_name: string
  last_name: string
  position_choice: string // one of CONTACT_POSITIONS, POSITION_OTHER, or ''
  position_other: string // typed by hand when position_choice === POSITION_OTHER
  email: string
  mobile: string
  landline: string
  birth_date: string // ISO, optional, for every contact person (legal and individual customers)
}
/** `amount` is a whole number PER YEAR, in `unit`. */
export interface ProducedForm { name: string, amount: string, unit: QuantityUnit }
export interface ConsumedForm { name: string, grade_specs: string, monthly: string, annual: string, unit: QuantityUnit }
/** A supplier the customer buys from + which consumed products (grades) come from it. */
export interface SupplierGradeForm { product: string, grade: string } // typed by hand, independent of the consumed products
export interface CurrentSupplierForm { name: string, supplier_id: number | null, grades: SupplierGradeForm[] }
export interface ContactLogForm { date: string, note: string }
export interface IndustryForm { category: string, subcategory: string }

export interface CustomerFormState {
  // step 1
  customer_type: 'INDIVIDUAL' | 'LEGAL'
  company_name: string
  company_national_id: string
  registration_number: string
  economic_id: string
  activity_start_date: string
  first_name: string
  last_name: string
  national_id: string
  brand_name: string // نام شرکت یا برند -- individual customers only
  contacts: CustomerContactForm[]
  head_office_address: string
  head_office_postal_code: string
  factory_address: string
  factory_postal_code: string
  acquaintance_source: AcquaintanceSource | ''
  acquaintance_source_other: string
  // step 2
  industries: IndustryForm[]
  activity_types: ActivityType[]
  produced_products: ProducedForm[]
  production_lines_count: string // تعداد خطوط تولید (typed by hand)
  production_line_names: string[] // free list of production line names (add / remove by hand)
  factory_province: string
  factory_city: string
  factory_location: string
  latitude: string
  longitude: string
  // step 3
  consumed_products: ConsumedForm[]
  current_suppliers: CurrentSupplierForm[]
  // step 4
  commercial_status: CommercialStatus
  operational_status: OperationalStatus
  contact_log: ContactLogForm[]
  first_purchase_date: string
  last_purchase_date: string
  assigned_to_user_id: number | null
  inactive_reason: string
  // step 5
  payment_type: PaymentType | ''
  credit_months: string // '' | '1'..'12' | 'OTHER'
  credit_other: string
  payment_terms: string
  purchase_method: PurchaseMethod | ''
  delivery_choice: DeliveryChoice
  delivery_other: string
  unloading_location: string
  approved_credit_limit: string
  credit_rating: CreditRating | ''
  // step 6
  internal_notes: string
  last_negotiation_date: string
  last_negotiation_result: string
  next_action: string
  next_follow_up_date: string
  registration_date: string
  finalize: boolean
}

export const blankContact = (): CustomerContactForm => ({
  first_name: '', last_name: '', position_choice: '', position_other: '', email: '', mobile: '', landline: '', birth_date: '',
})
export const blankIndustry = (): IndustryForm => ({ category: '', subcategory: '' })
export const blankProduced = (): ProducedForm => ({ name: '', amount: '', unit: 'TON' })
export const blankConsumed = (): ConsumedForm => ({ name: '', grade_specs: '', monthly: '', annual: '', unit: 'TON' })
export const blankSupplierGrade = (): SupplierGradeForm => ({ product: '', grade: '' })
export const blankCurrentSupplier = (): CurrentSupplierForm => ({ name: '', supplier_id: null, grades: [blankSupplierGrade()] })
export const blankLog = (): ContactLogForm => ({ date: '', note: '' })

export function blankCustomerForm(): CustomerFormState {
  return {
    customer_type: 'LEGAL',
    company_name: '', company_national_id: '', registration_number: '', economic_id: '', activity_start_date: '',
    first_name: '', last_name: '', national_id: '', brand_name: '',
    contacts: [blankContact()],
    head_office_address: '', head_office_postal_code: '', factory_address: '', factory_postal_code: '',
    acquaintance_source: '', acquaintance_source_other: '',
    industries: [blankIndustry()], activity_types: [], produced_products: [],
    production_lines_count: '',
    production_line_names: [],
    factory_province: '', factory_city: '', factory_location: '', latitude: '', longitude: '',
    consumed_products: [blankConsumed()], current_suppliers: [],
    commercial_status: 'NO_ACTION', operational_status: 'ACTIVE', contact_log: [],
    first_purchase_date: '', last_purchase_date: '', assigned_to_user_id: null, inactive_reason: '',
    payment_type: '', credit_months: '', credit_other: '', payment_terms: '', purchase_method: '',
    delivery_choice: '', delivery_other: '', unloading_location: '', approved_credit_limit: '', credit_rating: '',
    internal_notes: '', last_negotiation_date: '', last_negotiation_result: '', next_action: '',
    next_follow_up_date: '', registration_date: '', finalize: false,
  }
}

const str = (v: unknown) => (typeof v === 'string' ? v : '')
const numStr = (v: unknown) => (typeof v === 'number' ? String(v) : '')

/** Stored delivery text -> select choice (+ free text when it isn't one of the fixed choices). */
function deliveryToForm(v: string): Pick<CustomerFormState, 'delivery_choice' | 'delivery_other'> {
  const text = v.trim()
  if (!text) return { delivery_choice: '', delivery_other: '' }
  const hit = (Object.keys(DELIVERY_LABELS) as (keyof typeof DELIVERY_LABELS)[]).find(k => DELIVERY_LABELS[k] === text)
  return hit ? { delivery_choice: hit, delivery_other: '' } : { delivery_choice: 'OTHER', delivery_other: text }
}

/** Stored position text -> select choice (+ free text when it is not one of the fixed choices). */
function positionToForm(v: string): Pick<CustomerContactForm, 'position_choice' | 'position_other'> {
  const text = v.trim()
  if (!text) return { position_choice: '', position_other: '' }
  return CONTACT_POSITIONS.includes(text)
    ? { position_choice: text, position_other: '' }
    : { position_choice: POSITION_OTHER, position_other: text }
}

export const MAX_PRODUCTION_LINES = 200

/** API customer -> editable form state. */
export function customerToForm(c: Customer): CustomerFormState {
  // Older records may still carry free-text acquaintance sources: show them as "Other".
  const src = str(c.acquaintance_source)
  const srcKnown = src in SOURCE_LABELS
  // `category`/`subcategory` mirror the first industry; used only when a record has no `industries`.
  const legacy = c as Customer & { category?: string | null, subcategory?: string | null }
  const industries: IndustryForm[] = c.industries?.length
    ? c.industries.map(i => ({ category: str(i.category), subcategory: str(i.subcategory) }))
    : legacy.category ? [{ category: str(legacy.category), subcategory: str(legacy.subcategory) }] : [blankIndustry()]

  return {
    ...blankCustomerForm(),
    customer_type: c.customer_type,
    company_name: str(c.company_name), company_national_id: str(c.company_national_id),
    registration_number: str(c.registration_number), economic_id: str(c.economic_id),
    activity_start_date: str(c.activity_start_date),
    first_name: str(c.first_name), last_name: str(c.last_name), national_id: str(c.national_id),
    brand_name: str(c.brand_name),
    contacts: c.contacts?.length
      ? c.contacts.map((p): CustomerContactForm => ({
          first_name: str(p.first_name), last_name: str(p.last_name), ...positionToForm(str(p.position)),
          email: str(p.email), mobile: str(p.mobile), landline: str(p.landline), birth_date: str(p.birth_date),
        }))
      : [blankContact()],
    head_office_address: str(c.head_office_address), head_office_postal_code: str(c.head_office_postal_code),
    factory_address: str(c.factory_address), factory_postal_code: str(c.factory_postal_code),
    acquaintance_source: !src ? '' : srcKnown ? src as AcquaintanceSource : 'OTHER',
    acquaintance_source_other: srcKnown ? str(c.acquaintance_source_other) : src,
    industries,
    activity_types: [...(c.activity_types ?? [])],
    produced_products: (c.produced_products ?? []).map((p): ProducedForm => ({
      name: str(p.name), amount: numStr(p.amount), unit: normalizeUnit(p.unit),
    })),
    production_lines_count: numStr(c.production_lines_count),
    production_line_names: Array.isArray(c.production_line_names) ? c.production_line_names.map(str) : [],
    factory_province: str(c.factory_province), factory_city: str(c.factory_city),
    factory_location: str(c.factory_location), latitude: numStr(c.latitude), longitude: numStr(c.longitude),
    consumed_products: c.consumed_products?.length
      ? c.consumed_products.map((p): ConsumedForm => ({
          name: str(p.name), grade_specs: str(p.grade_specs),
          monthly: numStr(p.monthly_consumption), annual: numStr(p.annual_consumption), unit: normalizeUnit(p.unit),
        }))
      : [blankConsumed()],
    current_suppliers: (c.current_suppliers ?? []).map((s): CurrentSupplierForm => ({
      name: str(s.name), supplier_id: s.supplier_id ?? null,
      grades: (s.grades ?? []).map((g): SupplierGradeForm => ({ product: str(g.product), grade: str(g.grade) })),
    })),
    commercial_status: c.commercial_status, operational_status: c.operational_status,
    contact_log: (c.contact_log ?? []).map((l): ContactLogForm => ({ date: str(l.date), note: str(l.note) })),
    first_purchase_date: str(c.first_purchase_date), last_purchase_date: str(c.last_purchase_date),
    assigned_to_user_id: c.assigned_to_user_id ?? null, inactive_reason: str(c.inactive_reason),
    payment_type: c.payment_type ?? '',
    credit_months: c.credit_other ? 'OTHER' : c.credit_months ? String(c.credit_months) : '',
    credit_other: str(c.credit_other),
    payment_terms: str(c.payment_terms), purchase_method: c.purchase_method ?? '',
    ...deliveryToForm(str(c.delivery_type)),
    unloading_location: str(c.unloading_location),
    approved_credit_limit: numStr(c.approved_credit_limit), credit_rating: c.credit_rating ?? '',
    internal_notes: str(c.internal_notes), last_negotiation_date: str(c.last_negotiation_date),
    last_negotiation_result: str(c.last_negotiation_result), next_action: str(c.next_action),
    next_follow_up_date: str(c.next_follow_up_date), registration_date: str(c.registration_date),
    finalize: false,
  }
}

/* ───────────── form -> API ───────────── */
const nullIfBlank = (v: string) => (v.trim() ? v.trim() : null)
const digitsOrNull = (v: string) => nullIfBlank(toLatinDigits(v).replace(/[\s-]/g, ''))

/** '1,250.5' / '۱۲۵۰' / '١٢٥٠' -> 1250.5; '' -> null; garbage -> NaN (validation catches it first). */
export function parseNumber(v: string): number | null {
  const t = toLatinDigits(v).replace(/[,٬\s]/g, '').replace('٫', '.')
  if (!t) return null
  return /^\d+(\.\d+)?$/.test(t) ? Number(t) : Number.NaN
}

/** Amounts are whole numbers: '1,250' / '۱۲۵۰' -> 1250; '' -> null; '12.5' or garbage -> NaN (validation catches it first). */
export function parseWhole(v: string): number | null {
  const n = parseNumber(v)
  return n === null ? null : Number.isInteger(n) ? n : Number.NaN
}

/** ظرفیت تولید کارخانه: the yearly sum of the produced products, in tons (kilograms converted). null = nothing entered. */
export function totalCapacityTons(rows: ProducedForm[]): number | null {
  let kg = 0
  let any = false
  for (const p of rows) {
    const n = parseWhole(p.amount)
    if (n === null || Number.isNaN(n)) continue
    any = true
    kg += p.unit === 'KG' ? n : n * 1000
  }
  return any ? Math.round(kg) / 1000 : null
}

/** Form state -> body for POST /api/customers or PATCH /api/customers/:id. */
export function formToPayload(f: CustomerFormState) {
  const legal = f.customer_type === 'LEGAL'
  const credit = isCreditPayment(f.payment_type)
  return {
    customer_type: f.customer_type,
    // identity fields of the other type are cleared (matters when editing)
    company_name: legal ? nullIfBlank(f.company_name) : null,
    company_national_id: legal ? digitsOrNull(f.company_national_id) : null,
    registration_number: legal ? digitsOrNull(f.registration_number) : null,
    economic_id: legal ? digitsOrNull(f.economic_id) : null,
    activity_start_date: legal ? f.activity_start_date || null : null,
    first_name: legal ? null : nullIfBlank(f.first_name),
    last_name: legal ? null : nullIfBlank(f.last_name),
    national_id: legal ? null : digitsOrNull(f.national_id),
    brand_name: legal ? null : nullIfBlank(f.brand_name),
    contacts: f.contacts.map(c => ({
      first_name: c.first_name.trim(),
      last_name: c.last_name.trim(),
      position: (c.position_choice === POSITION_OTHER ? c.position_other : c.position_choice).trim(),
      email: nullIfBlank(c.email),
      mobile: digitsOrNull(c.mobile),
      landline: digitsOrNull(c.landline),
      birth_date: c.birth_date || null,
    })),
    head_office_address: nullIfBlank(f.head_office_address),
    head_office_postal_code: digitsOrNull(f.head_office_postal_code),
    factory_address: nullIfBlank(f.factory_address),
    factory_postal_code: digitsOrNull(f.factory_postal_code),
    acquaintance_source: f.acquaintance_source || null,
    acquaintance_source_other: f.acquaintance_source === 'OTHER' ? nullIfBlank(f.acquaintance_source_other) : null,

    industries: f.industries.filter(i => i.category.trim()).map(i => ({
      category: i.category.trim(), subcategory: nullIfBlank(i.subcategory),
    })),
    activity_types: f.activity_types,
    // production is always per year; the factory capacity is derived by the server
    produced_products: f.produced_products.filter(p => p.name.trim()).map(p => ({
      name: p.name.trim(), amount: parseWhole(p.amount), unit: p.unit,
    })),
    // تعداد خطوط تولید is typed by hand; when left empty it falls back to the number of named lines
    production_lines_count: parseWhole(f.production_lines_count) ?? (f.production_line_names.filter(n => n.trim()).length || null),
    production_line_names: f.production_line_names.map(n => n.trim()).filter(Boolean),
    factory_province: nullIfBlank(f.factory_province),
    factory_city: nullIfBlank(f.factory_city),
    factory_location: nullIfBlank(f.factory_location),
    latitude: parseNumber(f.latitude),
    longitude: parseNumber(f.longitude),

    consumed_products: f.consumed_products.filter(p => p.name.trim()).map(p => ({
      name: p.name.trim(), grade_specs: nullIfBlank(p.grade_specs),
      monthly_consumption: parseWhole(p.monthly), annual_consumption: parseWhole(p.annual), unit: p.unit,
    })),
    current_suppliers: f.current_suppliers
      .filter(s => s.supplier_id || s.name.trim())
      .map((s) => {
        // grades are typed by hand; fully blank rows are dropped
        const grades = s.grades
          .filter(g => g.product.trim() || g.grade.trim())
          .map(g => ({ product: g.product.trim(), grade: nullIfBlank(g.grade) }))
        return s.supplier_id ? { supplier_id: s.supplier_id, grades } : { name: s.name.trim(), grades }
      }),

    commercial_status: f.commercial_status,
    operational_status: f.operational_status,
    contact_log: f.contact_log.filter(l => l.date).map(l => ({ date: l.date, note: nullIfBlank(l.note) })),
    first_purchase_date: f.first_purchase_date || null,
    last_purchase_date: f.last_purchase_date || null,
    assigned_to_user_id: f.assigned_to_user_id,
    inactive_reason: nullIfBlank(f.inactive_reason),

    payment_type: f.payment_type || null,
    credit_months: credit && f.credit_months && f.credit_months !== 'OTHER' ? Number(f.credit_months) : null,
    credit_other: credit && f.credit_months === 'OTHER' ? nullIfBlank(f.credit_other) : null,
    payment_terms: nullIfBlank(f.payment_terms),
    purchase_method: f.purchase_method || null,
    delivery_type: f.delivery_choice === 'OTHER'
      ? nullIfBlank(f.delivery_other)
      : f.delivery_choice ? DELIVERY_LABELS[f.delivery_choice] : null,
    unloading_location: nullIfBlank(f.unloading_location),
    approved_credit_limit: parseNumber(f.approved_credit_limit),
    credit_rating: f.credit_rating || null,

    internal_notes: nullIfBlank(f.internal_notes),
    last_negotiation_date: f.last_negotiation_date || null,
    last_negotiation_result: nullIfBlank(f.last_negotiation_result),
    next_action: nullIfBlank(f.next_action),
    next_follow_up_date: f.next_follow_up_date || null,
  }
}

/* ───────────── validation (one block per wizard step) ───────────── */
export type StepErrors = Record<string, string>

const emailOk = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim())
const phoneOk = (raw: string) => /^\+?\d{7,15}$/.test(toLatinDigits(raw).replace(/[\s-]/g, ''))
const postalOk = (raw: string) => /^\d{10}$/.test(toLatinDigits(raw).replace(/[\s-]/g, ''))
const isBadNumber = (v: string) => v.trim() !== '' && Number.isNaN(parseNumber(v))
const isBadWhole = (v: string) => v.trim() !== '' && Number.isNaN(parseWhole(v))

export function validateCustomerStep(step: number, f: CustomerFormState): StepErrors {
  const e: StepErrors = {}

  if (step === 0) {
    if (f.customer_type === 'LEGAL') {
      if (!f.company_name.trim()) e.company_name = 'وارد کردن نام شرکت الزامی است.'
      const id = toLatinDigits(f.company_national_id.trim())
      if (!id) e.company_national_id = 'وارد کردن شناسه ملی الزامی است.'
      else if (!/^\d{11}$/.test(id)) e.company_national_id = 'شناسه ملی باید ۱۱ رقم باشد.'
    }
    else {
      if (!f.first_name.trim()) e.first_name = 'وارد کردن نام الزامی است.'
      if (!f.last_name.trim()) e.last_name = 'وارد کردن نام خانوادگی الزامی است.'
      const id = toLatinDigits(f.national_id.trim())
      if (!id) e.national_id = 'وارد کردن کد ملی الزامی است.'
      else if (!/^\d{10}$/.test(id)) e.national_id = 'کد ملی باید ۱۰ رقم باشد.'
    }
    if (f.head_office_postal_code.trim() && !postalOk(f.head_office_postal_code)) e.head_office_postal_code = 'کد پستی باید ۱۰ رقم باشد.'
    if (f.factory_postal_code.trim() && !postalOk(f.factory_postal_code)) e.factory_postal_code = 'کد پستی باید ۱۰ رقم باشد.'
    if (f.acquaintance_source === 'OTHER' && !f.acquaintance_source_other.trim()) {
      e.acquaintance_source_other = 'منبع آشنایی را توضیح دهید.'
    }

    if (!f.contacts.length) e.contacts = 'حداقل یک فرد تماس لازم است.'
    f.contacts.forEach((c, i) => {
      if (!c.first_name.trim()) e[`contact.${i}.first_name`] = 'وارد کردن نام الزامی است.'
      if (!c.last_name.trim()) e[`contact.${i}.last_name`] = 'وارد کردن نام خانوادگی الزامی است.'
      if (!c.position_choice) e[`contact.${i}.position`] = 'انتخاب سمت الزامی است.'
      else if (c.position_choice === POSITION_OTHER && !c.position_other.trim()) e[`contact.${i}.position`] = 'سمت را بنویسید.'
      if (c.email.trim() && !emailOk(c.email)) e[`contact.${i}.email`] = 'یک نشانی ایمیل معتبر وارد کنید.'
      const mobile = c.mobile.trim()
      const landline = c.landline.trim()
      if (!mobile && !landline) e[`contact.${i}.numbers`] = 'وارد کردن حداقل یک شماره موبایل یا تلفن ثابت الزامی است.'
      else if (mobile && !phoneOk(mobile)) e[`contact.${i}.numbers`] = `شماره موبایل «${mobile}» معتبر نیست.`
      else if (landline && !phoneOk(landline)) e[`contact.${i}.numbers`] = `شماره تلفن ثابت «${landline}» معتبر نیست.`
    })
  }

  if (step === 1) {
    if (!f.industries.some(i => i.category.trim())) e.industries = 'انتخاب حداقل یک صنعت فعالیت الزامی است.'
    const seen = new Set<string>()
    f.industries.forEach((r, i) => {
      if (!r.category.trim()) {
        if (r.subcategory.trim()) e[`industry.${i}.category`] = 'ابتدا صنعت اصلی را انتخاب کنید.'
        return
      }
      const key = `${r.category.trim()}|${r.subcategory.trim()}`
      if (seen.has(key)) e[`industry.${i}.category`] = 'این صنعت قبلاً اضافه شده است.'
      seen.add(key)
    })
    if (!f.activity_types.length) e.activity_types = 'حداقل یک نوع فعالیت را انتخاب کنید.'
    if (!f.factory_province.trim()) e.factory_province = 'انتخاب استان الزامی است.'
    if (!f.factory_city.trim()) e.factory_city = 'وارد کردن شهر الزامی است.'
    if (f.production_lines_count.trim()) {
      const n = parseWhole(f.production_lines_count)
      if (n === null || n === undefined || Number.isNaN(n) || n < 0) e.production_lines_count = 'تعداد خطوط تولید باید یک عدد صحیح و نامنفی باشد.'
    }
    if (f.production_line_names.filter(n => n.trim()).length > MAX_PRODUCTION_LINES) {
      e.production_line_names = `حداکثر ${MAX_PRODUCTION_LINES} خط تولید قابل ثبت است.`
    }
    const lat = parseNumber(f.latitude)
    const lng = parseNumber(f.longitude)
    if (f.latitude.trim() && (lat === null || Number.isNaN(lat) || lat > 90)) e.latitude = 'عرض جغرافیایی باید بین ۰ تا ۹۰ باشد.'
    if (f.longitude.trim() && (lng === null || Number.isNaN(lng) || lng > 180)) e.longitude = 'طول جغرافیایی باید بین ۰ تا ۱۸۰ باشد.'
    f.produced_products.forEach((p, i) => {
      const active = p.name.trim() || p.amount.trim()
      if (!active) return
      if (!p.name.trim()) e[`produced.${i}.name`] = 'وارد کردن نام محصول الزامی است.'
      if (isBadWhole(p.amount)) e[`produced.${i}.amount`] = 'میزان تولید سالانه باید عدد صحیح باشد.'
    })
  }

  if (step === 2) {
    const rows = f.consumed_products.filter(p => p.name.trim() || p.monthly.trim() || p.annual.trim() || p.grade_specs.trim())
    if (!rows.length) e.consumed = 'حداقل یک محصول مصرفی را اضافه کنید.'
    f.consumed_products.forEach((p, i) => {
      const active = p.name.trim() || p.monthly.trim() || p.annual.trim() || p.grade_specs.trim()
      if (!active) return
      if (!p.name.trim()) e[`consumed.${i}.name`] = 'وارد کردن نام محصول الزامی است.'
      if (!p.monthly.trim()) e[`consumed.${i}.monthly`] = 'مصرف ماهانه الزامی است.'
      else if (isBadWhole(p.monthly)) e[`consumed.${i}.monthly`] = 'مصرف ماهانه باید عدد صحیح باشد.'
      if (!p.annual.trim()) e[`consumed.${i}.annual`] = 'مصرف سالانه الزامی است.'
      else if (isBadWhole(p.annual)) e[`consumed.${i}.annual`] = 'مصرف سالانه باید عدد صحیح باشد.'
    })
    f.current_suppliers.forEach((s, i) => {
      s.grades.forEach((g, j) => {
        if (g.grade.trim() && !g.product.trim()) e[`supplier.${i}.grade.${j}`] = 'نام محصول را وارد کنید.'
      })
    })
  }

  if (step === 3) {
    f.contact_log.forEach((l, i) => {
      if (l.note.trim() && !l.date) e[`log.${i}.date`] = 'تاریخ تماس را وارد کنید.'
    })
    if (f.first_purchase_date && f.last_purchase_date && f.last_purchase_date < f.first_purchase_date) {
      e.last_purchase_date = 'تاریخ آخرین خرید نمی‌تواند قبل از اولین خرید باشد.'
    }
  }

  if (step === 4) {
    if (isCreditPayment(f.payment_type)) {
      if (!f.credit_months) e.credit_months = 'مدت اعتبار را انتخاب کنید.'
      else if (f.credit_months === 'OTHER' && !f.credit_other.trim()) e.credit_other = 'مدت اعتبار را وارد کنید.'
    }
    if (f.delivery_choice === 'OTHER' && !f.delivery_other.trim()) e.delivery_other = 'نوع تحویل را بنویسید.'
    if (isBadNumber(f.approved_credit_limit)) e.approved_credit_limit = 'سقف اعتبار باید عدد باشد.'
  }

  return e
}