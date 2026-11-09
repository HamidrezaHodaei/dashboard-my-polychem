"""customers (CRM) -- customer file + industry categories + crm.customer.* permissions

* customers            : the 6-step customer file (see app/modules/customers/models.py)
* customer_categories  : admin-managed industry list, two levels (parent_id)
* data: inserts the crm.customer.{create,read,update,delete} permissions (if missing)
  and grants them to the `admin` role at GLOBAL scope -- same idempotent approach as
  c9d2e7a4b1f5 (procurement.supplier.*), so existing databases don't answer 403.

Revision ID: d7f3b9a5e2c1
Revises: c6e2a8d4f1b9
Create Date: 2026-10-23 10:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "d7f3b9a5e2c1"
down_revision = "c6e2a8d4f1b9"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
ACTIONS = ("create", "read", "update", "delete")


def _enum(length: int):
    # Plain VARCHAR (native_enum=False, no CHECK), like every other enum column in the project.
    return sa.String(length=length)


def upgrade():
    op.create_table(
        "customer_categories",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("parent_id", BIG, nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["parent_id"], ["customer_categories.id"], ondelete="CASCADE",
                                name="fk_customer_categories_parent"),
        sa.UniqueConstraint("parent_id", "name", name="uq_customer_categories_parent_name"),
    )

    op.create_table(
        "customers",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        # step 1
        sa.Column("customer_type", _enum(10), nullable=False),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("national_id", sa.String(10)),
        sa.Column("company_name", sa.String(255)),
        sa.Column("company_national_id", sa.String(11)),
        sa.Column("registration_number", sa.String(50)),
        sa.Column("economic_id", sa.String(20)),
        sa.Column("activity_start_date", sa.Date()),
        sa.Column("contacts", sa.JSON(), nullable=False),
        sa.Column("head_office_address", sa.Text()),
        sa.Column("head_office_postal_code", sa.String(10)),
        sa.Column("factory_address", sa.Text()),
        sa.Column("factory_postal_code", sa.String(10)),
        sa.Column("acquaintance_source", sa.String(255)),
        # step 2
        sa.Column("category", sa.String(100)),
        sa.Column("subcategory", sa.String(100)),
        sa.Column("activity_types_csv", sa.String(100)),
        sa.Column("produced_products", sa.JSON(), nullable=False),
        sa.Column("production_lines_count", sa.Integer()),
        sa.Column("production_capacity", sa.String(100)),
        sa.Column("factory_province", sa.String(100)),
        sa.Column("factory_city", sa.String(100)),
        sa.Column("factory_location", sa.String(500)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        # step 3
        sa.Column("consumed_products", sa.JSON(), nullable=False),
        sa.Column("current_suppliers", sa.JSON(), nullable=False),
        # step 4
        sa.Column("commercial_status", _enum(30), nullable=False, server_default="NO_ACTION"),
        sa.Column("operational_status", _enum(10), nullable=False, server_default="ACTIVE"),
        sa.Column("contact_log", sa.JSON(), nullable=False),
        sa.Column("first_contact_date", sa.Date()),
        sa.Column("first_purchase_date", sa.Date()),
        sa.Column("last_purchase_date", sa.Date()),
        sa.Column("assigned_to_user_id", BIG),
        sa.Column("inactive_reason", sa.Text()),
        # step 5
        sa.Column("payment_terms", sa.Text()),
        sa.Column("purchase_method", _enum(12)),
        sa.Column("delivery_type", sa.String(255)),
        sa.Column("unloading_location", sa.Text()),
        sa.Column("approved_credit_limit", sa.BigInteger()),
        sa.Column("expected_price_min", sa.Numeric(18, 2)),
        sa.Column("expected_price_max", sa.Numeric(18, 2)),
        sa.Column("expected_price_unit", sa.String(50)),
        # step 6
        sa.Column("internal_notes", sa.Text()),
        sa.Column("last_negotiation_date", sa.Date()),
        sa.Column("last_negotiation_result", sa.Text()),
        sa.Column("next_action", sa.Text()),
        sa.Column("next_follow_up_date", sa.Date()),
        sa.Column("registration_date", sa.Date()),
        sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("finalized_at", sa.DateTime()),
        sa.Column("finalized_by_user_id", BIG),
        sa.Column("created_by_user_id", BIG),
        # mixins
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL", name="fk_customers_assigned_to"),
        sa.ForeignKeyConstraint(["finalized_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_customers_finalized_by"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_customers_created_by"),
    )
    op.create_index("ix_customers_category_subcategory", "customers", ["category", "subcategory"])
    op.create_index("ix_customers_commercial_status", "customers", ["commercial_status"])
    op.create_index("ix_customers_province_city", "customers", ["factory_province", "factory_city"])
    op.create_index("ix_customers_assigned_to", "customers", ["assigned_to_user_id"])
    op.create_index("ix_customers_next_follow_up", "customers", ["next_follow_up_date"])

    _seed_permissions()


def _seed_permissions():
    bind = op.get_bind()
    now = datetime.utcnow()
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
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for action in ACTIONS:
        key = f"crm.customer.{action}"
        perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if perm_id is None:
            bind.execute(permissions.insert().values(
                key=key, module="crm", resource="customer", action=action, is_delegable=True,
                description=f"{action.capitalize()} crm customer records.", created_at=now, updated_at=now,
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
    for name in ("ix_customers_next_follow_up", "ix_customers_assigned_to", "ix_customers_province_city",
                 "ix_customers_commercial_status", "ix_customers_category_subcategory"):
        op.drop_index(name, table_name="customers")
    op.drop_table("customers")
    op.drop_table("customer_categories")
    # Permission rows are intentionally kept (removing them could strip access granted meanwhile).