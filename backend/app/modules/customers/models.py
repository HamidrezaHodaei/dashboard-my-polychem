"""
Customer model -- CRM module (the 6-step customer file / "پرونده مشتری").

Step -> columns:
  1  identity & file      customer_type, names/ids, contacts, addresses, source, activity_start_date
  2  activity profile     industries (one or more category/subcategory pairs; the first is mirrored
                          into category/subcategory for indexing), activity_types, produced_products,
                          production_lines_count, production_capacity, factory province/city/location
  3  product needs        consumed_products, current_suppliers
  4  status & cooperation commercial_status, operational_status, contact_log, purchase dates,
                          assigned_to, inactive_reason
  5  commercial terms     payment_type (+ credit_months / credit_other), purchase_method, delivery,
                          credit limit, credit_rating
  6  follow-up & sign-off notes, last negotiation, next action/follow-up, completed_by, finalized

Design notes (same reasoning as suppliers/models.py):
* Repeatable rows (contacts, produced/consumed products, current suppliers,
  contact log) are JSON columns -- they are entered/edited as a whole with the
  customer and never joined on. Everything the panel FILTERS or SORTS by is a
  plain indexed column (category, status, province/city, assignee, follow-up).
* `category` / `subcategory` store the category *names* (not FKs), exactly like
  Supplier, so renaming/removing an entry never breaks existing customers.
* Two separate statuses on purpose: `commercial_status` (where the deal is in
  the sales pipeline) and `operational_status` (is the customer an active
  account at all) -- the spec asks to keep them apart.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.creator_snapshot import display_name as _creator_display, register as _register_creator
from app.core.base import ActiveFlagMixin, BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.extensions import db


class CustomerType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"  # حقیقی
    LEGAL = "LEGAL"  # حقوقی


class CommercialStatus(str, enum.Enum):
    """وضعیت مشتری و تجاری -- the sales pipeline."""

    NO_ACTION = "NO_ACTION"  # بدون اقدام
    MARKETING_NEGOTIATION = "MARKETING_NEGOTIATION"  # در حال مذاکره و بازاریابی
    SAMPLE_SENT = "SAMPLE_SENT"  # ارسال نمونه
    AWAITING_SAMPLE_APPROVAL = "AWAITING_SAMPLE_APPROVAL"  # منتظر تایید نمونه
    SALES_NEGOTIATION = "SALES_NEGOTIATION"  # در حال مذاکره فروش
    ACQUIRED = "ACQUIRED"  # مشتری جذب شده
    REPEAT_ACTIVE = "REPEAT_ACTIVE"  # مشتری تکرار شونده - فعال
    INACTIVE_LOST = "INACTIVE_LOST"  # غیرفعال - از دست رفته
    POTENTIAL = "POTENTIAL"  # بالقوه


class OperationalStatus(str, enum.Enum):
    """وضعیت عملیاتی -- independent of the pipeline stage."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PurchaseMethod(str, enum.Enum):
    OFFICIAL = "OFFICIAL"  # رسمی
    UNOFFICIAL = "UNOFFICIAL"  # غیر رسمی
    BOTH = "BOTH"  # هر دو


class AcquaintanceSource(str, enum.Enum):
    """منبع آشنایی با مشتری. `OTHER` comes with free text (`acquaintance_source_other`)."""

    WEBSITE = "WEBSITE"  # وب‌سایت شرکت
    GOOGLE_SEARCH = "GOOGLE_SEARCH"  # جست‌وجوی گوگل
    SOCIAL_MEDIA = "SOCIAL_MEDIA"  # شبکه‌های اجتماعی
    EXHIBITION = "EXHIBITION"  # نمایشگاه و همایش
    CUSTOMER_REFERRAL = "CUSTOMER_REFERRAL"  # معرفی مشتریان دیگر
    PARTNER_REFERRAL = "PARTNER_REFERRAL"  # معرفی همکاران و ارتباطات تجاری
    INBOUND_CALL = "INBOUND_CALL"  # تماس ورودی مشتری
    OUTBOUND_CALL = "OUTBOUND_CALL"  # تماس خروجی شرکت
    FIELD_MARKETING = "FIELD_MARKETING"  # بازاریابی حضوری
    TELEMARKETING = "TELEMARKETING"  # بازاریابی تلفنی
    EMAIL_CAMPAIGN = "EMAIL_CAMPAIGN"  # ایمیل تبلیغاتی
    MESSENGERS = "MESSENGERS"  # پیام‌رسان‌ها
    COMPANY_DATABASE = "COMPANY_DATABASE"  # بانک اطلاعاتی شرکت
    PREVIOUS_CONNECTIONS = "PREVIOUS_CONNECTIONS"  # ارتباطات قبلی
    OTHER = "OTHER"  # سایر


class PaymentType(str, enum.Enum):
    CASH = "CASH"  # نقدی
    CREDIT = "CREDIT"  # اعتباری
    CASH_CREDIT = "CASH_CREDIT"  # نقدی - اعتباری


class CreditRating(str, enum.Enum):
    """وضعیت اعتباری مشتری (payment track record)."""

    EXCELLENT = "EXCELLENT"  # عالی
    GOOD = "GOOD"  # خوب
    AVERAGE = "AVERAGE"  # متوسط
    WEAK = "WEAK"  # ضعیف
    BAD_DEBTOR = "BAD_DEBTOR"  # بدحساب
    NO_HISTORY = "NO_HISTORY"  # فاقد سابقه اعتباری
    NEEDS_REVIEW = "NEEDS_REVIEW"  # نیازمند بررسی


class QuantityUnit(str, enum.Enum):
    """Unit of every produced / consumed amount. Amounts are whole numbers; the default is TON."""

    TON = "TON"  # تن
    KG = "KG"  # کیلوگرم


class OptionKind(str, enum.Enum):
    """Admin-managed pick-lists of the customer wizard (same idea as CustomerCategory)."""

    PRODUCT = "PRODUCT"  # legacy shared product list (kept; its entries were copied into PRODUCED and CONSUMED)
    GRADE = "GRADE"  # نام گرید
    PRODUCED = "PRODUCED"  # محصولات تولیدی -- its own list, managed by the admin
    CONSUMED = "CONSUMED"  # محصولات مصرفی -- its own list, managed by the admin


class ActivityType(str, enum.Enum):
    PRODUCER = "PRODUCER"  # تولید کننده
    DISTRIBUTOR = "DISTRIBUTOR"  # توزیع کننده
    EXPORTER = "EXPORTER"  # صادر کننده


class Customer(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_category_subcategory", "category", "subcategory"),
        Index("ix_customers_commercial_status", "commercial_status"),
        Index("ix_customers_province_city", "factory_province", "factory_city"),
        Index("ix_customers_assigned_to", "assigned_to_user_id"),
        Index("ix_customers_next_follow_up", "next_follow_up_date"),
        Index("ix_customers_credit_rating", "credit_rating"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)

    # ── step 1: identity & file ───────────────────────────────────────
    customer_type: Mapped[CustomerType] = mapped_column(
        SAEnum(CustomerType, name="customer_type", native_enum=False, length=10), nullable=False
    )
    # individual
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # نام شرکت یا برند -- optional, individual customers only (a legal customer's name IS its company)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # legal
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_national_id: Mapped[str | None] = mapped_column(String(11), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # تلفن شرکت (legal customers) -- the company's own number, separate from the contact persons' numbers
    company_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    economic_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activity_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # تاریخ شروع فعالیت (UI: شمسی)

    # {first_name, last_name, position, email, mobile, landline, birth_date?}
    contacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    head_office_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_office_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    factory_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    factory_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    acquaintance_source: Mapped[AcquaintanceSource | None] = mapped_column(
        SAEnum(AcquaintanceSource, name="customer_acquaintance_source", native_enum=False, length=30), nullable=True
    )  # منبع آشنایی
    acquaintance_source_other: Mapped[str | None] = mapped_column(String(255), nullable=True)  # when OTHER

    # ── step 2: activity profile ──────────────────────────────────────
    # [{category, subcategory?}] -- a customer can work in several industries (صنعت چندگانه).
    industries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # The FIRST industry, mirrored from `industries` (kept in sync by services.py): the indexed
    # columns the list/table and older clients read.
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # صنعت فعالیت (main)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)  # (sub)
    # comma-joined ActivityType values ("PRODUCER,EXPORTER"); exposed as a list
    # through `activity_types`. No value is a substring of another, so a LIKE
    # filter on one value is exact.
    activity_types_csv: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # {name, amount?: int, unit: TON|KG}  -- what the customer manufactures, always PER YEAR
    produced_products: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    production_lines_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # نام خطوط تولید -- one name per line (list of str); at most `production_lines_count` entries.
    production_line_names: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # how many units of each named line (parallel to production_line_names); the total count is their sum
    production_line_counts: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # ظرفیت تولید کارخانه: tons per year = the sum of produced_products amounts (kg converted).
    # Derived by services.py whenever produced_products is saved; never set by clients.
    production_capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    factory_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    factory_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    factory_location: Mapped[str | None] = mapped_column(String(500), nullable=True)  # free text / map link
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── step 3: product needs ─────────────────────────────────────────
    # {name, grade_specs?, monthly_consumption: int, annual_consumption: int, unit: TON|KG}
    consumed_products: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # {name, supplier_id?, grades: [{product, grade?}]}  -- who the customer buys from today and
    # which of its consumed products (grades) it takes from each supplier
    current_suppliers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ── step 4: status & cooperation ──────────────────────────────────
    commercial_status: Mapped[CommercialStatus] = mapped_column(
        SAEnum(CommercialStatus, name="customer_commercial_status", native_enum=False, length=30),
        nullable=False, default=CommercialStatus.NO_ACTION, server_default="NO_ACTION",
    )
    operational_status: Mapped[OperationalStatus] = mapped_column(
        SAEnum(OperationalStatus, name="customer_operational_status", native_enum=False, length=10),
        nullable=False, default=OperationalStatus.ACTIVE, server_default="ACTIVE",
    )
    # [{date: ISO, note?}] -- every contact attempt; first_contact_date is derived (earliest).
    contact_log: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    first_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # مسئول پیگیری
    inactive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── step 5: purchase info & commercial terms ──────────────────────
    payment_type: Mapped[PaymentType | None] = mapped_column(
        SAEnum(PaymentType, name="customer_payment_type", native_enum=False, length=12), nullable=True
    )  # شرایط پرداخت
    credit_months: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..12 (credit / cash+credit)
    credit_other: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "سایر" duration, free text
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)  # extra free-text note
    purchase_method: Mapped[PurchaseMethod | None] = mapped_column(
        SAEnum(PurchaseMethod, name="customer_purchase_method", native_enum=False, length=12), nullable=True
    )
    delivery_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unloading_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_credit_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # سقف اعتبار مصوب
    credit_rating: Mapped[CreditRating | None] = mapped_column(
        SAEnum(CreditRating, name="customer_credit_rating", native_enum=False, length=20), nullable=True
    )  # وضعیت اعتباری مشتری

    # ── step 6: follow-up & final sign-off ────────────────────────────
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_negotiation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_negotiation_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # تاریخ ثبت
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finalized_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── request review workflow (core/request_workflow.py) ─────────────
    review_status: Mapped[str] = mapped_column(String(12), nullable=False, default="PENDING", server_default="PENDING")
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)   # the manager's reason / what to fix
    decided_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_request_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # creator asks for a change
    change_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # تکمیل‌کننده -- the staff member who filled the file in.
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # The creator's name as TEXT, written once when the record is created (never a live join): it stays
    # correct when the account is renamed, re-assigned, moved or removed. See core/creator_snapshot.py.
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer id={self.id} display_name={self.display_name!r}>"

    @property
    def display_name(self) -> str:
        if self.customer_type == CustomerType.LEGAL:
            return self.company_name or f"Customer #{self.id}"
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or f"Customer #{self.id}"

    @property
    def activity_types(self) -> list[str]:
        return [x for x in (self.activity_types_csv or "").split(",") if x]

    @property
    def created_by_name(self) -> str | None:
        return _creator_display(self)

    @property
    def assigned_to_name(self) -> str | None:
        return self.assigned_to.full_name if self.assigned_to is not None else None


class CustomerCategory(TimestampMixin, ActiveFlagMixin, db.Model):
    """Admin-managed "صنعت فعالیت" list: main categories (`parent_id IS NULL`) and
    one level of sub-categories. Same two-level design as SupplierCategory but a
    separate table, so customer industries and supplier fields of activity are
    managed independently."""

    __tablename__ = "customer_categories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_customer_categories_parent_name"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("customer_categories.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CustomerCategory id={self.id} name={self.name!r} parent={self.parent_id}>"


class CustomerOptionItem(TimestampMixin, ActiveFlagMixin, db.Model):
    """Admin-managed pick-list entry for the customer wizard: a product name (PRODUCT) or a
    grade name (GRADE). Customers store the *name* (not an FK), exactly like industries, so
    renaming/removing an entry never breaks an existing customer."""

    __tablename__ = "customer_option_items"
    __table_args__ = (
        UniqueConstraint("kind", "name", name="uq_customer_option_items_kind_name"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    kind: Mapped[OptionKind] = mapped_column(
        SAEnum(OptionKind, name="customer_option_kind", native_enum=False, length=10), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CustomerOptionItem id={self.id} kind={self.kind} name={self.name!r}>"


_register_creator(Customer)
