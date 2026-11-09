"""CRM sales use the customer bank's product list (drop crm_products)

crm_sales.product_id used to point at a CRM-only `crm_products` table, so every product had to be
typed twice (once in the customer wizard's product pick-list, once in CRM). It now points straight
at `customer_option_items` (kind = 'PRODUCT') -- the single product list of the customer bank.

Data migration (idempotent, no sale is lost):
* every crm_products row is matched BY NAME (Persian/Arabic letter variants and spacing ignored) to
  an existing PRODUCT option item; when none exists, one is created from the CRM product;
* crm_sales.product_id is rewritten to the matching option item id;
* the foreign key is re-pointed and `crm_products` is dropped.

Downgrade recreates `crm_products` from the option items that sales use (codes are regenerated,
the original codes cannot be restored).

Revision ID: a4c8e2f6b1d3
Revises: d8ab5f4d9a39
Create Date: 2026-11-08 10:00:00
"""
import re
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "a4c8e2f6b1d3"
down_revision = "d8ab5f4d9a39"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_ZW = re.compile(r"[\u200c\u200f\u200e]")


def _norm(value):
    text = _ZW.sub(" ", (value or "").translate(_AR_TO_FA))
    return re.sub(r"\s+", " ", text).strip().lower()


def _fk_name(bind, table, column, referred):
    for fk in sa.inspect(bind).get_foreign_keys(table):
        if fk["constrained_columns"] == [column] and fk["referred_table"] == referred:
            return fk["name"]
    return None


def upgrade():
    bind = op.get_bind()
    now = datetime.utcnow()

    crm_products = sa.table("crm_products", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
    items = sa.table(
        "customer_option_items",
        sa.column("id", sa.BigInteger), sa.column("kind", sa.String), sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    sales = sa.table("crm_sales", sa.column("id", sa.BigInteger), sa.column("product_id", sa.BigInteger))

    # 1. crm_products -> option items (match by name, create when missing)
    existing = {
        _norm(r.name): r.id
        for r in bind.execute(sa.select(items.c.id, items.c.name).where(items.c.kind == "PRODUCT"))
    }
    next_order = (bind.execute(sa.select(sa.func.max(items.c.sort_order)).where(items.c.kind == "PRODUCT")).scalar() or 0)
    mapping = {}
    for row in bind.execute(sa.select(crm_products.c.id, crm_products.c.name).order_by(crm_products.c.id)):
        key = _norm(row.name)
        item_id = existing.get(key)
        if item_id is None:
            next_order += 1
            bind.execute(items.insert().values(
                kind="PRODUCT", name=(row.name or "").translate(_AR_TO_FA).strip()[:255] or f"محصول {row.id}",
                sort_order=next_order, is_active=True, created_at=now, updated_at=now,
            ))
            item_id = bind.execute(
                sa.select(items.c.id).where(items.c.kind == "PRODUCT", items.c.name == (row.name or "").translate(_AR_TO_FA).strip()[:255])
            ).scalar()
            existing[key] = item_id
        mapping[row.id] = item_id

    # 2. drop the old FK first (so ids can be rewritten freely), rewrite the sales
    fk = _fk_name(bind, "crm_sales", "product_id", "crm_products")
    if fk:
        op.drop_constraint(fk, "crm_sales", type_="foreignkey")
    if mapping:
        case = sa.case(*[(sales.c.product_id == o, n) for o, n in mapping.items()], else_=sales.c.product_id)
        bind.execute(sales.update().values(product_id=case))

    # 3. new FK + drop crm_products
    op.create_foreign_key(
        "fk_crm_sales_product_option", "crm_sales", "customer_option_items", ["product_id"], ["id"], ondelete="RESTRICT"
    )
    op.drop_table("crm_products")


def downgrade():
    bind = op.get_bind()
    now = datetime.utcnow()
    op.create_table(
        "crm_products",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_crm_products_code"),
    )
    op.create_index("ix_crm_products_name", "crm_products", ["name"])

    crm_products = sa.table(
        "crm_products", sa.column("id", sa.BigInteger), sa.column("name", sa.String), sa.column("code", sa.String),
        sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    items = sa.table("customer_option_items", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
    sales = sa.table("crm_sales", sa.column("product_id", sa.BigInteger))

    used = [r[0] for r in bind.execute(sa.select(sales.c.product_id).distinct())]
    mapping = {}
    for item_id in used:
        name = bind.execute(sa.select(items.c.name).where(items.c.id == item_id)).scalar() or f"محصول {item_id}"
        bind.execute(crm_products.insert().values(
            name=name[:150], code=f"P-{item_id}", is_active=True, created_at=now, updated_at=now,
        ))
        mapping[item_id] = bind.execute(sa.select(crm_products.c.id).where(crm_products.c.code == f"P-{item_id}")).scalar()

    fk = _fk_name(bind, "crm_sales", "product_id", "customer_option_items")
    if fk:
        op.drop_constraint(fk, "crm_sales", type_="foreignkey")
    if mapping:
        case = sa.case(*[(sales.c.product_id == o, n) for o, n in mapping.items()], else_=sales.c.product_id)
        bind.execute(sales.update().values(product_id=case))
    op.create_foreign_key(
        "fk_crm_sales_product", "crm_sales", "crm_products", ["product_id"], ["id"], ondelete="RESTRICT"
    )
