"""tasks: attachments, recurring tasks, due time, referral chain, @mentions; utf8mb4

Revision ID: e5c9a3b7d2f1
Revises: d4b8f2a6c1e9
Create Date: 2026-11-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "e5c9a3b7d2f1"
down_revision = "d4b8f2a6c1e9"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
TASK_TABLES = (
    "tasks", "task_assignments", "task_notes", "task_checklist_items", "task_files", "task_assignment_rules",
)


def upgrade():
    # -- tasks -----------------------------------------------------------
    op.add_column("tasks", sa.Column("due_time", sa.Time(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_unit", sa.String(length=10), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_interval", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_end_date", sa.Date(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_next_date", sa.Date(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_anchor_day", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_source_id", BIG, nullable=True))
    op.create_foreign_key(
        "fk_tasks_recurrence_source_id", "tasks", "tasks", ["recurrence_source_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_tasks_recurrence_next_date", "tasks", ["recurrence_next_date"])

    # -- referral chain --------------------------------------------------
    op.add_column("task_assignments", sa.Column("parent_assignment_id", BIG, nullable=True))
    op.add_column("task_assignments", sa.Column("end_reason", sa.String(length=10), nullable=True))
    op.add_column("task_assignments", sa.Column("referral_note", sa.String(length=500), nullable=True))
    op.create_foreign_key(
        "fk_task_assignments_parent", "task_assignments", "task_assignments",
        ["parent_assignment_id"], ["id"], ondelete="SET NULL",
    )
    # rows closed before this migration were plain removals
    op.execute("UPDATE task_assignments SET end_reason = 'REMOVED' WHERE unassigned_at IS NOT NULL")

    # -- @mentions -------------------------------------------------------
    op.add_column("task_notes", sa.Column("mentioned_user_ids", sa.JSON(), nullable=True))

    # -- attachments -----------------------------------------------------
    op.create_table(
        "task_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", BIG, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_files_task_id", "task_files", ["task_id"])

    # -- Persian text must round-trip: make every task table utf8mb4 (MySQL only) ----
    if op.get_bind().dialect.name == "mysql":
        for table in TASK_TABLES:
            op.execute(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")


def downgrade():
    op.drop_index("ix_task_files_task_id", table_name="task_files")
    op.drop_table("task_files")
    op.drop_column("task_notes", "mentioned_user_ids")
    op.drop_constraint("fk_task_assignments_parent", "task_assignments", type_="foreignkey")
    for col in ("referral_note", "end_reason", "parent_assignment_id"):
        op.drop_column("task_assignments", col)
    op.drop_index("ix_tasks_recurrence_next_date", table_name="tasks")
    op.drop_constraint("fk_tasks_recurrence_source_id", "tasks", type_="foreignkey")
    for col in ("recurrence_source_id", "recurrence_anchor_day", "recurrence_next_date", "recurrence_end_date",
                "recurrence_interval", "recurrence_unit", "due_time"):
        op.drop_column("tasks", col)
