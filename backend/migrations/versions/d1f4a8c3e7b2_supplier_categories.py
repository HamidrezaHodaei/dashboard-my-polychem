"""supplier_categories -- admin-managed category list

Seeds the list with the public form's previous hard-coded options plus any
category already used by an existing supplier, so nothing disappears.

Revision ID: d1f4a8c3e7b2
Revises: c9d2e7a4b1f5
Create Date: 2026-10-16 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "d1f4a8c3e7b2"
down_revision = "c9d2e7a4b1f5"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")

DEFAULTS = [
    "پلیمر و رزین",
    "رنگدانه و رنگ‌دهنده",
    "افزودنی و پرکننده",
    "بسته‌بندی",
    "ماشین‌آلات و قطعات یدکی",
    "حمل و نقل و لجستیک",
    "خدمات آزمایشگاهی و تست",
    "سایر",
]


def upgrade():
    table = op.create_table(
        "supplier_categories",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_supplier_categories_name"),
    )

    bind = op.get_bind()
    names = list(DEFAULTS)
    used = bind.execute(
        sa.text("SELECT DISTINCT category FROM suppliers WHERE category IS NOT NULL AND category <> ''")
    ).fetchall()
    for (name,) in used:
        if name not in names:
            names.append(name)

    now = datetime.utcnow()
    op.bulk_insert(
        table,
        [
            {"name": n, "sort_order": i + 1, "is_active": True, "created_at": now, "updated_at": now}
            for i, n in enumerate(names)
        ],
    )


def downgrade():
    op.drop_table("supplier_categories")
