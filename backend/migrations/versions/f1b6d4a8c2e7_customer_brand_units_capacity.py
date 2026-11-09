"""customer file revision 2 -- brand name, whole-number TON/KG amounts, yearly-only production, derived capacity.

* brand_name            : new, individual customers only (نام شرکت یا برند)
* produced_products     : amount -> whole number, unit -> TON|KG (default TON), `period` removed.
                          A MONTHLY amount is multiplied by 12 so every produced amount is yearly.
* consumed_products     : monthly/annual consumption -> whole numbers, unit -> TON|KG (default TON)
* production_capacity   : free text -> FLOAT tons/year, recomputed from produced_products
                          (the old free-text values are discarded)

Revision ID: f1b6d4a8c2e7
Revises: e8a4c2d6b9f3
Create Date: 2026-10-25 12:00:00
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "f1b6d4a8c2e7"
down_revision = "e8a4c2d6b9f3"
branch_labels = None
depends_on = None


def _rows(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return value if isinstance(value, list) else []


def _unit(value):
    text = str(value or "").strip().lower()
    return "KG" if text in ("kg", "kgs") or "کیلو" in text else "TON"


def _whole(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def upgrade():
    op.add_column("customers", sa.Column("brand_name", sa.String(255), nullable=True))
    op.drop_column("customers", "production_capacity")
    op.add_column("customers", sa.Column("production_capacity", sa.Float(), nullable=True))

    bind = op.get_bind()
    customers = sa.table(
        "customers",
        sa.column("id", sa.BigInteger), sa.column("produced_products", sa.JSON),
        sa.column("consumed_products", sa.JSON), sa.column("production_capacity", sa.Float),
    )
    for cid, produced, consumed in list(bind.execute(
        sa.select(customers.c.id, customers.c.produced_products, customers.c.consumed_products)
    )):
        new_produced, total_kg, any_amount = [], 0, False
        for p in _rows(produced):
            amount = _whole(p.get("amount"))
            if amount is not None and p.get("period") == "MONTHLY":
                amount *= 12
            unit = _unit(p.get("unit"))
            if amount is not None:
                any_amount = True
                total_kg += amount if unit == "KG" else amount * 1000
            new_produced.append({"name": p.get("name"), "amount": amount, "unit": unit})
        new_consumed = []
        for p in _rows(consumed):
            new_consumed.append({
                **{k: v for k, v in p.items() if k not in ("monthly_consumption", "annual_consumption", "unit")},
                "monthly_consumption": _whole(p.get("monthly_consumption")) or 0,
                "annual_consumption": _whole(p.get("annual_consumption")) or 0,
                "unit": _unit(p.get("unit")),
            })
        bind.execute(customers.update().where(customers.c.id == cid).values(
            produced_products=new_produced, consumed_products=new_consumed,
            production_capacity=round(total_kg / 1000, 3) if any_amount else None,
        ))


def downgrade():
    # Amounts stay whole numbers with the TON/KG unit; the yearly period is restored for produced items.
    bind = op.get_bind()
    customers = sa.table("customers", sa.column("id", sa.BigInteger), sa.column("produced_products", sa.JSON))
    for cid, produced in list(bind.execute(sa.select(customers.c.id, customers.c.produced_products))):
        rows = [{**p, "period": "YEARLY" if p.get("amount") is not None else None} for p in _rows(produced)]
        bind.execute(customers.update().where(customers.c.id == cid).values(produced_products=rows))
    op.drop_column("customers", "production_capacity")
    op.add_column("customers", sa.Column("production_capacity", sa.String(100), nullable=True))
    op.drop_column("customers", "brand_name")