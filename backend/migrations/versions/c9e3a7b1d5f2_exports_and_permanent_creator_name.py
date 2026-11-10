"""export / print permissions + permanent creator name on customers, suppliers, logistics, sales

* `creator_name` (String) is written once when a record is created and never follows the user's
  live account -- renaming, re-assigning, moving or deleting the user keeps the original creator
  identifiable. Existing rows are back-filled from the creator's current name (the best information
  that exists today).
* New non-delegable permissions, granted to the `admin` role (everyone else gets them from the
  permission matrix): crm.customer.export / review, procurement.supplier.export / review,
  logistics.company.export, logistics.driver.export, crm.sale.export, crm.sale.print.

Revision ID: c9e3a7b1d5f2
Revises: a4c8e2f6b1d3
Create Date: 2026-11-09 09:00:00
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "c9e3a7b1d5f2"
down_revision = "a4c8e2f6b1d3"
branch_labels = None
depends_on = None

TABLES = ("customers", "suppliers", "logistics_applicants", "crm_sales")
NEW_PERMISSIONS = (
    ("crm", "customer", "review"), ("crm", "customer", "export"),
    ("procurement", "supplier", "review"), ("procurement", "supplier", "export"),
    ("logistics", "company", "export"), ("logistics", "driver", "export"),
    ("crm", "sale", "export"), ("crm", "sale", "print"),
)

permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger), sa.column("key", sa.String), sa.column("module", sa.String),
    sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("is_delegable", sa.Boolean),
    sa.column("description", sa.String), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
role_scopes = sa.table(
    "role_permission_scopes",
    sa.column("id", sa.BigInteger), sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger),
    sa.column("scope_type", sa.String), sa.column("scope_id", sa.BigInteger), sa.column("is_active", sa.Boolean),
    sa.column("granted_by_user_id", sa.BigInteger), sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("creator_name", sa.String(length=200), nullable=True))
        op.execute(
            f"UPDATE {table} SET creator_name = "
            f"(SELECT u.full_name FROM users u WHERE u.id = {table}.created_by_user_id) "
            f"WHERE created_by_user_id IS NOT NULL"
        )
    _seed_permissions()


def _seed_permissions() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for module, resource, action in NEW_PERMISSIONS:
        key = f"{module}.{resource}.{action}"
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if pid is None:
            bind.execute(permissions.insert().values(
                key=key, module=module, resource=resource, action=action, is_delegable=False,
                description=f"{action.capitalize()} {module} {resource} records.", created_at=now, updated_at=now,
            ))
            pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if admin_id is None:
            continue
        row = bind.execute(sa.select(role_scopes.c.id).where(
            role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == pid, role_scopes.c.scope_type == "GLOBAL",
        )).first()
        if row is None:
            bind.execute(role_scopes.insert().values(
                role_id=admin_id, permission_id=pid, scope_type="GLOBAL", scope_id=None, is_active=True,
                granted_by_user_id=None, created_at=now, updated_at=now,
            ))


def downgrade():
    for table in TABLES:
        op.drop_column(table, "creator_name")
    # the permission rows are left in place (they may be granted to roles / users)
