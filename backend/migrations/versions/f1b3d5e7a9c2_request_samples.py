"""request samples (CRM): requests, items, dispatches, follow-ups, activity events, attachments + permissions

Permissions (crm.request_sample.*) are created and granted to the `admin` role; everybody else gets
them from the permission matrix.

Revision ID: f1b3d5e7a9c2
Revises: e3a5c7b9d1f2
Create Date: 2026-11-10 10:00:00
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "f1b3d5e7a9c2"
down_revision = "e3a5c7b9d1f2"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
ACTIONS = ("create", "read", "update", "delete", "approve", "reject", "dispatch", "follow_up", "feedback", "convert", "export")
NON_DELEGABLE = {"approve", "reject", "dispatch", "follow_up", "feedback", "convert", "export"}


def _ts():
    return [sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now())]


def upgrade():
    op.create_table(
        "request_samples",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("customer_id", BIG, sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sales_rep_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("creator_name", sa.String(200)),
        sa.Column("parent_request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("dispatch_ref_number", sa.String(100)),
        sa.Column("required_delivery_date", sa.Date()),
        sa.Column("purpose", sa.Text()), sa.Column("technical_requirements", sa.Text()),
        sa.Column("application", sa.String(255)), sa.Column("industry", sa.String(255)),
        sa.Column("production_process", sa.Text()), sa.Column("required_properties", sa.Text()),
        sa.Column("delivery_method", sa.String(100)), sa.Column("recipient_name", sa.String(200)),
        sa.Column("delivery_address", sa.Text()), sa.Column("country", sa.String(100)), sa.Column("city", sa.String(100)),
        sa.Column("postal_code", sa.String(20)), sa.Column("delivery_instructions", sa.Text()),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("decided_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_at", sa.DateTime()), sa.Column("approved_at", sa.DateTime()),
        sa.Column("first_dispatched_at", sa.DateTime()), sa.Column("closed_at", sa.DateTime()),
        sa.Column("reject_reason", sa.Text()), sa.Column("hold_reason", sa.Text()), sa.Column("cancel_reason", sa.Text()),
        sa.Column("fb_status", sa.String(30)), sa.Column("fb_date", sa.Date()),
        sa.Column("fb_product_evaluation", sa.Text()), sa.Column("fb_technical_acceptance", sa.Boolean()),
        sa.Column("fb_comments", sa.Text()), sa.Column("fb_rejection_reason", sa.Text()),
        sa.Column("fb_suggestions", sa.Text()), sa.Column("fb_evaluated_by", sa.String(200)),
        sa.Column("fb_recorded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("fb_recorded_at", sa.DateTime()),
        sa.Column("converted_sale_id", BIG, sa.ForeignKey("crm_sales.id", ondelete="SET NULL")),
        sa.Column("conversion_note", sa.Text()), sa.Column("converted_at", sa.DateTime()),
        sa.Column("deleted_at", sa.DateTime()),
        *_ts(),
    )
    op.create_index("ix_rs_status", "request_samples", ["status"])
    op.create_index("ix_rs_customer", "request_samples", ["customer_id"])
    op.create_index("ix_rs_rep", "request_samples", ["sales_rep_user_id"])
    op.create_index("ix_rs_requested_date", "request_samples", ["requested_date"])

    op.create_table(
        "request_sample_items",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_category", sa.String(200)), sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("grade", sa.String(255)), sa.Column("alternative_product", sa.String(255)),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False), sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("number_of_samples", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("packaging", sa.String(200)), sa.Column("specifications", sa.Text()),
    )
    op.create_index("ix_request_sample_items_request_id", "request_sample_items", ["request_id"])

    op.create_table(
        "request_sample_dispatches",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dispatch_date", sa.Date(), nullable=False), sa.Column("reference_number", sa.String(100), nullable=False),
        sa.Column("delivery_method", sa.String(100)), sa.Column("tracking_number", sa.String(100)),
        sa.Column("carrier", sa.String(200)), sa.Column("shipped_quantity", sa.Numeric(14, 3)),
        sa.Column("unit", sa.String(20), nullable=False), sa.Column("recipient_name", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("creator_name", sa.String(200)),
        *_ts(),
    )
    op.create_index("ix_request_sample_dispatches_request_id", "request_sample_dispatches", ["request_id"])

    op.create_table(
        "request_sample_followups",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("followup_date", sa.Date(), nullable=False), sa.Column("method", sa.String(30), nullable=False),
        sa.Column("contact_person", sa.String(200)), sa.Column("result", sa.Text()),
        sa.Column("customer_response", sa.Text()), sa.Column("next_followup_date", sa.Date()),
        sa.Column("responsible_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("creator_name", sa.String(200)),
        *_ts(),
    )
    op.create_index("ix_request_sample_followups_request_id", "request_sample_followups", ["request_id"])

    op.create_table(
        "request_sample_events",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("user_name", sa.String(200)), sa.Column("action", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(20)), sa.Column("to_status", sa.String(20)),
        sa.Column("note", sa.Text()), sa.Column("details", sa.JSON()),
    )
    op.create_index("ix_rs_events_request", "request_sample_events", ["request_id", "id"])

    op.create_table(
        "request_sample_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", BIG, sa.ForeignKey("request_samples.id", ondelete="CASCADE")),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False), sa.Column("stored_name", sa.String(80), nullable=False),
        sa.Column("content_type", sa.String(100)), sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_ts(),
    )
    op.create_index("ix_request_sample_files_request_id", "request_sample_files", ["request_id"])
    _seed_permissions()


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


def _seed_permissions() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for action in ACTIONS:
        key = f"crm.request_sample.{action}"
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if pid is None:
            bind.execute(permissions.insert().values(
                key=key, module="crm", resource="request_sample", action=action,
                is_delegable=action not in NON_DELEGABLE, description=f"{action} request samples.",
                created_at=now, updated_at=now,
            ))
            pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if admin_id is None:
            continue
        exists = bind.execute(sa.select(role_scopes.c.id).where(
            role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == pid, role_scopes.c.scope_type == "GLOBAL",
        )).first()
        if exists is None:
            bind.execute(role_scopes.insert().values(
                role_id=admin_id, permission_id=pid, scope_type="GLOBAL", scope_id=None, is_active=True,
                granted_by_user_id=None, created_at=now, updated_at=now,
            ))


def downgrade():
    for table in ("request_sample_files", "request_sample_events", "request_sample_followups",
                  "request_sample_dispatches", "request_sample_items", "request_samples"):
        op.drop_table(table)
