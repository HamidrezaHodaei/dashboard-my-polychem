# Polychem Automation System — Integrations

## 1. Principle

The existing CRM (`crm.polychemmb.com`) and existing APIs (`api.polychemmb.com`) are **untouched external systems** from this project's point of view. The new Flask backend never rewrites, migrates, or shares a database with them. It talks to them exclusively through **adapters** — a thin, isolated integration layer.

```
Flask module (e.g. crm business module)
        │  calls adapter interface, never an HTTP client directly
        ▼
Integration Adapter (app/integrations/crm_adapter/)
        │  owns: base URL, auth, retries, response mapping
        ▼
crm.polychemmb.com (external, untouched)
```

## 2. Why adapters, not direct calls from business modules

- **Isolation of change:** if the CRM's API shape changes, only the adapter changes — business-module code and Nuxt never know.
- **Single boundary for security review:** all outbound calls to external PolyChem systems live in one folder, easy to audit.
- **Testability:** business modules can be tested against a mocked adapter interface without hitting real external services.
- **Consistent error handling:** adapters translate external failures (timeouts, 5xxs, schema drift) into the platform's own standard error envelope, rather than leaking raw upstream errors to the frontend.

## 3. Planned adapters

| Adapter | Talks to | Used by module(s) |
|---|---|---|
| CRM Adapter | `crm.polychemmb.com` | CRM & Sales module |
| Customer Panel Adapter | `api.polychemmb.com` | Customer Panel module |
| Visitor Statistics Adapter | `api.polychemmb.com` | Visitor Statistics module |

Each adapter is a small package: a client class wrapping HTTP calls (e.g. via `requests` or `httpx`), a mapping layer converting external response shapes into internal Pydantic schemas, and its own error translation.

## 4. Shared adapter interface

`app/integrations/base.py` defines a common pattern every adapter follows:
- Explicit, environment-driven base URL and credentials (never hardcoded) — `CRM_ADAPTER_BASE_URL`, `CRM_ADAPTER_API_KEY`, etc. in `.env`.
- Timeouts on every request (no unbounded waits blocking a Flask worker).
- A small retry policy for idempotent (GET) calls only — no automatic retries on writes, to avoid duplicate side effects on the external system.
- Structured logging of every outbound call (endpoint, duration, status) distinct from application audit logs, for operational debugging of the integration boundary specifically.

## 5. Authentication to external systems

Not designed in detail yet — depends on what `crm.polychemmb.com` / `api.polychemmb.com` currently support (API key, shared secret, or session-based). This is flagged as an open item for the phase in which each adapter is actually built (see IMPLEMENTATION_PLAN.md); it does not block the core platform or module scaffolding phases.

## 6. Scope boundary — explicitly out of scope for this project

- No schema changes to the CRM's database.
- No new endpoints added to `crm.polychemmb.com` or `api.polychemmb.com` as part of this project.
- No direct database connection from the new Flask backend into the CRM's MySQL instance — all interaction is over HTTP through the adapters, even though both systems may eventually live on the same MySQL server. Cross-database queries are deliberately avoided to keep the systems decoupled and independently deployable.
