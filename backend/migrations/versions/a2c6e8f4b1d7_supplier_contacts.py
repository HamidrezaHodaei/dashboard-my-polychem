"""suppliers.contacts -- contact persons (name, position, email, mobile, landline)

Existing rows get an empty list; their flat `phones` stay untouched.

Revision ID: a2c6e8f4b1d7
Revises: e7a3c1d9b5f2
Create Date: 2026-10-18 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a2c6e8f4b1d7"
down_revision = "e7a3c1d9b5f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("suppliers", sa.Column("contacts", sa.JSON(), nullable=True))
    op.execute("UPDATE suppliers SET contacts = JSON_ARRAY()" if op.get_bind().dialect.name == "mysql"
               else "UPDATE suppliers SET contacts = '[]'")
    op.alter_column("suppliers", "contacts", existing_type=sa.JSON(), nullable=False)


def downgrade():
    op.drop_column("suppliers", "contacts")
