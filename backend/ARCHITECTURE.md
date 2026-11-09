# Polychem Automation System — Architecture

Status: **Design phase — no code implemented yet.**

## 1. System Overview

```
Nuxt 4 Frontend (panel.polychemmb.com / localhost:3000)
        │
        ▼
Flask Central Backend (backend.polychemmb.com / localhost:5000)
        │
        ├── Core Platform
        │     Auth · RBAC · Users · Roles · Permissions
        │     Organizations · Teams · Audit Logs
        │
        ├── Business Modules
        │     Dashboard · Tasks/Workspace · CRM & Sales · Finance
        │     Warehouse · Mail · Customer Panel · Website Mgmt
        │     Visitor Statistics
        │
        └── Integration Adapters
              CRM Adapter → crm.polychemmb.com
              Customer Panel Adapter → api.polychemmb.com
              Visitor Statistics Adapter → api.polychemmb.com
```

**Hard rule:** the Nuxt frontend never calls `crm.polychemmb.com` or `api.polychemmb.com` directly. Every request goes `Nuxt → Flask → Adapter → external service`. This keeps one auth boundary, one audit trail, and one place to change if an external service changes.

The existing CRM (`crm.polychemmb.com`) and existing APIs (`api.polychemmb.com`) are **not touched**. They remain independent, deployed as-is. The new backend is a new system that talks to them as external services through adapters, using its own database (`polychem_automation`), completely separate from the CRM's database.

## 2. Why Flask, not a "batteries-included" framework

Given the constraint (Flask + MySQL, no Django/FastAPI/NestJS), the architecture leans on a small set of well-established extensions rather than reinventing structure:

| Concern | Library | Why |
|---|---|---|
| App bootstrapping | Flask Application Factory pattern | Enables multiple config environments (dev/test/prod) and clean test isolation — no global app object |
| Routing/modularity | Flask Blueprints | One blueprint per module (auth, users, crm, finance, …), mirrors the module list 1:1 |
| ORM | Flask-SQLAlchemy | De facto standard, mature MySQL support, works cleanly with Alembic |
| Migrations | Flask-Migrate (Alembic) | Versioned, reviewable schema changes; required since this DB will grow across 17 modules |
| DB driver | **PyMySQL** | Pure-Python, no C build toolchain required (simpler local dev on any machine), fully compatible with SQLAlchemy's `mysql+pymysql://` dialect. `mysqlclient` is faster but requires MySQL C headers; not worth the friction for an internal admin platform. Can be swapped later without touching models. |
| AuthN tokens | Flask-JWT-Extended | Access + refresh tokens, token revocation via blocklist callback, custom claims (roles/permissions) built in |
| Rate limiting | Flask-Limiter | Needed for login brute-force protection and general API abuse protection; supports per-route limits |
| Validation/serialization | **Pydantic v2** | Chosen over Marshmallow for typed request/response schemas, better editor support, faster validation, and natural fit with the "schemas/" layer described below. Marshmallow is an acceptable substitute if the team prefers it — noted as the alternative, not the primary pick. |
| Testing | pytest + pytest-flask + factory_boy (or a lightweight fixture builder) | Application-factory pattern makes it trivial to spin up a test app + test DB per run |
| Production server | Gunicorn (+ sync or gthread workers) | Standard for Flask in production; not configured yet per instructions, but the app factory is written to be WSGI-server-agnostic from day one |
| Config | python-dotenv + a `Config` class hierarchy | Environment-based config classes (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`) reading from `.env` |

CORS is handled with **Flask-CORS**, scoped explicitly to `http://localhost:3000` in dev and `https://panel.polychemmb.com` in prod — no wildcard origins, since this API carries auth tokens.

## 3. Layered structure inside the backend

Each business module follows the same internal layering, so the codebase stays predictable as it grows from 2 modules to 17:

```
Route (Blueprint)  →  Schema (Pydantic)  →  Service  →  Repository  →  Model (SQLAlchemy)
```

- **Route**: HTTP concerns only — parses request, calls service, returns response. No business logic, no direct DB queries.
- **Schema**: Pydantic models validate input and shape output. Nothing reaches a service un-validated.
- **Service**: business logic and orchestration (e.g. "create user" = hash password + assign default role + write audit log). Services never touch Flask's `request`/`g` directly — keeps them testable and reusable.
- **Repository**: thin data-access layer wrapping SQLAlchemy queries. Optional for simple modules, valuable for modules with complex queries (CRM, Finance, Warehouse) so services aren't full of raw ORM calls.
- **Model**: SQLAlchemy models — the source of truth for schema, paired with Alembic migrations.

Permission checks happen as a **decorator on the route**, backed by a centralized permission-checking service (see AUTHORIZATION.md) — never hand-written `if` checks scattered through handlers.

## 4. Folder Structure

```
polychem-automation-backend/
├── app/
│   ├── __init__.py                # application factory: create_app()
│   ├── extensions.py               # db, migrate, jwt, limiter, cors instances
│   ├── config.py                   # Config / DevelopmentConfig / TestingConfig / ProductionConfig
│   │
│   ├── core/                       # cross-cutting platform concerns
│   │   ├── auth/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── services.py
│   │   │   └── models.py           # RefreshToken / session model lives here
│   │   ├── users/
│   │   ├── roles/
│   │   ├── permissions/
│   │   ├── organizations/
│   │   ├── departments/           # new — sits between organizations and teams
│   │   ├── teams/
│   │   └── audit_logs/
│   │
│   ├── modules/                    # business modules — one package per module
│   │   ├── dashboard/
│   │   ├── tasks/
│   │   ├── crm/
│   │   ├── finance/
│   │   ├── warehouse/
│   │   ├── mail/
│   │   ├── customer_panel/
│   │   ├── website/
│   │   └── visitor_stats/
│   │   # each module package: routes.py, schemas.py, services.py,
│   │   #                       repository.py, models.py, tests/
│   │
│   ├── integrations/               # adapters to external systems
│   │   ├── base.py                 # shared adapter interface / HTTP client wrapper
│   │   ├── crm_adapter/
│   │   ├── customer_panel_adapter/
│   │   └── visitor_stats_adapter/
│   │
│   ├── permissions/                 # RBAC + Scope engine (module-agnostic)
│   │   ├── decorators.py           # @require_permission("crm.customer.read", scope_resolver=...)
│   │   ├── registry.py             # canonical list of permission strings + is_delegable flags
│   │   ├── service.py              # unions role_permission_scopes + user_permission_scopes → effective grants
│   │   ├── scope.py                # scope containment/expansion logic (GLOBAL>ORG>DEPT>TEAM>SELF)
│   │   └── delegation.py           # user-targeted delegation eligibility (possession/delegable/containment/org-relationship/grant-authority)
│   │
│   ├── middleware/
│   │   ├── error_handlers.py       # unified error response format
│   │   ├── request_context.py      # correlation IDs, current-user loader
│   │   └── security_headers.py
│   │
│   └── utils/
│       ├── responses.py            # standard success/error envelope helpers
│       └── pagination.py
│
├── migrations/                     # Alembic migration scripts
├── tests/
│   ├── conftest.py                 # app factory fixture, test DB fixture
│   ├── core/
│   └── modules/
├── scripts/
│   └── seed_roles_permissions.py   # seeds initial roles/permission registry
├── .env.example
├── requirements.txt
├── wsgi.py                         # gunicorn entrypoint (prod, not configured yet)
└── run.py                          # local dev entrypoint (flask run equivalent)
```

Design intent: `core/` (identity & platform) is stable and rarely changes shape. `modules/` grows module-by-module — each one addable/removable independently, which matches the phased implementation plan. `integrations/` is the *only* place that is allowed to make outbound HTTP calls to `crm.polychemmb.com` or `api.polychemmb.com`.

## 5. Organizational hierarchy & authorization (revised, v3)

Authorization is **role + user-level grants + organizational scope**, and is kept strictly separate from organizational membership:

```
Organization
    └── Department
            └── Team
                    └── User
```

- **Organizational membership** — "where does this employee belong" — is tracked directly on `users.organization_id`/`users.department_id`, plus `team_members` for team membership. This is plain placement data; it grants nothing.
- **Authorization** — "what can this employee do, and where" — is resolved from two grant sources: **Role-level base grants** (`role_permission_scopes`, the default capabilities of a role) and **User-level scoped grants** (`user_permission_scopes`, additional permission+scope granted to one specific user, e.g. via delegation). The engine unions both before checking Permission → Scope → Resource Ownership/Organizational Relationship → Allow/Deny.
- `departments.manager_user_id` / `teams.manager_user_id` are **informational org-chart fields only** — never read by the authorization engine.

See AUTHORIZATION.md for the full model, delegation rules (now user-targeted), and privilege-escalation safeguards — this section only notes the structural impact on the platform layer. The Task module (`modules/tasks/`) resolves authorization from each task's own `department_id`/`team_id`/assignees, never from the acting user's own placement — see AUTHORIZATION.md §8 and DATABASE.md.

## 6. Related documents
- `DATABASE.md` — schema for core platform tables, including role- and user-level scoped grants and task tables
- `AUTHORIZATION.md` — RBAC + Scope + user-level Delegation model in detail
- `API.md` — REST conventions, response envelopes, auth endpoints
- `INTEGRATIONS.md` — adapter pattern and boundary rules
- `SECURITY.md` — security controls across the stack
- `IMPLEMENTATION_PLAN.md` — phased build order
