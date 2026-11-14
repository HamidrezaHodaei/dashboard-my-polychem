"""request samples: customer receipt (delivered_at / received_by / note)

Revision ID: a1c5e9d3b7f2
Revises: f1b3d5e7a9c2
Create Date: 2026-11-12 15:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "a1c5e9d3b7f2"
down_revision = "f1b3d5e7a9c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("request_samples", sa.Column("delivered_at", sa.Date(), nullable=True))
    op.add_column("request_samples", sa.Column("delivery_received_by", sa.String(200), nullable=True))
    op.add_column("request_samples", sa.Column("delivery_note", sa.Text(), nullable=True))
    # requests already past the dispatch step are treated as delivered (they were «AWAITING_FEEDBACK» before)
    op.execute("UPDATE request_samples SET delivered_at = DATE(first_dispatched_at) "
               "WHERE status = 'AWAITING_FEEDBACK' AND delivered_at IS NULL AND first_dispatched_at IS NOT NULL")


def downgrade() -> None:
    op.drop_column("request_samples", "delivery_note")
    op.drop_column("request_samples", "delivery_received_by")
    op.drop_column("request_samples", "delivered_at")
