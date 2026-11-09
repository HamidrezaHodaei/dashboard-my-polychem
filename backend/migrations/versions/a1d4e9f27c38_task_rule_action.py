"""task_assignment_rules: add action (CREATE/ASSIGN/BOTH)

Revision ID: a1d4e9f27c38
Revises: a8e3f1b6c4d9
Create Date: 2026-10-11 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1d4e9f27c38'
down_revision = 'a8e3f1b6c4d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "task_assignment_rules",
        sa.Column("action", sa.String(length=10), nullable=False, server_default="BOTH"),
    )


def downgrade():
    op.drop_column("task_assignment_rules", "action")
