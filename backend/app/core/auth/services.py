"""
Authentication business logic -- Master Context layering (Route ->
Schema -> Service -> Repository -> Model): all of it lives here, not in
routes.py, per the approved Phase 3 decisions ("Services should contain:
password verification, login logic, token creation, refresh rotation,
revocation, reuse detection, audit events").

Design decisions worth surfacing to a reviewer:

- Passwords use Argon2 (argon2-cffi) per SECURITY.md §1's stated
  preference.
- Refresh tokens are OPAQUE, cryptographically random strings
  (`secrets.token_urlsafe`) -- not JWTs. Only a hash is ever persisted,
  in the existing `refresh_tokens.token_hash` column. They are hashed
  with SHA-256, not Argon2: Argon2 (and other deliberately slow KDFs)
  exist to resist brute-forcing a *low-entropy* human-chosen secret
  (a password); a 512-bit `secrets.token_urlsafe(64)` value has no such
  weakness, so a fast, deterministic hash is both sufficient and
  appropriate for a high-frequency lookup path (every refresh call does
  one). This is a considered choice, not a shortcut.
- `authenticate()` always calls `verify_password()` against something --
  a dummy pre-computed hash when no matching user exists -- specifically
  so a request for an unknown identifier takes the same shape of work
  as one for a real user with a wrong password, per "no user
  enumeration."
"""
import base64
import binascii
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from flask import current_app
from flask_jwt_extended import create_access_token

from app.core.audit_logs.models import AuditLog
from app.core.auth.exceptions import AuthenticationFailed
from app.core.auth.models import RefreshToken, UserSession
from app.core.auth.useragent import clean_user_agent, parse_user_agent
from app.core.users.models import User
from app.extensions import db
from app.utils.exceptions import ConflictError

_password_hasher = PasswordHasher()

# Computed once at import time so `authenticate()` can always run a real
# Argon2 verification, even when no user matches the given identifier --
# see module docstring ("no user enumeration").
_DUMMY_PASSWORD_HASH = _password_hasher.hash("dummy-password-for-timing-safety")

_GENERIC_LOGIN_ERROR = "Invalid credentials."
_GENERIC_REFRESH_ERROR = "Invalid refresh token."


# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Never store the return value anywhere but `users.password_hash`;
    never log `plain_password`."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False


# ---------------------------------------------------------------------
# Refresh token helpers
# ---------------------------------------------------------------------


def _as_aware_utc(value: datetime) -> datetime:
    """
    `RefreshToken.expires_at`/`issued_at`/`revoked_at` are plain
    `DateTime` columns (no `timezone=True`) -- like every other
    timestamp in this schema (see app/core/base.py's `_utcnow`). Both
    SQLite and MySQL round-trip a value written as timezone-aware back
    as a *naive* datetime once it's been persisted and reloaded in a
    later request/session. Comparing that naive value directly against
    `datetime.now(timezone.utc)` would raise `TypeError` (or silently
    compare wrong if it didn't). Since every datetime this codebase ever
    writes is already UTC, a naive value read back is always safe to
    reinterpret as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _generate_raw_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def _issue_refresh_token(user: User, session_id: int | None = None) -> tuple[RefreshToken, str]:
    raw_token = _generate_raw_refresh_token()
    lifetime_days = current_app.config["REFRESH_TOKEN_EXPIRES_DAYS"]
    now = datetime.now(timezone.utc)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        issued_at=now,
        expires_at=now + timedelta(days=lifetime_days),
        session_id=session_id,
    )
    db.session.add(row)
    db.session.flush()  # assign row.id before it's referenced elsewhere
    return row, raw_token


def _issue_access_token(user: User) -> str:
    # Deliberately identity-only: sub/iat/exp/jti/type=access are all
    # Flask-JWT-Extended's own defaults for create_access_token(). No
    # roles/permissions/scopes/org placement/PII are added -- Phase 2's
    # engine re-resolves those fresh from the DB on every request (see
    # app/core/auth/decorators.py and app/permissions/service.py), so
    # nothing authorization-relevant is ever baked into the token.
    return create_access_token(identity=str(user.id))


def _revoke_all_active_tokens_for_user(user_id: int, *, now: datetime, reason: str = "revoked") -> int:
    active_tokens = (
        db.session.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for token in active_tokens:
        token.revoked_at = now
    _end_open_sessions(user_id, now=now, reason=reason)
    return len(active_tokens)


# ---------------------------------------------------------------------
# Sessions (the per-user activity page reads these)
# ---------------------------------------------------------------------


def _client_meta(user_agent: str | None) -> dict:
    """What the server really knows about the client: the (truncated) UA string + parsed labels."""
    ua = clean_user_agent(user_agent)
    return {"user_agent": ua, **parse_user_agent(ua)}


def _start_session(user: User, *, ip_address: str | None, user_agent: str | None, now: datetime) -> UserSession:
    meta = _client_meta(user_agent)
    session = UserSession(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=meta["user_agent"],
        device_type=meta["device_type"],
        os=meta["os"],
        browser=meta["browser"],
        login_at=now,
        last_seen_at=now,
    )
    db.session.add(session)
    db.session.flush()
    return session


def _end_open_sessions(user_id: int, *, now: datetime, reason: str) -> None:
    for session in (
        db.session.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.logout_at.is_(None))
        .all()
    ):
        session.logout_at = now
        session.logout_reason = reason


def _touch_session(session_id: int | None, *, now: datetime) -> None:
    if session_id is None:
        return
    session = db.session.get(UserSession, session_id)
    if session is not None and session.logout_at is None:
        session.last_seen_at = now


# ---------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------


def _write_audit_event(
    *, user_id: int | None, action: str, ip_address: str | None, metadata: dict | None = None
) -> None:
    # Never pass password/hash/token material as `metadata` -- callers in
    # this module never do; this function does not defend against that
    # itself since it has no way to tell a safe dict from an unsafe one.
    db.session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            module="auth",
            event_metadata=metadata,
            ip_address=ip_address,
        )
    )


# ---------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------


def _find_user_by_identifier(identifier: str) -> User | None:
    """The login identifier is a username OR an e-mail. Both columns are unique, but ONE user's username
    can equal ANOTHER user's e-mail (or the DB collation is case-insensitive), so the lookup may match
    two rows. That must never be a 500: the identifier's shape decides which column wins (contains "@"
    -> e-mail first, otherwise username first), then the oldest row, so the result is deterministic."""
    rows = (
        db.session.query(User)
        .filter(
            (User.username == identifier) | (User.email == identifier),
            User.deleted_at.is_(None),
        )
        .order_by(User.id)
        .all()
    )
    if len(rows) <= 1:
        return rows[0] if rows else None
    by_email = "@" in identifier
    exact = [u for u in rows if (u.email == identifier if by_email else u.username == identifier)]
    # prefer a case-exact match of the preferred column, then the other column, then the oldest user
    for group in (exact, [u for u in rows if u.username == identifier or u.email == identifier]):
        if group:
            return group[0]
    return rows[0]


def authenticate(
    identifier: str, password: str, *, ip_address: str | None = None, user_agent: str | None = None
) -> tuple[User, str, str]:
    """
    Returns (user, access_token, raw_refresh_token) on success.

    Raises AuthenticationFailed with the SAME generic message for every
    failure path (unknown identifier, wrong password, inactive user,
    soft-deleted user) -- callers must not vary the message by case.
    """
    user = _find_user_by_identifier(identifier)

    if user is not None:
        password_ok = verify_password(password, user.password_hash)
    else:
        # Burn equivalent Argon2 work even when there's no user to check
        # against, so response timing doesn't signal "identifier exists."
        verify_password(password, _DUMMY_PASSWORD_HASH)
        password_ok = False

    account_ok = user is not None and user.is_active and user.deleted_at is None

    if not password_ok or not account_ok:
        _write_audit_event(
            user_id=user.id if user is not None else None,
            action="login_failure",
            ip_address=ip_address,
            metadata=_client_meta(user_agent),
        )
        db.session.commit()
        raise AuthenticationFailed(_GENERIC_LOGIN_ERROR)

    now = datetime.now(timezone.utc)
    user.last_login_at = now
    session = _start_session(user, ip_address=ip_address, user_agent=user_agent, now=now)
    access_token = _issue_access_token(user)
    _refresh_row, raw_refresh_token = _issue_refresh_token(user, session.id)
    _write_audit_event(
        user_id=user.id, action="login_success", ip_address=ip_address,
        metadata={**_client_meta(user_agent), "session_id": session.id},
    )
    db.session.commit()
    return user, access_token, raw_refresh_token


# ---------------------------------------------------------------------
# Refresh (rotation + reuse detection)
# ---------------------------------------------------------------------


def refresh(
    raw_refresh_token: str | None, *, ip_address: str | None = None, user_agent: str | None = None
) -> tuple[User, str, str | None]:
    """
    Validate and rotate a refresh token. Returns
    (user, new_access_token, new_raw_refresh_token) on success.

    Raises AuthenticationFailed (same generic message every time) for:
    missing/unknown/expired token, inactive/soft-deleted user. On reuse
    of an already-revoked (already-rotated) token, additionally revokes
    every other currently-active refresh token for that user
    (chain-wide revocation) before raising -- no new access token is
    ever issued on this path.
    """
    if not raw_refresh_token:
        raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

    token_hash = _hash_token(raw_refresh_token)
    row = db.session.query(RefreshToken).filter_by(token_hash=token_hash).one_or_none()

    if row is None:
        raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

    now = datetime.now(timezone.utc)

    if row.revoked_at is not None:
        # Benign race: the token was ROTATED (replaced_by_token_id set -- logout leaves it empty)
        # moments ago, e.g. a page reload or second tab replayed the old cookie before the new one
        # was stored. Hand out an access token only; the browser already holds the newer cookie.
        grace = current_app.config.get("REFRESH_REUSE_GRACE_SECONDS", 0)
        if (
            grace > 0
            and row.replaced_by_token_id is not None
            and (now - _as_aware_utc(row.revoked_at)).total_seconds() <= grace
        ):
            user = db.session.get(User, row.user_id)
            if user is not None and user.is_active and user.deleted_at is None:
                access_token = _issue_access_token(user)
                _touch_session(row.session_id, now=now)
                _write_audit_event(
                    user_id=user.id, action="refresh_success", ip_address=ip_address,
                    metadata={"reason": "rotation_grace", "session_id": row.session_id},
                )
                db.session.commit()
                return user, access_token, None
            raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

        # Reuse of a token that was already rotated/revoked -- treat as
        # a theft signal (SECURITY.md §1) and revoke the whole chain.
        revoked_count = _revoke_all_active_tokens_for_user(row.user_id, now=now, reason="token_reuse")
        _write_audit_event(
            user_id=row.user_id, action="refresh_reuse_detected", ip_address=ip_address
        )
        _write_audit_event(
            user_id=row.user_id,
            action="refresh_revoked",
            ip_address=ip_address,
            metadata={"reason": "reuse_detected", "revoked_count": revoked_count},
        )
        db.session.commit()
        raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

    if _as_aware_utc(row.expires_at) <= now:
        raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

    user = db.session.get(User, row.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

    new_row, new_raw_token = _issue_refresh_token(user, row.session_id)
    row.revoked_at = now
    row.replaced_by_token_id = new_row.id
    _touch_session(row.session_id, now=now)

    access_token = _issue_access_token(user)
    _write_audit_event(
        user_id=user.id, action="refresh_success", ip_address=ip_address,
        metadata={"session_id": row.session_id} if row.session_id else None,
    )
    db.session.commit()
    return user, access_token, new_raw_token


# ---------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------


def logout(raw_refresh_token: str | None, *, ip_address: str | None = None, user_agent: str | None = None) -> None:
    """
    Revoke the current refresh token if a valid, not-already-revoked row
    is found. Always succeeds from the caller's perspective -- safe to
    call repeatedly, with a missing cookie, or with an already-revoked/
    unknown token -- and never reveals which case occurred.
    """
    if raw_refresh_token:
        token_hash = _hash_token(raw_refresh_token)
        row = db.session.query(RefreshToken).filter_by(token_hash=token_hash).one_or_none()
        if row is not None and row.revoked_at is None:
            now = datetime.now(timezone.utc)
            row.revoked_at = now
            if row.session_id is not None:
                session = db.session.get(UserSession, row.session_id)
                if session is not None and session.logout_at is None:
                    session.logout_at = now
                    session.logout_reason = "logout"
            _write_audit_event(
                user_id=row.user_id, action="logout", ip_address=ip_address,
                metadata={**_client_meta(user_agent), **({"session_id": row.session_id} if row.session_id else {})},
            )
    db.session.commit()


# ---------------------------------------------------------------------
# Profile photo (the user's OWN avatar)
# ---------------------------------------------------------------------

_AVATAR_DATA_URL = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=\s]+)$")
_AVATAR_MAX_BYTES = 300_000  # the client sends ~256px JPEGs (a few tens of KB); this is a generous ceiling


def _looks_like_image(kind: str, raw: bytes) -> bool:
    """Check the real file signature, so a mislabeled data URL (text, SVG, HTML...) is never stored."""
    if kind == "png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if kind == "jpeg":
        return raw.startswith(b"\xff\xd8\xff")
    if kind == "webp":
        return raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    return False


def set_avatar(user: User, image: str | None, *, ip_address: str | None = None) -> User:
    """Set (data URL) or clear (None) the user's own profile photo. Only png/jpeg/webp are accepted."""
    if image is None:
        user.avatar_data = None
    else:
        match = _AVATAR_DATA_URL.match(image.strip())
        if match is None:
            raise ConflictError("Only PNG, JPEG or WebP images are accepted.")
        kind, b64 = match.group(1), re.sub(r"\s+", "", match.group(2))
        try:
            raw = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ConflictError("The image is not valid base64 data.") from exc
        if len(raw) > _AVATAR_MAX_BYTES:
            raise ConflictError("The image is too large.")
        if not _looks_like_image(kind, raw):
            raise ConflictError("The file content does not match an image of that type.")
        user.avatar_data = f"data:image/{kind};base64,{b64}"
    _write_audit_event(
        user_id=user.id,
        action="avatar_removed" if image is None else "avatar_changed",
        ip_address=ip_address,
    )
    db.session.commit()
    return user
