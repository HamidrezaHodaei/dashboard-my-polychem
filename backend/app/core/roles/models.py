"""
Role model — DATABASE.md "RBAC tables > roles".

A role's *default* capabilities are defined by its active
`role_permission_scopes` rows (app/core/authorization/models.py) — nothing
about capabilities is stored on the Role row itself. Roles are kept
strictly separate from departments (AUTHORIZATION.md's revision notes):
holding a role is never inferred from department membership.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.core.base import TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, BigIntUnsigned


class Role(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    # Machine-readable identifier, e.g. "sales_manager". Distinct from
    # display_name, which carries the Persian label shown in the UI.
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # System roles are seeded/framework-defined (see scripts/seed_roles_permissions.py)
    # and are not deletable through ordinary admin CRUD in later phases.
    is_system_role: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role id={self.id} name={self.name!r}>"
