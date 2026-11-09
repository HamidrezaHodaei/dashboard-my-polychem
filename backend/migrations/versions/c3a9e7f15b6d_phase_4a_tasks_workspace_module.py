"""Phase 4a: Tasks / Workspace module - tasks, task_assignments

Revision ID: c3a9e7f15b6d
Revises: b7f3a1c9d2e4
Create Date: 2026-09-21 00:00:00.000000

Mirrors app/modules/tasks/models.py exactly (Task, TaskAssignment).
Hand-written for the same reason noted in b7f3a1c9d2e4's docstring (no
network access in this sandbox to run `flask db migrate` and confirm
autogenerate produces no diff) -- verify with that command against an
up-to-date checkout before relying on this migration.

`priority`/`status` are stored as VARCHAR (native_enum=False on the ORM
side, matching app/core/base.py's general avoidance of MySQL native
ENUM elsewhere in this schema) rather than a native SQL ENUM type, so
adding a new priority/status value later is a plain data change, not a
schema migration.

DATABASE.md's "UNIQUE(task_id, assignee_user_id) where unassigned_at IS
NULL" is a partial unique index, not portable across MySQL/SQLite via a
single Alembic op, and is therefore enforced in
app/modules/tasks/services.py instead -- see that module's docstring.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = 'c3a9e7f15b6d'
down_revision = 'b7f3a1c9d2e4'
branch_labels = None
depends_on = None


BIGINT_UNSIGNED = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("creator_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("department_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("team_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("project_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="TODO"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["creator_id"], ["users.id"], name="fk_tasks_creator_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"],
            name="fk_tasks_department_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name="fk_tasks_team_id", ondelete="SET NULL",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_tasks_department_id", "tasks", ["department_id"])
    op.create_index("ix_tasks_team_id", "tasks", ["team_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])

    op.create_table(
        "task_assignments",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("task_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("assignee_user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("assigned_by_user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name="fk_task_assignments_task_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_user_id"], ["users.id"],
            name="fk_task_assignments_assignee_user_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"],
            name="fk_task_assignments_assigned_by_user_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_task_assignments_assignee_user_id", "task_assignments", ["assignee_user_id"]
    )


def downgrade():
    op.drop_index("ix_task_assignments_assignee_user_id", table_name="task_assignments")
    op.drop_table("task_assignments")

    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_team_id", table_name="tasks")
    op.drop_index("ix_tasks_department_id", table_name="tasks")
    op.drop_table("tasks")
