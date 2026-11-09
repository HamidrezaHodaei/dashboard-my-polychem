"""
Authentication (Phase 3): login/refresh/logout, JWT access tokens,
opaque server-side-hashed refresh tokens, and `require_authenticated`.

    models.py       RefreshToken (Phase 1 schema, unchanged)
    schemas.py      Pydantic request/response contracts
    services.py     password hashing, login, refresh rotation + reuse
                     detection, logout, audit events -- all business
                     logic lives here, per Master Context layering
    decorators.py   require_authenticated -- JWT validation only, sets
                     g.current_user; no role/permission/scope logic
    routes.py       POST /api/auth/login|refresh|logout, GET /api/me

Authorization (roles/permissions/scopes/delegation) remains entirely
Phase 2's (`app/permissions/*`), unchanged by this package.
"""
