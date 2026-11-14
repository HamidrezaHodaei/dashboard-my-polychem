"""
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/me

Per Master Context layering, this module only translates HTTP <->
app.core.auth.services -- no password/token/rotation logic lives here.
"""
import limits
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter

from flask import Blueprint, current_app, g, request

from app.core.auth import services
from app.core.auth.decorators import require_authenticated
from app.core.auth.schemas import LoginRequest, UserPublic
from app.core.roles.models import Role
from app.core.authorization.models import UserRole
from app.extensions import db
from app.permissions.navigation import resolve_navigation
from app.permissions.schemas import EffectivePermission, NavigationItem
from app.permissions.service import summarize_effective_permissions
from app.utils.responses import error_response, success_response

bp = Blueprint("auth", __name__, url_prefix="/api")


def _refresh_cookie_kwargs() -> dict:
    return dict(
        key=current_app.config["REFRESH_TOKEN_COOKIE_NAME"],
        httponly=current_app.config["REFRESH_TOKEN_COOKIE_HTTPONLY"],
        secure=current_app.config["REFRESH_TOKEN_COOKIE_SECURE"],
        samesite=current_app.config["REFRESH_TOKEN_COOKIE_SAMESITE"],
        path=current_app.config["REFRESH_TOKEN_COOKIE_PATH"],
    )


def _set_refresh_cookie(response, raw_refresh_token: str) -> None:
    max_age = current_app.config["REFRESH_TOKEN_EXPIRES_DAYS"] * 24 * 60 * 60
    response.set_cookie(value=raw_refresh_token, max_age=max_age, **_refresh_cookie_kwargs())


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(**_refresh_cookie_kwargs())


def _current_refresh_cookie() -> str | None:
    return request.cookies.get(current_app.config["REFRESH_TOKEN_COOKIE_NAME"])


def _get_login_rate_limiter() -> FixedWindowRateLimiter:
    """
    One counter per Flask app instance, stored on `current_app.extensions`
    -- deliberately NOT a module-level singleton. This codebase creates a
    fresh app per test (see app/__init__.py: "No global `app` object
    exists anywhere in this codebase"), so a process-wide counter would
    leak hit-counts between unrelated tests that happen to share this
    Python process.
    """
    if "login_rate_limiter" not in current_app.extensions:
        current_app.extensions["login_rate_limiter"] = FixedWindowRateLimiter(MemoryStorage())
    return current_app.extensions["login_rate_limiter"]


def _enforce_login_rate_limit():
    """
    Returns an error_response tuple if the configured login rate limit
    has been exceeded, else None.

    Deliberately NOT implemented via Flask-Limiter's own
    `@limiter.limit(...)` decorator: Flask-Limiter reads
    `RATELIMIT_ENABLED` exactly once, at `limiter.init_app()` time (i.e.
    inside `create_app()`), and caches it as an instance attribute that
    gates its entire before_request hook -- including any per-route
    `exempt_when`, which never even gets evaluated once that gate is
    closed. A config value changed on an already-created app (as our own
    dedicated rate-limit test does, and as any caller using the
    app-factory pattern after the fact might do) has no effect on
    already-initialized Flask-Limiter state, confirmed empirically: an
    `exempt_when` fix had zero effect. Checking `RATELIMIT_ENABLED`
    directly, ourselves, fresh on every request via `current_app.config`
    -- using the same underlying `limits` package/algorithm Flask-Limiter
    itself is built on -- is what actually makes this dynamic and
    config-driven, independent of when the app was created.
    """
    if not current_app.config.get("RATELIMIT_ENABLED", True):
        return None

    limit_item = limits.parse(current_app.config["LOGIN_RATE_LIMIT"])
    key = request.remote_addr or "unknown"
    if _get_login_rate_limiter().hit(limit_item, "login", key):
        return None

    return error_response(
        "RATE_LIMITED",
        f"Too many login attempts. Limit: {current_app.config['LOGIN_RATE_LIMIT']}.",
        429,
    )


@bp.post("/auth/login")
def login():
    rate_limited = _enforce_login_rate_limit()
    if rate_limited is not None:
        return rate_limited

    payload = LoginRequest.model_validate(request.get_json(silent=True) or {})
    user, access_token, raw_refresh_token = services.authenticate(
        payload.identifier, payload.password, ip_address=request.remote_addr
    )
    response, status_code = success_response(
        data={
            "access_token": access_token,
            "user": _public_user(user),
        }
    )
    _set_refresh_cookie(response, raw_refresh_token)
    return response, status_code


@bp.post("/auth/refresh")
def refresh():
    user, access_token, new_raw_refresh_token = services.refresh(
        _current_refresh_cookie(), ip_address=request.remote_addr
    )
    response, status_code = success_response(data={"access_token": access_token})
    if new_raw_refresh_token is not None:  # None = rotation-grace replay: keep the newer cookie
        _set_refresh_cookie(response, new_raw_refresh_token)
    return response, status_code


@bp.post("/auth/logout")
def logout():
    services.logout(_current_refresh_cookie(), ip_address=request.remote_addr)
    response, status_code = success_response(data={})
    _clear_refresh_cookie(response)
    return response, status_code


def _public_user(user) -> dict:
    """UserPublic + the user's active roles (the UI uses them to show admin-only controls)."""
    rows = (
        db.session.query(Role.name, Role.display_name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id, Role.is_active.is_(True), Role.deleted_at.is_(None))
        .order_by(Role.name).all()
    )
    data = UserPublic.model_validate(user).model_dump(mode="json")
    data["roles"] = [{"name": n, "display_name": d} for n, d in rows]
    data["is_admin"] = any(n == "admin" for n, _ in rows)
    return data


@bp.get("/me")
@require_authenticated
def me():
    return success_response(data=_public_user(g.current_user))


@bp.get("/me/permissions")
@require_authenticated
def me_permissions():
    summary = summarize_effective_permissions(g.current_user)
    permissions = [EffectivePermission(**item).model_dump() for item in summary]
    return success_response(data={"permissions": permissions})


@bp.get("/me/navigation")
@require_authenticated
def me_navigation():
    entries = resolve_navigation(g.current_user)
    navigation = [NavigationItem(**item).model_dump() for item in entries]
    return success_response(data={"navigation": navigation})
