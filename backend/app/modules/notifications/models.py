"""In-app notifications (the bell in the header)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BigIntUnsigned, TimestampMixin
from app.extensions import db


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_id", "user_id", "read_at", "id"),
        Index("ix_notifications_user_type", "user_id", "type"),
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


# ── Web Push ──────────────────────────────────────────────────────────────────────────────────
class PushSubscription(TimestampMixin, db.Model):
    """One browser/device of one user. The endpoint is unique across users: a shared computer that signs in as
    somebody else re-binds the same endpoint to the new user instead of leaving it with the old one."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_push_subscriptions_endpoint"),
        Index("ix_push_subscriptions_user_active", "user_id", "disabled_at"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 of the endpoint
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)


class PushDelivery(TimestampMixin, db.Model):
    """Outbox row: one notification x one device. The unique pair is what makes a notification reach a
    device at most once however many times the dispatcher runs; PENDING rows are retried by the cron."""

    __tablename__ = "push_deliveries"
    __table_args__ = (
        UniqueConstraint("notification_id", "subscription_id", name="uq_push_deliveries_pair"),
        Index("ix_push_deliveries_due", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING")  # PENDING SENT FAILED EXPIRED SKIPPED
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NotificationSetting(TimestampMixin, db.Model):
    """Per-user push settings (one row, created on first save; defaults apply until then)."""

    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # false: lock screen shows no text
    quiet_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_start: Mapped[str] = mapped_column(String(5), nullable=False, default="22:00")  # Tehran time, HH:MM
    quiet_end: Mapped[str] = mapped_column(String(5), nullable=False, default="07:00")


class NotificationPreference(TimestampMixin, db.Model):
    """A category the user switched OFF for push (absent row = on). The in-app bell is never filtered."""

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_notification_preferences_user_category"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
