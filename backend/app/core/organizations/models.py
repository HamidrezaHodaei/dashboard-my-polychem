"""
Organization model — DATABASE.md "Organizational structure > organizations".

Organizational membership only ("where does this employee belong") —
never a source of authorization by itself. See AUTHORIZATION.md §2.
"""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, BigIntUnsigned


class Organization(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_organization_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )

    parent: Mapped["Organization | None"] = relationship(
        "Organization", remote_side="Organization.id", back_populates="children"
    )
    children: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="parent"
    )

    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="organization"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Organization id={self.id} name={self.name!r}>"
