"""purchase reports: expert review status (cartable) + direct purchases

* purchase_requests: review_status (default PENDING_REVIEW for every existing row), review_note, reviewed_at, reviewed_by_name.
  Request numbers are typed by the expert from now on; existing numbers are kept and become editable.
* purchase_direct: direct purchases recorded without a request / quotations.

Revision ID: e6a1c4d8f2b3
Revises: d5f9b3a7c1e2
Create Date: 2026-11-18 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "e6a1c4d8f2b3"
down_revision = "d5f9b3a7c1e2"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    with op.batch_alter_table("purchase_requests") as b:
        b.add_column(sa.Column("review_status", sa.String(length=20), nullable=False, server_default="PENDING_REVIEW"))
        b.add_column(sa.Column("review_note", sa.String(length=1000), nullable=True))
        b.add_column(sa.Column("reviewed_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("reviewed_by_name", sa.String(length=200), nullable=True))
        b.create_index("ix_purchase_requests_review", ["review_status"])

    op.create_table(
        "purchase_direct",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("doc_no", sa.String(length=50), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", BIG, sa.ForeignKey("supplier_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_name", sa.String(length=100), nullable=True),
        sa.Column("supplier_id", BIG, sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("usage_place", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("creator_name", sa.String(length=200), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("doc_no", name="uq_purchase_direct_doc_no"),
    )
    op.create_index("ix_purchase_direct_date", "purchase_direct", ["purchase_date"])
    op.create_index("ix_purchase_direct_supplier", "purchase_direct", ["supplier_id"])


def downgrade():
    op.drop_index("ix_purchase_direct_supplier", table_name="purchase_direct")
    op.drop_index("ix_purchase_direct_date", table_name="purchase_direct")
    op.drop_table("purchase_direct")
    with op.batch_alter_table("purchase_requests") as b:
        b.drop_index("ix_purchase_requests_review")
        for c in ("reviewed_by_name", "reviewed_at", "review_note", "review_status"):
            b.drop_column(c)
