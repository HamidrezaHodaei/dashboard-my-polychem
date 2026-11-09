"""suppliers.brand_name -- نام برند یا مغازه (optional, individual suppliers only)

Revision ID: a9d4f2c7e1b6
Revises: f1b6d4a8c2e7
Create Date: 2026-10-26 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a9d4f2c7e1b6"
down_revision = "f1b6d4a8c2e7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("suppliers", sa.Column("brand_name", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("suppliers", "brand_name")