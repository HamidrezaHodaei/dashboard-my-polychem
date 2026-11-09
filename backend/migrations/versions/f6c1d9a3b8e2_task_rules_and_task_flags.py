"""task assignment rules + task draft/archive/progress flags

Revision ID: f6c1d9a3b8e2
Revises: e5b2c8d4f1a7
Create Date: 2026-10-04 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")

revision = 'f6c1d9a3b8e2'
down_revision = 'e5b2c8d4f1a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("tasks", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("tasks", sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.create_table(
        "task_assignment_rules",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("grantor_type", sa.String(length=20), nullable=False),
        sa.Column("grantor_id", BIG, nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", BIG, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_task_assignment_rules_grantor", "task_assignment_rules", ["grantor_type", "grantor_id"]
    )


def downgrade():
    op.drop_index("ix_task_assignment_rules_grantor", table_name="task_assignment_rules")
    op.drop_table("task_assignment_rules")
    op.drop_column("tasks", "progress")
    op.drop_column("tasks", "is_archived")
    op.drop_column("tasks", "is_draft")
