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
    SENT_TO_FINANCE = "SENT_TO_FINANCE"          # ارسال به مالی
    AWAITING_DELIVERY = "AWAITING_DELIVERY"      # در حال تحویل و حمل (value kept from the first release)
    COMPLETED = "COMPLETED"                      # پایان‌یافته (value kept from the first release)
    CANCELLED = "CANCELLED"                      # لغوشده
    NEEDS_REVISION = "NEEDS_REVISION"            # نیازمند اصلاح اطلاعات
    # -- statuses of the item-based flow (flow_version = 2), see flow.py --
    UNDER_REVIEW = "UNDER_REVIEW"                # در حال بررسی (first status, set by the system)
    SOURCING = "SOURCING"                        # در حال استعلام و تأمین
    REFERRED_FINANCE = "REFERRED_FINANCE"        # ارجاع استعلام به مالی (set by the system)
    FOLLOW_UP = "FOLLOW_UP"                      # پیگیری پرداخت و حمل (set by the system)
    PARTIAL_DELIVERY = "PARTIAL_DELIVERY"        # تحویل داده‌شده – جزئی (computed from the items)
    RETURNED = "RETURNED"                        # استرداد جهت اصلاح
    VOID = "VOID"                                # ابطال


# Statuses in which a request is "open / in progress" (KPI 3). A draft is not yet a request in the
# pipeline, a completed or cancelled one is closed.
OPEN_STATUSES = (
    PurchaseStatus.ENTERING, PurchaseStatus.AWAITING_INQUIRY, PurchaseStatus.INQUIRING,
    PurchaseStatus.AWAITING_SELECTION, PurchaseStatus.PURCHASING, PurchaseStatus.SENT_TO_FINANCE,
    PurchaseStatus.AWAITING_DELIVERY,
    PurchaseStatus.NEEDS_REVISION,
)


class ReviewStatus(str, enum.Enum):
    """The expert's review of the request (cartable). Separate from the procurement workflow `status`:
    a request may arrive on paper, be recorded, and be judged here independently of how far the purchase got."""
    PENDING_REVIEW = "PENDING_REVIEW"    # در انتظار بررسی
    APPROVED = "APPROVED"                # تأیید شده
    REJECTED = "REJECTED"                # رد شده (stays in the records)
    NEEDS_REVISION = "NEEDS_REVISION"    # نیازمند اصلاح


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


class ItemStatus(str, enum.Enum):
    """Status of ONE goods line of a request (flow_version 2). Every line moves on its own."""
    PENDING = "PENDING"                      # ثبت‌شده، هنوز وارد استعلام نشده
    INQUIRY = "INQUIRY"                      # در حال استعلام و تأمین
    AWAITING_APPROVAL = "AWAITING_APPROVAL"  # منتظر تأیید مدیر
    IN_FINANCE = "IN_FINANCE"                # تأیید شده و ارجاع‌شده به مالی (در انتظار پرداخت)
    PAID = "PAID"                            # پرداخت‌شده
    SHIPPING = "SHIPPING"                    # در حال حمل
    DELIVERED = "DELIVERED"                  # تحویل داده‌شده
    CANCELLED = "CANCELLED"                  # ابطال


class SupplyPlace(str, enum.Enum):
    LOCAL = "LOCAL"          # محلی
    NON_LOCAL = "NON_LOCAL"  # غیرمحلی


class PurchaseSubject(str, enum.Enum):
    ASSET = "ASSET"          # دارایی
    GENERAL = "GENERAL"      # عمومی


class PayMethod(str, enum.Enum):
    CASH = "CASH"            # نقدی
    CHEQUE = "CHEQUE"        # چکی


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

    sent_to_finance_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

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

    # 1 = the original request-level workflow (kept readable), 2 = the item-based flow (flow.py)
    flow_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # SLA clock starts here

    review_status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, name="purchase_review_status", native_enum=False, length=20),
        nullable=False, default=ReviewStatus.PENDING_REVIEW, server_default="PENDING_REVIEW",
    )
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

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
    # the catalog product (purchase_products); name / code are copied so history survives a later rename
    product_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_products.id", ondelete="SET NULL"), nullable=True
    )
    product_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
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

    # -- item-based flow (flow_version 2): every column below belongs to THIS line only --
    current_stock: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)   # موجودی فعلی انبار (manual)
    reorder_point: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)   # نقطه سفارش (optional)
    request_type: Mapped[str | None] = mapped_column(String(150), nullable=True)         # نوع درخواست (admin list)
    purchase_subject: Mapped[PurchaseSubject | None] = mapped_column(
        SAEnum(PurchaseSubject, name="purchase_subject", native_enum=False, length=10), nullable=True)
    priority: Mapped[PurchasePriority | None] = mapped_column(
        SAEnum(PurchasePriority, name="purchase_item_priority", native_enum=False, length=10), nullable=True)
    item_status: Mapped[ItemStatus] = mapped_column(
        SAEnum(ItemStatus, name="purchase_item_status", native_enum=False, length=20),
        nullable=False, default=ItemStatus.PENDING, server_default="PENDING")
    supply_place: Mapped[SupplyPlace | None] = mapped_column(
        SAEnum(SupplyPlace, name="purchase_supply_place", native_enum=False, length=10), nullable=True)
    selected_quote_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)  # plain id: no circular FK
    manager_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)       # finance returned it as paid
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # KPI: delivered on time?
    delivered_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_files.id", ondelete="SET NULL", use_alter=True,
                               name="fk_purchase_items_receipt_file"), nullable=True)
    receipt_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)   # cancel / manager-return reason

    request: Mapped[PurchaseRequest] = relationship("PurchaseRequest", back_populates="items")
    quotes: Mapped[list["PurchaseItemQuote"]] = relationship(
        "PurchaseItemQuote", back_populates="item", cascade="all, delete-orphan", passive_deletes=True,
        order_by="PurchaseItemQuote.position")
    payment: Mapped["PurchaseItemPayment | None"] = relationship(
        "PurchaseItemPayment", back_populates="item", cascade="all, delete-orphan", passive_deletes=True, uselist=False)
    receipt_file = relationship("PurchaseFile", foreign_keys=[receipt_file_id])


class PurchaseItemQuote(TimestampMixin, db.Model):
    """One supplier quotation for ONE item (flow v2). An item may have several, each item is independent."""
    __tablename__ = "purchase_item_quotes"
    __table_args__ = (Index("ix_purchase_item_quotes_item", "item_id"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    supplier_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)            # snapshot
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)          # whole rials
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_method: Mapped[PayMethod | None] = mapped_column(
        SAEnum(PayMethod, name="purchase_pay_method", native_enum=False, length=10), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    item: Mapped[PurchaseItem] = relationship("PurchaseItem", back_populates="quotes")
    file = relationship("PurchaseFile", foreign_keys=[file_id])


class PurchaseItemPayment(TimestampMixin, db.Model):
    """The payment of ONE item, recorded by finance. Written once -- never overwritten."""
    __tablename__ = "purchase_item_payments"
    __table_args__ = (UniqueConstraint("item_id", name="uq_purchase_item_payments_item"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False)
    quote_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    method: Mapped[PayMethod] = mapped_column(
        SAEnum(PayMethod, name="purchase_payment_method", native_enum=False, length=10), nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    # cash
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)           # شناسه پرداخت
    receipt_file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True)
    # cheque
    cheque_file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True)
    cheque_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cheque_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    cheque_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cheque_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cheque_bank: Mapped[str | None] = mapped_column(String(150), nullable=True)
    cheque_payee: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    recorded_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    item: Mapped[PurchaseItem] = relationship("PurchaseItem", back_populates="payment")
    receipt_file = relationship("PurchaseFile", foreign_keys=[receipt_file_id])
    cheque_file = relationship("PurchaseFile", foreign_keys=[cheque_file_id])


class PurchaseOption(TimestampMixin, db.Model):
    """Admin-managed pick lists of the request form: requesting units (kind UNIT) and request types (REQUEST_TYPE)."""
    __tablename__ = "purchase_options"
    __table_args__ = (UniqueConstraint("kind", "label", name="uq_purchase_options_kind_label"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True, server_default="1")


class PurchaseSla(TimestampMixin, db.Model):
    """Allowed supply + delivery time per priority (set by the system admin); the base of the KPIs."""
    __tablename__ = "purchase_sla"
    __table_args__ = (UniqueConstraint("priority", name="uq_purchase_sla_priority"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(5), nullable=False, default="DAYS", server_default="DAYS")  # DAYS | HOURS
    updated_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


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
    # flow v2: the goods line this entry is about (kind ITEM); NULL = the whole request
    item_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(200), nullable=True)   # snapshot, survives user removal
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PurchaseProduct(TimestampMixin, db.Model):
    """The purchase module's OWN product catalog (independent of other modules), managed by an admin.
    `code` is free text typed by the admin (letters, digits and a few separators) -- never generated or numeric."""
    __tablename__ = "purchase_products"
    __table_args__ = (
        UniqueConstraint("name", name="uq_purchase_products_name"),
        UniqueConstraint("code", name="uq_purchase_products_code"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)   # واحد اندازه‌گیری: fills the request line
    category_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True, server_default="1")
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class PurchaseDirect(TimestampMixin, SoftDeleteMixin, db.Model):
    """A DIRECT purchase: recorded as a report line only -- no request, no quotations. It still feeds the
    aggregate reports and the dashboard (spent, groups, suppliers, trend)."""
    __tablename__ = "purchase_direct"
    __table_args__ = (
        UniqueConstraint("doc_no", name="uq_purchase_direct_doc_no"),
        Index("ix_purchase_direct_date", "purchase_date"),
        Index("ix_purchase_direct_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    doc_no: Mapped[str] = mapped_column(String(50), nullable=False)          # typed by the expert
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)         # goods / service name
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True
    )
    category_name: Mapped[str | None] = mapped_column(String(100), nullable=True)   # snapshot
    supplier_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)       # whole rials
    usage_place: Mapped[str] = mapped_column(String(255), nullable=False)       # محل مصرف
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


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
