"""In-app notifications (the bell in the header)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BigIntUnsigned, TimestampMixin
from app.extensions import db


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_id", "user_id", "read_at", "id"),
        # one notification per (user, dedupe_key): a deadline warning for the same task and
        # due date is created once, however many times the list is polled
        UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
