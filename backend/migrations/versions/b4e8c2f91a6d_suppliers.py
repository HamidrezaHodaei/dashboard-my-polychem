"""suppliers table -- Procurement module

Revision ID: b4e8c2f91a6d
Revises: a1d4e9f27c38
Create Date: 2026-10-15 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'b4e8c2f91a6d'
down_revision = 'a1d4e9f27c38'
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
JSON_TYPE = sa.JSON().with_variant(mysql.JSON(), "mysql")


def upgrade():
    op.create_table(
        "suppliers",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("supplier_type", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="SEMI_ACTIVE"),
        sa.Column("quality", sa.String(length=10), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("national_id", sa.String(length=10), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("company_national_id", sa.String(length=11), nullable=True),
        sa.Column("registration_number", sa.String(length=50), nullable=True),
        sa.Column("company_type", sa.String(length=50), nullable=True),
        sa.Column("established_date", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("activity_type", sa.String(length=255), nullable=True),
        sa.Column("capacity", sa.String(length=100), nullable=True),
        sa.Column("experience", sa.String(length=50), nullable=True),
        sa.Column("phones", JSON_TYPE, nullable=False),
        sa.Column("products", JSON_TYPE, nullable=False),
        sa.Column("catalog_files", JSON_TYPE, nullable=False),
        sa.Column("is_public_submission", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_suppliers_category", "suppliers", ["category"])


def downgrade():
    op.drop_index("ix_suppliers_category", table_name="suppliers")
    op.drop_table("suppliers")
