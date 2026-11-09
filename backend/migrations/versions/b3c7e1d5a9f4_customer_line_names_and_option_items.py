"""customer: production line names + admin-managed product / grade pick-lists

* customers.production_line_names : JSON list, one name per production line (nullable)
* customer_option_items           : admin-managed lists of product names (PRODUCT) and grade
                                    names (GRADE) for the customer wizard, seeded from the
                                    values customers already store.

Nothing in the supplier module is touched.

Revision ID: b3c7e1d5a9f4
Revises: a9d4f2c7e1b6
Create Date: 2026-10-29 10:00:00
"""
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "b3c7e1d5a9f4"
down_revision = "a9d4f2c7e1b6"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def _rows(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return value if isinstance(value, list) else []


def upgrade():
    op.add_column("customers", sa.Column("production_line_names", sa.JSON(), nullable=True))

    op.create_table(
        "customer_option_items",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("kind", "name", name="uq_customer_option_items_kind_name"),
    )
    op.create_index("ix_customer_option_items_kind", "customer_option_items", ["kind"])

    # Seed the lists with what customers already typed, so nothing they entered is lost.
    bind = op.get_bind()
    customers = sa.table(
        "customers",
        sa.column("produced_products", sa.JSON), sa.column("consumed_products", sa.JSON),
        sa.column("current_suppliers", sa.JSON), sa.column("deleted_at", sa.DateTime),
    )
    products: dict[str, None] = {}
    grades: dict[str, None] = {}
    for produced, consumed, suppliers in bind.execute(
        sa.select(customers.c.produced_products, customers.c.consumed_products, customers.c.current_suppliers)
    ):
        for p in _rows(produced) + _rows(consumed):
            if isinstance(p, dict) and (p.get("name") or "").strip():
                products[" ".join(p["name"].split())] = None
        for p in _rows(consumed):
            if isinstance(p, dict) and (p.get("grade_specs") or "").strip():
                grades[" ".join(p["grade_specs"].split())] = None
        for s in _rows(suppliers):
            for g in (s.get("grades") or []) if isinstance(s, dict) else []:
                if (g.get("product") or "").strip():
                    products[" ".join(g["product"].split())] = None
                if (g.get("grade") or "").strip():
                    grades[" ".join(g["grade"].split())] = None

    items = sa.table(
        "customer_option_items",
        sa.column("kind", sa.String), sa.column("name", sa.String), sa.column("sort_order", sa.Integer),
    )
    rows = [
        {"kind": kind, "name": name[:255], "sort_order": i}
        for kind, names in (("PRODUCT", products), ("GRADE", grades))
        for i, name in enumerate(sorted(names), start=1)
    ]
    if rows:
        op.bulk_insert(items, rows)


def downgrade():
    op.drop_index("ix_customer_option_items_kind", table_name="customer_option_items")
    op.drop_table("customer_option_items")
    op.drop_column("customers", "production_line_names")