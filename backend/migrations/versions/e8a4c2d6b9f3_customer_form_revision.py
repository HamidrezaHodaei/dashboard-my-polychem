"""customer file revision -- multiple industries, acquaintance source list, payment type + credit
duration, credit rating, supplier grades (JSON only), purchase method BOTH, expected price removed.

* industries            : JSON list of {category, subcategory}; back-filled from category/subcategory
                          (which stay as a mirror of the first industry)
* acquaintance_source   : free text -> fixed list. Existing free text becomes 'OTHER' + acquaintance_source_other
* payment_type / credit_months / credit_other : structured payment terms (payment_terms stays as a note)
* credit_rating         : وضعیت اعتباری مشتری
* expected_price_*      : dropped (data is discarded)

Revision ID: e8a4c2d6b9f3
Revises: d7f3b9a5e2c1
Create Date: 2026-10-23 16:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "e8a4c2d6b9f3"
down_revision = "d7f3b9a5e2c1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("industries", sa.JSON(), nullable=True))
    op.add_column("customers", sa.Column("acquaintance_source_other", sa.String(255), nullable=True))
    op.add_column("customers", sa.Column("payment_type", sa.String(12), nullable=True))
    op.add_column("customers", sa.Column("credit_months", sa.Integer(), nullable=True))
    op.add_column("customers", sa.Column("credit_other", sa.String(100), nullable=True))
    op.add_column("customers", sa.Column("credit_rating", sa.String(20), nullable=True))
    op.create_index("ix_customers_credit_rating", "customers", ["credit_rating"])

    bind = op.get_bind()
    customers = sa.table(
        "customers",
        sa.column("id", sa.BigInteger), sa.column("category", sa.String), sa.column("subcategory", sa.String),
        sa.column("industries", sa.JSON), sa.column("acquaintance_source", sa.String),
        sa.column("acquaintance_source_other", sa.String),
    )
    # industries <- the single category/subcategory
    for cid, category, subcategory in bind.execute(sa.select(customers.c.id, customers.c.category, customers.c.subcategory)):
        value = [{"category": category, "subcategory": subcategory}] if category else []
        bind.execute(customers.update().where(customers.c.id == cid).values(industries=value))
    # free-text source -> OTHER + text
    bind.execute(
        customers.update().where(customers.c.acquaintance_source.isnot(None))
        .values(acquaintance_source_other=customers.c.acquaintance_source, acquaintance_source="OTHER")
    )

    op.alter_column("customers", "industries", existing_type=sa.JSON(), nullable=False)
    op.alter_column("customers", "acquaintance_source", existing_type=sa.String(255), type_=sa.String(30),
                    existing_nullable=True)
    op.drop_column("customers", "expected_price_min")
    op.drop_column("customers", "expected_price_max")
    op.drop_column("customers", "expected_price_unit")


def downgrade():
    op.add_column("customers", sa.Column("expected_price_unit", sa.String(50), nullable=True))
    op.add_column("customers", sa.Column("expected_price_max", sa.Numeric(18, 2), nullable=True))
    op.add_column("customers", sa.Column("expected_price_min", sa.Numeric(18, 2), nullable=True))
    op.alter_column("customers", "acquaintance_source", existing_type=sa.String(30), type_=sa.String(255),
                    existing_nullable=True)
    op.drop_index("ix_customers_credit_rating", table_name="customers")
    for col in ("credit_rating", "credit_other", "credit_months", "payment_type", "acquaintance_source_other",
                "industries"):
        op.drop_column("customers", col)