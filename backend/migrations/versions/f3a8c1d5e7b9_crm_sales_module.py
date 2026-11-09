"""CRM sales module -- crm_products, crm_payment_methods, crm_sales + crm.sale.* / crm.product.* permissions

* crm_sales.customer_id is a FOREIGN KEY to the existing `customers` table (the customer bank).
  No customer data is duplicated: this migration creates no customer / province / industry table.
* sale_date is a DATE; jalali_year / jalali_month are stored beside it for exact Persian-month
  grouping and filtering.
* data: seeds the default payment methods, and inserts the crm.sale.* and crm.product.*
  permissions (if missing) and grants them to the `admin` role at GLOBAL scope -- the same
  idempotent approach as d7f3b9a5e2c1 / c9d2e7a4b1f5.

Revision ID: f3a8c1d5e7b9
Revises: e5c9a3b7d2f1
Create Date: 2026-11-06 12:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "f3a8c1d5e7b9"
down_revision = "e5c9a3b7d2f1"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
ACTIONS = ("create", "read", "update", "delete")
RESOURCES = ("sale", "product")
DEFAULT_PAYMENT_METHODS = ("نقدی", "چکی", "حواله بانکی", "اعتباری")

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
payment_methods = sa.table(
    "crm_payment_methods",
    sa.column("name", sa.String), sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ]


def upgrade():
    op.create_table(
        "crm_products",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_crm_products_code"),
    )
    op.create_index("ix_crm_products_name", "crm_products", ["name"])

    op.create_table(
        "crm_payment_methods",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_crm_payment_methods_name"),
    )

    op.create_table(
        "crm_sales",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("customer_id", BIG, nullable=False),
        sa.Column("product_id", BIG, nullable=False),
        sa.Column("payment_method_id", BIG, nullable=True),
        sa.Column("quantity_kg", sa.Numeric(16, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("sale_type", sa.String(12), nullable=False, server_default="OFFICIAL"),
        sa.Column("document_type", sa.String(10), nullable=False, server_default="INVOICE"),
        sa.Column("status", sa.String(12), nullable=False, server_default="PROCESSING"),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("jalali_year", sa.SmallInteger(), nullable=False),
        sa.Column("jalali_month", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_by_user_id", BIG, nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT", name="fk_crm_sales_customer"),
        sa.ForeignKeyConstraint(["product_id"], ["crm_products.id"], ondelete="RESTRICT", name="fk_crm_sales_product"),
        sa.ForeignKeyConstraint(["payment_method_id"], ["crm_payment_methods.id"], ondelete="SET NULL",
                                name="fk_crm_sales_payment_method"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_crm_sales_user"),
    )
    op.create_index("ix_crm_sales_sale_date", "crm_sales", ["sale_date"])
    op.create_index("ix_crm_sales_customer_date", "crm_sales", ["customer_id", "sale_date"])
    op.create_index("ix_crm_sales_jalali", "crm_sales", ["jalali_year", "jalali_month"])
    op.create_index("ix_crm_sales_product", "crm_sales", ["product_id"])

    # ── data ──────────────────────────────────────────────────────────
    bind = op.get_bind()
    now = datetime.utcnow()

    for name in DEFAULT_PAYMENT_METHODS:
        bind.execute(payment_methods.insert().values(name=name, is_active=True, created_at=now, updated_at=now))

    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for resource in RESOURCES:
        for action in ACTIONS:
            key = f"crm.{resource}.{action}"
            perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
            if perm_id is None:
                bind.execute(permissions.insert().values(
                    key=key, module="crm", resource=resource, action=action, is_delegable=True,
                    description=f"{action.capitalize()} crm {resource} records.", created_at=now, updated_at=now,
                ))
                perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
            if admin_id is None:
                continue
            grant = bind.execute(sa.select(role_scopes.c.id).where(
                role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == perm_id,
                role_scopes.c.scope_type == "GLOBAL",
            )).first()
            if grant is None:
                bind.execute(role_scopes.insert().values(
                    role_id=admin_id, permission_id=perm_id, scope_type="GLOBAL", scope_id=None,
                    is_active=True, granted_by_user_id=None, created_at=now, updated_at=now,
                ))
            else:
                bind.execute(role_scopes.update().where(role_scopes.c.id == grant[0]).values(is_active=True))


def downgrade():
    # Permission rows are left in place on purpose (see c9d2e7a4b1f5): dropping them could strip
    # access granted to other roles meanwhile. Only the CRM sales tables are removed.
    op.drop_table("crm_sales")
    op.drop_table("crm_payment_methods")
    op.drop_table("crm_products")
