"""
Logistics module models -- transport-company / driver registration.

Storage layout (the wizard's "stored independently per applicant type" rule):

    logistics_applicants          one row per registrant; type, status, review trail
      |- logistics_company_profiles   1:1, only for applicant_type = COMPANY
      |- logistics_driver_profiles    1:1, only for applicant_type = DRIVER (holds the vehicle)
      `- logistics_service_areas      1:1, shared *shape* for both types, but every
                                      applicant owns its own row

A company has no vehicle columns anywhere -- vehicle data physically lives
only in `logistics_driver_profiles`, so it cannot be stored for a company.

Provinces/cities are stored by name (same convention as the suppliers and
customers modules). Repeatable / structured parts of the service area
(coverage, countries, permits) are JSON: they are written once at
registration and filtered only through the denormalised columns on
`logistics_applicants` / service area (`area_type`).
"""
import enum
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.creator_snapshot import display_name as _creator_display, register as _register_creator
from app.core.base import ActiveFlagMixin, BigIntUnsigned, SoftDeleteMixin, TimestampMixin
from app.extensions import db


class ApplicantType(str, enum.Enum):
    COMPANY = "COMPANY"
    DRIVER = "DRIVER"


class ApplicantStatus(str, enum.Enum):
    PENDING = "PENDING"        # submitted, waiting for review
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    NEEDS_EDIT = "NEEDS_EDIT"  # a manager sent it back to its creator for edits / missing information


class LegalType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"  # حقیقی
    LEGAL = "LEGAL"            # حقوقی


class AreaType(str, enum.Enum):
    CITY = "CITY"
    PROVINCIAL = "PROVINCIAL"
    INTERPROVINCIAL = "INTERPROVINCIAL"
    INTERNATIONAL = "INTERNATIONAL"


class LogisticsApplicant(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "logistics_applicants"
    __table_args__ = (
        Index("ix_logistics_applicants_type_status", "applicant_type", "status"),
        Index("ix_logistics_applicants_type_mobile", "applicant_type", "mobile"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    applicant_type: Mapped[ApplicantType] = mapped_column(
        SAEnum(ApplicantType, name="logistics_applicant_type", native_enum=False, length=10), nullable=False
    )
    status: Mapped[ApplicantStatus] = mapped_column(
        SAEnum(ApplicantStatus, name="logistics_applicant_status", native_enum=False, length=10),
        nullable=False, default=ApplicantStatus.PENDING, server_default="PENDING",
    )

    # Denormalised from the profile so list/search/duplicate checks stay plain column lookups.
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(11), nullable=False)

    is_public_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # The creator's name as TEXT, written once when the record is created (never a live join): it stays
    # correct when the account is renamed, re-assigned, moved or removed. See core/creator_snapshot.py.
    creator_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # "ثبت نهایی": until the creator finalises, a PENDING record is still theirs to edit.
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    # A finalised record is read-only for its creator; they can ask the manager for a change instead.
    change_request_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    change_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    company = relationship(
        "LogisticsCompanyProfile", uselist=False, lazy="joined", cascade="all, delete-orphan", back_populates="applicant"
    )
    driver = relationship(
        "LogisticsDriverProfile", uselist=False, lazy="joined", cascade="all, delete-orphan", back_populates="applicant"
    )
    service_area = relationship(
        "LogisticsServiceArea", uselist=False, lazy="joined", cascade="all, delete-orphan", back_populates="applicant"
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")

    @property
    def created_by_name(self) -> str | None:
        return _creator_display(self)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LogisticsApplicant id={self.id} type={self.applicant_type} name={self.display_name!r}>"


class LogisticsCompanyProfile(TimestampMixin, db.Model):
    """Step 2 + 3 of the company path. NO vehicle data here by design."""

    __tablename__ = "logistics_company_profiles"
    __table_args__ = (Index("ix_logistics_company_province_city", "province", "city"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("logistics_applicants.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    entity_type: Mapped[LegalType] = mapped_column(
        SAEnum(LegalType, name="logistics_legal_type", native_enum=False, length=10), nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)   # LEGAL only
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)     # INDIVIDUAL only
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)      # INDIVIDUAL only
    national_id: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)  # شناسه ملی, LEGAL only, optional
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    office_address: Mapped[str] = mapped_column(Text, nullable=False)

    rep_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rep_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rep_position: Mapped[str] = mapped_column(String(30), nullable=False)          # code from REPRESENTATIVE_POSITIONS
    rep_position_other: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rep_mobile: Mapped[str] = mapped_column(String(11), nullable=False)
    rep_landline: Mapped[str | None] = mapped_column(String(11), nullable=True)

    applicant = relationship("LogisticsApplicant", back_populates="company")


class LogisticsDriverProfile(TimestampMixin, db.Model):
    """Steps 2-4 of the driver path, including the vehicle / body."""

    __tablename__ = "logistics_driver_profiles"
    __table_args__ = (Index("ix_logistics_driver_vehicle", "vehicle_type", "body_type"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("logistics_applicants.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    mobile: Mapped[str] = mapped_column(String(11), nullable=False)
    alt_phone: Mapped[str | None] = mapped_column(String(11), nullable=True)

    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_type_other: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body_type: Mapped[str] = mapped_column(String(20), nullable=False)
    body_type_other: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity_tons: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    cargo_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cargo_type_other: Mapped[str | None] = mapped_column(String(150), nullable=True)

    applicant = relationship("LogisticsApplicant", back_populates="driver")


class LogisticsServiceArea(TimestampMixin, db.Model):
    """محدوده فعالیت -- same shape for both types, one independent row per applicant."""

    __tablename__ = "logistics_service_areas"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("logistics_applicants.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    area_type: Mapped[AreaType] = mapped_column(
        SAEnum(AreaType, name="logistics_area_type", native_enum=False, length=20), nullable=False, index=True
    )
    # [{"province": "تهران", "all_cities": false, "cities": ["تهران", "شهریار"]}, ...]
    coverage: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    origin_countries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)       # ISO codes
    destination_countries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # ISO codes
    # [{"type": "TIR_CARNET", "number": "...", "expires_at": "1405/01/01", "file": {id,name,size}}]
    permits: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    applicant = relationship("LogisticsApplicant", back_populates="service_area")


class LogisticsFile(TimestampMixin, db.Model):
    """Uploaded permit scan. Random UUID id; on-disk name is never the user's."""

    __tablename__ = "logistics_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


_register_creator(LogisticsApplicant)
