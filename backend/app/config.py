"""
Environment-based configuration for the PolyChem Automation System backend.

Phase 0 scope: only the settings needed to boot the app, connect to MySQL,
and run the health endpoint. Business/auth/RBAC settings are added in later
phases.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration. Shared defaults; subclasses override per-environment."""

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://USERNAME:PASSWORD@localhost:3306/polychem_automation",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # --- CORS ---
    # Comma-separated list of allowed origins. Never '*' — this API carries
    # authenticated requests in later phases.
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    # --- Rate limiting ---
    # In-memory storage is fine for local/dev; revisit for production later.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per minute")
    # Dedicated, stricter limit for POST /api/auth/login (SECURITY.md §2),
    # kept separate from the general platform-wide default above.
    LOGIN_RATE_LIMIT = os.environ.get("LOGIN_RATE_LIMIT", "5 per minute")

    # --- Authentication / JWT (Phase 3) ---
    # Access tokens only -- refresh tokens are opaque, server-side-hashed
    # random strings (SECURITY.md §1), never JWTs, so Flask-JWT-Extended's
    # own refresh-token machinery is not used.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-jwt-secret")
    # 12 hours by default so a working day never hits an expiry mid-task. Safe here because
    # nothing authorization-relevant lives in the token: permissions/roles are re-resolved from
    # the DB on every request and a deactivated user is rejected per request.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "720"))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Opaque refresh token lifetime (SECURITY.md §1 gives a 7-30 day
    # range; 14 is this project's chosen default within it).
    REFRESH_TOKEN_EXPIRES_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRES_DAYS", "14"))
    REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
    REFRESH_TOKEN_COOKIE_HTTPONLY = True
    REFRESH_TOKEN_COOKIE_SAMESITE = "Strict"
    # Scoped to /api/auth (login/refresh/logout) rather than the whole
    # site -- the cookie is never needed by any other route.
    # Must be a prefix of the URL path the BROWSER uses to call /auth/refresh. Production
    # (https://<api-host>/api/auth/...) matches the default; behind a path-rewriting proxy set
    # REFRESH_TOKEN_COOKIE_PATH to the public path (or "/"), otherwise the cookie is never sent
    # and every page reload logs the user out.
    REFRESH_TOKEN_COOKIE_PATH = os.environ.get("REFRESH_TOKEN_COOKIE_PATH", "/api/auth")
    # A refresh token that was rotated less than this many seconds ago may be presented again
    # without being treated as theft: reloads, two tabs or a dropped response make the browser
    # replay the old cookie. Within the window we issue a fresh access token only (the newer
    # cookie is already on its way to the browser). 0 disables the tolerance.
    REFRESH_REUSE_GRACE_SECONDS = int(os.environ.get("REFRESH_REUSE_GRACE_SECONDS", "30"))
    # Secure=False is only acceptable for local plain-HTTP dev
    # (SECURITY.md §5); ProductionConfig below defaults this to True.
    REFRESH_TOKEN_COOKIE_SECURE = (
        os.environ.get("REFRESH_TOKEN_COOKIE_SECURE", "false").lower() == "true"
    )

    # --- Supplier file uploads (catalogs / datasheets) ---
    # Files are written to local disk. Point UPLOAD_DIR at a persistent,
    # backed-up folder in production; it is created on first upload.
    UPLOAD_DIR = os.environ.get(
        "UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    )
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))

    # --- Misc ---
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True
    ENV_NAME = "development"


class TestingConfig(Config):
    """
    Used by the pytest suite. Deliberately does NOT require a live MySQL
    server — Phase 0 tests exercise the application factory, error handling,
    CORS, and the health endpoint, none of which require real business data.
    A file-less SQLite database is enough to prove the app boots and the
    DB extension initializes correctly; real MySQL connectivity is verified
    separately per the README's local setup steps.
    """

    DEBUG = True
    TESTING = True
    ENV_NAME = "testing"
    REFRESH_REUSE_GRACE_SECONDS = 0  # strict reuse detection stays the default under test
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    RATELIMIT_ENABLED = False  # keep tests deterministic, not rate-limit-sensitive


class ProductionConfig(Config):
    """
    Placeholder only. Not configured or exercised in Phase 0 — no Gunicorn,
    no reverse proxy, no production secrets. Present so the config hierarchy
    is complete and future phases don't need to restructure this file.
    """

    DEBUG = False
    ENV_NAME = "production"
    # Production is always HTTPS-only (SECURITY.md §5); default to secure
    # cookies even if REFRESH_TOKEN_COOKIE_SECURE was left unset, while
    # still allowing an explicit env override if ever genuinely needed.
    REFRESH_TOKEN_COOKIE_SECURE = (
        os.environ.get("REFRESH_TOKEN_COOKIE_SECURE", "true").lower() == "true"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> type[Config]:
    """Resolve a config class by name, defaulting to development."""
    env_name = env_name or os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env_name, DevelopmentConfig)
