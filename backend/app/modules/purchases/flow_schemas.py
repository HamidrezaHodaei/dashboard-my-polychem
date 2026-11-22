"""Request bodies of the item-based purchase flow (/api/purchases/flow). Business rules (required fields,
permitted transitions) are enforced in flow.py with Persian messages that name the field."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.purchases.models import PurchasePriority

Priority = PurchasePriority


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


class FlowItemIn(_Body):
    id: int | None = None                      # an existing line (edit after «استرداد جهت اصلاح»)
    product_id: int | None = None
    category_id: int | None = None             # only used when the product has no group
    unit: str | None = Field(default=None, max_length=40)   # only used when the product has no unit
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=3)
    current_stock: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    reorder_point: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    request_type: str | None = Field(default=None, max_length=150)
    purchase_subject: Literal["ASSET", "GENERAL"] | None = None
    priority: Priority | None = None


class FlowRequestIn(_Body):
    request_no: str | None = Field(default=None, max_length=30)
    requester_unit: str | None = Field(default=None, max_length=200)
    requester_name: str | None = Field(default=None, max_length=150)
    required_date: str | None = None
    items: list[FlowItemIn] = Field(default_factory=list, max_length=200)


class StatusIn(_Body):
    status: Literal["UNDER_REVIEW", "SOURCING", "RETURNED", "VOID"]
    note: str | None = Field(default=None, max_length=1000)


class SupplyPlaceIn(_Body):
    supply_place: Literal["LOCAL", "NON_LOCAL"]


class QuoteIn(_Body):
    id: int | None = None
    supplier_id: int | None = None
    supplier_name: str | None = Field(default=None, max_length=255)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    received_date: str | None = None
    validity_days: int | None = Field(default=None, ge=0, le=3650)
    delivery_days: int | None = Field(default=None, ge=0, le=3650)
    payment_method: Literal["CASH", "CHEQUE"] | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    file_id: str | None = Field(default=None, max_length=36)
    note: str | None = Field(default=None, max_length=5000)


class SubmitItemsIn(_Body):
    item_ids: list[int] = Field(min_length=1, max_length=200)


class ManagerDecisionIn(_Body):
    action: Literal["APPROVE", "RETURN"]
    quote_id: int | None = None                # APPROVE: the chosen quotation of THIS item
    note: str | None = Field(default=None, max_length=1000)


class PaymentIn(_Body):
    method: Literal["CASH", "CHEQUE"] | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    # cash
    paid_date: str | None = None
    payment_ref: str | None = Field(default=None, max_length=100)
    receipt_file_id: str | None = Field(default=None, max_length=36)
    # cheque
    cheque_file_id: str | None = Field(default=None, max_length=36)
    cheque_no: str | None = Field(default=None, max_length=50)
    cheque_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=0)
    cheque_issue_date: str | None = None
    cheque_due_date: str | None = None
    cheque_bank: str | None = Field(default=None, max_length=150)
    cheque_payee: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)


class FinanceReturnIn(_Body):
    item_ids: list[int] | None = Field(default=None, max_length=200)


class ItemStatusIn(_Body):
    status: Literal["SHIPPING", "DELIVERED", "CANCELLED"]   # «پرداخت‌شده» is set by finance handing the request back
    note: str | None = Field(default=None, max_length=1000)
    file_id: str | None = Field(default=None, max_length=36)   # the warehouse receipt, optionally together with DELIVERED


class ReceiptIn(_Body):
    file_id: str = Field(max_length=36)


class OptionIn(_Body):
    kind: Literal["UNIT", "REQUEST_TYPE"] | None = None
    label: str | None = Field(default=None, max_length=150)
    sort_order: int | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None


class SlaRowIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority: Priority
    amount: int = Field(ge=1, le=100000)
    unit: Literal["DAYS", "HOURS"]


class SlaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[SlaRowIn] = Field(min_length=1, max_length=3)
