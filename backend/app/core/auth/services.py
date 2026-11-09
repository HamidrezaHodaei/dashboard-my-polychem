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
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from flask import current_app
from flask_jwt_extended import create_access_token

from app.core.audit_logs.models import AuditLog
from app.core.auth.exceptions import AuthenticationFailed
from app.core.auth.models import RefreshToken
from app.core.users.models import User
from app.extensions import db

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


def _issue_refresh_token(user: User) -> tuple[RefreshToken, str]:
    raw_token = _generate_raw_refresh_token()
    lifetime_days = current_app.config["REFRESH_TOKEN_EXPIRES_DAYS"]
    now = datetime.now(timezone.utc)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        issued_at=now,
        expires_at=now + timedelta(days=lifetime_days),
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


def _revoke_all_active_tokens_for_user(user_id: int, *, now: datetime) -> int:
    active_tokens = (
        db.session.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for token in active_tokens:
        token.revoked_at = now
    return len(active_tokens)


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
    return (
        db.session.query(User)
        .filter(
            (User.username == identifier) | (User.email == identifier),
            User.deleted_at.is_(None),
        )
        .one_or_none()
    )


def authenticate(
    identifier: str, password: str, *, ip_address: str | None = None
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
        )
        db.session.commit()
        raise AuthenticationFailed(_GENERIC_LOGIN_ERROR)

    user.last_login_at = datetime.now(timezone.utc)
    access_token = _issue_access_token(user)
    _refresh_row, raw_refresh_token = _issue_refresh_token(user)
    _write_audit_event(user_id=user.id, action="login_success", ip_address=ip_address)
    db.session.commit()
    return user, access_token, raw_refresh_token


# ---------------------------------------------------------------------
# Refresh (rotation + reuse detection)
# ---------------------------------------------------------------------


def refresh(raw_refresh_token: str | None, *, ip_address: str | None = None) -> tuple[User, str, str | None]:
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
                _write_audit_event(
                    user_id=user.id, action="refresh_success", ip_address=ip_address,
                    metadata={"reason": "rotation_grace"},
                )
                db.session.commit()
                return user, access_token, None
            raise AuthenticationFailed(_GENERIC_REFRESH_ERROR)

        # Reuse of a token that was already rotated/revoked -- treat as
        # a theft signal (SECURITY.md §1) and revoke the whole chain.
        revoked_count = _revoke_all_active_tokens_for_user(row.user_id, now=now)
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

    new_row, new_raw_token = _issue_refresh_token(user)
    row.revoked_at = now
    row.replaced_by_token_id = new_row.id

    access_token = _issue_access_token(user)
    _write_audit_event(user_id=user.id, action="refresh_success", ip_address=ip_address)
    db.session.commit()
    return user, access_token, new_raw_token


# ---------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------


def logout(raw_refresh_token: str | None, *, ip_address: str | None = None) -> None:
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
            row.revoked_at = datetime.now(timezone.utc)
            _write_audit_event(user_id=row.user_id, action="logout", ip_address=ip_address)
    db.session.commit()
