"""supplier sub-categories -- two-level category tree

* supplier_categories.parent_id (self FK): NULL = main category, else the
  sub-category's main category. Name uniqueness moves from "globally unique"
  to "unique per parent".
* suppliers.subcategory: the chosen sub-category name (nullable).

Existing rows stay valid: every current category becomes a main category.

Revision ID: b5d1f7a3c9e8
Revises: a2c6e8f4b1d7
Create Date: 2026-10-22 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "b5d1f7a3c9e8"
down_revision = "a2c6e8f4b1d7"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def upgrade():
    op.add_column("supplier_categories", sa.Column("parent_id", BIG, nullable=True))
    # Create the new unique index first: it also serves as the FK's index.
    op.create_unique_constraint(
        "uq_supplier_categories_parent_name", "supplier_categories", ["parent_id", "name"]
    )
    op.create_foreign_key(
        "fk_supplier_categories_parent", "supplier_categories", "supplier_categories",
        ["parent_id"], ["id"], ondelete="CASCADE",
    )
    op.drop_constraint("uq_supplier_categories_name", "supplier_categories", type_="unique")

    op.add_column("suppliers", sa.Column("subcategory", sa.String(length=100), nullable=True))
    op.create_index("ix_suppliers_category_subcategory", "suppliers", ["category", "subcategory"])


def downgrade():
    op.drop_index("ix_suppliers_category_subcategory", table_name="suppliers")
    op.drop_column("suppliers", "subcategory")

    # Sub-categories can't exist under the old globally-unique-name schema.
    op.execute("DELETE FROM supplier_categories WHERE parent_id IS NOT NULL")
    op.create_unique_constraint("uq_supplier_categories_name", "supplier_categories", ["name"])
    op.drop_constraint("fk_supplier_categories_parent", "supplier_categories", type_="foreignkey")
    op.drop_constraint("uq_supplier_categories_parent_name", "supplier_categories", type_="unique")
    op.drop_column("supplier_categories", "parent_id")