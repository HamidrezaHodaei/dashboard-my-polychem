"""user sessions: one row per login (IP, device, OS, browser, logout) + refresh_tokens.session_id

Revision ID: c8d2e4f6a1b3
Revises: b4c7d1e9f2a3
Create Date: 2026-11-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "c8d2e4f6a1b3"
down_revision = "b4c7d1e9f2a3"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.create_table(
        "user_sessions",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("device_type", sa.String(length=20), nullable=True),
        sa.Column("os", sa.String(length=40), nullable=True),
        sa.Column("browser", sa.String(length=40), nullable=True),
        sa.Column("login_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("logout_at", sa.DateTime(), nullable=True),
        sa.Column("logout_reason", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_user_sessions_user_login", "user_sessions", ["user_id", "login_at"])

    with op.batch_alter_table("refresh_tokens") as batch:
        batch.add_column(sa.Column("session_id", BIG, nullable=True))
        batch.create_foreign_key(
            "fk_refresh_tokens_session", "user_sessions", ["session_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_refresh_tokens_session_id", ["session_id"])


def downgrade():
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.drop_index("ix_refresh_tokens_session_id")
        batch.drop_constraint("fk_refresh_tokens_session", type_="foreignkey")
        batch.drop_column("session_id")
    op.drop_index("ix_user_sessions_user_login", table_name="user_sessions")
    op.drop_table("user_sessions")
