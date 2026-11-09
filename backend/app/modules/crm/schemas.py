"""Pydantic schemas for /api/crm -- sales, payment methods, import.

(There are no product schemas: products live in the customer bank's pick-list and are managed there.)"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.crm.models import DocumentType, SaleStatus, SaleType
from app.utils.jalali import parse_date_input

_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})


def clean_text(v):
    if v is None:
        return None
    return str(v).translate(_AR_TO_FA).strip() or None


def _date_text(v):
    """Validate now so a bad date is a field error (400) rather than a 500 later."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        parse_date_input(v)
    except (ValueError, TypeError) as exc:
        raise ValueError("Date must be a valid Jalali (1405/08/15) or Gregorian (2026-11-06) date.") from exc
    return v


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SaleCreate(_Base):
    customer_id: int = Field(gt=0)  # customer bank primary key
    product_id: int = Field(gt=0)
    payment_method_id: int | None = Field(default=None, gt=0)
    quantity_kg: Decimal = Field(ge=0, max_digits=16, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    # Optional explicit total (spreadsheet imports carry the net amount); otherwise quantity x price.
    amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=2)
    sale_type: SaleType = SaleType.OFFICIAL
    document_type: DocumentType = DocumentType.INVOICE
    status: SaleStatus = SaleStatus.PROCESSING
    date: str | None = None  # Jalali or Gregorian; empty -> today (Tehran)
    description: str | None = Field(default=None, max_length=5000)

    v_date = field_validator("date", mode="before")(_date_text)
    v_desc = field_validator("description", mode="before")(clean_text)


class SaleUpdate(_Base):
    customer_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)
    payment_method_id: int | None = Field(default=None, gt=0)
    clear_payment_method: bool = False
    quantity_kg: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=2)
    sale_type: SaleType | None = None
    document_type: DocumentType | None = None
    status: SaleStatus | None = None
    date: str | None = None
    description: str | None = Field(default=None, max_length=5000)

    v_date = field_validator("date", mode="before")(_date_text)
    v_desc = field_validator("description", mode="before")(clean_text)


class PaymentMethodIn(_Base):
    name: str = Field(min_length=1, max_length=100)

    v_name = field_validator("name", mode="before")(clean_text)


class PaymentMethodUpdate(_Base):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

    v_name = field_validator("name", mode="before")(clean_text)


class ImportRow(_Base):
    """One spreadsheet line. The customer is matched BY NAME against the customer bank --
    it is never created here (the bank is the single source of customers)."""

    customer: str = Field(min_length=1, max_length=255)
    product: str = Field(min_length=1, max_length=150)
    quantity_kg: Decimal = Field(ge=0)
    unit_price: Decimal = Field(default=Decimal(0), ge=0)
    amount: Decimal | None = Field(default=None, ge=0)
    payment: str | None = Field(default=None, max_length=100)
    date: str
    document_type: DocumentType = DocumentType.INVOICE
    sale_type: SaleType = SaleType.OFFICIAL
    status: SaleStatus = SaleStatus.COMPLETED
    description: str | None = Field(default=None, max_length=5000)

    v_date = field_validator("date", mode="before")(_date_text)


class ImportRequest(_Base):
    rows: list[ImportRow] = Field(min_length=1, max_length=2000)
    dry_run: bool = False
