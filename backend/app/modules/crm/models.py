"""
CRM sales models.

Integration rules (the point of this module):
* There is NO customer table here. `crm_sales.customer_id` is a foreign key to the customer bank
  (`customers.id`, app/modules/customers). Province / industry of a sale are read from the
  customer's own file, never copied.
* Dates: `sale_date` is a real DATE (Gregorian, what the DB can sort/range-filter). The Jalali
  year/month are stored beside it (`jalali_year`, `jalali_month`, kept in sync by services.py)
  so "by Persian month" grouping and year/month filters are plain indexed column comparisons
  on any database. The API speaks Jalali strings (`1405/08/15`) to the UI.
* Products are NOT stored here either. `crm_sales.product_id` is a foreign key to the customer
  bank's product pick-list (`customer_option_items`, kind=PRODUCT -- the same list the customer
  wizard uses for produced / consumed products), so a product is defined exactly once.
* Quantity is stored in KILOGRAMS (`quantity_kg`) -- the legacy CRM column was named `tons` but
  has always held kg (its UI and Excel import are in kg).
"""
import enum
from datetime import date

from sqlalchemy import (
    Date, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import ActiveFlagMixin, BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.extensions import db


class SaleType(str, enum.Enum):
    OFFICIAL = "OFFICIAL"  # رسمی
    UNOFFICIAL = "UNOFFICIAL"  # غیررسمی


class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"  # فاکتور فروش
    RETURN = "RETURN"  # برگشت از فروش (counted negatively in every total)


class SaleStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"  # در حال پردازش
    COMPLETED = "COMPLETED"  # تکمیل شده


class CrmPaymentMethod(TimestampMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "crm_payment_methods"
    __table_args__ = (UniqueConstraint("name", name="uq_crm_payment_methods_name"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class CrmSale(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "crm_sales"
    __table_args__ = (
        Index("ix_crm_sales_sale_date", "sale_date"),
        Index("ix_crm_sales_customer_date", "customer_id", "sale_date"),
        Index("ix_crm_sales_jalali", "jalali_year", "jalali_month"),
        Index("ix_crm_sales_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)

    # The customer bank's primary key -- the only link between CRM and a customer.
    customer_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("customer_option_items.id", ondelete="RESTRICT"), nullable=False
    )
    payment_method_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("crm_payment_methods.id", ondelete="SET NULL"), nullable=True
    )

    quantity_kg: Mapped[float] = mapped_column(Numeric(16, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)  # rial per kg
    amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)  # rial, always positive

    sale_type: Mapped[SaleType] = mapped_column(
        SAEnum(SaleType, name="crm_sale_type", native_enum=False, length=12),
        nullable=False, default=SaleType.OFFICIAL, server_default="OFFICIAL",
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="crm_document_type", native_enum=False, length=10),
        nullable=False, default=DocumentType.INVOICE, server_default="INVOICE",
    )
    status: Mapped[SaleStatus] = mapped_column(
        SAEnum(SaleStatus, name="crm_sale_status", native_enum=False, length=12),
        nullable=False, default=SaleStatus.PROCESSING, server_default="PROCESSING",
    )

    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    jalali_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    jalali_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    customer = relationship("Customer", lazy="joined")
    # The customer bank's product pick-list entry (CustomerOptionItem, kind=PRODUCT).
    product = relationship("CustomerOptionItem", lazy="joined")
    payment_method = relationship("CrmPaymentMethod", lazy="joined")

    @property
    def is_return(self) -> bool:
        return self.document_type == DocumentType.RETURN

    @property
    def sign(self) -> int:
        return -1 if self.is_return else 1
