"""task internal notes + checklist items

Revision ID: a8e3f1b6c4d9
Revises: f6c1d9a3b8e2
Create Date: 2026-10-05 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'a8e3f1b6c4d9'
down_revision = 'f6c1d9a3b8e2'
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.create_table(
        "task_notes",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("task_id", BIG, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_notes_task_id", "task_notes", ["task_id"])

    op.create_table(
        "task_checklist_items",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("task_id", BIG, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])


def downgrade():
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")
    op.drop_index("ix_task_notes_task_id", table_name="task_notes")
    op.drop_table("task_notes")
