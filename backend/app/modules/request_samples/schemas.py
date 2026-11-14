"""Request / response shapes of the Request Sample module (dates are ISO `YYYY-MM-DD`)."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PRIORITIES = ("LOW", "NORMAL", "HIGH", "URGENT")
FOLLOWUP_METHODS = ("PHONE", "EMAIL", "MEETING", "MESSAGE", "OTHER")
FEEDBACK_STATUSES = ("ACCEPTED", "REJECTED", "ACCEPTED_WITH_CONDITIONS", "UNDER_EVALUATION", "NO_RESPONSE")
TRANSITIONS = ("submit", "approve", "reject", "hold", "resume", "complete", "cancel")
UNITS = ("kg", "g", "ton", "liter", "piece")


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _blank_to_none(v):
    return None if isinstance(v, str) and not v.strip() else v


class ItemIn(_In):
    product_name: str = Field(min_length=1, max_length=255)
    grade: str | None = Field(default=None, max_length=255)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = "kg"
    number_of_samples: int = Field(default=1, ge=1, le=10000)
    packaging: str | None = Field(default=None, max_length=200)
    specifications: str | None = None

    @field_validator("grade", "packaging", "specifications", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)

    @field_validator("unit")
    @classmethod
    def _unit(cls, v):
        if v not in UNITS:
            raise ValueError(f"unit must be one of {', '.join(UNITS)}")
        return v


class RequestIn(_In):
    """Create / update. A draft may be incomplete; `submit` re-validates everything."""

    customer_id: int
    sales_rep_user_id: int | None = None
    priority: str = "NORMAL"
    dispatch_ref_number: str | None = Field(default=None, max_length=100)
    required_delivery_date: date | None = None
    purpose: str | None = None
    technical_requirements: str | None = None
    delivery_method: str | None = Field(default=None, max_length=100)
    recipient_name: str | None = Field(default=None, max_length=200)
    delivery_address: str | None = None
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    delivery_instructions: str | None = None
    internal_notes: str | None = None
    items: list[ItemIn] = Field(default_factory=list, max_length=50)
    file_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator(
        "dispatch_ref_number", "purpose", "technical_requirements", "delivery_method", "recipient_name", "delivery_address", "country", "city",
        "postal_code", "delivery_instructions", "internal_notes", mode="before",
    )
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)

    @field_validator("priority")
    @classmethod
    def _priority(cls, v):
        if v not in PRIORITIES:
            raise ValueError(f"priority must be one of {', '.join(PRIORITIES)}")
        return v


class TransitionIn(_In):
    action: str
    note: str | None = None

    @field_validator("action")
    @classmethod
    def _action(cls, v):
        if v not in TRANSITIONS:
            raise ValueError(f"action must be one of {', '.join(TRANSITIONS)}")
        return v


class DispatchIn(_In):
    dispatch_date: date
    reference_number: str = Field(min_length=1, max_length=100)
    delivery_method: str | None = Field(default=None, max_length=100)
    tracking_number: str | None = Field(default=None, max_length=100)
    carrier: str | None = Field(default=None, max_length=200)
    shipped_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    unit: str = "kg"
    recipient_name: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    # true when this shipment completes the dispatch -> the request moves to "Awaiting Feedback"
    all_shipped: bool = True
    file_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("delivery_method", "tracking_number", "carrier", "recipient_name", "notes", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)


class DeliveryIn(_In):
    """The customer has received the sample (moves the request from «ارسال‌شده» to the follow-up phase)."""

    delivered_date: date
    received_by: str | None = Field(default=None, max_length=200)
    note: str | None = None

    @field_validator("received_by", "note", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)


class FollowUpIn(_In):
    followup_date: date
    method: str
    contact_person: str | None = Field(default=None, max_length=200)
    result: str | None = None
    customer_response: str | None = None
    next_followup_date: date | None = None
    responsible_user_id: int | None = None
    internal_notes: str | None = None
    file_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("contact_person", "result", "customer_response", "internal_notes", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)

    @field_validator("method")
    @classmethod
    def _method(cls, v):
        if v not in FOLLOWUP_METHODS:
            raise ValueError(f"method must be one of {', '.join(FOLLOWUP_METHODS)}")
        return v


class FeedbackIn(_In):
    feedback_status: str
    feedback_date: date
    product_evaluation: str | None = None
    technical_acceptance: bool | None = None
    customer_comments: str | None = None
    rejection_reason: str | None = None
    improvement_suggestions: str | None = None
    evaluated_by: str | None = Field(default=None, max_length=200)
    file_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("product_evaluation", "customer_comments", "rejection_reason", "improvement_suggestions",
                     "evaluated_by", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)

    @field_validator("feedback_status")
    @classmethod
    def _status(cls, v):
        if v not in FEEDBACK_STATUSES:
            raise ValueError(f"feedback_status must be one of {', '.join(FEEDBACK_STATUSES)}")
        return v


class ConvertIn(_In):
    sale_id: int | None = None
    note: str | None = None
