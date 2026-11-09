# Polychem Automation System — Implementation Plan

Each phase is small, independently testable, and **does not auto-continue** into the next — every phase ends with a checkpoint for review before starting the next one. No phase includes production deployment or connections to the live CRM/API systems.

---

### Phase 0 — Project & environment scaffolding
**Goal:** an empty, runnable Flask app with the folder structure in place, and a local MySQL database created.
- Create `polychem_automation` database locally (MySQL on `localhost:3306`).
- Scaffold the folder structure from ARCHITECTURE.md (empty packages, `__init__.py` files).
- Application factory (`create_app()`) with `DevelopmentConfig`/`TestingConfig` only (no `ProductionConfig` logic exercised yet).
- `.env.example` with all required keys (DB URL, JWT secret placeholder, CORS origin).
- Flask-SQLAlchemy + Flask-Migrate wired up, first empty migration runs cleanly (`flask db upgrade` against a fresh DB).
- Health check endpoint `GET /api/health` returning the standard success envelope.
**Test:** `pytest` runs (even if just one smoke test), `flask run` serves `/api/health` on `localhost:5000`, Nuxt at `localhost:3000` can reach it with CORS working.

### Phase 1 — Core schema: identity, organizational hierarchy & scoped RBAC tables
**Goal:** all tables from DATABASE.md exist via migrations, including the organizational hierarchy (with `users.organization_id`/`department_id` as membership, separate from authorization) and both grant sources.
- Models: `User` (with `organization_id`, `department_id`), `Role`, `Permission` (with `is_delegable`), `UserRole`, `Organization`, `Department` (with informational `manager_user_id`), `Team` (with informational `manager_user_id`), `TeamMember`, `RolePermissionScope`, `UserPermissionScope`, `Delegation` (with `delegatee_user_id`), `RefreshToken`, `AuditLog`.
- Migrations generated and reviewed — in particular confirm `manager_user_id` fields carry no FK-level or application-level authorization behavior, only display use.
- Seed script creates the 16 initial roles plus the initial organizational structure (دفتر مرکزی, کارخانه organizations; فروش, مالی, تدارکات, تولید, انبار, کنترل کیفیت, لجستیک departments; فروش داخلی team) as reference/test data — no grants issued yet except `admin @ GLOBAL`.
**Test:** migrations apply cleanly to a fresh DB; seed script idempotent; model-level pytest tests (create a department under an organization, place a user via `department_id`, separately assign a role, confirm the two are independent — placing a user in a department grants nothing by itself).

### Phase 2 — Permission + Scope engine, and user-level delegation (no HTTP yet)
**Goal:** the authorization engine — unioning both grant sources — works as a library, independent of any route.
- `app/permissions/registry.py` with an initial permission set (Users, Roles, Organizations, Departments, Teams), each marked `is_delegable` per the registry rules.
- `app/permissions/service.py`: resolves `Effective Grants(user) = active role_permission_scopes UNION active user_permission_scopes`.
- `app/permissions/scope.py`: scope containment/expansion.
- `app/permissions/delegation.py`: the five-check eligibility (possession, delegable, scope containment, target user's organizational relationship, delegator's own `authz.grant.delegate` authority) plus the explicit self-delegation block.
- `require_permission` decorator implementing the full four-step resolution order (Permission → Scope → Resource Ownership/Organizational Relationship → Allow/Deny).
**Test:** pytest suite reproducing every scenario in AUTHORIZATION.md §10 (A–J), including: a role grant and a user grant both independently satisfying the same check; a targeted delegation to one user *not* leaking to other holders of that user's role; all five delegation-blocking cases; the explicit self-delegation rejection.

### Phase 3 — Authentication (design → now implement)
**Goal:** working login/refresh/logout against the seeded `admin` user.
- Password hashing, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/refresh`.
- Refresh token rotation + revocation-on-reuse logic.
- Flask-Limiter on the login route.
- `GET /api/me`, `/api/me/roles`, `/api/me/permissions`, `/api/me/navigation` (navigation can return a static/minimal structure until modules exist).
**Test:** pytest covering successful login, wrong password, inactive user rejected, rate limit triggers after N attempts, refresh rotation invalidates the old token, logout revokes the session.

### Phase 4 — Core CRUD modules: Users, Roles, Permissions, Organizations, Departments, Teams
**Goal:** admin-manageable core platform, fully permission-gated **and** scope-gated.
- Standard CRUD blueprints for each, each route wired to its `core.<resource>.<action>` permission plus the appropriate scope resolver (e.g. a department manager can list/edit users within their own department, not globally).
- A first delegation endpoint (`authz.grant.delegate`) so a department manager can delegate a delegable, in-scope permission to a **specific team member** — exercising the Phase 2 delegation logic end to end, confirming the grant lands only on that one user's `user_permission_scopes`, not their whole role.
- Audit logging wired into every mutating action, including delegation grants/revocations (`delegations` table, kept in sync with `user_permission_scopes.is_active`).
**Test:** per-module pytest suite (CRUD + permission-denied + out-of-scope-denied cases) + delegation scenarios (allowed, all five blocked cases, self-delegation blocked) + a regression test proving a delegated grant to one user does not appear for another user sharing that role + manual Nuxt integration smoke test against `localhost:5000`.

### Phase 4a — Tasks / Workspace module (scope-aware)
**Goal:** the Task module, pulled forward because it's the clearest proof that the scope model works end to end for a real business module.
- `Task` and `TaskAssignment` models/migrations (from DATABASE.md).
- `tasks.task.create/read/update/delete/assign` permissions registered, department- and team-scoped grants seeded for مدیر فروش and كارشناس فروش داخلی as a concrete test case.
- Scope-filtered list/analytics endpoints (a manager's "my tasks" view is server-side constrained to their scope, never filtered only in the frontend).
**Test:** مدیر فروش can create/assign within فروش and its teams; denied outside فروش; كارشناس فروش داخلی (via delegated grant from Phase 4) can assign only within فروش داخلی.

### Phase 5 — Nuxt ↔ Flask integration baseline
**Goal:** the admin panel can log in and manage users/roles end to end, locally.
- Nuxt API client centralized (single base URL config, easy to repoint later), auth cookie handling, route guards using `/api/me/permissions` and `/api/me/navigation`.
**Test:** manual end-to-end walkthrough: log in as seeded admin, view/edit a user, confirm a permission-less action is blocked with a 403 surfaced cleanly in the UI.

### Phase 6+ — Remaining business modules, one at a time
Each remaining business module (Dashboard, CRM & Sales, Finance, Warehouse, Mail, Customer Panel, Website Management, Visitor Statistics — Tasks/Workspace was pulled into Phase 4a) becomes its own phase:
1. Define module-specific tables (migration).
2. Define module's permission set, add to registry, extend seed mapping for relevant roles.
3. Build routes/services/repository for that module only.
4. Wire audit logging.
5. Nuxt screens for that module.
6. Only for CRM & Sales, Customer Panel, Visitor Statistics: build the corresponding **adapter** (per INTEGRATIONS.md) as a distinct sub-phase, tested against a mocked external response before any real credentials are introduced.

Suggested order (lowest external dependency / highest internal value first): **Users, Orgs & Tasks (done in Phases 4/4a) → Dashboard (mostly read-only, good integration test) → CRM & Sales (adapter) → Finance → Warehouse → Mail → Customer Panel (adapter) → Website Management → Visitor Statistics (adapter) → Settings**. This order is a recommendation, not a constraint — modules are independent enough to be reordered based on business priority. Each module inherits the scope model from Phase 2/4a rather than reinventing its own authorization logic — e.g. Finance grants will use `ORGANIZATION`/`DEPARTMENT` scope the same way Tasks does, with its own set of non-delegable permissions (financial permissions in particular should default `is_delegable = FALSE` per the security rule that a sales manager must never gain a path to finance access).

### Deferred (explicitly not part of any phase above)
- Production deployment (Gunicorn process management, reverse proxy, TLS termination, systemd/CI-CD) — a phase of its own once the platform is functionally complete locally.
- Real credentials/connection to `crm.polychemmb.com` and `api.polychemmb.com` — adapters are built and tested against mocks first; real connection is a deliberate, separately-approved step.
