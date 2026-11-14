"""
Request Sample (درخواست نمونه محصول) -- CRM sub-module.

A sales rep asks for a product sample for a customer; a manager approves / rejects; the sample is
dispatched (possibly in several shipments); the rep records any number of follow-ups; the customer's
FINAL feedback is recorded once, separately from the follow-ups; an accepted sample can be converted
to sales. Every step is written to `request_sample_events` (the activity timeline).

Integration rules:
* The customer is the customer bank's row (`customers.id`) -- nothing about a customer is copied here.
* `creator_name` is the permanent text snapshot of the creator (see core/creator_snapshot.py).
* Product / grade are stored as the names chosen from the customer bank's lists (PRODUCED / CONSUMED /
  GRADE pick-lists) so a request still reads correctly if a list entry is later renamed or removed.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.core.creator_snapshot import display_name as _creator_display, register as _register_creator
from app.extensions import db


class SampleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    NEW_REQUEST = "NEW_REQUEST"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ON_HOLD = "ON_HOLD"
    DISPATCHED = "DISPATCHED"
    AWAITING_FEEDBACK = "AWAITING_FEEDBACK"
    COMPLETED = "COMPLETED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"


TERMINAL = (SampleStatus.REJECTED, SampleStatus.COMPLETED, SampleStatus.CONVERTED, SampleStatus.CANCELLED)


class SamplePriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class FeedbackStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ACCEPTED_WITH_CONDITIONS = "ACCEPTED_WITH_CONDITIONS"
    UNDER_EVALUATION = "UNDER_EVALUATION"
    NO_RESPONSE = "NO_RESPONSE"


class RequestSample(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "request_samples"
    __table_args__ = (
        Index("ix_rs_status", "status"),
        Index("ix_rs_customer", "customer_id"),
        Index("ix_rs_rep", "sales_rep_user_id"),
        Index("ix_rs_requested_date", "requested_date"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    sales_rep_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # a request raised because an earlier sample was rejected by the customer / needs a corrected sample
    parent_request_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SampleStatus.DRAFT.value)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default=SamplePriority.NORMAL.value)
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)

    # step 1
    dispatch_ref_number: Mapped[str | None] = mapped_column(String(100), nullable=True)  # شماره حواله نمونه
    # step 3 -- sample requirements
    required_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    # (legacy, no longer collected -- the «کاربرد و اطلاعات فنی» step was removed; columns kept for old rows)
    application: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_process: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_properties: Mapped[str | None] = mapped_column(Text, nullable=True)
    # step 5 -- shipping
    delivery_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # workflow milestones
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # approved / rejected
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # the customer's receipt of the sample (ارسال‌شده -> تحویل شد)
    delivered_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_received_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # final customer feedback (ONE per request; the routine follow-ups are a separate table)
    fb_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fb_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fb_product_evaluation: Mapped[str | None] = mapped_column(Text, nullable=True)
    fb_technical_acceptance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fb_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    fb_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fb_suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    fb_evaluated_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fb_recorded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    fb_recorded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # conversion to sales (link to a CRM sale when one exists)
    converted_sale_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("crm_sales.id", ondelete="SET NULL"), nullable=True
    )
    conversion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("Customer", lazy="joined")
    sales_rep = relationship("User", foreign_keys=[sales_rep_user_id], lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="select")
    items = relationship(
        "RequestSampleItem", cascade="all, delete-orphan", order_by="RequestSampleItem.id", lazy="selectin"
    )
    dispatches = relationship(
        "RequestSampleDispatch", cascade="all, delete-orphan", order_by="RequestSampleDispatch.id", lazy="selectin"
    )
    followups = relationship(
        "RequestSampleFollowUp", cascade="all, delete-orphan",
        order_by="RequestSampleFollowUp.followup_date, RequestSampleFollowUp.id", lazy="selectin",
    )

    @property
    def code(self) -> str:
        """The request's identifier everywhere in the system = the user-entered dispatch reference
        number (شماره حواله). A draft saved before the number is typed falls back to a placeholder."""
        ref = (self.dispatch_ref_number or "").strip()
        return ref if ref else f"RS-{self.id:05d}"

    @property
    def created_by_name(self) -> str | None:
        return _creator_display(self)


class RequestSampleItem(db.Model):
    """One product row of a request (a request can carry several)."""

    __tablename__ = "request_sample_items"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_category: Mapped[str | None] = mapped_column(String(200), nullable=True)  # legacy, no longer collected
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alternative_product: Mapped[str | None] = mapped_column(String(255), nullable=True)  # legacy, no longer collected
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    number_of_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    packaging: Mapped[str | None] = mapped_column(String(200), nullable=True)
    specifications: Mapped[str | None] = mapped_column(Text, nullable=True)


class RequestSampleDispatch(TimestampMixin, db.Model):
    """One shipment. A request may have several (the sample need not leave in one go)."""

    __tablename__ = "request_sample_dispatches"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shipped_quantity: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class RequestSampleFollowUp(TimestampMixin, db.Model):
    """A routine follow-up with the customer (calls, mails, meetings). NOT the final feedback."""

    __tablename__ = "request_sample_followups"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False, index=True
    )
    followup_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)  # PHONE EMAIL MEETING MESSAGE OTHER
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_followup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    responsible_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    responsible = relationship("User", foreign_keys=[responsible_user_id], lazy="joined")


class RequestSampleEvent(db.Model):
    """The activity timeline: who did what, when. Written for every state change and record."""

    __tablename__ = "request_sample_events"
    __table_args__ = (Index("ix_rs_events_request", "request_id", "id"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False
    )
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # text snapshot
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RequestSampleFile(TimestampMixin, db.Model):
    """An attachment. Uploaded first (request_id NULL), then linked to a request; random UUID id."""

    __tablename__ = "request_sample_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="TECHNICAL")  # TECHNICAL DISPATCH FOLLOWUP FEEDBACK OTHER
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


_register_creator(RequestSample)
_register_creator(RequestSampleDispatch)
_register_creator(RequestSampleFollowUp)
