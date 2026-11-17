"""
Purchase Reports module (procurement) -- purchase requests recorded end to end by the
procurement & logistics staff, from the request itself to the final delivery.

Tables
    purchase_requests          one row per request: basic info, budget, selection, final result, status
      |- purchase_items          the goods of the request (each with its commodity group)
      |- purchase_inquiries      up to 3 supplier quotations (suppliers come from the `suppliers` bank)
      |    `- purchase_inquiry_items   the unit price each quotation gives for each item
      |- purchase_events         who did what and when: wizard steps + every status change
      `- purchase_files          attachments (budget documents, pro-forma invoices, final documents)

Money is stored as DECIMAL (never float). The commodity group of an item is a reference to the
admin-managed `supplier_categories` main category (parent_id IS NULL) -- no group list lives in code;
the name is also kept on the item so a deleted/renamed group never blanks old reports.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.core.creator_snapshot import display_name as _creator_display, register as _register_creator
from app.extensions import db


class PurchasePriority(str, enum.Enum):
    NORMAL = "NORMAL"          # عادی
    URGENT = "URGENT"          # فوری
    EMERGENCY = "EMERGENCY"    # اضطراری


class PurchaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"                              # پیش‌نویس
    ENTERING = "ENTERING"                        # در حال ثبت اطلاعات
    AWAITING_INQUIRY = "AWAITING_INQUIRY"        # در انتظار استعلام
    INQUIRING = "INQUIRING"                      # در حال استعلام
    AWAITING_SELECTION = "AWAITING_SELECTION"    # در انتظار انتخاب تأمین‌کننده
    PURCHASING = "PURCHASING"                    # در حال انجام خرید
    AWAITING_DELIVERY = "AWAITING_DELIVERY"      # در انتظار تحویل
    COMPLETED = "COMPLETED"                      # تکمیل‌شده
    CANCELLED = "CANCELLED"                      # لغوشده
    NEEDS_REVISION = "NEEDS_REVISION"            # نیازمند اصلاح اطلاعات


# Statuses in which a request is "open / in progress" (KPI 3). A draft is not yet a request in the
# pipeline, a completed or cancelled one is closed.
OPEN_STATUSES = (
    PurchaseStatus.ENTERING, PurchaseStatus.AWAITING_INQUIRY, PurchaseStatus.INQUIRING,
    PurchaseStatus.AWAITING_SELECTION, PurchaseStatus.PURCHASING, PurchaseStatus.AWAITING_DELIVERY,
    PurchaseStatus.NEEDS_REVISION,
)


class DeliveryStatus(str, enum.Enum):
    NOT_DELIVERED = "NOT_DELIVERED"
    PARTIAL = "PARTIAL"
    DELIVERED = "DELIVERED"


class ReferenceSource(str, enum.Enum):
    """Where an item's reference (base) price comes from. Savings are only computed against an
    APPROVED reference price, so the source is always recorded."""
    LAST_PURCHASE = "LAST_PURCHASE"    # قیمت آخرین خرید ثبت‌شده در سامانه
    CONTRACT = "CONTRACT"              # قرارداد یا تعرفه تأییدشده
    PRICE_LIST = "PRICE_LIST"          # لیست قیمت رسمی / پیش‌فاکتور مبنا
    OTHER = "OTHER"


class PurchaseRequest(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "purchase_requests"
    __table_args__ = (
        UniqueConstraint("request_no", name="uq_purchase_requests_request_no"),
        Index("ix_purchase_requests_status", "status"),
        Index("ix_purchase_requests_request_date", "request_date"),
        Index("ix_purchase_requests_required_date", "required_date"),
        Index("ix_purchase_requests_unit", "requester_unit"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_no: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[PurchaseStatus] = mapped_column(
        SAEnum(PurchaseStatus, name="purchase_status", native_enum=False, length=20),
        nullable=False, default=PurchaseStatus.DRAFT, server_default="DRAFT",
    )
    # highest wizard step (1-6) the data of which has been saved; used to resume a draft
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # -- step 1: basic info --
    requester_unit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requester_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    request_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[PurchasePriority] = mapped_column(
        SAEnum(PurchasePriority, name="purchase_priority", native_enum=False, length=10),
        nullable=False, default=PurchasePriority.NORMAL, server_default="NORMAL",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- step 3: budget & estimate (the estimated total is the sum of the items' lines) --
    budget_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    budget_files: Mapped[list | None] = mapped_column(JSON, nullable=True)   # [{id, name, size}]

    # -- step 4: inquiries --
    inquiry_shortfall_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    inquiries_finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # -- step 5: selection --
    selected_inquiry_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_inquiries.id", ondelete="SET NULL", use_alter=True,
                                   name="fk_purchase_requests_selected_inquiry"), nullable=True,
    )
    selection_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)  # LOWEST_PRICE, QUALITY, ...
    selection_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- step 6: result --
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    final_extra_costs: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    final_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)   # computed server-side
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="purchase_delivery_status", native_enum=False, length=15),
        nullable=False, default=DeliveryStatus.NOT_DELIVERED, server_default="NOT_DELIVERED",
    )
    completion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_files: Mapped[list | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # cancel / revision reason

    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # frozen at insert
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    items: Mapped[list["PurchaseItem"]] = relationship(
        "PurchaseItem", back_populates="request", cascade="all, delete-orphan",
        order_by="PurchaseItem.position", passive_deletes=True,
    )
    inquiries: Mapped[list["PurchaseInquiry"]] = relationship(
        "PurchaseInquiry", back_populates="request", cascade="all, delete-orphan",
        order_by="PurchaseInquiry.position", passive_deletes=True,
        foreign_keys="PurchaseInquiry.request_id",
    )
    selected_inquiry: Mapped["PurchaseInquiry | None"] = relationship(
        "PurchaseInquiry", foreign_keys=[selected_inquiry_id], post_update=True,
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    @property
    def creator_display(self) -> str | None:
        return _creator_display(self)


class PurchaseItem(TimestampMixin, db.Model):
    __tablename__ = "purchase_items"
    __table_args__ = (Index("ix_purchase_items_request", "request_id"), Index("ix_purchase_items_category", "category_id"))

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    category_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True
    )
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specs: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)

    estimated_unit_price: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # reference (base) price for the savings formula -- counts only once approved
    reference_unit_price: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    reference_source: Mapped[ReferenceSource | None] = mapped_column(
        SAEnum(ReferenceSource, name="purchase_reference_source", native_enum=False, length=15), nullable=True
    )
    reference_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # when the source is LAST_PURCHASE, the earlier completed item the price was taken from
    reference_item_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_items.id", ondelete="SET NULL"), nullable=True
    )
    reference_approved_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reference_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # final result (steps 5-6)
    final_unit_price: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    purchased_quantity: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)

    request: Mapped[PurchaseRequest] = relationship("PurchaseRequest", back_populates="items")


class PurchaseInquiry(TimestampMixin, db.Model):
    __tablename__ = "purchase_inquiries"
    __table_args__ = (
        UniqueConstraint("request_id", "position", name="uq_purchase_inquiries_request_position"),
        UniqueConstraint("request_id", "supplier_id", name="uq_purchase_inquiries_request_supplier"),
        Index("ix_purchase_inquiries_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..3

    supplier_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)   # snapshot
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra_costs: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    # sum(item quantity x quoted unit price) + extra costs, kept so lists/comparisons need no joins
    total_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped[PurchaseRequest] = relationship(
        "PurchaseRequest", back_populates="inquiries", foreign_keys=[request_id]
    )
    lines: Mapped[list["PurchaseInquiryItem"]] = relationship(
        "PurchaseInquiryItem", back_populates="inquiry", cascade="all, delete-orphan", passive_deletes=True
    )
    file = relationship("PurchaseFile", foreign_keys=[file_id])


class PurchaseInquiryItem(db.Model):
    __tablename__ = "purchase_inquiry_items"
    __table_args__ = (UniqueConstraint("inquiry_id", "item_id", name="uq_purchase_inquiry_items_pair"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_inquiries.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False
    )
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)

    inquiry: Mapped[PurchaseInquiry] = relationship("PurchaseInquiry", back_populates="lines")


class PurchaseEvent(db.Model):
    """Append-only trail shown on the request: a wizard step saved, or a status change."""
    __tablename__ = "purchase_events"
    __table_args__ = (Index("ix_purchase_events_request", "request_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)       # STEP | STATUS | REFERENCE
    step: Mapped[str | None] = mapped_column(String(20), nullable=True)  # basic|items|budget|inquiries|selection|result
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(200), nullable=True)   # snapshot, survives user removal
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PurchaseFile(TimestampMixin, db.Model):
    """Attachment bytes live on disk (config UPLOAD_DIR, random name); only users who may read purchases
    can download them -- see routes.download_file."""
    __tablename__ = "purchase_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


_register_creator(PurchaseRequest)
