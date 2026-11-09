"""
Supplier model -- Procurement module.

Mirrors the public supplier-registration page's data shape one-to-one so
nothing gets lost between the public form and the admin panel: identity
fields, contact fields, business/supply fields, plus three JSON columns
(phones / products / catalog_files) for the form's repeatable rows.

JSON columns (not child tables) for phones/products/catalog_files:
these are display/record data entered once at registration time, never
queried or joined on individually by any feature requested so far (no
"find all suppliers who sell X product" filter, no per-phone permission
check) -- a normalized schema would add four extra tables and migrations
for zero behavioral benefit right now. `category` IS a plain indexed
column (not buried in JSON) because search/filter-by-category is an
explicit requirement.

Catalog/datasheet files: the bytes live on local disk (config UPLOAD_DIR)
and each upload gets a `supplier_files` row. `Supplier.catalog_files` and
`products[].datasheet` hold small file references ({id, name, size}) that
point at those rows. Older records that stored a bare filename string are
still read as-is (they just have nothing to download).
"""
import enum

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import ActiveFlagMixin, BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.extensions import db


class SupplierType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    LEGAL = "LEGAL"


class SupplierStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SEMI_ACTIVE = "SEMI_ACTIVE"
    INACTIVE = "INACTIVE"


class SupplierQuality(str, enum.Enum):
    EXCELLENT = "EXCELLENT"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class Supplier(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("ix_suppliers_category", "category"),
        Index("ix_suppliers_category_subcategory", "category", "subcategory"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)

    supplier_type: Mapped[SupplierType] = mapped_column(
        SAEnum(SupplierType, name="supplier_type", native_enum=False, length=10), nullable=False
    )
    status: Mapped[SupplierStatus] = mapped_column(
        SAEnum(SupplierStatus, name="supplier_status", native_enum=False, length=12),
        nullable=False, default=SupplierStatus.SEMI_ACTIVE, server_default="SEMI_ACTIVE",
    )
    quality: Mapped[SupplierQuality | None] = mapped_column(
        SAEnum(SupplierQuality, name="supplier_quality", native_enum=False, length=10), nullable=True
    )

    # -- identity (individual) --
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # نام برند یا مغازه -- optional, individual suppliers only (a legal supplier's name IS its company)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # -- identity (legal) --
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_national_id: Mapped[str | None] = mapped_column(String(11), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    established_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # -- contact --
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # -- business / supply --
    # `category` == the public form's "زمینه فعالیت" (activity) field --
    # indexed separately from the rest so list filtering stays a plain
    # WHERE instead of a JSON/LIKE scan.
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Sub-category of `category` (stored by name, same reasoning as `category`).
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)  # comma-joined, like the form
    capacity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # -- repeatable rows from the public form, kept verbatim --
    # `contacts` = people to reach: {first_name, last_name, position, email,
    # mobile, landline} -- one person may have one mobile AND one landline.
    # `phones` stays as a flat {type, number} list *derived* from contacts
    # (kept for the public form and older rows).
    contacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    phones: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    products: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    catalog_files: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # حساب‌های بانکی: any number of optional rows {holder_name, bank_name, card_number,
    # account_number, sheba}; every field is optional, fully blank rows are never stored.
    bank_accounts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # True for rows the public form created; False for rows an admin/staff
    # member added directly in the panel (no public counterpart exists).
    # ── request review workflow (core/request_workflow.py) ─────────────
    review_status: Mapped[str] = mapped_column(String(12), nullable=False, default="PENDING", server_default="PENDING")
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)   # the manager's reason / what to fix
    decided_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_request_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # creator asks for a change
    change_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # "ثبت نهایی": until the creator finalises, a PENDING request is still theirs to edit.
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_public_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Loaded together with the supplier so the list view can show "added by"
    # without one extra query per row.
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Supplier id={self.id} display_name={self.display_name!r}>"

    @property
    def created_by_name(self) -> str | None:
        """Staff member who added this supplier; None for public-form rows."""
        return self.created_by.full_name if self.created_by is not None else None

    @property
    def display_name(self) -> str:
        if self.supplier_type == SupplierType.LEGAL:
            return self.company_name or f"Supplier #{self.id}"
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or f"Supplier #{self.id}"


class SupplierCategory(TimestampMixin, ActiveFlagMixin, db.Model):
    """Admin-managed list behind the public form's "زمینه فعالیت" select and
    the panel's category filter/select.

    Two levels only: a main category (`parent_id IS NULL`) and sub-categories
    that point at a main category. `Supplier.category` / `Supplier.subcategory`
    keep storing the plain *names* (not FKs) so renaming/removing an entry
    never breaks or hides existing supplier rows -- see
    services.update_category(). Names are unique per parent (the same
    sub-category name, e.g. "سایر", may exist under different main categories).
    """

    __tablename__ = "supplier_categories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_supplier_categories_parent_name"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("supplier_categories.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SupplierCategory id={self.id} name={self.name!r} parent={self.parent_id}>"


class SupplierFile(TimestampMixin, db.Model):
    """One uploaded catalog / datasheet file. The id is a random UUID so file
    URLs can't be guessed; `stored_name` is the on-disk name (never the
    user-supplied one, which is kept only for display and download)."""

    __tablename__ = "supplier_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # NULL = uploaded through the public registration form.
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SupplierFile id={self.id} name={self.original_name!r}>"