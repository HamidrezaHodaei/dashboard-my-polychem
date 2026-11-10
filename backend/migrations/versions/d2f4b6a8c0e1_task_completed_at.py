"""tasks.completed_at -- when a task reached DONE (feeds the employee KPI analytics)

Revision ID: d2f4b6a8c0e1
Revises: c9e3a7b1d5f2
Create Date: 2026-11-09 12:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "d2f4b6a8c0e1"
down_revision = "c9e3a7b1d5f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(), nullable=True))
    # best information available for tasks that are already done: their last update
    op.execute("UPDATE tasks SET completed_at = updated_at WHERE status = 'DONE'")


def downgrade():
    op.drop_column("tasks", "completed_at")
