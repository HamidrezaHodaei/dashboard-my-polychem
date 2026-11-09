"""suppliers.bank_accounts -- optional list of bank accounts (holder, bank, card, account, sheba)

Revision ID: d4b8f2a6c1e9
Revises: a7c3e9d1f5b2
Create Date: 2026-10-31 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "d4b8f2a6c1e9"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("suppliers", sa.Column("bank_accounts", sa.JSON(), nullable=True))
    op.execute("UPDATE suppliers SET bank_accounts = JSON_ARRAY()" if op.get_bind().dialect.name == "mysql"
               else "UPDATE suppliers SET bank_accounts = '[]'")
    op.alter_column("suppliers", "bank_accounts", existing_type=sa.JSON(), nullable=False)


def downgrade():
    op.drop_column("suppliers", "bank_accounts")
