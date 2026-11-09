# Polychem Automation System — Security Architecture

## 1. Authentication & password security
- Passwords hashed with **Argon2** (preferred) or bcrypt via `passlib`/`argon2-cffi` — never reversible encryption, never plaintext.
- JWT **access tokens**: short-lived (target ~15 min), signed with a server-side secret (`JWT_SECRET_KEY` from environment, never committed).
- JWT **refresh tokens**: longer-lived (e.g. 7–30 days), stored server-side as a hash in `refresh_tokens`, delivered to the browser as an **HttpOnly, Secure, SameSite=Strict** cookie — not accessible to JS, mitigates XSS token theft.
- **Refresh rotation**: every use of a refresh token issues a new one and immediately revokes the old (`revoked_at` set, `replaced_by_token_id` links the chain). Reuse of an already-rotated token is treated as a signal of token theft and revokes the entire session chain for that user.
- **Revocation**: logout, password change, or admin action revokes refresh tokens immediately (DB-backed, not just token-expiry-based) — access tokens still expire naturally within minutes, and sensitive routes can force a DB permission re-check when instant effect matters (see AUTHORIZATION.md §4).
- **Inactive user protection**: `is_active = FALSE` blocks login at the authentication service layer, checked before password verification is even considered a success.

## 2. Brute-force / rate limiting
- **Flask-Limiter** applied to `/api/auth/login` with a strict per-IP and per-account limit (e.g. 5 attempts / minute, with backoff), separate from general API rate limits.
- Failed login attempts are logged (without logging the submitted password) and feed into the same audit trail so repeated failures are visible to admins.
- General API rate limiting applied platform-wide as a baseline abuse guard, independent of the login-specific limit.

## 3. Authorization
- All server-side, decorator-enforced, centrally defined — see AUTHORIZATION.md. Frontend checks are UI-only and carry no trust.

## 4. Input validation & injection protection
- Every request body validated through a Pydantic schema before it reaches a service — rejects unexpected fields and wrong types at the boundary.
- All database access through SQLAlchemy's ORM/query builder — no raw string-interpolated SQL. Any unavoidable raw SQL uses parameterized queries only, never f-string/`%`-formatted values.
- File uploads (once relevant, e.g. Mail or Customer Panel modules) validated by type/size and stored outside any web-executable path.

## 5. Transport & headers
- HTTPS enforced in production (`https://backend.polychemmb.com`); local dev over plain HTTP is acceptable since it's localhost-only.
- **CORS**: explicit allow-list — `http://localhost:3000` in dev, `https://panel.polychemmb.com` in prod. Credentials allowed only for that exact origin; no wildcard `*` origin given the auth cookie is in play.
- Security headers (via `flask-talisman` or a small custom middleware): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` (prod only), a conservative `Content-Security-Policy` for any served content, `Referrer-Policy: strict-origin-when-cross-origin`.

## 6. Secrets management
- All secrets (`JWT_SECRET_KEY`, DB credentials, adapter API keys) in environment variables loaded via `python-dotenv` locally; `.env` is git-ignored, `.env.example` documents required keys with placeholder values only.
- No secrets in source control, ever — enforced by `.gitignore` + a pre-commit check as a recommended (not yet implemented) addition.
- Config split by environment (`DevelopmentConfig`/`TestingConfig`/`ProductionConfig`), selected via `FLASK_ENV`/`APP_ENV`, so production secrets are never present in a developer's local `.env`.

## 7. Audit logging
- Every authentication event (login success/failure, logout, token refresh, token revocation) and every mutating business action writes to `audit_logs`, via a shared service call — not left to individual route authors to remember.
- Audit logs are append-only (no update/delete path exposed via the API) and store `user_id`, `action`, `module`, `entity_type`/`entity_id`, a `metadata` JSON diff where relevant, `ip_address`, and `created_at`.

## 8. Application logging
- Structured logging (JSON logs recommended for production) separate from audit logs — audit logs are business-event records for compliance/traceability; application logs are operational (errors, request timing, integration-call outcomes).
- No sensitive data (passwords, raw tokens, full card/account numbers if ever handled by Finance) ever written to application logs.

## 9. Dependency & environment hygiene
- Pinned dependency versions in `requirements.txt`.
- MySQL user for the app has least-privilege grants scoped to `polychem_automation` only — explicitly **no** access to the CRM's database, enforced at the MySQL grant level, not just by convention.
