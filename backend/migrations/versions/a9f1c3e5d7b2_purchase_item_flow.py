"""purchase module: item-based flow (warehouse -> procurement -> manager -> finance -> delivery)

* purchase_requests   -- flow_version (1 = the old request-level workflow, kept; 2 = this flow), submitted_at (SLA clock)
* purchase_items      -- per-item stock / reorder point / request type / subject / priority / status / supply place,
                         manager approval, paid / shipped / delivered stamps, warehouse receipt file
* purchase_item_quotes, purchase_item_payments -- quotations and the payment of ONE item
* purchase_options    -- admin-managed pick lists (requesting units, request types)
* purchase_sla        -- allowed delivery time per priority (admin)
* purchase_events     -- item_id (history of each item's status changes)
* purchase_products   -- unit (the measuring unit that fills the request line)
* permissions procurement.purchase.{warehouse,procure,manager,finance,settings}; roles purchase_flow_*

Revision ID: a9f1c3e5d7b2
Revises: a3e7c1f5b9d2
Create Date: 2026-11-19 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "a9f1c3e5d7b2"
down_revision = "a3e7c1f5b9d2"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def upgrade():
    with op.batch_alter_table("purchase_requests") as b:
        b.add_column(sa.Column("flow_version", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("submitted_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("purchase_products") as b:
        b.add_column(sa.Column("unit", sa.String(length=40), nullable=True))

    with op.batch_alter_table("purchase_events") as b:
        b.add_column(sa.Column("item_id", BIG, nullable=True))

    with op.batch_alter_table("purchase_items") as b:
        b.add_column(sa.Column("current_stock", sa.Numeric(18, 3), nullable=True))
        b.add_column(sa.Column("reorder_point", sa.Numeric(18, 3), nullable=True))
        b.add_column(sa.Column("request_type", sa.String(length=150), nullable=True))
        b.add_column(sa.Column("purchase_subject", sa.String(length=10), nullable=True))
        b.add_column(sa.Column("priority", sa.String(length=10), nullable=True))
        b.add_column(sa.Column("item_status", sa.String(length=20), nullable=False, server_default="PENDING"))
        b.add_column(sa.Column("supply_place", sa.String(length=10), nullable=True))
        b.add_column(sa.Column("selected_quote_id", BIG, nullable=True))
        b.add_column(sa.Column("manager_note", sa.String(length=1000), nullable=True))
        b.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("approved_by_name", sa.String(length=200), nullable=True))
        b.add_column(sa.Column("paid_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("shipped_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("delivered_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("delivered_by_name", sa.String(length=200), nullable=True))
        b.add_column(sa.Column("receipt_file_id", sa.String(length=36), nullable=True))
        b.add_column(sa.Column("receipt_uploaded_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("status_note", sa.String(length=1000), nullable=True))
        b.create_foreign_key("fk_purchase_items_receipt_file", "purchase_files", ["receipt_file_id"], ["id"],
                             ondelete="SET NULL")
        b.create_index("ix_purchase_items_status", ["item_status"])

    op.create_table(
        "purchase_item_quotes",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("item_id", BIG, sa.ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supplier_id", BIG, sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("payment_method", sa.String(length=10), nullable=True),
        sa.Column("payment_terms", sa.String(length=500), nullable=True),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_name", sa.String(length=200), nullable=True),
        *_ts(),
    )
    op.create_index("ix_purchase_item_quotes_item", "purchase_item_quotes", ["item_id"])

    op.create_table(
        "purchase_item_payments",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("item_id", BIG, sa.ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quote_id", BIG, nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("payment_ref", sa.String(length=100), nullable=True),
        sa.Column("receipt_file_id", sa.String(length=36), sa.ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cheque_file_id", sa.String(length=36), sa.ForeignKey("purchase_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cheque_no", sa.String(length=50), nullable=True),
        sa.Column("cheque_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("cheque_issue_date", sa.Date(), nullable=True),
        sa.Column("cheque_due_date", sa.Date(), nullable=True),
        sa.Column("cheque_bank", sa.String(length=150), nullable=True),
        sa.Column("cheque_payee", sa.String(length=200), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("recorded_by_name", sa.String(length=200), nullable=True),
        *_ts(),
        sa.UniqueConstraint("item_id", name="uq_purchase_item_payments_item"),
    )

    op.create_table(
        "purchase_options",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
        sa.UniqueConstraint("kind", "label", name="uq_purchase_options_kind_label"),
    )

    op.create_table(
        "purchase_sla",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=5), nullable=False, server_default="DAYS"),
        sa.Column("updated_by_name", sa.String(length=200), nullable=True),
        *_ts(),
        sa.UniqueConstraint("priority", name="uq_purchase_sla_priority"),
    )

    _seed()


# ---------------------------------------------------------------------
# Data seed (idempotent)
# ---------------------------------------------------------------------
NEW_ACTIONS = ("warehouse", "procure", "manager", "finance", "settings")
ROLES = {
    "purchase_flow_warehouse": ("انبار – ثبت درخواست خرید", "Registers purchase requests, follows their status, uploads warehouse receipts.",
                                ("warehouse",)),
    "purchase_flow_procurement": ("کارشناس تدارکات", "Procurement cartable: statuses, local / non-local, quotations, shipping and delivery.",
                                  ("procure", "read", "export")),
    "purchase_flow_manager": ("مدیر – تأیید استعلام خرید", "Approves or returns the quotation of each item.",
                              ("manager", "read", "export")),
    "purchase_flow_finance": ("مالی – پرداخت خرید", "Records cash / cheque payments of approved purchases.", ("finance",)),
}
DEFAULT_SLA = (("NORMAL", 14), ("URGENT", 7), ("EMERGENCY", 2))   # days; the admin edits them in the settings tab
DEFAULT_REQUEST_TYPES = ("خرید جدید", "تأمین مجدد موجودی", "جایگزینی / تعویض")

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
options = sa.table(
    "purchase_options",
    sa.column("kind", sa.String), sa.column("label", sa.String), sa.column("sort_order", sa.Integer),
    sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
sla = sa.table(
    "purchase_sla",
    sa.column("priority", sa.String), sa.column("amount", sa.Integer), sa.column("unit", sa.String),
    sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)


def _permission_id(bind, action: str, now) -> int:
    key = f"procurement.purchase.{action}"
    pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    if pid is None:
        bind.execute(permissions.insert().values(
            key=key, module="procurement", resource="purchase", action=action, is_delegable=False,
            description=f"{action.capitalize()} procurement purchase records.", created_at=now, updated_at=now))
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    return pid


def _grant_global(bind, role_id: int, permission_id: int, now) -> None:
    row = bind.execute(sa.select(role_scopes.c.id).where(
        role_scopes.c.role_id == role_id, role_scopes.c.permission_id == permission_id,
        role_scopes.c.scope_type == "GLOBAL")).first()
    if row is None:
        bind.execute(role_scopes.insert().values(
            role_id=role_id, permission_id=permission_id, scope_type="GLOBAL", scope_id=None, is_active=True,
            granted_by_user_id=None, created_at=now, updated_at=now))
    else:
        bind.execute(role_scopes.update().where(role_scopes.c.id == row[0]).values(is_active=True))


def _seed():
    bind = op.get_bind()
    now = datetime.utcnow()
    ids = {a: _permission_id(bind, a, now) for a in (*NEW_ACTIONS, "read", "export")}

    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if admin_id is not None:
        for a in NEW_ACTIONS:
            _grant_global(bind, admin_id, ids[a], now)

    for name, (display, description, actions) in ROLES.items():
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        if role_id is None:
            bind.execute(roles.insert().values(
                name=name, display_name=display, description=description, is_system_role=True, is_active=True,
                created_at=now, updated_at=now))
            role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        for a in actions:
            _grant_global(bind, role_id, ids[a], now)

    # requesting units: start from the organisation's departments (the admin then manages the list)
    if bind.execute(sa.select(sa.func.count()).select_from(options).where(options.c.kind == "UNIT")).scalar() == 0:
        names = bind.execute(sa.text(
            "SELECT DISTINCT name FROM departments WHERE deleted_at IS NULL ORDER BY name")).scalars().all()
        for i, n in enumerate(names):
            bind.execute(options.insert().values(kind="UNIT", label=n, sort_order=i, is_active=True, created_at=now, updated_at=now))
    if bind.execute(sa.select(sa.func.count()).select_from(options).where(options.c.kind == "REQUEST_TYPE")).scalar() == 0:
        for i, n in enumerate(DEFAULT_REQUEST_TYPES):
            bind.execute(options.insert().values(kind="REQUEST_TYPE", label=n, sort_order=i, is_active=True,
                                                 created_at=now, updated_at=now))
    if bind.execute(sa.select(sa.func.count()).select_from(sla)).scalar() == 0:
        for pr, days in DEFAULT_SLA:
            bind.execute(sla.insert().values(priority=pr, amount=days, unit="DAYS", created_at=now, updated_at=now))


def downgrade():
    op.drop_table("purchase_sla")
    op.drop_table("purchase_options")
    op.drop_table("purchase_item_payments")
    op.drop_index("ix_purchase_item_quotes_item", table_name="purchase_item_quotes")
    op.drop_table("purchase_item_quotes")
    with op.batch_alter_table("purchase_items") as b:
        b.drop_index("ix_purchase_items_status")
        b.drop_constraint("fk_purchase_items_receipt_file", type_="foreignkey")
        for c in ("status_note", "receipt_uploaded_at", "receipt_file_id", "delivered_by_name", "delivered_at",
                  "shipped_at", "paid_at", "approved_by_name", "approved_at", "manager_note", "selected_quote_id",
                  "supply_place", "item_status", "priority", "purchase_subject", "request_type", "reorder_point",
                  "current_stock"):
            b.drop_column(c)
    with op.batch_alter_table("purchase_events") as b:
        b.drop_column("item_id")
    with op.batch_alter_table("purchase_products") as b:
        b.drop_column("unit")
    with op.batch_alter_table("purchase_requests") as b:
        b.drop_column("submitted_at")
        b.drop_column("flow_version")
    # permission / role rows are kept on purpose (see the first purchase migration)
