"""department worklist pictures (logo + header) and the «فروش» -> «بازاریابی و فروش» rename

Revision ID: b2d4f6a8c0e3
Revises: a1c5e9d3b7f2
"""
import sqlalchemy as sa
from alembic import op

revision = "b2d4f6a8c0e3"
down_revision = "a1c5e9d3b7f2"
branch_labels = None
depends_on = None

OLD_NAME = "فروش"
NEW_NAME = "بازاریابی و فروش"


def upgrade() -> None:
    op.add_column("departments", sa.Column("logo_file", sa.String(64), nullable=True))
    op.add_column("departments", sa.Column("logo_content_type", sa.String(50), nullable=True))
    op.add_column("departments", sa.Column("header_file", sa.String(64), nullable=True))
    op.add_column("departments", sa.Column("header_content_type", sa.String(50), nullable=True))
    op.add_column("departments", sa.Column("branding_version", sa.Integer(), nullable=False, server_default="0"))

    # One organizational unit title everywhere: the existing department row is renamed in place
    # (same id, so tasks / users / grants that point at it are untouched).
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE departments SET name = :new WHERE name = :old"),
        {"new": NEW_NAME, "old": OLD_NAME},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE departments SET name = :old WHERE name = :new"),
        {"new": NEW_NAME, "old": OLD_NAME},
    )
    op.drop_column("departments", "branding_version")
    op.drop_column("departments", "header_content_type")
    op.drop_column("departments", "header_file")
    op.drop_column("departments", "logo_content_type")
    op.drop_column("departments", "logo_file")
