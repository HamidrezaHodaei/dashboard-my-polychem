"""notifications, profile photo, shared request-review workflow (logistics / suppliers / customers)

Revision ID: f6d1b8c4e2a7
Revises: e5c9a3b7d2f1
Create Date: 2026-11-02 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "f6d1b8c4e2a7"
down_revision = "e5c9a3b7d2f1"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
LONGTEXT = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def _review_columns(table: str) -> None:
    op.add_column(table, sa.Column("review_status", sa.String(length=12), nullable=False, server_default="PENDING"))
    op.add_column(table, sa.Column("review_note", sa.String(length=1000), nullable=True))
    op.add_column(table, sa.Column("decided_by_user_id", BIG, nullable=True))
    op.add_column(table, sa.Column("decided_at", sa.DateTime(), nullable=True))
    op.add_column(table, sa.Column("change_request_note", sa.String(length=1000), nullable=True))
    op.add_column(table, sa.Column("change_requested_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(f"fk_{table}_decided_by", table, "users", ["decided_by_user_id"], ["id"], ondelete="SET NULL")


def upgrade():
    # -- profile photo -------------------------------------------------
    op.add_column("users", sa.Column("avatar_data", LONGTEXT, nullable=True))

    # -- notifications -------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=True),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("task_id", BIG, nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )
    op.create_index("ix_notifications_user_read_id", "notifications", ["user_id", "read_at", "id"])

    # -- suppliers: review workflow -----------------------------------
    _review_columns("suppliers")
    op.add_column("suppliers", sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    op.add_column("suppliers", sa.Column("finalized_at", sa.DateTime(), nullable=True))
    # suppliers that already exist were accepted before this workflow existed
    op.execute("UPDATE suppliers SET review_status = 'APPROVED', finalized_at = created_at")

    # -- customers: review workflow (is_finalized already existed) -----
    _review_columns("customers")
    op.execute("UPDATE customers SET review_status = CASE WHEN is_finalized = 1 THEN 'APPROVED' ELSE 'PENDING' END")

    # -- logistics: finalisation + change requests ---------------------
    op.add_column("logistics_applicants", sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    op.add_column("logistics_applicants", sa.Column("change_request_note", sa.String(length=1000), nullable=True))
    op.add_column("logistics_applicants", sa.Column("change_requested_at", sa.DateTime(), nullable=True))

    _seed_review_permissions()


# ---------------------------------------------------------------------
# Data seed (idempotent): `review` permission for customers and suppliers, granted to admin
# ---------------------------------------------------------------------
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


def _seed_review_permissions() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for module, resource in (("crm", "customer"), ("procurement", "supplier")):
        key = f"{module}.{resource}.review"
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if pid is None:
            bind.execute(permissions.insert().values(
                key=key, module=module, resource=resource, action="review", is_delegable=False,
                description=f"Review (approve / reject / return for edits) {module} {resource} requests.",
                created_at=now, updated_at=now,
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
    for col in ("change_requested_at", "change_request_note", "is_finalized"):
        op.drop_column("logistics_applicants", col)
    for table in ("customers", "suppliers"):
        op.drop_constraint(f"fk_{table}_decided_by", table, type_="foreignkey")
        for col in ("change_requested_at", "change_request_note", "decided_at", "decided_by_user_id", "review_note", "review_status"):
            op.drop_column(table, col)
    op.drop_column("suppliers", "finalized_at")
    op.drop_column("suppliers", "is_finalized")
    op.drop_index("ix_notifications_user_read_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_column("users", "avatar_data")
