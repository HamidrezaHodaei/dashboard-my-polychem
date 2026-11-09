"""Pydantic schemas for /api/customers -- CRM module (6-step customer file)."""
import datetime as dt
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.customers.models import (
    AcquaintanceSource, ActivityType, CommercialStatus, CreditRating, CustomerType, OperationalStatus, PaymentType,
    PurchaseMethod, QuantityUnit, OptionKind,
)

# ── helpers ──────────────────────────────────────────────────────────
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _digits_only(v, length: int, label: str):
    """Persian/Arabic digits -> Latin, spaces/dashes dropped, exact length."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"{label} must be text.")
    v = v.translate(_DIGITS).replace(" ", "").replace("-", "")
    if not v:
        return None
    if not (v.isascii() and v.isdigit() and len(v) == length):
        raise ValueError(f"{label} must be {length} digits.")
    return v


def _phone(v, label: str):
    """Lenient on purpose (customers may be foreign): optional +, 7-15 digits."""
    if v is None:
        return None
    v = str(v).translate(_DIGITS).replace(" ", "").replace("-", "")
    if not v:
        return None
    body = v[1:] if v.startswith("+") else v
    if not (body.isascii() and body.isdigit() and 7 <= len(body) <= 15):
        raise ValueError(f"{label} is not a valid phone number.")
    return v


def _not_future(v: dt.date | None, label: str):
    if v is not None and v > dt.date.today():
        raise ValueError(f"{label} cannot be in the future.")
    return v


_UNIT_ALIASES = {
    "TON": "TON", "TONS": "TON", "T": "TON", "تن": "TON",
    "KG": "KG", "KGS": "KG", "کیلو": "KG", "کیلوگرم": "KG", "کیلو گرم": "KG",
}


def _unit(v):
    """Missing -> TON (the default). Accepts the enum value plus the common Persian / English spellings."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return QuantityUnit.TON.value
    if isinstance(v, QuantityUnit):
        return v.value
    if isinstance(v, str):
        hit = _UNIT_ALIASES.get(v.strip().upper().replace("ي", "ی").replace("ك", "ک"))
        if hit:
            return hit
    raise ValueError("Unit must be TON or KG.")


class _Strip(BaseModel):
    """Trims every string; a blank string becomes None (so 'required' checks see it as missing)."""

    @field_validator("*", mode="before")
    @classmethod
    def _strip_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


# ── repeatable rows ──────────────────────────────────────────────────
class CustomerContact(_Strip):
    """A person to reach. Name + position mandatory; at least one number.
    `position` is picked from a fixed list in the panel (GET /options -> contact_positions) or,
    for "سایر", typed by hand -- so it is stored as plain text. `birth_date` is optional."""

    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    position: str = Field(..., max_length=100)
    email: str | None = Field(default=None, max_length=255)
    mobile: str | None = Field(default=None, max_length=30)
    landline: str | None = Field(default=None, max_length=30)
    birth_date: dt.date | None = None

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v):
        return _phone(v, "Mobile number")

    @field_validator("landline")
    @classmethod
    def _landline(cls, v):
        return _phone(v, "Landline number")

    @field_validator("birth_date")
    @classmethod
    def _birth(cls, v):
        return _not_future(v, "Birth date")

    @model_validator(mode="after")
    def _needs_a_number(self):
        if not self.mobile and not self.landline:
            raise ValueError("Each contact needs a mobile or a landline number.")
        return self


class ProducedProduct(_Strip):
    """What the customer manufactures, and how much PER YEAR (whole number, in `unit`).
    An old `period` key sent by a stale client is ignored: production is yearly only."""

    name: str = Field(..., max_length=255)
    amount: int | None = Field(default=None, ge=0, le=10**12)
    unit: QuantityUnit = QuantityUnit.TON

    @field_validator("unit", mode="before")
    @classmethod
    def _u(cls, v):
        return _unit(v)


class ConsumedProduct(_Strip):
    """A product the customer needs (no photo/datasheet on purpose)."""

    name: str = Field(..., max_length=255)
    grade_specs: str | None = None  # grade / technical requirements
    monthly_consumption: int = Field(..., ge=0, le=10**12)  # whole numbers, in `unit`
    annual_consumption: int = Field(..., ge=0, le=10**12)
    unit: QuantityUnit = QuantityUnit.TON

    @field_validator("unit", mode="before")
    @classmethod
    def _u(cls, v):
        return _unit(v)


class SupplierGrade(_Strip):
    """One consumed product (and its grade) the customer takes from a given supplier."""

    product: str = Field(..., max_length=255)
    grade: str | None = None


class CurrentSupplier(_Strip):
    """A supplier the customer buys from today -- free text, optionally linked
    to a supplier already in the system (then the name is filled from it).
    `grades` lists which of the customer's consumed products/grades come from it."""

    name: str | None = Field(default=None, max_length=255)
    supplier_id: int | None = Field(default=None, ge=1)
    grades: list[SupplierGrade] = Field(default_factory=list)

    @field_validator("grades")
    @classmethod
    def _unique_grades(cls, v):
        seen, out = set(), []
        for g in v:
            key = (g.product, g.grade or "")
            if key not in seen:
                seen.add(key)
                out.append(g)
        return out

    @model_validator(mode="after")
    def _name_or_link(self):
        if not self.name and not self.supplier_id:
            raise ValueError("A current supplier needs a name or a linked supplier.")
        return self


class ContactLogEntry(_Strip):
    date: dt.date
    note: str | None = None

    @field_validator("date")
    @classmethod
    def _past(cls, v):
        return _not_future(v, "Contact date")


class Industry(_Strip):
    """One industry of a customer: a main category plus an optional sub-category."""

    category: str = Field(..., max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)


def _dedupe_industries(rows):
    seen, out = set(), []
    for r in rows:
        key = (r.category, r.subcategory)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ── the customer file ────────────────────────────────────────────────
class CustomerFields(_Strip):
    """Every column the file can hold, all optional here. CustomerCreate adds the
    required rules; CustomerUpdate keeps everything optional (partial PATCH)."""

    # step 1
    customer_type: CustomerType | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    national_id: str | None = None
    brand_name: str | None = Field(default=None, max_length=255)  # individual customers only
    company_name: str | None = Field(default=None, max_length=255)
    company_national_id: str | None = None
    registration_number: str | None = Field(default=None, max_length=50)
    economic_id: str | None = Field(default=None, max_length=20)
    activity_start_date: dt.date | None = None
    contacts: list[CustomerContact] | None = None
    head_office_address: str | None = None
    head_office_postal_code: str | None = None
    factory_address: str | None = None
    factory_postal_code: str | None = None
    acquaintance_source: AcquaintanceSource | None = None
    acquaintance_source_other: str | None = Field(default=None, max_length=255)  # required when OTHER
    # step 2
    industries: list[Industry] | None = None
    # Single-industry shorthand kept for older clients: means "industries = [{category, subcategory}]".
    category: str | None = Field(default=None, max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    activity_types: list[ActivityType] | None = None
    produced_products: list[ProducedProduct] | None = None
    production_lines_count: int | None = Field(default=None, ge=0, le=100000)
    production_line_names: list[str] | None = None  # free list: as many lines as the user adds
    # production_capacity is NOT an input: services.py derives it from produced_products.
    factory_province: str | None = Field(default=None, max_length=100)
    factory_city: str | None = Field(default=None, max_length=100)
    factory_location: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    # step 3
    consumed_products: list[ConsumedProduct] | None = None
    current_suppliers: list[CurrentSupplier] | None = None
    # step 4
    commercial_status: CommercialStatus | None = None
    operational_status: OperationalStatus | None = None
    contact_log: list[ContactLogEntry] | None = None
    first_purchase_date: dt.date | None = None
    last_purchase_date: dt.date | None = None
    assigned_to_user_id: int | None = Field(default=None, ge=1)
    inactive_reason: str | None = None
    # step 5
    payment_type: PaymentType | None = None
    credit_months: int | None = Field(default=None, ge=1, le=12)
    credit_other: str | None = Field(default=None, max_length=100)
    payment_terms: str | None = None
    purchase_method: PurchaseMethod | None = None
    delivery_type: str | None = Field(default=None, max_length=255)
    unloading_location: str | None = None
    approved_credit_limit: int | None = Field(default=None, ge=0)
    credit_rating: CreditRating | None = None
    # step 6
    internal_notes: str | None = None
    last_negotiation_date: dt.date | None = None
    last_negotiation_result: str | None = None
    next_action: str | None = None
    next_follow_up_date: dt.date | None = None
    registration_date: dt.date | None = None

    @field_validator("national_id")
    @classmethod
    def _nid(cls, v):
        return _digits_only(v, 10, "National ID")

    @field_validator("company_national_id")
    @classmethod
    def _cnid(cls, v):
        return _digits_only(v, 11, "Company national ID")

    @field_validator("head_office_postal_code", "factory_postal_code")
    @classmethod
    def _postal(cls, v):
        return _digits_only(v, 10, "Postal code")

    @field_validator("activity_start_date", "first_purchase_date", "last_purchase_date", "last_negotiation_date")
    @classmethod
    def _past(cls, v):
        return _not_future(v, "Date")

    @field_validator("production_line_names")
    @classmethod
    def _line_names(cls, v):
        if v is None:
            return v
        out = []
        for name in v:
            if name is None:
                name = ""
            if not isinstance(name, str):
                raise ValueError("Production line names must be text.")
            name = " ".join(name.split())
            if len(name) > 255:
                raise ValueError("A production line name can be at most 255 characters.")
            out.append(name)
        out = [n for n in out if n]  # blank rows carry no information
        if len(out) > 200:
            raise ValueError("At most 200 production lines can be listed.")
        return out

    @field_validator("industries")
    @classmethod
    def _industries(cls, v):
        return _dedupe_industries(v) if v is not None else v

    @model_validator(mode="after")
    def _ranges(self):
        fp, lp = self.first_purchase_date, self.last_purchase_date
        if fp and lp and lp < fp:
            raise ValueError("Last purchase date cannot be before the first purchase date.")
        return self


def check_identity(customer_type, f) -> None:
    """Identity rules by type. `f` is anything with the identity attributes
    (a schema or the Customer row), so create and the post-merge update check share it."""
    if customer_type == CustomerType.LEGAL:
        if not f.company_name:
            raise ValueError("Company name is required for a legal customer.")
        if not f.company_national_id:
            raise ValueError("Company national ID (11 digits) is required for a legal customer.")
    else:
        if not f.first_name or not f.last_name:
            raise ValueError("First name and last name are required for an individual customer.")
        if not f.national_id:
            raise ValueError("National ID (10 digits) is required for an individual customer.")


class CustomerCreate(CustomerFields):
    """Everything marked ضروری in the spec is required here."""

    customer_type: CustomerType
    contacts: list[CustomerContact] = Field(..., min_length=1)
    activity_types: list[ActivityType] = Field(..., min_length=1)
    factory_province: str = Field(..., min_length=1, max_length=100)
    factory_city: str = Field(..., min_length=1, max_length=100)
    consumed_products: list[ConsumedProduct] = Field(..., min_length=1)
    commercial_status: CommercialStatus
    produced_products: list[ProducedProduct] = Field(default_factory=list)
    current_suppliers: list[CurrentSupplier] = Field(default_factory=list)
    contact_log: list[ContactLogEntry] = Field(default_factory=list)
    operational_status: OperationalStatus = OperationalStatus.ACTIVE
    # True -> the file is signed off ("ثبت نهایی") in the same request.
    finalize: bool = False

    @model_validator(mode="after")
    def _identity(self):
        check_identity(self.customer_type, self)
        return self

    @model_validator(mode="after")
    def _industry_required(self):
        """At least one industry: `industries`, or the single `category` (+ `subcategory`) shorthand."""
        if not self.industries:
            if not self.category:
                raise ValueError("At least one industry is required.")
            self.industries = [Industry(category=self.category, subcategory=self.subcategory)]
        first = self.industries[0]
        self.category, self.subcategory = first.category, first.subcategory
        return self

    @model_validator(mode="after")
    def _terms(self):
        if self.acquaintance_source == AcquaintanceSource.OTHER and not self.acquaintance_source_other:
            raise ValueError("Describe the acquaintance source when choosing 'Other'.")
        if self.payment_type in (PaymentType.CREDIT, PaymentType.CASH_CREDIT) and not (
            self.credit_months or self.credit_other
        ):
            raise ValueError("Credit duration (1-12 months or other) is required for credit payments.")
        return self


# Fields that may be omitted from a PATCH but never set to null.
_NOT_NULLABLE = (
    "customer_type", "contacts", "category", "industries", "activity_types", "factory_province", "factory_city",
    "consumed_products", "commercial_status", "operational_status", "produced_products",
    "current_suppliers", "contact_log",
)


class CustomerUpdate(CustomerFields):
    """Partial update (exclude_unset in services.py). Lists that must not be
    empty keep that rule when they are sent."""

    contacts: list[CustomerContact] | None = Field(default=None, min_length=1)
    industries: list[Industry] | None = Field(default=None, min_length=1)
    activity_types: list[ActivityType] | None = Field(default=None, min_length=1)
    consumed_products: list[ConsumedProduct] | None = Field(default=None, min_length=1)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _no_nulls(self):
        for name in _NOT_NULLABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be empty.")
        return self


class CustomerPublic(BaseModel):
    """Response shape (never validated from a request)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    customer_type: CustomerType
    first_name: str | None
    last_name: str | None
    national_id: str | None
    brand_name: str | None
    company_name: str | None
    company_national_id: str | None
    registration_number: str | None
    economic_id: str | None
    activity_start_date: dt.date | None
    contacts: list[dict]
    head_office_address: str | None
    head_office_postal_code: str | None
    factory_address: str | None
    factory_postal_code: str | None
    acquaintance_source: AcquaintanceSource | None
    acquaintance_source_other: str | None
    industries: list[dict]
    category: str | None  # first industry (kept for older clients)
    subcategory: str | None
    activity_types: list[str]
    produced_products: list[dict]
    production_lines_count: int | None
    production_line_names: list[str]
    production_capacity: float | None  # tons per year (sum of produced_products)
    factory_province: str | None
    factory_city: str | None
    factory_location: str | None
    latitude: float | None
    longitude: float | None
    consumed_products: list[dict]
    current_suppliers: list[dict]
    commercial_status: CommercialStatus
    operational_status: OperationalStatus
    contact_log: list[dict]
    first_contact_date: dt.date | None
    first_purchase_date: dt.date | None
    last_purchase_date: dt.date | None
    assigned_to_user_id: int | None
    assigned_to_name: str | None
    inactive_reason: str | None
    payment_type: PaymentType | None
    credit_months: int | None
    credit_other: str | None
    payment_terms: str | None
    purchase_method: PurchaseMethod | None
    delivery_type: str | None
    unloading_location: str | None
    approved_credit_limit: int | None
    credit_rating: CreditRating | None
    internal_notes: str | None
    last_negotiation_date: dt.date | None
    last_negotiation_result: str | None
    next_action: str | None
    next_follow_up_date: dt.date | None
    registration_date: dt.date | None
    review_status: str
    review_note: str | None
    decided_at: dt.datetime | None
    change_request_note: str | None
    change_requested_at: dt.datetime | None
    is_finalized: bool
    finalized_at: dt.datetime | None
    finalized_by_user_id: int | None
    is_active: bool
    created_by_user_id: int | None
    created_by_name: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    @field_validator("production_line_names", mode="before")
    @classmethod
    def _names_default(cls, v):
        return v or []


# ── categories ───────────────────────────────────────────────────────
def _clean_name(v: str | None) -> str | None:
    if v is None:
        return v
    v = " ".join(v.split())
    if not v:
        raise ValueError("Category name cannot be empty.")
    return v


class CategoryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    # None = main category; an id = sub-category of that main category.
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        return _clean_name(v)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        return _clean_name(v)


# ── product / grade pick-lists ───────────────────────────────────────
class OptionItemIn(BaseModel):
    kind: OptionKind
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        return _clean_name(v)


class OptionItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        return _clean_name(v)