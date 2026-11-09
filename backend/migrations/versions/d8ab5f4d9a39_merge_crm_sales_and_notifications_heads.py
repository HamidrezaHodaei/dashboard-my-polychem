"""merge crm sales and notifications heads

Revision ID: d8ab5f4d9a39
Revises: f3a8c1d5e7b9, f6d1b8c4e2a7
Create Date: 2026-11-07 15:04:28.502698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8ab5f4d9a39'
down_revision = ('f3a8c1d5e7b9', 'f6d1b8c4e2a7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
