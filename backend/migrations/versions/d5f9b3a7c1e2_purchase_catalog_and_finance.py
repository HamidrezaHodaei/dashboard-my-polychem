"""purchase reports: product catalog, item product link, "sent to finance" timestamp

* purchase_products   -- the module's own product catalog (name + free-text String code), admin managed
* purchase_items      -- product_id (FK) + product_code snapshot
* purchase_requests   -- sent_to_finance_at (status SENT_TO_FINANCE is a new value of the existing varchar status column;
                         AWAITING_DELIVERY / COMPLETED keep their values and are only relabelled in the UI)
* permission procurement.purchase.manage_catalog, granted GLOBAL to the admin role

Revision ID: d5f9b3a7c1e2
Revises: c4e8a2f6b9d1
Create Date: 2026-11-16 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "d5f9b3a7c1e2"
down_revision = "c4e8a2f6b9d1"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.create_table(
        "purchase_products",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("category_id", BIG, sa.ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_purchase_products_name"),
        sa.UniqueConstraint("code", name="uq_purchase_products_code"),
    )
    with op.batch_alter_table("purchase_items") as b:
        b.add_column(sa.Column("product_id", BIG, nullable=True))
        b.add_column(sa.Column("product_code", sa.String(length=64), nullable=True))
        b.create_foreign_key("fk_purchase_items_product", "purchase_products", ["product_id"], ["id"], ondelete="SET NULL")
        b.create_index("ix_purchase_items_product", ["product_id"])
    with op.batch_alter_table("purchase_requests") as b:
        b.add_column(sa.Column("sent_to_finance_at", sa.DateTime(), nullable=True))

    _seed()


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


def _seed():
    bind = op.get_bind()
    now = datetime.utcnow()
    key = "procurement.purchase.manage_catalog"
    pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    if pid is None:
        bind.execute(permissions.insert().values(
            key=key, module="procurement", resource="purchase", action="manage_catalog", is_delegable=False,
            description="Manage the purchase product catalog.", created_at=now, updated_at=now))
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if admin_id is None:
        return
    row = bind.execute(sa.select(role_scopes.c.id).where(
        role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == pid, role_scopes.c.scope_type == "GLOBAL")).first()
    if row is None:
        bind.execute(role_scopes.insert().values(
            role_id=admin_id, permission_id=pid, scope_type="GLOBAL", scope_id=None, is_active=True,
            granted_by_user_id=None, created_at=now, updated_at=now))
    else:
        bind.execute(role_scopes.update().where(role_scopes.c.id == row[0]).values(is_active=True))


def downgrade():
    with op.batch_alter_table("purchase_requests") as b:
        b.drop_column("sent_to_finance_at")
    with op.batch_alter_table("purchase_items") as b:
        b.drop_index("ix_purchase_items_product")
        b.drop_constraint("fk_purchase_items_product", type_="foreignkey")
        b.drop_column("product_code")
        b.drop_column("product_id")
    op.drop_table("purchase_products")
    # the permission row is kept on purpose (see the first purchase migration)
