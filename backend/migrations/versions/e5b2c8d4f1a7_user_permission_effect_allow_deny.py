"""user_permission_scopes.effect (ALLOW / DENY) -- per-user permission matrix

Adds an explicit effect to direct user grants so an admin can *restrict*
a single user below what their roles grant (per-user DENY), not only add
to it. Existing rows become ALLOW (identical to the previous behaviour).

Revision ID: e5b2c8d4f1a7
Revises: c3a9e7f15b6d
Create Date: 2026-10-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b2c8d4f1a7'
down_revision = 'c3a9e7f15b6d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_permission_scopes",
        sa.Column(
            "effect",
            sa.Enum("ALLOW", "DENY", name="user_permission_scopes_effect"),
            nullable=False,
            server_default="ALLOW",
        ),
    )


def downgrade():
    op.drop_column("user_permission_scopes", "effect")
