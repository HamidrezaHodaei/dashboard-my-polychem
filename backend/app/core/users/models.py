"""
User model — DATABASE.md "users (changed: explicit organizational
placement, separate from authorization)".

`organization_id` / `department_id` are the user's **primary organizational
placement** — "where does this employee belong." They grant zero
permissions by themselves; see AUTHORIZATION.md §2. Team-level placement
is many-to-many via `team_members` (a user can belong to more than one
team; department is singular/primary).

No password hashing helpers here — Phase 1 is schema only. Phase 3 (see
IMPLEMENTATION_PLAN.md) adds the authentication service that writes/verifies
`password_hash`.
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Index, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, BigIntUnsigned


class User(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_department_id", "department_id"),
        Index("ix_users_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)

    # Organizational placement ONLY — never an authorization signal.
    # See AUTHORIZATION.md §2 for the explicit separation rule.
    organization_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Phase 1: column exists per DATABASE.md; no hashing/verification logic
    # is implemented until Phase 3 (Authentication).
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Profile photo as a small data URL (the client downsizes it; the server validates type and size).
    # Deferred: only loaded when /api/me asks for it.
    avatar_data: Mapped[str | None] = mapped_column(
        Text().with_variant(mysql.MEDIUMTEXT(), "mysql"), nullable=True, deferred=True
    )

    organization: Mapped["Organization | None"] = relationship(
        "Organization", foreign_keys=[organization_id]
    )
    department: Mapped["Department | None"] = relationship(
        "Department", foreign_keys=[department_id]
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"
