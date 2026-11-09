# Polychem Automation System — API Design

Base path: `/api/...`. REST over HTTPS in production, HTTP locally. JSON only (`Content-Type: application/json`).

## 1. Response envelope

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "per_page": 20, "total": 134 }
}
```
`meta` only present on paginated list endpoints.

**Error (all error types share one shape):**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": [
      { "field": "email", "message": "Not a valid email address" }
    ]
  }
}
```

## 2. Status codes & error codes

| Situation | HTTP status | `error.code` |
|---|---|---|
| Validation failure (Pydantic) | 400 | `VALIDATION_ERROR` |
| Missing/invalid/expired JWT | 401 | `AUTHENTICATION_ERROR` |
| Valid token, insufficient permission | 403 | `AUTHORIZATION_ERROR` |
| Resource not found | 404 | `NOT_FOUND` |
| Conflict (e.g. duplicate email) | 409 | `CONFLICT` |
| Rate limit exceeded | 429 | `RATE_LIMITED` |
| Unhandled server error | 500 | `INTERNAL_ERROR` |

All of these are produced by a **single centralized error handler** (`app/middleware/error_handlers.py`) registered on the app factory — no route is responsible for formatting its own error responses. Pydantic `ValidationError` and Flask-JWT-Extended's exceptions are both caught here and translated into the envelope above.

## 3. Auth endpoints (design only — not implemented yet)

| Method & path | Purpose |
|---|---|
| `POST /api/auth/login` | email/username + password → access + refresh token |
| `POST /api/auth/logout` | revokes the current refresh token |
| `POST /api/auth/refresh` | rotates refresh token, issues new access token |
| `GET /api/me` | current user profile |
| `GET /api/me/roles` | current user's roles |
| `GET /api/me/permissions` | current user's effective permissions |
| `GET /api/me/navigation` | permission-filtered menu tree |

Access tokens are sent as `Authorization: Bearer <token>`. Refresh tokens are delivered as an **HttpOnly, Secure, SameSite=Strict cookie** rather than JSON body — keeps them out of reach of frontend JS/XSS, standard practice for Flask-JWT-Extended's cookie mode.

## 4. Conventions for module endpoints

- Resource-oriented paths: `/api/crm/customers`, `/api/finance/transactions`, `/api/warehouse/inventory-items`.
- Standard CRUD verbs: `GET` (list/detail), `POST` (create), `PATCH` (partial update), `DELETE` (soft delete where applicable).
- List endpoints support `?page=`, `?per_page=`, and module-specific filters (e.g. `?status=`); default `per_page` capped (e.g. 100) to prevent unbounded queries.
- Every mutating endpoint is decorated with `@require_permission("<module>.<resource>.<action>")` — see AUTHORIZATION.md.
- Every mutating endpoint writes an `audit_logs` entry via the shared audit-logging service — not opt-in per module, called from a shared service-layer helper so it can't be forgotten.

## 5. Versioning

Not introduced yet (single internal frontend, single backend team) — routes stay at `/api/...` without a version segment. If external/third-party consumption is ever needed, `/api/v1/...` can be introduced without breaking the internal frontend, since Nuxt's API client is centralized behind one config value.


## Permission matrix & user access (added)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/core/users?include_inactive=true&q=...` | list incl. deactivated users, server-side search |
| GET | `/api/core/users/<id>/access` | roles + role grants + direct grants + merged effective permissions |
| GET/PUT | `/api/core/users/<id>/permission-matrix` | body `{"cells": {"crm.customer": {"read": true, "create": false, "update": false, "delete": false}}}` -> desired FINAL access |
| GET/PUT | `/api/core/roles/<id>/permission-matrix` | same body; checked = role holds the permission |
| GET | `/api/core/roles?include_inactive=true` | list incl. deactivated roles |

Merge rules: see AUTHORIZATION.md §11 (DENY > direct ALLOW > role grants; roles are unioned).
