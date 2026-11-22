"""Request bodies for /api/purchases. Every field is optional here on purpose: a wizard step can be saved
as a draft at any time. What a step REQUIRES is enforced by services.py when the step is completed
(`complete: true`), with Persian error messages that name the field."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.purchases.models import DeliveryStatus, PurchasePriority, ReferenceSource

Money = Decimal | None


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


class FileRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(max_length=36)


class BasicIn(_Body):
    request_no: str | None = Field(default=None, max_length=30)
    requester_unit: str | None = Field(default=None, max_length=200)
    requester_name: str | None = Field(default=None, max_length=150)
    request_date: str | None = None
    subject: str | None = Field(default=None, max_length=255)
    priority: PurchasePriority | None = None
    reason: str | None = Field(default=None, max_length=5000)
    description: str | None = Field(default=None, max_length=5000)
    complete: bool = False


class ItemIn(_Body):
    id: int | None = None
    product_id: int | None = None
    category_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    specs: str | None = Field(default=None, max_length=5000)
    brand_model: str | None = Field(default=None, max_length=150)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    unit: str | None = Field(default=None, max_length=40)
    estimated_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    reference_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    reference_source: ReferenceSource | None = None
    reference_note: str | None = Field(default=None, max_length=500)
    reference_item_id: int | None = None


class ItemsIn(_Body):
    items: list[ItemIn] = Field(default_factory=list, max_length=200)
    complete: bool = False


class BudgetIn(_Body):
    budget_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    required_date: str | None = None
    delivery_location: str | None = Field(default=None, max_length=255)
    files: list[FileRef] | None = None
    complete: bool = False


class InquiryLineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: int
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=0)


class InquiryIn(_Body):
    supplier_id: int | None = None
    received_date: str | None = None
    validity_days: int | None = Field(default=None, ge=0, le=3650)
    delivery_days: int | None = Field(default=None, ge=0, le=3650)
    payment_terms: str | None = Field(default=None, max_length=500)
    extra_costs: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    file_id: str | None = Field(default=None, max_length=36)
    note: str | None = Field(default=None, max_length=5000)
    lines: list[InquiryLineIn] = Field(default_factory=list, max_length=200)


class InquiriesIn(_Body):
    # at most three quotations per request (a hard rule, also enforced in the service)
    inquiries: list[InquiryIn] = Field(default_factory=list, max_length=3)
    shortfall_reason: str | None = Field(default=None, max_length=5000)
    complete: bool = False


SelectionReason = Literal["LOWEST_PRICE", "QUALITY", "DELIVERY_TIME", "PAYMENT_TERMS", "OTHER"]


class SelectionLineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: int
    final_unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=0)


class SelectionIn(_Body):
    inquiry_id: int | None = None
    reasons: list[SelectionReason] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=5000)
    # agreed final unit price per item; an item left out takes the selected quotation's unit price
    lines: list[SelectionLineIn] = Field(default_factory=list, max_length=200)
    complete: bool = False


class ResultLineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: int
    purchased_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=3)
    final_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)


class ResultIn(_Body):
    purchase_date: str | None = None
    final_extra_costs: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    delivery_status: DeliveryStatus | None = None
    completion_note: str | None = Field(default=None, max_length=5000)
    files: list[FileRef] | None = None
    lines: list[ResultLineIn] = Field(default_factory=list, max_length=200)
    complete: bool = False


class NoteIn(_Body):
    note: str | None = Field(default=None, max_length=1000)


class ApproveReferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_ids: list[int] = Field(min_length=1, max_length=200)


class ProductIn(_Body):
    name: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    unit: str | None = Field(default=None, max_length=40)
    category_id: int | None = None
    is_active: bool | None = None


class ReviewIn(_Body):
    status: Literal["PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_REVISION"]
    note: str | None = Field(default=None, max_length=1000)


class DirectIn(_Body):
    doc_no: str | None = Field(default=None, max_length=50)
    purchase_date: str | None = None
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    supplier_id: int | None = None
    supplier_name: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    usage_place: str | None = Field(default=None, max_length=255)
