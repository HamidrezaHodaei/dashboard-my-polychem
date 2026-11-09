"""
AuditLog model — SECURITY.md §7: "Every authentication event ... and every
mutating business action writes to audit_logs ... stores user_id, action,
module, entity_type/entity_id, a metadata JSON diff where relevant,
ip_address, and created_at."

Append-only by convention: no update/delete path is exposed via the API
(none exists yet in Phase 1 anyway — no HTTP routes in this phase). No
`updated_at`/`deleted_at` on this table on purpose — an audit record is
never edited or soft-deleted once written.

`user_id` is nullable to allow future system-initiated events (e.g. a
scheduled job) that have no acting user — not exercised by anything yet
in Phase 1.
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import _utcnow, BigIntUnsigned


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    # DB column is literally "metadata" per SECURITY.md §7; the Python
    # attribute is renamed to `event_metadata` because `metadata` is
    # reserved by SQLAlchemy's declarative machinery (Base.metadata).
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog id={self.id} action={self.action!r} module={self.module!r}>"
