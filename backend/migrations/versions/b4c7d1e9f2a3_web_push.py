"""web push: devices, outbox, per-user notification settings

Revision ID: b4c7d1e9f2a3
Revises: a9f1c3e5d7b2
Create Date: 2026-11-23 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "b4c7d1e9f2a3"
down_revision = "a9f1c3e5d7b2"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.create_table(
        "push_subscriptions",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("platform", sa.String(length=20), nullable=True),
        sa.Column("device_label", sa.String(length=100), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=300), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_reason", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("endpoint_hash", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index("ix_push_subscriptions_user_active", "push_subscriptions", ["user_id", "disabled_at"])

    op.create_table(
        "push_deliveries",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("notification_id", BIG, sa.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", BIG, sa.ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(length=300), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("notification_id", "subscription_id", name="uq_push_deliveries_pair"),
    )
    op.create_index("ix_push_deliveries_due", "push_deliveries", ["status", "next_attempt_at"])

    op.create_table(
        "notification_settings",
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, autoincrement=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_preview", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quiet_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_start", sa.String(length=5), nullable=False, server_default="22:00"),
        sa.Column("quiet_end", sa.String(length=5), nullable=False, server_default="07:00"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "category", name="uq_notification_preferences_user_category"),
    )

    # the notification centre searches title/body and filters by type
    op.create_index("ix_notifications_user_type", "notifications", ["user_id", "type"])


def downgrade():
    op.drop_index("ix_notifications_user_type", table_name="notifications")
    op.drop_table("notification_preferences")
    op.drop_table("notification_settings")
    op.drop_index("ix_push_deliveries_due", table_name="push_deliveries")
    op.drop_table("push_deliveries")
    op.drop_index("ix_push_subscriptions_user_active", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
