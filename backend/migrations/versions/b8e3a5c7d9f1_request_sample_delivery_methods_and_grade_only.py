"""request samples: admin-managed delivery methods; product identified by grade only

* `request_sample_delivery_methods` -- the catalogue behind the «روش تحویل نمونه» dropdown. Seeded with the
  seven methods that used to be hard-coded in the frontend plus any other name already stored on a request
  or shipment, so no existing request loses its value.
* `request_sample_items.product_name` becomes nullable (the field was removed from the form; old rows keep it).
* permission `crm.request_sample.manage_catalog` (add / edit / delete delivery methods), granted to `admin`.

Revision ID: b8e3a5c7d9f1
Revises: e6a1c4d8f2b3
Create Date: 2026-11-18 10:00:00
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "b8e3a5c7d9f1"
down_revision = "e6a1c4d8f2b3"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
DEFAULT_METHODS = ("پیک موتوری", "تحویل حضوری", "باربری", "پست پیشتاز", "حمل جاده‌ای (کامیون)", "حمل هوایی", "سایر")
PERM_KEY = "crm.request_sample.manage_catalog"

methods = sa.table(
    "request_sample_delivery_methods",
    sa.column("name", sa.String), sa.column("sort_order", sa.Integer), sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
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
    sa.column("granted_by_user_id", sa.BigInteger), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    op.create_table(
        "request_sample_delivery_methods",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_rs_delivery_methods_name"),
    )
    op.alter_column("request_sample_items", "product_name", existing_type=sa.String(255), nullable=True)

    bind = op.get_bind()
    now = datetime.utcnow()

    # seed the catalogue: the former hard-coded list, then any other value already in use
    names = list(DEFAULT_METHODS)
    for table in ("request_samples", "request_sample_dispatches"):
        for (value,) in bind.execute(sa.text(f"SELECT DISTINCT delivery_method FROM {table} WHERE delivery_method IS NOT NULL")):
            value = (value or "").strip()
            if value and value.lower() not in {n.lower() for n in names}:
                names.append(value)
    for order, name in enumerate(names, start=1):
        bind.execute(methods.insert().values(name=name, sort_order=order * 10, is_active=True, created_at=now, updated_at=now))

    # permission + admin grant (idempotent)
    perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == PERM_KEY)).scalar()
    if perm_id is None:
        bind.execute(permissions.insert().values(
            key=PERM_KEY, module="crm", resource="request_sample", action="manage_catalog", is_delegable=False,
            description="Manage the sample delivery methods.", created_at=now, updated_at=now,
        ))
        perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == PERM_KEY)).scalar()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if admin_id is not None:
        grant = bind.execute(sa.select(role_scopes.c.id).where(
            role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == perm_id, role_scopes.c.scope_type == "GLOBAL",
        )).first()
        if grant is None:
            bind.execute(role_scopes.insert().values(
                role_id=admin_id, permission_id=perm_id, scope_type="GLOBAL", scope_id=None, is_active=True,
                granted_by_user_id=None, created_at=now, updated_at=now,
            ))
        else:
            bind.execute(role_scopes.update().where(role_scopes.c.id == grant[0]).values(is_active=True))


def downgrade() -> None:
    # rows saved without a product name get their grade back into the NOT NULL column
    op.execute("UPDATE request_sample_items SET product_name = COALESCE(NULLIF(grade, ''), '-') WHERE product_name IS NULL")
    op.alter_column("request_sample_items", "product_name", existing_type=sa.String(255), nullable=False)
    op.drop_table("request_sample_delivery_methods")
    # the permission row is intentionally kept (removing it could silently strip access granted meanwhile)
