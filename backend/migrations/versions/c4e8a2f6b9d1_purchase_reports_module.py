"""purchase reports module -- purchase requests, items, quotations, events, files

Creates the six purchase tables, then seeds (idempotently):
  * the `procurement.purchase.{create,read,update,delete,approve,export}` permissions,
  * GLOBAL grants of all of them to the `admin` role,
  * three ready-made roles:
        purchase_manager  -- everything (incl. approve reference prices / send back / export)
        purchase_expert   -- read / create / update / export (records purchases; no delete, no approve)
        purchase_viewer   -- read only
Existing roles (e.g. procurement_manager) are NOT touched: grant them in the permission matrix.

Revision ID: c4e8a2f6b9d1
Revises: b2d4f6a8c0e3
Create Date: 2026-11-15 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "c4e8a2f6b9d1"
down_revision = "b2d4f6a8c0e3"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
JSON_TYPE = sa.JSON().with_variant(mysql.JSON(), "mysql")


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ]


def upgrade():
    op.create_table(
        "purchase_requests",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_no", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requester_unit", sa.String(length=200), nullable=True),
        sa.Column("requester_name", sa.String(length=150), nullable=True),
        sa.Column("request_date", sa.Date(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="NORMAL"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("delivery_location", sa.String(length=255), nullable=True),
        sa.Column("budget_files", JSON_TYPE, nullable=True),
        sa.Column("inquiry_shortfall_reason", sa.Text(), nullable=True),
        sa.Column("inquiries_finalized_at", sa.DateTime(), nullable=True),
        sa.Column("selected_inquiry_id", BIG, nullable=True),
        sa.Column("selection_reasons", JSON_TYPE, nullable=True),
        sa.Column("selection_note", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("final_extra_costs", sa.Numeric(18, 2), nullable=True),
        sa.Column("final_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("delivery_status", sa.String(length=15), nullable=False, server_default="NOT_DELIVERED"),
        sa.Column("completion_note", sa.Text(), nullable=True),
        sa.Column("final_files", JSON_TYPE, nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status_note", sa.String(length=1000), nullable=True),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("creator_name", sa.String(length=200), nullable=True),
        sa.Column("updated_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        *_ts(),
        sa.UniqueConstraint("request_no", name="uq_purchase_requests_request_no"),
    )
    op.create_index("ix_purchase_requests_status", "purchase_requests", ["status"])
    op.create_index("ix_purchase_requests_request_date", "purchase_requests", ["request_date"])
    op.create_index("ix_purchase_requests_required_date", "purchase_requests", ["required_date"])
    op.create_index("ix_purchase_requests_unit", "purchase_requests", ["requester_unit"])

    op.create_table(
        "purchase_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("request_id", BIG, sa.ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_ts(),
    )

    op.create_table(
        "purchase_items",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("category_id", BIG, sa.ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_name", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specs", sa.Text(), nullable=True),
        sa.Column("brand_model", sa.String(length=150), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("estimated_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("reference_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("reference_source", sa.String(length=15), nullable=True),
        sa.Column("reference_note", sa.String(length=500), nullable=True),
        sa.Column("reference_item_id", BIG, sa.ForeignKey("purchase_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reference_approved_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reference_approved_at", sa.DateTime(), nullable=True),
        sa.Column("final_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("purchased_quantity", sa.Numeric(18, 3), nullable=True),
        *_ts(),
    )
    op.create_index("ix_purchase_items_request", "purchase_items", ["request_id"])
    op.create_index("ix_purchase_items_category", "purchase_items", ["category_id"])

    op.create_table(
        "purchase_inquiries",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("supplier_id", BIG, sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("payment_terms", sa.String(length=500), nullable=True),
        sa.Column("extra_costs", sa.Numeric(18, 2), nullable=True),
        sa.Column("total_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_ts(),
        sa.UniqueConstraint("request_id", "position", name="uq_purchase_inquiries_request_position"),
        sa.UniqueConstraint("request_id", "supplier_id", name="uq_purchase_inquiries_request_supplier"),
    )
    op.create_index("ix_purchase_inquiries_supplier", "purchase_inquiries", ["supplier_id"])

    op.create_table(
        "purchase_inquiry_items",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("inquiry_id", BIG, sa.ForeignKey("purchase_inquiries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", BIG, sa.ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint("inquiry_id", "item_id", name="uq_purchase_inquiry_items_pair"),
    )

    op.create_table(
        "purchase_events",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("step", sa.String(length=20), nullable=True),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_purchase_events_request", "purchase_events", ["request_id", "created_at"])

    # circular reference (request -> chosen quotation); SQLite cannot ALTER ... ADD CONSTRAINT
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_purchase_requests_selected_inquiry", "purchase_requests", "purchase_inquiries",
            ["selected_inquiry_id"], ["id"], ondelete="SET NULL",
        )

    _seed_permissions_and_roles()


# ---------------------------------------------------------------------
# Data seed (idempotent)
# ---------------------------------------------------------------------
ACTIONS = ("create", "read", "update", "delete", "approve", "export")
ROLES = {
    "purchase_manager": ("مدیر خرید", "Full access to Purchase Reports, including approving reference prices.", ACTIONS),
    "purchase_expert": ("کارشناس خرید", "Records and edits purchases and exports reports; cannot delete or approve.",
                        ("read", "create", "update", "export")),
    "purchase_viewer": ("مشاهده‌گر گزارشات خرید", "Read-only access to Purchase Reports.", ("read",)),
}

permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger), sa.column("key", sa.String), sa.column("module", sa.String),
    sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("is_delegable", sa.Boolean),
    sa.column("description", sa.String), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
roles = sa.table(
    "roles",
    sa.column("id", sa.BigInteger), sa.column("name", sa.String), sa.column("display_name", sa.String),
    sa.column("description", sa.String), sa.column("is_system_role", sa.Boolean), sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
role_scopes = sa.table(
    "role_permission_scopes",
    sa.column("id", sa.BigInteger), sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger),
    sa.column("scope_type", sa.String), sa.column("scope_id", sa.BigInteger), sa.column("is_active", sa.Boolean),
    sa.column("granted_by_user_id", sa.BigInteger), sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def _permission_id(bind, action: str, now) -> int:
    key = f"procurement.purchase.{action}"
    pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    if pid is None:
        bind.execute(permissions.insert().values(
            key=key, module="procurement", resource="purchase", action=action, is_delegable=False,
            description=f"{action.capitalize()} procurement purchase records.", created_at=now, updated_at=now,
        ))
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    return pid


def _grant_global(bind, role_id: int, permission_id: int, now) -> None:
    row = bind.execute(sa.select(role_scopes.c.id).where(
        role_scopes.c.role_id == role_id, role_scopes.c.permission_id == permission_id,
        role_scopes.c.scope_type == "GLOBAL",
    )).first()
    if row is None:
        bind.execute(role_scopes.insert().values(
            role_id=role_id, permission_id=permission_id, scope_type="GLOBAL", scope_id=None,
            is_active=True, granted_by_user_id=None, created_at=now, updated_at=now,
        ))
    else:
        bind.execute(role_scopes.update().where(role_scopes.c.id == row[0]).values(is_active=True))


def _seed_permissions_and_roles() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    ids = {act: _permission_id(bind, act, now) for act in ACTIONS}

    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if admin_id is not None:
        for pid in ids.values():
            _grant_global(bind, admin_id, pid, now)

    for name, (display, description, actions) in ROLES.items():
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        if role_id is None:
            bind.execute(roles.insert().values(
                name=name, display_name=display, description=description, is_system_role=True,
                is_active=True, created_at=now, updated_at=now,
            ))
            role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        for act in actions:
            _grant_global(bind, role_id, ids[act], now)


def downgrade():
    # Tables only. Permission/role rows are kept on purpose: removing them could silently strip
    # access that was assigned in the meantime.
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_purchase_requests_selected_inquiry", "purchase_requests", type_="foreignkey")
    op.drop_index("ix_purchase_events_request", table_name="purchase_events")
    op.drop_table("purchase_events")
    op.drop_table("purchase_inquiry_items")
    op.drop_index("ix_purchase_inquiries_supplier", table_name="purchase_inquiries")
    op.drop_table("purchase_inquiries")
    op.drop_index("ix_purchase_items_category", table_name="purchase_items")
    op.drop_index("ix_purchase_items_request", table_name="purchase_items")
    op.drop_table("purchase_items")
    op.drop_table("purchase_files")
    for ix in ("unit", "required_date", "request_date", "status"):
        op.drop_index(f"ix_purchase_requests_{ix}", table_name="purchase_requests")
    op.drop_table("purchase_requests")
