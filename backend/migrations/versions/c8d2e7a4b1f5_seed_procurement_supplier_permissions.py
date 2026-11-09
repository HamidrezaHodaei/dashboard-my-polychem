"""seed procurement.supplier.* permissions + admin GLOBAL grants

The suppliers migration (b4e8c2f91a6d) only created the `suppliers` table.
The `procurement.supplier.{create,read,update,delete}` keys exist in
app/permissions/registry.py, but has_permission() only ever looks at the
`permissions` / `role_permission_scopes` tables -- so on any database that
was seeded before those keys were added to the registry, even the admin
role got 403 "Missing permission 'procurement.supplier.read'".

This data migration is idempotent: it only inserts rows that are missing.

Revision ID: c9d2e7a4b1f5
Revises: b4e8c2f91a6d
Create Date: 2026-10-16 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "c9d2e7a4b1f5"
down_revision = "b4e8c2f91a6d"
branch_labels = None
depends_on = None

ACTIONS = ("create", "read", "update", "delete")

permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger),
    sa.column("key", sa.String),
    sa.column("module", sa.String),
    sa.column("resource", sa.String),
    sa.column("action", sa.String),
    sa.column("is_delegable", sa.Boolean),
    sa.column("description", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)
roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
role_scopes = sa.table(
    "role_permission_scopes",
    sa.column("id", sa.BigInteger),
    sa.column("role_id", sa.BigInteger),
    sa.column("permission_id", sa.BigInteger),
    sa.column("scope_type", sa.String),
    sa.column("scope_id", sa.BigInteger),
    sa.column("is_active", sa.Boolean),
    sa.column("granted_by_user_id", sa.BigInteger),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade():
    bind = op.get_bind()
    now = datetime.utcnow()

    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()

    for action in ACTIONS:
        key = f"procurement.supplier.{action}"
        perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if perm_id is None:
            bind.execute(
                permissions.insert().values(
                    key=key, module="procurement", resource="supplier", action=action,
                    is_delegable=True,
                    description=f"{action.capitalize()} procurement supplier records.",
                    created_at=now, updated_at=now,
                )
            )
            perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()

        if admin_id is None:
            continue
        has_grant = bind.execute(
            sa.select(role_scopes.c.id).where(
                role_scopes.c.role_id == admin_id,
                role_scopes.c.permission_id == perm_id,
                role_scopes.c.scope_type == "GLOBAL",
            )
        ).first()
        if has_grant is None:
            bind.execute(
                role_scopes.insert().values(
                    role_id=admin_id, permission_id=perm_id, scope_type="GLOBAL", scope_id=None,
                    is_active=True, granted_by_user_id=None, created_at=now, updated_at=now,
                )
            )
        else:
            # Re-activate if an earlier grant was switched off.
            bind.execute(
                role_scopes.update()
                .where(role_scopes.c.id == has_grant[0])
                .values(is_active=True)
            )


def downgrade():
    # Intentionally a no-op: removing permission rows could silently strip
    # access that was granted to other roles in the meantime.
    pass
