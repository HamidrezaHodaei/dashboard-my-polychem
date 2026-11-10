"""customers: company phone, units per production line, separate produced / consumed product lists

* customers.company_phone                (legal customers' own number)
* customers.production_line_counts       (JSON list parallel to production_line_names)
* customer_option_items: kinds PRODUCED / CONSUMED. The old shared PRODUCT list is COPIED into both
  new lists, so nothing disappears; from now on each list is managed on its own.

Revision ID: e3a5c7b9d1f2
Revises: d2f4b6a8c0e1
Create Date: 2026-11-09 15:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "e3a5c7b9d1f2"
down_revision = "d2f4b6a8c0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("company_phone", sa.String(length=30), nullable=True))
    op.add_column("customers", sa.Column("production_line_counts", sa.JSON(), nullable=True))
    # existing lines: one unit each, so the total (sum) equals the old count of names
    op.execute("UPDATE customers SET production_line_counts = NULL")
    for new_kind in ("PRODUCED", "CONSUMED"):
        op.execute(
            "INSERT INTO customer_option_items (kind, name, is_active, sort_order, created_at, updated_at) "
            f"SELECT '{new_kind}', name, is_active, sort_order, created_at, updated_at "
            "FROM customer_option_items WHERE kind = 'PRODUCT' "
            f"AND name NOT IN (SELECT name FROM (SELECT name FROM customer_option_items WHERE kind = '{new_kind}') AS x)"
        )


def downgrade():
    op.execute("DELETE FROM customer_option_items WHERE kind IN ('PRODUCED', 'CONSUMED')")
    op.drop_column("customers", "production_line_counts")
    op.drop_column("customers", "company_phone")
