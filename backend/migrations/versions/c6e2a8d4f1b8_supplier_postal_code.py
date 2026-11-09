"""suppliers.postal_code -- 10-digit Iranian postal code (optional)

Revision ID: c6e2a8d4f1b9
Revises: b5d1f7a3c9e8
Create Date: 2026-10-22 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "c6e2a8d4f1b9"
down_revision = "b5d1f7a3c9e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("suppliers", sa.Column("postal_code", sa.String(length=10), nullable=True))


def downgrade():
    op.drop_column("suppliers", "postal_code")