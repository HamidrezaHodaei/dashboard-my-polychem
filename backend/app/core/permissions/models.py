"""
Permission model — DATABASE.md "RBAC tables > permissions".

`key` follows the `[module].[resource].[action]` format (e.g.
`tasks.task.assign`). `is_delegable` defaults to FALSE — per
AUTHORIZATION.md §9 / DATABASE.md's privilege-escalation notes, financial,
system, security, and role/permission-management permissions must default
non-delegable and stay that way regardless of who holds them.

The canonical permission *set* (which keys exist, what they mean) is a
Phase 2 deliverable (`app/permissions/registry.py`, per
IMPLEMENTATION_PLAN.md Phase 2). This model only defines the storage shape.
"""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.core.base import TimestampMixin, BigIntUnsigned


class Permission(TimestampMixin, db.Model):
    __tablename__ = "permissions"
    # No deleted_at — DATABASE.md does not list soft-delete for permissions;
    # the canonical set is managed via the Phase 2 registry/migrations, not
    # via ad hoc soft deletion.

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    is_delegable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission id={self.id} key={self.key!r}>"
