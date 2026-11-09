"""
Department model — DATABASE.md "Organizational structure > departments".

`manager_user_id` is **informational only** — an org-chart label, never
read by the authorization engine. See AUTHORIZATION.md §2 for the
explicit rule against deriving authorization from this field.
"""
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, BigIntUnsigned


class Department(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "departments"
    __table_args__ = (
        Index("ix_departments_organization_id", "organization_id"),
        Index("ix_departments_parent_department_id", "parent_department_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_department_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )
    # Informational org-chart label only — NEVER read by the authorization
    # engine (AUTHORIZATION.md §2). No application code may branch on this
    # field to make an allow/deny decision.
    # use_alter=True: departments.manager_user_id -> users.id and
    # users.department_id -> departments.id form a circular table
    # dependency. use_alter defers this specific FK constraint to a
    # separate ALTER TABLE emitted after both tables exist, which is what
    # lets both db.create_all() (tests) and Alembic's migration resolve
    # table creation order without a CircularDependencyError.
    manager_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_departments_manager_user_id",
        ),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="departments"
    )
    parent: Mapped["Department | None"] = relationship(
        "Department", remote_side="Department.id", back_populates="children"
    )
    children: Mapped[list["Department"]] = relationship(
        "Department", back_populates="parent"
    )
    manager: Mapped["User | None"] = relationship(
        "User", foreign_keys=[manager_user_id]
    )
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="department")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Department id={self.id} name={self.name!r}>"
