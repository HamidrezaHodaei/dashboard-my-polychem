/**
 * Shared form logic for the logistics wizard (staff add + edit).
 * Nuxt auto-imports everything exported from `utils/`.
 *
 * No option list lives here: vehicle/body/cargo types, areas, countries,
 * permits and provinces/cities all come from GET /api/logistics/public/reference
 * (see stores/logistics.ts), so the UI can never drift from what the server accepts.
 * Validation below mirrors backend/app/modules/logistics/schemas.py, only to give
 * instant Persian messages; the server stays the authority.
 */
import type { FileRef } from './supplier-form'

export type ApplicantType = 'COMPANY' | 'DRIVER'
export type ApplicantStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | 'NEEDS_EDIT'
export type AreaType = 'CITY' | 'PROVINCIAL' | 'INTERPROVINCIAL' | 'INTERNATIONAL'
export type LegalType = 'INDIVIDUAL' | 'LEGAL'

export interface Option { code: string, label: string }
export interface PermitTypeDef { code: string, label: string, for_type: 'COMPANY' | 'DRIVER' | 'BOTH', required: boolean }
export interface LogisticsReference {
  legal_types: Option[]
  vehicle_types: Option[]
  body_types: Option[]
  cargo_types: Option[]
  area_types: Option[]
  representative_positions: Option[]
  countries: Option[]
  permit_types: PermitTypeDef[]
  provinces: { name: string, cities: string[] }[]
}

export const TYPE_LABELS: Record<ApplicantType, string> = { COMPANY: 'شرکت حمل‌ونقل', DRIVER: 'راننده' }
export const STATUS_LABELS: Record<ApplicantStatus, string> = {
  PENDING: 'در انتظار بررسی', APPROVED: 'تأیید', REJECTED: 'رد درخواست', SUSPENDED: 'تعلیق',
  NEEDS_EDIT: 'نیازمند ویرایش یا تکمیل اطلاعات',
}
export const labelOf = (list: Option[] | undefined, code: string | null | undefined) =>
  (code ? list?.find(o => o.code === code)?.label ?? code : '')

/* ───────────── form state ───────────── */
export interface CoverageRow { province: string, all_cities: boolean, cities: string[] }
export interface PermitRow { type: string, number: string, expires_at: string, file: FileRef | null }

export interface LogisticsFormState {
  applicant_type: ApplicantType | ''
  status: ApplicantStatus
  company: {
    entity_type: LegalType, company_name: string, first_name: string, last_name: string,
    national_id: string, province: string, city: string, office_address: string,
  }
  rep: { first_name: string, last_name: string, position: string, position_other: string, mobile: string, landline: string }
  identity: { first_name: string, last_name: string, national_code: string }
  contact: { mobile: string, alt_phone: string }
  vehicle: {
    vehicle_type: string, vehicle_type_other: string, body_type: string, body_type_other: string,
    capacity_tons: string, cargo_types: string[], cargo_type_other: string,
  }
  area: {
    area_type: AreaType | '', coverage: CoverageRow[], origin_countries: string[],
    destination_countries: string[], permits: PermitRow[],
  }
}

export const blankCoverage = (): CoverageRow => ({ province: '', all_cities: false, cities: [] })

export function blankLogisticsForm(): LogisticsFormState {
  return {
    applicant_type: '',
    status: 'PENDING',
    company: {
      entity_type: 'LEGAL', company_name: '', first_name: '', last_name: '', national_id: '',
      province: '', city: '', office_address: '',
    },
    rep: { first_name: '', last_name: '', position: '', position_other: '', mobile: '', landline: '' },
    identity: { first_name: '', last_name: '', national_code: '' },
    contact: { mobile: '', alt_phone: '' },
    vehicle: {
      vehicle_type: '', vehicle_type_other: '', body_type: '', body_type_other: '',
      capacity_tons: '', cargo_types: [], cargo_type_other: '',
    },
    area: { area_type: '', coverage: [], origin_countries: [], destination_countries: [], permits: [] },
  }
}

/* ───────────── steps ───────────── */
export type StepKey = 'type' | 'company_info' | 'representative' | 'identity' | 'contact' | 'vehicle' | 'service_area'

const STEP_TITLES: Record<StepKey, string> = {
  type: 'نوع متقاضی',
  company_info: 'اطلاعات شرکت',
  representative: 'نماینده و تماس',
  identity: 'اطلاعات هویتی',
  contact: 'اطلاعات تماس',
  vehicle: 'وسیله نقلیه و بارگیر',
  service_area: 'محدوده فعالیت',
}

/** The type chooser is always first; the vehicle step exists ONLY on the driver path. */
export function stepsFor(type: ApplicantType | '', { withTypeStep = true } = {}): { key: StepKey, title: string }[] {
  const keys: StepKey[] = type === 'COMPANY'
    ? ['company_info', 'representative', 'service_area']
    : type === 'DRIVER' ? ['identity', 'contact', 'vehicle', 'service_area'] : []
  const all: StepKey[] = withTypeStep ? ['type', ...keys] : keys
  return all.map(key => ({ key, title: STEP_TITLES[key] }))
}

/* ───────────── digit / format helpers ───────────── */
const PERSIAN = '۰۱۲۳۴۵۶۷۸۹'
const ARABIC = '٠١٢٣٤٥٦٧٨٩'
export const toLatin = (s: string) =>
  String(s ?? '').replace(/[۰-۹]/g, d => String(PERSIAN.indexOf(d))).replace(/[٠-٩]/g, d => String(ARABIC.indexOf(d)))
const compact = (s: string) => toLatin(s).replace(/[\s-]/g, '')
const blankToNull = (s: string) => (s.trim() ? s.trim() : null)

export function isValidNationalCode(raw: string): boolean {
  const v = compact(raw)
  if (!/^\d{10}$/.test(v) || new Set(v).size === 1) return false
  const sum = [...v.slice(0, 9)].reduce((a, d, i) => a + Number(d) * (10 - i), 0)
  const r = sum % 11
  return (r < 2 ? r : 11 - r) === Number(v[9])
}

export function isValidLegalId(raw: string): boolean {
  const v = compact(raw)
  if (!/^\d{11}$/.test(v) || new Set(v).size === 1 || Number(v.slice(3, 9)) === 0) return false
  const d = Number(v[9]) + 2
  const coeffs = [29, 27, 23, 19, 17, 29, 27, 23, 19, 17]
  const sum = coeffs.reduce((a, c, i) => a + (Number(v[i]) + d) * c, 0)
  const r = sum % 11
  return (r === 10 ? 0 : r) === Number(v[10])
}

export const isMobile = (raw: string) => /^(\+98|0098|98|0)?9\d{9}$/.test(compact(raw))
export const isLandline = (raw: string) => /^(\+98|0098|98|0)?[1-8]\d{9}$/.test(compact(raw)) && /^(0|\+98|0098|98)/.test(compact(raw))

/* ───────────── service area helpers ───────────── */
export const permitDefsFor = (ref: LogisticsReference | null, type: ApplicantType | '') =>
  (ref?.permit_types ?? []).filter(p => p.for_type === 'BOTH' || p.for_type === type)

/**
 * Switching the activity type updates the dependent fields straight away:
 * coverage is reshaped to what the new type allows, and countries/permits are
 * cleared when the type is not international (the server clears them too).
 */
export function setAreaType(form: LogisticsFormState, next: AreaType, ref: LogisticsReference | null) {
  const a = form.area
  a.area_type = next
  const filled = a.coverage.filter(c => c.province)
  if (next === 'CITY') {
    const first = filled[0]
    a.coverage = [{ province: first?.province ?? '', all_cities: false, cities: first?.cities.slice(0, 1) ?? [] }]
  }
  else if (next === 'PROVINCIAL') {
    const first = a.coverage[0]
    a.coverage = [first ? { ...first, cities: [...first.cities] } : blankCoverage()]
  }
  else if (next === 'INTERPROVINCIAL') {
    a.coverage = a.coverage.map(c => ({ ...c, cities: [...c.cities] }))
    while (a.coverage.length < 2) a.coverage.push(blankCoverage())
  }
  else {
    // international coverage is optional: keep only the rows that are already complete
    a.coverage = filled.filter(c => c.all_cities || c.cities.length).map(c => ({ ...c, cities: [...c.cities] }))
  }
  if (next !== 'INTERNATIONAL') {
    a.origin_countries = []
    a.destination_countries = []
    a.permits = []
  }
  else {
    for (const def of permitDefsFor(ref, form.applicant_type)) {
      if (def.required && !a.permits.some(p => p.type === def.code)) {
        a.permits.push({ type: def.code, number: '', expires_at: '', file: null })
      }
    }
  }
}

/* ───────────── validation (one entry per wizard step) ───────────── */
export type StepErrors = Record<string, string>

export function validateLogisticsStep(
  key: StepKey, f: LogisticsFormState, ref: LogisticsReference | null = null,
): StepErrors {
  const e: StepErrors = {}
  const req = (path: string, value: string, msg: string) => { if (!value.trim()) e[path] = msg }

  if (key === 'type') {
    if (!f.applicant_type) e.applicant_type = 'نوع متقاضی را انتخاب کنید.'
  }
  else if (key === 'company_info') {
    const c = f.company
    if (c.entity_type === 'LEGAL') {
      req('company.company_name', c.company_name, 'وارد کردن نام شرکت الزامی است.')
      if (c.national_id.trim() && !isValidLegalId(c.national_id)) e['company.national_id'] = 'شناسه ملی باید ۱۱ رقم و معتبر باشد.'
    }
    else {
      req('company.first_name', c.first_name, 'وارد کردن نام الزامی است.')
      req('company.last_name', c.last_name, 'وارد کردن نام خانوادگی الزامی است.')
    }
    req('company.province', c.province, 'استان محل فعالیت را انتخاب کنید.')
    req('company.city', c.city, 'شهر محل فعالیت را انتخاب کنید.')
    if (c.office_address.trim().length < 10) e['company.office_address'] = 'نشانی دفتر را کامل وارد کنید (حداقل ۱۰ نویسه).'
  }
  else if (key === 'representative') {
    const r = f.rep
    req('rep.first_name', r.first_name, 'وارد کردن نام نماینده الزامی است.')
    req('rep.last_name', r.last_name, 'وارد کردن نام خانوادگی نماینده الزامی است.')
    req('rep.position', r.position, 'سمت نماینده را انتخاب کنید.')
    if (r.position === 'OTHER') req('rep.position_other', r.position_other, 'عنوان سمت را وارد کنید.')
    if (!r.mobile.trim()) e['rep.mobile'] = 'وارد کردن شماره موبایل الزامی است.'
    else if (!isMobile(r.mobile)) e['rep.mobile'] = 'شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷).'
    if (r.landline.trim() && !isLandline(r.landline)) e['rep.landline'] = 'تلفن ثابت را همراه با کد شهر وارد کنید (مثال: ۰۲۱۲۲۳۳۴۴۵۵).'
  }
  else if (key === 'identity') {
    const i = f.identity
    req('identity.first_name', i.first_name, 'وارد کردن نام الزامی است.')
    req('identity.last_name', i.last_name, 'وارد کردن نام خانوادگی الزامی است.')
    if (!i.national_code.trim()) e['identity.national_code'] = 'وارد کردن کد ملی الزامی است.'
    else if (!isValidNationalCode(i.national_code)) e['identity.national_code'] = 'کد ملی باید ۱۰ رقم و معتبر باشد.'
  }
  else if (key === 'contact') {
    const c = f.contact
    if (!c.mobile.trim()) e['contact.mobile'] = 'وارد کردن شماره موبایل الزامی است.'
    else if (!isMobile(c.mobile)) e['contact.mobile'] = 'شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷).'
    if (c.alt_phone.trim() && !isMobile(c.alt_phone) && !isLandline(c.alt_phone)) {
      e['contact.alt_phone'] = 'تلفن جایگزین باید موبایل یا تلفن ثابت (با کد شهر) باشد.'
    }
  }
  else if (key === 'vehicle') {
    const v = f.vehicle
    req('vehicle.vehicle_type', v.vehicle_type, 'نوع خودرو را انتخاب کنید.')
    if (v.vehicle_type === 'OTHER') req('vehicle.vehicle_type_other', v.vehicle_type_other, 'نوع خودرو را توضیح دهید.')
    req('vehicle.body_type', v.body_type, 'نوع بارگیر را انتخاب کنید.')
    if (v.body_type === 'OTHER') req('vehicle.body_type_other', v.body_type_other, 'نوع بارگیر را توضیح دهید.')
    const cap = Number(toLatin(v.capacity_tons).replace('٫', '.').replace(',', '.'))
    if (!v.capacity_tons.trim()) e['vehicle.capacity_tons'] = 'وارد کردن ظرفیت حمل الزامی است.'
    else if (!Number.isFinite(cap) || cap <= 0) e['vehicle.capacity_tons'] = 'ظرفیت باید عددی بزرگ‌تر از صفر باشد.'
    else if (cap > 100) e['vehicle.capacity_tons'] = 'ظرفیت نمی‌تواند بیشتر از ۱۰۰ تن باشد.'
    if (!v.cargo_types.length) e['vehicle.cargo_types'] = 'حداقل یک نوع کالا را انتخاب کنید.'
    if (v.cargo_types.includes('OTHER')) req('vehicle.cargo_type_other', v.cargo_type_other, 'نوع کالا را توضیح دهید.')
  }
  else if (key === 'service_area') {
    const a = f.area
    if (!a.area_type) { e['area.area_type'] = 'نوع محدوده فعالیت را انتخاب کنید.'; return e }
    const rows = a.coverage
    const rowOk = (c: CoverageRow) => !!c.province && (c.all_cities || c.cities.length > 0)
    if (a.area_type === 'CITY') {
      if (!rows[0]?.province) e['area.coverage'] = 'استان را انتخاب کنید.'
      else if (rows[0].cities.length !== 1) e['area.coverage'] = 'شهر محل فعالیت را انتخاب کنید.'
    }
    else if (a.area_type === 'PROVINCIAL') {
      if (!rows[0]?.province) e['area.coverage'] = 'استان را انتخاب کنید.'
      else if (!rowOk(rows[0])) e['area.coverage'] = 'کل استان یا حداقل یک شهر را انتخاب کنید.'
    }
    else if (a.area_type === 'INTERPROVINCIAL') {
      const names = rows.map(c => c.province).filter(Boolean)
      if (names.length < 2 || rows.some(c => !c.province)) e['area.coverage'] = 'حداقل دو استان را انتخاب کنید.'
      else if (new Set(names).size !== names.length) e['area.coverage'] = 'هر استان فقط یک بار می‌تواند انتخاب شود.'
      else if (rows.some(c => !rowOk(c))) e['area.coverage'] = 'برای هر استان، کل استان یا حداقل یک شهر را انتخاب کنید.'
    }
    else {
      const filled = rows.filter(c => c.province)
      if (filled.some(c => !rowOk(c))) e['area.coverage'] = 'برای هر استان، کل استان یا حداقل یک شهر را انتخاب کنید.'
      if (!a.origin_countries.length) e['area.origin_countries'] = 'حداقل یک کشور مبدأ را انتخاب کنید.'
      if (!a.destination_countries.length) e['area.destination_countries'] = 'حداقل یک کشور مقصد را انتخاب کنید.'
      if (a.origin_countries.length && a.destination_countries.length
        && ![...a.origin_countries, ...a.destination_countries].some(c => c !== 'IR')) {
        e['area.destination_countries'] = 'حداقل یک کشور غیر از ایران لازم است.'
      }
      for (const def of permitDefsFor(ref, f.applicant_type).filter(d => d.required)) {
        const row = a.permits.find(p => p.type === def.code)
        if (!row?.file) e[`area.permit.${def.code}`] = `بارگذاری «${def.label}» الزامی است.`
      }
    }
  }
  return e
}

/* ───────────── payloads ───────────── */
function areaPayload(f: LogisticsFormState) {
  const a = f.area
  const intl = a.area_type === 'INTERNATIONAL'
  return {
    area_type: a.area_type,
    coverage: a.coverage.filter(c => c.province).map(c => ({
      province: c.province,
      all_cities: a.area_type === 'CITY' ? false : c.all_cities,
      cities: c.all_cities && a.area_type !== 'CITY' ? [] : c.cities,
    })),
    origin_countries: intl ? a.origin_countries : [],
    destination_countries: intl ? a.destination_countries : [],
    permits: intl
      ? a.permits.filter(p => p.type && (p.file || p.number.trim())).map(p => ({
          type: p.type,
          number: blankToNull(p.number),
          expires_at: blankToNull(p.expires_at),
          file: p.file ? { id: p.file.id, name: p.file.name, size: p.file.size ?? null } : null,
        }))
      : [],
  }
}

/** The request body of ONE wizard section (used for per-step server validation and for saving). */
export function sectionPayload(key: StepKey, f: LogisticsFormState): Record<string, unknown> {
  if (key === 'company_info') {
    const c = f.company
    const legal = c.entity_type === 'LEGAL'
    return {
      entity_type: c.entity_type,
      company_name: legal ? blankToNull(c.company_name) : null,
      first_name: legal ? null : blankToNull(c.first_name),
      last_name: legal ? null : blankToNull(c.last_name),
      national_id: legal ? blankToNull(compact(c.national_id)) : null,
      province: c.province, city: c.city, office_address: c.office_address.trim(),
    }
  }
  if (key === 'representative') {
    const r = f.rep
    return {
      first_name: r.first_name.trim(), last_name: r.last_name.trim(), position: r.position,
      position_other: r.position === 'OTHER' ? blankToNull(r.position_other) : null,
      mobile: compact(r.mobile), landline: blankToNull(compact(r.landline)),
    }
  }
  if (key === 'identity') {
    const i = f.identity
    return { first_name: i.first_name.trim(), last_name: i.last_name.trim(), national_code: compact(i.national_code) }
  }
  if (key === 'contact') {
    return { mobile: compact(f.contact.mobile), alt_phone: blankToNull(compact(f.contact.alt_phone)) }
  }
  if (key === 'vehicle') {
    const v = f.vehicle
    return {
      vehicle_type: v.vehicle_type,
      vehicle_type_other: v.vehicle_type === 'OTHER' ? blankToNull(v.vehicle_type_other) : null,
      body_type: v.body_type,
      body_type_other: v.body_type === 'OTHER' ? blankToNull(v.body_type_other) : null,
      capacity_tons: Number(toLatin(v.capacity_tons).replace('٫', '.').replace(',', '.')),
      cargo_types: v.cargo_types,
      cargo_type_other: v.cargo_types.includes('OTHER') ? blankToNull(v.cargo_type_other) : null,
    }
  }
  return areaPayload(f)
}

/** Sections that belong to the chosen type -- a company never produces a `vehicle` key. */
export function sectionKeysFor(type: ApplicantType): StepKey[] {
  return type === 'COMPANY'
    ? ['company_info', 'representative', 'service_area']
    : ['identity', 'contact', 'vehicle', 'service_area']
}

/** POST /api/logistics/applicants */
export function formToCreatePayload(f: LogisticsFormState, finalized = true) {
  const type = f.applicant_type as ApplicantType
  // a draft stays PENDING and editable by its creator until "ثبت نهایی"
  const body: Record<string, unknown> = { applicant_type: type, status: finalized ? f.status : 'PENDING', is_finalized: finalized }
  for (const k of sectionKeysFor(type)) body[k] = sectionPayload(k, f)
  return body
}

/** PATCH /api/logistics/applicants/:id -- every section is replaced as a whole. */
export function formToUpdatePayload(f: LogisticsFormState) {
  const body: Record<string, unknown> = {}
  for (const k of sectionKeysFor(f.applicant_type as ApplicantType)) body[k] = sectionPayload(k, f)
  return body
}

/** Applicant detail returned by the API -> editable form state. */
export function applicantToForm(a: any): LogisticsFormState {
  const base = blankLogisticsForm()
  const s = (v: unknown) => (typeof v === 'string' ? v : '')
  const ci = a.company_info
  const rp = a.representative
  const id = a.identity
  const ct = a.contact
  const vh = a.vehicle
  const sa = a.service_area
  return {
    ...base,
    applicant_type: a.applicant_type,
    status: a.status,
    company: ci
      ? {
          entity_type: ci.entity_type, company_name: s(ci.company_name), first_name: s(ci.first_name),
          last_name: s(ci.last_name), national_id: s(ci.national_id), province: s(ci.province),
          city: s(ci.city), office_address: s(ci.office_address),
        }
      : base.company,
    rep: rp
      ? {
          first_name: s(rp.first_name), last_name: s(rp.last_name), position: s(rp.position),
          position_other: s(rp.position_other), mobile: s(rp.mobile), landline: s(rp.landline),
        }
      : base.rep,
    identity: id ? { first_name: s(id.first_name), last_name: s(id.last_name), national_code: s(id.national_code) } : base.identity,
    contact: ct ? { mobile: s(ct.mobile), alt_phone: s(ct.alt_phone) } : base.contact,
    vehicle: vh
      ? {
          vehicle_type: s(vh.vehicle_type), vehicle_type_other: s(vh.vehicle_type_other),
          body_type: s(vh.body_type), body_type_other: s(vh.body_type_other),
          capacity_tons: vh.capacity_tons != null ? String(vh.capacity_tons) : '',
          cargo_types: [...(vh.cargo_types ?? [])], cargo_type_other: s(vh.cargo_type_other),
        }
      : base.vehicle,
    area: sa
      ? {
          area_type: sa.area_type,
          coverage: (sa.coverage ?? []).map((c: any): CoverageRow => ({
            province: s(c.province), all_cities: !!c.all_cities, cities: [...(c.cities ?? [])],
          })),
          origin_countries: [...(sa.origin_countries ?? [])],
          destination_countries: [...(sa.destination_countries ?? [])],
          permits: (sa.permits ?? []).map((p: any): PermitRow => ({
            type: s(p.type), number: s(p.number), expires_at: s(p.expires_at), file: p.file ?? null,
          })),
        }
      : base.area,
  }
}

/* ───────────── server validation errors -> form errors ───────────── */
const SECTION_TO_FORM: Record<string, string> = {
  company_info: 'company', representative: 'rep', identity: 'identity',
  contact: 'contact', vehicle: 'vehicle', service_area: 'area',
}

/**
 * Backend `details: [{field: 'company_info.city', message}]` -> `{ errors, step }`
 * where errors use this file's keys ('company.city') and `step` is the first
 * wizard step that has a problem, so the dialog can jump straight to it.
 */
export function mapServerErrors(details: unknown): { errors: StepErrors, step: StepKey | null } {
  const errors: StepErrors = {}
  let step: StepKey | null = null
  if (!Array.isArray(details)) return { errors, step }
  for (const d of details as { field?: string, message?: string }[]) {
    const [section, field = ''] = String(d.field ?? '').split('.')
    const formKey = SECTION_TO_FORM[section ?? '']
    if (!formKey) continue
    step ??= section as StepKey
    errors[`${formKey}.${field || 'section'}`] ??= d.message ?? 'مقدار نامعتبر است.'
  }
  return { errors, step }
}

/** Which wizard step a flat error key belongs to. */
export function stepOfErrorKey(key: string, type: ApplicantType | ''): StepKey | null {
  const prefix = key.split('.')[0]
  const map: Record<string, StepKey> = {
    applicant_type: 'type', company: 'company_info', rep: 'representative',
    identity: 'identity', contact: 'contact', vehicle: 'vehicle', area: 'service_area',
  }
  return (prefix && map[prefix]) || (type ? null : 'type')
}

/** Persian text for the backend's duplicate (409) messages. */
export function conflictMessage(message: string): string {
  const m = message.toLowerCase()
  if (m.includes('national code')) return 'راننده‌ای با این کد ملی قبلاً ثبت شده است.'
  if (m.includes('legal national id')) return 'شرکتی با این شناسه ملی قبلاً ثبت شده است.'
  if (m.includes('mobile')) return 'این شماره موبایل قبلاً ثبت شده است.'
  if (m.includes('file')) return 'فایل پیوست‌شده پیدا نشد؛ لطفاً دوباره بارگذاری کنید.'
  return message
}

/** Which wizard step a duplicate (409) message is about, so the dialog can jump there. */
export function conflictStep(message: string, type: ApplicantType | ''): StepKey | null {
  const m = message.toLowerCase()
  if (m.includes('national code')) return 'identity'
  if (m.includes('legal national id')) return 'company_info'
  if (m.includes('mobile')) return type === 'COMPANY' ? 'representative' : 'contact'
  if (m.includes('file')) return 'service_area'
  return null
}
