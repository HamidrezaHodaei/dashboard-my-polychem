/**
 * Shared form logic for the admin supplier wizard (create + edit).
 * Nuxt auto-imports everything exported from `utils/`.
 *
 * The option lists below mirror the public registration page so a supplier
 * looks identical whether staff typed it in or the supplier did.
 * (Categories are NOT here -- they are admin-managed and come from the API.)
 */

export const ACTIVITY_TYPE_OPTIONS = ['تولید کننده', 'توزیع کننده', 'نمایندگی رسمی', 'عمده فروش', 'وارد کننده', 'شرکت بازرگانی']
export const COMPANY_TYPE_OPTIONS = ['سهامی خاص', 'سهامی عام', 'مسئولیت محدود', 'تضامنی', 'نسبی', 'تعاونی', 'سایر']
export const EXPERIENCE_OPTIONS = ['کمتر از ۱ سال', '۱ تا ۳ سال', '۳ تا ۵ سال', '۵ تا ۱۰ سال', 'بیش از ۱۰ سال']

export const PAYMENT_LABELS: Record<string, string> = {
  cash: 'نقدی',
  credit: 'اعتباری',
  both: 'نقدی و اعتباری',
}

export type FormPayment = '' | 'cash' | 'credit' | 'both'

/** Pointer to an uploaded file ({id,name,size} from POST /api/suppliers/files). */
export interface FileRef { id: string, name: string, size?: number | null }
/** Older records stored just a filename string -- still shown, but not downloadable. */
export type StoredFile = FileRef | string

export const isFileRef = (f: unknown): f is FileRef => typeof f === 'object' && f !== null && 'id' in f
export const fileLabel = (f: StoredFile) => (typeof f === 'string' ? f : f.name)

export const UPLOAD_ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.zip,.rar,.txt'
export const IMAGE_ACCEPT = '.png,.jpg,.jpeg,.webp'
export const MAX_UPLOAD_MB = 10

/** Client-side check so people get an instant message; the server enforces the same rules. */
export function checkUploadFile(file: File, accept: string = UPLOAD_ACCEPT): string | null {
  const ext = file.name.includes('.') ? '.' + file.name.split('.').pop()!.toLowerCase() : ''
  if (!accept.split(',').includes(ext)) return `نوع فایل «${file.name}» مجاز نیست.`
  if (file.size === 0) return `فایل «${file.name}» خالی است.`
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `حجم فایل «${file.name}» بیشتر از ${MAX_UPLOAD_MB} مگابایت است.`
  return null
}

/**
 * One contact person. Each person may have one mobile AND one landline
 * (at least one of the two is required).
 */
export interface ContactForm {
  first_name: string
  last_name: string
  position: string
  email: string
  mobile: string
  landline: string
}

export interface ProductForm {
  name: string
  specs: string
  payment: FormPayment
  creditMonths: string // '' | '1'..'12'
  description: string
  datasheet: StoredFile | null // uploaded file (or an older filename string)
  image: FileRef | null // product photo -- required
}

/** One bank account row. Every field is optional; fully blank rows are never sent. */
export interface BankAccountForm {
  holder_name: string // اسم شخص یا شرکت
  bank_name: string
  card_number: string
  account_number: string
  sheba: string
}
export const blankBankAccount = (): BankAccountForm => ({
  holder_name: '', bank_name: '', card_number: '', account_number: '', sheba: '',
})

export interface SupplierFormState {
  supplier_type: 'INDIVIDUAL' | 'LEGAL'
  first_name: string
  last_name: string
  national_id: string
  brand_name: string // نام برند یا مغازه -- optional, individual suppliers only
  company_name: string
  company_national_id: string
  registration_number: string
  company_type: string
  established_date: string
  email: string
  website: string
  address: string
  postal_code: string // 10 digits, optional
  contacts: ContactForm[]
  category: string
  subcategory: string // sub-category of `category`; '' = none
  activity_types: string[]
  capacity: string
  experience: string
  products: ProductForm[]
  catalog_files: StoredFile[]
  bank_accounts: BankAccountForm[] // optional, any number
  status: 'ACTIVE' | 'SEMI_ACTIVE' | 'INACTIVE'
  quality: 'EXCELLENT' | 'MEDIUM' | 'WEAK' | null
}

export const blankContact = (): ContactForm => ({
  first_name: '', last_name: '', position: '', email: '', mobile: '', landline: '',
})

export const blankProduct = (): ProductForm => ({
  name: '', specs: '', payment: '', creditMonths: '', description: '', datasheet: null, image: null,
})

export function blankSupplierForm(): SupplierFormState {
  return {
    supplier_type: 'LEGAL',
    first_name: '', last_name: '', national_id: '', brand_name: '',
    company_name: '', company_national_id: '', registration_number: '', company_type: '', established_date: '',
    email: '', website: '', address: '', postal_code: '',
    contacts: [blankContact()],
    category: '', subcategory: '', activity_types: [], capacity: '', experience: '',
    products: [],
    catalog_files: [],
    bank_accounts: [],
    status: 'SEMI_ACTIVE',
    quality: null,
  }
}

/**
 * Older records have no `contacts`, only a flat `phones` list. Turn those into
 * contact rows (first mobile + first landline together, and so on) so staff
 * only have to add the names and positions.
 */
function contactsFromLegacyPhones(s: any, str: (v: unknown) => string): ContactForm[] {
  const phones: any[] = Array.isArray(s.phones) ? s.phones : []
  const mobiles = phones.filter(p => p?.type === 'mobile').map(p => str(p.number))
  const landlines = phones.filter(p => p?.type === 'landline').map(p => str(p.number))
  const count = Math.max(mobiles.length, landlines.length)
  if (!count) return [blankContact()]
  return Array.from({ length: count }, (_, i): ContactForm => ({
    ...blankContact(),
    // an individual supplier's own name is a sensible default for the first person
    first_name: i === 0 && s.supplier_type === 'INDIVIDUAL' ? str(s.first_name) : '',
    last_name: i === 0 && s.supplier_type === 'INDIVIDUAL' ? str(s.last_name) : '',
    email: i === 0 ? str(s.email) : '',
    mobile: mobiles[i] ?? '',
    landline: landlines[i] ?? '',
  }))
}

/** Turn a supplier returned by the API into editable form state. */
export function supplierToForm(s: any): SupplierFormState {
  const base = blankSupplierForm()
  const str = (v: unknown) => (typeof v === 'string' ? v : '')
  return {
    ...base,
    supplier_type: s.supplier_type,
    first_name: str(s.first_name), last_name: str(s.last_name), national_id: str(s.national_id),
    brand_name: str(s.brand_name),
    company_name: str(s.company_name), company_national_id: str(s.company_national_id),
    registration_number: str(s.registration_number), company_type: str(s.company_type),
    established_date: str(s.established_date),
    email: str(s.email), website: str(s.website), address: str(s.address),
    postal_code: str(s.postal_code),
    contacts: s.contacts?.length
      ? s.contacts.map((c: any): ContactForm => ({
          first_name: str(c.first_name), last_name: str(c.last_name), position: str(c.position),
          email: str(c.email), mobile: str(c.mobile), landline: str(c.landline),
        }))
      : contactsFromLegacyPhones(s, str),
    category: str(s.category),
    subcategory: str(s.subcategory),
    activity_types: str(s.activity_type).split(',').map(x => x.trim()).filter(Boolean),
    capacity: str(s.capacity), experience: str(s.experience),
    products: (s.products ?? []).map((p: any): ProductForm => ({
      name: str(p.name), specs: str(p.specs), payment: (p.payment ?? '') as FormPayment,
      creditMonths: p.creditMonths ? String(p.creditMonths) : '',
      description: str(p.description), datasheet: p.datasheet || null,
      image: isFileRef(p.image) ? p.image : null,
    })),
    catalog_files: [...(s.catalog_files ?? [])],
    bank_accounts: (s.bank_accounts ?? []).map((b: any): BankAccountForm => ({
      holder_name: str(b.holder_name), bank_name: str(b.bank_name), card_number: str(b.card_number),
      account_number: str(b.account_number), sheba: str(b.sheba),
    })),
    status: s.status,
    quality: s.quality ?? null,
  }
}

const nullIfBlank = (v: string) => (v.trim() ? v.trim() : null)

/** Form state -> body for POST /api/suppliers or PATCH /api/suppliers/:id. */
export function formToPayload(f: SupplierFormState) {
  const legal = f.supplier_type === 'LEGAL'
  return {
    supplier_type: f.supplier_type,
    // identity fields that don't apply to the chosen type are cleared (matters when editing)
    first_name: legal ? null : nullIfBlank(f.first_name),
    last_name: legal ? null : nullIfBlank(f.last_name),
    national_id: legal ? null : nullIfBlank(toLatinDigits(f.national_id)),
    // نام برند یا مغازه: individual only; null for legal clears an old value
    brand_name: legal ? null : nullIfBlank(f.brand_name),
    company_name: legal ? nullIfBlank(f.company_name) : null,
    company_national_id: legal ? nullIfBlank(toLatinDigits(f.company_national_id)) : null,
    registration_number: legal ? nullIfBlank(f.registration_number) : null,
    company_type: legal ? nullIfBlank(f.company_type) : null,
    established_date: legal ? nullIfBlank(f.established_date) : null,
    email: nullIfBlank(f.email),
    website: nullIfBlank(f.website),
    address: nullIfBlank(f.address),
    postal_code: nullIfBlank(toLatinDigits(f.postal_code).replace(/[\s-]/g, '')),
    // `phones` is not sent: the server derives it from `contacts`.
    contacts: f.contacts.map(c => ({
      first_name: c.first_name.trim(),
      last_name: c.last_name.trim(),
      position: c.position.trim(),
      email: nullIfBlank(c.email),
      mobile: nullIfBlank(toLatinDigits(c.mobile)),
      landline: nullIfBlank(toLatinDigits(c.landline)),
    })),
    category: nullIfBlank(f.category),
    // a sub-category only makes sense together with its main category
    subcategory: f.category.trim() ? nullIfBlank(f.subcategory) : null,
    activity_type: f.activity_types.length ? f.activity_types.join(',') : null,
    capacity: nullIfBlank(f.capacity),
    experience: nullIfBlank(f.experience),
    products: f.products.filter(p => p.name.trim()).map(p => ({
      name: p.name.trim(),
      specs: nullIfBlank(p.specs),
      payment: p.payment || null,
      creditMonths: p.payment && p.payment !== 'cash' && p.creditMonths ? Number(p.creditMonths) : null,
      description: nullIfBlank(p.description),
      datasheet: p.datasheet || null,
      image: p.image,
    })),
    catalog_files: f.catalog_files,
    // blank rows are dropped; digits are normalised (the server re-validates)
    bank_accounts: f.bank_accounts.map(b => ({
      holder_name: nullIfBlank(b.holder_name),
      bank_name: nullIfBlank(b.bank_name),
      card_number: nullIfBlank(toLatinDigits(b.card_number).replace(/[\s-]/g, '')),
      account_number: nullIfBlank(toLatinDigits(b.account_number).replace(/\s/g, '')),
      sheba: nullIfBlank(normalizeSheba(b.sheba)),
    })).filter(b => Object.values(b).some(Boolean)),
    status: f.status,
    quality: f.quality,
  }
}

/* ───────────── validation (one function per wizard step) ───────────── */
const PERSIAN = '۰۱۲۳۴۵۶۷۸۹'
const ARABIC = '٠١٢٣٤٥٦٧٨٩'
export const toLatinDigits = (s: string) =>
  s.replace(/[۰-۹]/g, d => String(PERSIAN.indexOf(d))).replace(/[٠-٩]/g, d => String(ARABIC.indexOf(d)))

export type StepErrors = Record<string, string>

/** Card number: 16 digits + Luhn check (catches most typing mistakes). */
export function isValidCardNumber(raw: string): boolean {
  const v = toLatinDigits(raw).replace(/[\s-]/g, '')
  if (!/^\d{16}$/.test(v)) return false
  let sum = 0
  ;[...v].reverse().forEach((ch, i) => {
    let d = Number(ch)
    if (i % 2 === 1) d = d > 4 ? d * 2 - 9 : d * 2
    sum += d
  })
  return sum % 10 === 0
}

/** 'IR' + 24 digits, canonical; accepts the number written without the IR prefix. */
export function normalizeSheba(raw: string): string {
  const v = toLatinDigits(raw).replace(/[\s-]/g, '').toUpperCase()
  if (!v) return ''
  return /^\d{24}$/.test(v) ? `IR${v}` : v
}
export function isValidSheba(raw: string): boolean {
  const v = normalizeSheba(raw)
  if (!/^IR\d{24}$/.test(v)) return false
  // ISO 7064 mod 97-10: move "IRxx" to the end (I=18, R=27)
  const digits = v.slice(4) + '1827' + v.slice(2, 4)
  let rem = 0
  for (const ch of digits) rem = (rem * 10 + Number(ch)) % 97
  return rem === 1
}
export const isValidAccountNumber = (raw: string) => /^[0-9][0-9.-]{3,29}$/.test(toLatinDigits(raw).replace(/\s/g, ''))

const mobileOk = (raw: string) => /^(\+98|0098|0)?9\d{9}$/.test(toLatinDigits(raw).replace(/[\s-]/g, ''))
const landlineOk = (raw: string) => /^\+?\d{7,14}$/.test(toLatinDigits(raw).replace(/[\s-]/g, ''))

export function validateSupplierStep(step: number, f: SupplierFormState): StepErrors {
  const e: StepErrors = {}
  if (step === 0) {
    if (f.supplier_type === 'LEGAL') {
      if (!f.company_name.trim()) e.company_name = 'وارد کردن نام شرکت الزامی است.'
      const id = toLatinDigits(f.company_national_id.trim())
      if (!id) e.company_national_id = 'وارد کردن شناسه ملی الزامی است.'
      else if (!/^\d{11}$/.test(id)) e.company_national_id = 'شناسه ملی باید ۱۱ رقم باشد.'
    }
    else {
      if (!f.first_name.trim()) e.first_name = 'وارد کردن نام الزامی است.'
      if (!f.last_name.trim()) e.last_name = 'وارد کردن نام خانوادگی الزامی است.'
      const id = toLatinDigits(f.national_id.trim())
      if (id && !/^\d{10}$/.test(id)) e.national_id = 'کد ملی باید ۱۰ رقم باشد.'
      if (f.brand_name.trim().length > 255) e.brand_name = 'نام برند یا مغازه نباید بیشتر از ۲۵۵ نویسه باشد.'
    }
  }
  if (step === 1) {
    if (f.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.email.trim())) e.email = 'یک نشانی ایمیل معتبر وارد کنید.'
    if (f.website.trim() && !/^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(\/\S*)?$/i.test(f.website.trim())) e.website = 'یک نشانی وب‌سایت معتبر وارد کنید.'

    const postal = toLatinDigits(f.postal_code).replace(/[\s-]/g, '')
    if (postal && !/^\d{10}$/.test(postal)) e.postal_code = 'کد پستی باید ۱۰ رقم باشد.'

    if (!f.contacts.length) e.contacts = 'حداقل یک فرد تماس لازم است.'
    f.contacts.forEach((c, i) => {
      if (!c.first_name.trim()) e[`contact.${i}.first_name`] = 'وارد کردن نام الزامی است.'
      if (!c.last_name.trim()) e[`contact.${i}.last_name`] = 'وارد کردن نام خانوادگی الزامی است.'
      if (!c.position.trim()) e[`contact.${i}.position`] = 'انتخاب سمت الزامی است.'
      if (c.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(c.email.trim())) {
        e[`contact.${i}.email`] = 'یک نشانی ایمیل معتبر وارد کنید.'
      }
      const mobile = c.mobile.trim()
      const landline = c.landline.trim()
      if (!mobile && !landline) e[`contact.${i}.numbers`] = 'وارد کردن حداقل یک شماره موبایل یا تلفن ثابت الزامی است.'
      else if (mobile && !mobileOk(mobile)) e[`contact.${i}.numbers`] = `شماره موبایل «${mobile}» معتبر نیست.`
      else if (landline && !landlineOk(landline)) e[`contact.${i}.numbers`] = `شماره تلفن ثابت «${landline}» معتبر نیست.`
    })
  }
  if (step === 3) {
    f.products.forEach((p, i) => {
      const active = p.name.trim() || p.specs.trim() || p.description.trim() || p.datasheet || p.image || p.payment
      if (!active) return
      if (!p.name.trim()) e[`product.${i}.name`] = 'وارد کردن نام کالا یا خدمت الزامی است.'
      if (!p.image) e[`product.${i}.image`] = 'بارگذاری تصویر کالا الزامی است.'
      if (!p.payment) e[`product.${i}.payment`] = 'روش پرداخت را انتخاب کنید.'
      else if (p.payment !== 'cash' && !p.creditMonths) e[`product.${i}.months`] = 'مدت اعتبار را انتخاب کنید.'
    })
  }
  if (step === 4) {
    f.bank_accounts.forEach((b, i) => {
      if (b.holder_name.trim().length > 255) e[`bank.${i}.holder_name`] = 'نام صاحب حساب نباید بیشتر از ۲۵۵ نویسه باشد.'
      if (b.bank_name.trim().length > 100) e[`bank.${i}.bank_name`] = 'نام بانک نباید بیشتر از ۱۰۰ نویسه باشد.'
      if (b.card_number.trim() && !isValidCardNumber(b.card_number)) e[`bank.${i}.card_number`] = 'شماره کارت باید ۱۶ رقم و معتبر باشد.'
      if (b.account_number.trim() && !isValidAccountNumber(b.account_number)) {
        e[`bank.${i}.account_number`] = 'شماره حساب فقط شامل رقم، خط تیره و نقطه (۴ تا ۳۰ نویسه) باشد.'
      }
      if (b.sheba.trim() && !isValidSheba(b.sheba)) e[`bank.${i}.sheba`] = 'شماره شبا باید IR و ۲۴ رقم معتبر باشد.'
    })
  }
  return e
}