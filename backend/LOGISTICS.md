# Logistics module — ثبت‌نام شرکت حمل‌ونقل و راننده

Backend for the registration wizard + staff panel. Built on the same pattern as
`modules/suppliers` (Flask blueprint → Pydantic schemas → service layer with
permission checks → audit log). Frontend comes next; everything it needs is
served by the API (`/public/wizard`, `/public/reference`, `/public/validate-step`).

## Run it

```bash
flask db upgrade            # revision a7c3e9d1f5b2 (down_revision b3c7e1d5a9f4)
pytest tests/modules/logistics
```
The migration creates the tables **and** seeds permissions, the admin grants and three roles.
Run `python scripts/seed_roles_permissions.py` too if you seed fresh databases that way
(it already walks `REGISTRY`, which now contains the logistics keys).

## Wizard (what the frontend renders)

| Step | COMPANY (شرکت) | DRIVER (راننده) |
|---|---|---|
| 1 | انتخاب نوع متقاضی (2 cards) | same |
| 2 | `company_info` اطلاعات شرکت | `identity` اطلاعات هویتی |
| 3 | `representative` نماینده و تماس | `contact` اطلاعات تماس |
| 4 | `service_area` محدوده فعالیت | `vehicle` وسیله نقلیه و بارگیر (**driver only**) |
| 5 | — | `service_area` محدوده فعالیت |

`GET /api/logistics/public/wizard` returns this with every field's label, widget,
`required`, `visible_when`, `required_when`, format and `options_ref`.
The company path has **no vehicle step**, and the API rejects a `vehicle` section for a company
(vehicle columns exist only in `logistics_driver_profiles`).

## Field rules

**company_info**
- `entity_type` required: `INDIVIDUAL` | `LEGAL`
- `LEGAL` → `company_name` required; `first_name/last_name` dropped
- `INDIVIDUAL` → `first_name`, `last_name` required; `company_name` and `national_id` dropped
- `national_id` (شناسه ملی): **optional**, legal only; if sent: 11 digits + official check digit
- `province`, `city` **required**; city must belong to province
- `office_address` required, ≥ 10 chars

**representative**: `first_name`, `last_name`, `position` (code) required; `position_other` required iff `OTHER`;
`mobile` required (`09XXXXXXXXX`, +98/Persian digits accepted); `landline` optional (with area code).

**identity**: `first_name`, `last_name`, `national_code` (10 digits + check digit) required, unique among live drivers.
**contact**: `mobile` required; `alt_phone` optional (mobile or landline).

**vehicle** (driver only): `vehicle_type`, `body_type`, `capacity_tons` (0.01–100), `cargo_types` (≥1) required.
`*_other` text required iff the matching value is `OTHER` (cargo: iff `OTHER` is among `cargo_types`), otherwise cleared.

**service_area** (shared; stored as an independent row per applicant)

| `area_type` | `coverage` | countries | permits |
|---|---|---|---|
| `CITY` | exactly 1 province, exactly 1 city | cleared | cleared |
| `PROVINCIAL` | exactly 1 province; whole province or ≥1 city | cleared | cleared |
| `INTERPROVINCIAL` | ≥ 2 provinces; each whole or ≥1 city | cleared | cleared |
| `INTERNATIONAL` | optional (e.g. border provinces) | `origin_countries` ≥1 and `destination_countries` ≥1, at least one non-IR | see below |

Changing `area_type` never errors on leftovers — irrelevant fields are cleared server-side.
Permits (international only): company must attach `INTL_TRANSPORT_LICENSE`, driver `INTL_DRIVER_PERMIT`
(each **with a file**); `TIR_CARNET`, `CMR_INSURANCE`, `OTHER_PERMIT` optional. Upload via `POST /public/files`,
then send `{type, number?, expires_at?, file:{id}}`; file name/size are re-read from the upload record.

## Payloads

```jsonc
// POST /api/logistics/public/register
{ "applicant_type": "COMPANY",
  "company_info": {"entity_type":"LEGAL","company_name":"…","national_id":"…","province":"تهران","city":"شهریار","office_address":"…"},
  "representative": {"first_name":"…","last_name":"…","position":"CEO","mobile":"09121234567"},
  "service_area": {"area_type":"PROVINCIAL","coverage":[{"province":"تهران","all_cities":true}]} }

{ "applicant_type": "DRIVER",
  "identity": {…}, "contact": {…},
  "vehicle": {"vehicle_type":"TRAILER","body_type":"REFRIGERATED","capacity_tons":22.5,"cargo_types":["FOOD"]},
  "service_area": {…} }
```
Errors: `400 VALIDATION_ERROR` with `details:[{field,message}]` (e.g. `company_info.city`),
`409 CONFLICT` for duplicates (driver national code, company legal ID, mobile per type) or unknown file id.

## Endpoints

Public (no auth, rate-limited): `GET /public/wizard`, `GET /public/reference`, `POST /public/validate-step`
(`{applicant_type, step, data}` → normalised data), `POST /public/files`, `POST /public/register` (→ `PENDING`).

Staff: `GET/POST /applicants`, `GET/PATCH/DELETE /applicants/<id>`, `POST /applicants/<id>/review`
(`APPROVE|REJECT|SUSPEND|REOPEN`, note required for REJECT/SUSPEND), `GET /stats`, `GET /files/<id>`.
List filters: `applicant_type, search, status, province, area_type, vehicle_type, body_type, include_inactive, page, per_page`.
`PATCH` replaces each section sent as a whole (validated as complete).

Status flow: `PENDING → APPROVED | REJECTED`, `APPROVED → SUSPENDED → APPROVED`, `REJECTED → PENDING (REOPEN)`.

## Access levels (backend-enforced)

Keys: `logistics.company.*` and `logistics.driver.*` × `read, create, update, delete, review`.
Checks are per applicant type (in `services.py`): a user with only `logistics.driver.read` sees drivers only,
gets 403 on a company id, and `?applicant_type=COMPANY` is 403. `review` (decide a registration) is separate from
`update` and non-delegable; creating a record directly as `APPROVED/REJECTED/SUSPENDED` also needs `review`.

Seeded by the migration (GLOBAL grants on both types): `admin` (all), `logistics_manager` (all),
`logistics_operator` (read/create/update), `logistics_viewer` (read). The two types appear as rows
"Transport Companies" / "Drivers" in the role and per-user permission matrix with five columns
(read, create, update, delete, **review**). `review` is a per-row extra action (`MatrixModule.extra_actions`),
so only these two rows show it; every other row keeps its four columns.
Navigation (`/api/me/navigation`) gains `logistics_companies` and `logistics_drivers`.

## Decisions to confirm
- `office_address` is **required** (your list marked only province/city as required).
- Reference lists (`reference_data.py`) hold main cities per province (≈270), not every city in Iran — extend `CITIES` freely.
- Duplicate checks run in `validate-step` too (better UX), which lets anyone probe whether a national code/mobile is registered; it is rate-limited. Drop those calls in `services.validate_public_step` if that is unacceptable.
- Permission scoping is GLOBAL only (like Suppliers); no department/team scoping.
