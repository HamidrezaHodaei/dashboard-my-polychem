# Polychem Automation System — Database Design

Database: **MySQL 8.x**, schema `polychem_automation` (separate from the CRM database — no shared tables, no cross-database FKs).

Engine: InnoDB. Charset: `utf8mb4` / collation `utf8mb4_unicode_ci`.

**Revision note (v3):** adds `user_permission_scopes` (direct user-level grants, alongside the existing role-level `role_permission_scopes`); updates `delegations` to target a specific user (`delegatee_user_id`) with a full lifecycle; adds `organization_id`/`department_id` directly on `users` as their primary organizational placement, explicitly separate from authorization; documents `manager_user_id` as informational-only.

## Conventions (unchanged)
- PK: `id BIGINT UNSIGNED AUTO_INCREMENT`
- `created_at` / `updated_at` on all tables; `deleted_at` (soft delete) on entities with audit/history value
- `is_active BOOLEAN NOT NULL DEFAULT TRUE` on users, roles, organizations, departments, teams
- FKs default `ON DELETE RESTRICT` unless noted

## Organizational structure

### `organizations`
`id, name, parent_organization_id (FK→organizations.id NULL), is_active, created_at, updated_at, deleted_at`

### `departments`
| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| organization_id | BIGINT UNSIGNED FK → organizations.id ON DELETE CASCADE | |
| name | VARCHAR(150) | e.g. "بازاریابی و فروش" |
| parent_department_id | BIGINT UNSIGNED FK → departments.id NULL | headroom for sub-departments |
| manager_user_id | BIGINT UNSIGNED FK → users.id NULL | **informational only** — org-chart label. Never read by the authorization engine. See AUTHORIZATION.md §2. |
| logo_file / logo_content_type | VARCHAR(64) / VARCHAR(50) NULL | worklist (کارتابل) logo; random file name under `UPLOAD_DIR/departments` |
| header_file / header_content_type | VARCHAR(64) / VARCHAR(50) NULL | banner behind the worklist card |
| branding_version | INT NOT NULL DEFAULT 0 | +1 on every picture change (client cache key) |
| is_active | BOOLEAN | |
| created_at / updated_at / deleted_at | | |

Indexes: INDEX(organization_id), INDEX(parent_department_id).

### `teams`
| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| department_id | BIGINT UNSIGNED FK → departments.id ON DELETE CASCADE | |
| name | VARCHAR(150) | e.g. "فروش داخلی" |
| manager_user_id | BIGINT UNSIGNED FK → users.id NULL | **informational only**, same caveat as `departments.manager_user_id` |
| is_active | BOOLEAN | |
| created_at / updated_at / deleted_at | | |

Indexes: INDEX(department_id).

### `team_members` (many-to-many — team membership, not authorization)
`id, team_id (FK→teams.id CASCADE), user_id (FK→users.id CASCADE), joined_at` — UNIQUE(team_id, user_id).

### `users` (changed: explicit organizational placement, separate from authorization)
| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| **organization_id** | BIGINT UNSIGNED FK → organizations.id NULL | **primary organizational placement** — "where does this employee belong," not an authorization signal |
| **department_id** | BIGINT UNSIGNED FK → departments.id NULL | primary department placement, same caveat |
| full_name | VARCHAR(150) | |
| email | VARCHAR(255) UNIQUE | |
| username | VARCHAR(100) UNIQUE | |
| password_hash | VARCHAR(255) | |
| is_active | BOOLEAN | |
| last_login_at | DATETIME NULL | |
| created_at / updated_at / deleted_at | | |

Indexes: UNIQUE(email), UNIQUE(username), INDEX(organization_id), INDEX(department_id), INDEX(is_active).

Team-level placement remains many-to-many via `team_members` (a user can belong to more than one team; department is singular/primary). **None of `organization_id`, `department_id`, or `team_members` rows grant any permission by themselves** — they answer "where," not "what's allowed." See AUTHORIZATION.md §2.

## RBAC tables

### `roles`
`id, name (UNIQUE), display_name, description, is_system_role, is_active, created_at, updated_at, deleted_at`

### `permissions`
`id, key (UNIQUE, [module].[resource].[action]), module, resource, action, is_delegable BOOLEAN DEFAULT FALSE, description, created_at, updated_at`

### `user_roles`
`id, user_id (FK CASCADE), role_id (FK CASCADE), organization_id (FK NULL), assigned_at`

### `role_permission_scopes` — Role-level base grants
The *default* capabilities that come with holding a role.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| role_id | BIGINT UNSIGNED FK → roles.id ON DELETE CASCADE | |
| permission_id | BIGINT UNSIGNED FK → permissions.id ON DELETE CASCADE | |
| scope_type | ENUM('GLOBAL','ORGANIZATION','DEPARTMENT','TEAM','SELF') NOT NULL | |
| scope_id | BIGINT UNSIGNED NULL | NULL when GLOBAL/SELF |
| is_active | BOOLEAN DEFAULT TRUE | |
| granted_by_user_id | BIGINT UNSIGNED FK → users.id NULL | NULL for seed-time grants |
| created_at / updated_at | | |

Indexes: INDEX(role_id, permission_id), INDEX(scope_type, scope_id).

### `user_permission_scopes` — User-level scoped grants (new)
Additional permission+scope granted directly to **one specific user**, independent of role — this is what a targeted delegation (e.g. "علی specifically gets task-assign in فروش داخلی") writes to, so it never widens every holder of علی's role.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| user_id | BIGINT UNSIGNED FK → users.id ON DELETE CASCADE | the specific target user |
| permission_id | BIGINT UNSIGNED FK → permissions.id ON DELETE CASCADE | |
| scope_type | ENUM('GLOBAL','ORGANIZATION','DEPARTMENT','TEAM','SELF') NOT NULL | |
| scope_id | BIGINT UNSIGNED NULL | NULL when GLOBAL/SELF |
| is_active | BOOLEAN DEFAULT TRUE | set FALSE on revocation, row retained for history |
| granted_by_user_id | BIGINT UNSIGNED FK → users.id NULL | who granted it (the delegator, or an admin granting directly) |
| created_at / updated_at | | |

Indexes: INDEX(user_id, permission_id), INDEX(scope_type, scope_id).

Same grant shape as `role_permission_scopes` by design — the permission engine unions both tables into one flat set of grants before evaluating any check (AUTHORIZATION.md §5); nothing downstream treats a role-sourced grant differently from a user-sourced one.

### `delegations` — user-targeted delegation lifecycle (changed)
Answers: who delegated, to which **user**, which permission, which scope, when, still active, who revoked, when.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| delegator_user_id | BIGINT UNSIGNED FK → users.id | who granted it |
| **delegatee_user_id** | **BIGINT UNSIGNED FK → users.id** | **the specific target user** (replaces the v2 `delegatee_role_id`) |
| resulting_user_permission_scope_id | BIGINT UNSIGNED FK → user_permission_scopes.id | the grant row this delegation created |
| delegated_at | DATETIME | |
| revoked_at | DATETIME NULL | |
| revoked_by_user_id | BIGINT UNSIGNED FK → users.id NULL | |

Indexes: INDEX(delegator_user_id), INDEX(delegatee_user_id).

Revoking a delegation (`revoked_at` set) must, in the same transaction, set the linked `user_permission_scopes.is_active = FALSE` — the two rows are kept consistent by the service layer, never independently editable.

> Role-level delegation is not implemented in v1 (see AUTHORIZATION.md §6) — the `delegations` table therefore only ever points at `user_permission_scopes`, not `role_permission_scopes`. If role-level delegation is added later, it would need its own parallel table rather than overloading this one, since the two have different blast radii and different approval rules.

## Task module tables (unchanged from v2)

### `tasks`
`id, title, description, creator_id (FK→users.id), department_id (FK→departments.id, required), team_id (FK→teams.id NULL), project_id (NULL, reserved), priority ENUM, status ENUM, due_date DATE NULL, created_at, updated_at, deleted_at`

Indexes: INDEX(department_id), INDEX(team_id), INDEX(status), INDEX(due_date).

Authorization for every task action resolves from `tasks.department_id`/`tasks.team_id`/assignee membership — never from the acting user's own `department_id`. See AUTHORIZATION.md §8.

### `task_assignments`
`id, task_id (FK CASCADE), assignee_user_id (FK CASCADE), assigned_by_user_id (FK), assigned_at, unassigned_at NULL`

Indexes: UNIQUE(task_id, assignee_user_id) where unassigned_at IS NULL (enforced at service layer), INDEX(assignee_user_id).

## Unchanged tables
`refresh_tokens`, `audit_logs` — no changes in this revision.

## Full entity list (as requested)
```
organizations
departments
teams
team_members
users

roles
permissions
user_roles

role_permission_scopes      — base grants via Role
user_permission_scopes      — additional grants via specific User

delegations                 — audit/lifecycle of user-level grants

tasks
task_assignments

refresh_tokens
audit_logs
```

## Entity relationship summary

```
organizations 1─* departments 1─* teams 1─* team_members *─1 users
users *─1 organizations, users *─1 departments        (organizational placement — NOT authorization)
departments/teams *─1 manager_user_id → users          (informational label — NOT authorization)

roles *─* permissions   via role_permission_scopes   (scope_type + scope_id per row)
users *─* permissions   via user_permission_scopes   (scope_type + scope_id per row)
users *─* roles         via user_roles

delegations: delegator_user_id → users
             delegatee_user_id → users
             resulting_user_permission_scope_id → user_permission_scopes

tasks *─1 departments, tasks *─0..1 teams, tasks *─1 users (creator)
tasks *─* users          via task_assignments
```

## Privilege-escalation protection at the schema level
- `user_permission_scopes.user_id` and `delegations.delegator_user_id` are separate FKs — a self-delegation (`delegator_user_id = delegatee_user_id`) is not blocked by the schema itself, but is rejected by the service layer per AUTHORIZATION.md §9; documented here so a future reviewer doesn't assume the DB enforces it.
- `permissions.is_delegable` is the single source of truth for whether *any* delegation (to any user, at any scope) of that permission can ever succeed — checked before a `user_permission_scopes`/`delegations` row is ever written.
- Both grant tables carry `granted_by_user_id`, so every permission a user holds — whether from a role or delegated directly — is traceable to who authorized it (seed script, admin action, or a specific delegation).

## Migration strategy (unchanged mechanism)
Flask-Migrate/Alembic. This revision's migration set: add `users.organization_id`/`users.department_id`; create `user_permission_scopes`; alter `delegations` (`delegatee_role_id` → `delegatee_user_id`, repoint `resulting_role_permission_scope_id` → `resulting_user_permission_scope_id`); no change needed to `role_permission_scopes` itself (unchanged from v2).
