"""
RefreshToken model — table shape only (Phase 1). Column shape follows
SECURITY.md §1 (refresh tokens stored server-side as a hash, rotation via
`replaced_by_token_id`, revocation via `revoked_at`).

DATABASE.md lists `refresh_tokens` as a "required Phase 1 table" but its
column-level shape is documented in SECURITY.md rather than DATABASE.md's
table listing (which marks it "unchanged" from an earlier revision not
included in this repo's docs) — this model is reconstructed from
SECURITY.md §1 accordingly, flagged here for reviewer visibility.

No token issuance, rotation, or revocation LOGIC is implemented here —
that is Phase 3 (Authentication).
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import _utcnow, BigIntUnsigned


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Never the raw token — only a hash, per SECURITY.md §1.
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # The login session this token belongs to. Every rotation of a token keeps the same
    # session_id, so one login = one session however many times the token is refreshed.
    # NULL on tokens issued before sessions were recorded.
    session_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True
    )
    # Rotation chain: the token that replaced this one, once rotated.
    replaced_by_token_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User")
    replaced_by: Mapped["RefreshToken | None"] = relationship(
        "RefreshToken", remote_side="RefreshToken.id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken id={self.id} user_id={self.user_id}>"


class UserSession(db.Model):
    """
    One row per successful login -- the "نشست" shown on the user's activity page.

    Only facts the server really observed are stored: the client IP (as the backend sees it),
    the User-Agent header and the three labels parsed from it. A column that could not be
    determined stays NULL -- the UI shows NULL as "ثبت نشده", it never invents a value.

    Lifecycle: created at login; `last_seen_at` moves forward on every token refresh;
    `logout_at` + `logout_reason` are set on logout ("logout"), on a refresh-token reuse
    revocation ("token_reuse") or when an admin/password change revokes it ("revoked").
    A session whose logout_at is NULL and whose newest refresh token is neither revoked nor
    expired is "active"; one that simply expired has no logout_at and is shown as "expired".
    """
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_login", "user_id", "login_at"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    os: Mapped[str | None] = mapped_column(String(40), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(40), nullable=True)
    login_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    logout_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserSession id={self.id} user_id={self.user_id}>"
