"""
Grant / association models — DATABASE.md "RBAC tables" (user_roles,
role_permission_scopes, user_permission_scopes) and "delegations".

None of these classes implement any authorization *decision* — no
possession/scope/ownership checks, no effective-grants union, no
delegation eligibility rules. That logic is Phase 2 (`app/permissions/`)
and Phase 2's delegation service. This module only defines how the grants
are stored.

Effective Grants(user) = active role_permission_scopes (via user_roles)
                          UNION active user_permission_scopes
— see AUTHORIZATION.md §5. Both grant tables share the same shape
(permission_id, scope_type, scope_id, is_active, granted_by_user_id) by
design, so the future engine can treat a role-sourced grant and a
user-sourced grant identically once resolved.
"""
import enum
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Boolean, Index, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import TimestampMixin, _utcnow, BigIntUnsigned


class ScopeType(str, enum.Enum):
    """AUTHORIZATION.md's scope taxonomy: GLOBAL > ORGANIZATION > DEPARTMENT > TEAM > SELF."""

    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    SELF = "SELF"


class PermissionEffect(str, enum.Enum):
    """
    Effect of a `user_permission_scopes` row.

    ALLOW (default) -- an additional grant, exactly the original Phase 1
    behaviour (and what every delegation writes).
    DENY            -- an explicit per-user revocation: removes a matching
    permission (at a covered scope) that the user would otherwise get
    from their roles or from ALLOW rows. This is what makes an
    unchecked cell in the per-user permission matrix actually restrict
    a user whose role would have granted it. See
    app/permissions/service.py for the precedence rules.
    """

    ALLOW = "ALLOW"
    DENY = "DENY"


class UserRole(db.Model):
    """
    DATABASE.md "user_roles": which role(s) a user holds, optionally
    contextualized to a specific organization (e.g. the same person
    holding the same role in both دفتر مرکزی and کارخانه as two distinct
    assignments). Carries no permission/scope data itself — that comes
    from the role's active `role_permission_scopes` rows.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship("Role")
    organization: Mapped["Organization | None"] = relationship("Organization")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"


class RolePermissionScope(TimestampMixin, db.Model):
    """
    DATABASE.md "role_permission_scopes" — Role-level base grants: the
    *default* capabilities that come with holding a role.
    """

    __tablename__ = "role_permission_scopes"
    __table_args__ = (
        Index("ix_role_permission_scopes_role_permission", "role_id", "permission_id"),
        Index("ix_role_permission_scopes_scope", "scope_type", "scope_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[ScopeType] = mapped_column(
        SAEnum(ScopeType, name="role_permission_scopes_scope_type"), nullable=False
    )
    # NULL when scope_type is GLOBAL/SELF. Polymorphic — points at an
    # organizations.id, departments.id, or teams.id row depending on
    # scope_type, so it intentionally cannot be a normal single-target FK.
    # Validity of scope_id against scope_type is enforced at the
    # application/service layer (Phase 2), not the database layer.
    scope_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    role: Mapped["Role"] = relationship("Role")
    permission: Mapped["Permission"] = relationship("Permission")
    granted_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[granted_by_user_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RolePermissionScope role_id={self.role_id} "
            f"permission_id={self.permission_id} scope={self.scope_type}:{self.scope_id}>"
        )


class UserPermissionScope(TimestampMixin, db.Model):
    """
    DATABASE.md "user_permission_scopes" — User-level scoped grants:
    additional permission+scope granted directly to one specific user,
    independent of role. This is what a targeted delegation writes to
    (AUTHORIZATION.md §4/§6), so it never widens every holder of that
    user's role.
    """

    __tablename__ = "user_permission_scopes"
    __table_args__ = (
        Index("ix_user_permission_scopes_user_permission", "user_id", "permission_id"),
        Index("ix_user_permission_scopes_scope", "scope_type", "scope_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[ScopeType] = mapped_column(
        SAEnum(ScopeType, name="user_permission_scopes_scope_type"), nullable=False
    )
    # Same polymorphic-scope caveat as RolePermissionScope.scope_id above.
    scope_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    # ALLOW (default) or DENY -- see PermissionEffect above.
    effect: Mapped[PermissionEffect] = mapped_column(
        SAEnum(PermissionEffect, name="user_permission_scopes_effect"),
        nullable=False,
        default=PermissionEffect.ALLOW,
        server_default=PermissionEffect.ALLOW.value,
    )
    # Set FALSE on revocation — the row is retained for history rather than
    # deleted, per DATABASE.md. Delegation revocation keeps this in sync
    # with the linked `delegations.revoked_at` in the same transaction
    # (Phase 2/4 service logic — not implemented yet).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    permission: Mapped["Permission"] = relationship("Permission")
    granted_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[granted_by_user_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UserPermissionScope user_id={self.user_id} "
            f"permission_id={self.permission_id} scope={self.scope_type}:{self.scope_id}>"
        )


class Delegation(db.Model):
    """
    DATABASE.md "delegations" — user-targeted delegation lifecycle record.
    Answers: who delegated, to which user, resulting in which grant row,
    when, still active, who revoked, when.

    No eligibility checks (possession/delegable/containment/org-relationship/
    grant-authority) or self-delegation guard live here — those are Phase 2
    service-layer rules (AUTHORIZATION.md §6/§9). This is storage only.
    """

    __tablename__ = "delegations"
    __table_args__ = (
        Index("ix_delegations_delegator_user_id", "delegator_user_id"),
        Index("ix_delegations_delegatee_user_id", "delegatee_user_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    delegator_user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    delegatee_user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    resulting_user_permission_scope_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("user_permission_scopes.id", ondelete="RESTRICT"), nullable=False
    )
    delegated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    delegator: Mapped["User"] = relationship(
        "User", foreign_keys=[delegator_user_id]
    )
    delegatee: Mapped["User"] = relationship(
        "User", foreign_keys=[delegatee_user_id]
    )
    revoked_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[revoked_by_user_id]
    )
    resulting_user_permission_scope: Mapped["UserPermissionScope"] = relationship(
        "UserPermissionScope"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Delegation delegator={self.delegator_user_id} "
            f"delegatee={self.delegatee_user_id}>"
        )
