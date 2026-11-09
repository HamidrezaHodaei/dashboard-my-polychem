"""Pydantic schemas for /api/suppliers -- Procurement module."""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.request_schemas import ChangeRequestIn, ReviewIn  # noqa: F401  (shared with customers)

from app.modules.suppliers.models import SupplierQuality, SupplierStatus, SupplierType


class FileRef(BaseModel):
    """Pointer to an uploaded file (see POST /api/suppliers/files)."""

    id: str = Field(..., min_length=1, max_length=36)
    name: str = Field(..., min_length=1, max_length=255)
    size: int | None = None


class SupplierPhone(BaseModel):
    type: str = Field(..., pattern="^(mobile|landline)$")
    number: str = Field(..., min_length=1, max_length=30)


class SupplierContact(BaseModel):
    """One contact person. Name and position are mandatory; each person may
    have one mobile and one landline (at least one of the two)."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    mobile: str | None = Field(default=None, max_length=30)
    landline: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name", "position", "email", "mobile", "landline", mode="before")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def _needs_a_number(self):
        if not self.first_name or not self.last_name or not self.position:
            raise ValueError("Contact first name, last name and position are required.")
        if not self.mobile and not self.landline:
            raise ValueError("Each contact needs a mobile or a landline number.")
        return self


_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _clean_postal_code(v):
    """Blank -> None; Persian/Arabic digits -> Latin; must be exactly 10 digits."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Postal code must be text.")
    v = v.translate(_DIGIT_MAP).replace(" ", "").replace("-", "")
    if not v:
        return None
    if not (v.isascii() and v.isdigit() and len(v) == 10):
        raise ValueError("Postal code must be 10 digits.")
    return v


def _clean_brand_name(v):
    """نام برند یا مغازه: trimmed; blank -> None."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Brand name must be text.")
    return " ".join(v.split()) or None


def phones_from_contacts(contacts) -> list[dict]:
    """Flatten contacts into the legacy [{type, number}] list."""
    out: list[dict] = []
    for c in contacts:
        c = c if isinstance(c, dict) else c.model_dump()
        if c.get("mobile"):
            out.append({"type": "mobile", "number": c["mobile"]})
        if c.get("landline"):
            out.append({"type": "landline", "number": c["landline"]})
    return out


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _plain(v, max_len: int) -> str | None:
    """Trim + collapse spaces; blank -> None."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Value must be text.")
    out = " ".join(v.split())
    if len(out) > max_len:
        raise ValueError(f"At most {max_len} characters.")
    return out or None


class SupplierBankAccount(BaseModel):
    """One bank account of the supplier. EVERY field is optional (a row may hold only a
    card, only a Sheba, only a name ...); what is typed must be well-formed."""

    holder_name: str | None = None      # اسم شخص یا شرکت صاحب کارت / حساب
    bank_name: str | None = None        # typed by hand
    card_number: str | None = None      # 16 digits
    account_number: str | None = None   # digits (dashes / dots allowed)
    sheba: str | None = None            # IR + 24 digits

    @field_validator("holder_name", mode="before")
    @classmethod
    def _holder(cls, v):
        return _plain(v, 255)

    @field_validator("bank_name", mode="before")
    @classmethod
    def _bank(cls, v):
        return _plain(v, 100)

    @field_validator("card_number", mode="before")
    @classmethod
    def _card(cls, v):
        v = _plain(v, 40)
        if v is None:
            return None
        digits = v.translate(_DIGITS).replace(" ", "").replace("-", "")
        if not (digits.isascii() and digits.isdigit() and len(digits) == 16):
            raise ValueError("Card number must be 16 digits.")
        total = 0
        for i, ch in enumerate(reversed(digits)):  # Luhn: catches most typing mistakes
            d = int(ch)
            if i % 2 == 1:
                d = d * 2 - 9 if d > 4 else d * 2
            total += d
        if total % 10 != 0:
            raise ValueError("Card number is not valid.")
        return digits

    @field_validator("account_number", mode="before")
    @classmethod
    def _account(cls, v):
        v = _plain(v, 40)
        if v is None:
            return None
        out = v.translate(_DIGITS).replace(" ", "")
        if not re.fullmatch(r"[0-9][0-9.\-]{3,29}", out):
            raise ValueError("Account number may only contain digits, dashes and dots (4-30 characters).")
        return out

    @field_validator("sheba", mode="before")
    @classmethod
    def _sheba(cls, v):
        v = _plain(v, 40)
        if v is None:
            return None
        out = v.translate(_DIGITS).upper().replace(" ", "").replace("-", "")
        if out.startswith("IR"):
            out = out[2:]
        if not (out.isascii() and out.isdigit() and len(out) == 24):
            raise ValueError("Sheba must be IR followed by 24 digits.")
        # ISO 7064 mod 97-10: move "IRxx" to the end, I=18, R=27
        rearranged = out[2:] + "1827" + out[:2]
        if int(rearranged) % 97 != 1:
            raise ValueError("Sheba is not valid.")
        return "IR" + out

    @property
    def is_blank(self) -> bool:
        return not any((self.holder_name, self.bank_name, self.card_number, self.account_number, self.sheba))


def _drop_blank_accounts(rows):
    """Fully blank rows (an 'add' the user never filled in) carry no information."""
    if rows is None:
        return rows
    kept = [r for r in rows if not r.is_blank]
    if len(kept) > 50:
        raise ValueError("At most 50 bank accounts can be listed.")
    return kept


class SupplierProduct(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    specs: str | None = None
    payment: str | None = Field(default=None, pattern="^(cash|credit|both)$")
    creditMonths: int | None = Field(default=None, ge=1, le=12)
    description: str | None = None
    # FileRef for new uploads; a bare filename string only on older records.
    datasheet: FileRef | str | None = None
    # Product photo (an uploaded image). Optional here so the public form keeps
    # working until it sends one; the admin schemas below make it required.
    image: FileRef | None = None


class SupplierProductAdmin(SupplierProduct):
    """Product row as staff enter it in the panel: the photo is mandatory."""

    image: FileRef


class SupplierBase(BaseModel):
    """Fields shared by both the public form and the admin "add supplier"
    form -- same shape as the public page's `handleComplete()` payload."""

    supplier_type: SupplierType
    first_name: str | None = None
    last_name: str | None = None
    national_id: str | None = None
    brand_name: str | None = Field(default=None, max_length=255)  # individual suppliers only
    company_name: str | None = None
    company_national_id: str | None = None
    registration_number: str | None = None
    company_type: str | None = None
    established_date: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    postal_code: str | None = None
    category: str | None = None
    subcategory: str | None = None
    activity_type: str | None = None
    capacity: str | None = None
    experience: str | None = None
    contacts: list[SupplierContact] = Field(default_factory=list)
    phones: list[SupplierPhone] = Field(default_factory=list)
    products: list[SupplierProduct] = Field(default_factory=list)
    catalog_files: list[FileRef | str] = Field(default_factory=list)
    bank_accounts: list[SupplierBankAccount] = Field(default_factory=list)  # optional, any number

    @field_validator("bank_accounts", mode="after")
    @classmethod
    def _accounts(cls, v):
        return _drop_blank_accounts(v)

    @field_validator("postal_code", mode="before")
    @classmethod
    def _postal(cls, v):
        return _clean_postal_code(v)

    @field_validator("brand_name", mode="before")
    @classmethod
    def _brand(cls, v):
        return _clean_brand_name(v)

    @model_validator(mode="after")
    def _contacts_or_legacy_phones(self):
        if self.contacts:
            # phones is always derived from contacts when contacts are sent.
            self.phones = [SupplierPhone(**p) for p in phones_from_contacts(self.contacts)]
            return self
        # Legacy payload (public form not yet sending contacts): keep its rule
        # of at least one landline + one mobile.
        if not any(p.type == "landline" for p in self.phones) or not any(p.type == "mobile" for p in self.phones):
            raise ValueError("At least one landline and one mobile phone are required.")
        return self


class SupplierCreate(SupplierBase):
    """Used by the public, unauthenticated submission endpoint."""


class SupplierCreateAdmin(SupplierBase):
    """Used when staff add a supplier directly in the panel -- same shape,
    plus the two admin-only fields set at creation time."""

    contacts: list[SupplierContact] = Field(..., min_length=1)
    products: list[SupplierProductAdmin] = Field(default_factory=list)
    status: SupplierStatus = SupplierStatus.SEMI_ACTIVE
    quality: SupplierQuality | None = None
    # False = save as a draft: still the creator's to edit until they press "ثبت نهایی"
    is_finalized: bool = True


class SupplierUpdate(BaseModel):
    """Partial update -- covers both the admin's status/quality controls
    and ordinary field edits, all optional (exclude_unset in services.py)."""

    status: SupplierStatus | None = None
    quality: SupplierQuality | None = None
    is_active: bool | None = None
    supplier_type: SupplierType | None = None
    first_name: str | None = None
    last_name: str | None = None
    national_id: str | None = None
    brand_name: str | None = Field(default=None, max_length=255)  # individual suppliers only
    company_name: str | None = None
    company_national_id: str | None = None
    registration_number: str | None = None
    company_type: str | None = None
    established_date: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    postal_code: str | None = None
    category: str | None = None
    subcategory: str | None = None
    activity_type: str | None = None
    capacity: str | None = None
    experience: str | None = None
    contacts: list[SupplierContact] | None = Field(default=None, min_length=1)
    phones: list[SupplierPhone] | None = None
    products: list[SupplierProductAdmin] | None = None
    catalog_files: list[FileRef | str] | None = None
    bank_accounts: list[SupplierBankAccount] | None = None  # replaces the whole list

    @field_validator("bank_accounts", mode="after")
    @classmethod
    def _accounts(cls, v):
        return _drop_blank_accounts(v)

    @field_validator("postal_code", mode="before")
    @classmethod
    def _postal(cls, v):
        return _clean_postal_code(v)

    @field_validator("brand_name", mode="before")
    @classmethod
    def _brand(cls, v):
        return _clean_brand_name(v)


class SupplierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_type: SupplierType
    status: SupplierStatus
    quality: SupplierQuality | None
    display_name: str
    first_name: str | None
    last_name: str | None
    national_id: str | None
    brand_name: str | None
    company_name: str | None
    company_national_id: str | None
    registration_number: str | None
    company_type: str | None
    established_date: str | None
    email: str | None
    website: str | None
    address: str | None
    postal_code: str | None
    category: str | None
    subcategory: str | None
    activity_type: str | None
    capacity: str | None
    experience: str | None
    contacts: list[dict]
    phones: list[dict]
    products: list[dict]
    catalog_files: list[FileRef | str]
    bank_accounts: list[dict]
    is_public_submission: bool
    review_status: str
    review_note: str | None
    is_finalized: bool
    decided_at: datetime | None
    change_request_note: str | None
    change_requested_at: datetime | None
    is_active: bool
    created_by_user_id: int | None
    created_by_name: str | None
    reviewed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class CategoryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    # None = a main category; an id = a sub-category of that main category.
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Category name cannot be empty.")
        return v


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("Category name cannot be empty.")
        return v