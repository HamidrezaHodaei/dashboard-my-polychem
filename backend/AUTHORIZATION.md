# Polychem Automation System — Authorization (RBAC + Scope + User-Level Delegation)

**Revision note (v3):** this revision (1) splits grants into **Role-level base grants** and **User-level scoped grants**, with effective authorization being the union of both; (2) makes delegation target a specific **user**, not just a role; (3) separates organizational membership (`organization_id`/`department_id` on `users`, `team_members`) from authorization entirely; (4) makes explicit that `manager_user_id` fields are informational metadata only and must never be checked directly for authorization.

## 1. Organizational hierarchy (unchanged from v2)

```
Organization
    └── Department
            └── Team
                    └── User
```

## 2. Organizational membership vs. Authorization — kept strictly separate

These answer two different questions and must never be conflated:

| | Question | Mechanism |
|---|---|---|
| **Organizational membership** | "Where does this employee belong?" | `users.organization_id`, `users.department_id` (primary placement) + `team_members` (many-to-many team membership) |
| **Authorization** | "What is this employee allowed to do, and where?" | `Role → Permission + Scope` and `User → Permission + Scope`, resolved through the permission engine |

A user's `department_id` says which department they work in. It grants **zero** permissions by itself. Whether that user can, say, create tasks in their own department is entirely determined by whether some active Role grant or User grant gives them `tasks.task.create @ DEPARTMENT` (or broader) covering that department — never inferred from `users.department_id` matching the target resource's department. This separation is mandatory precisely so "which department someone sits in" and "what they're allowed to touch" can diverge (e.g. a newly-transferred employee, or a cross-department delegated permission).

`departments.manager_user_id` and `teams.manager_user_id` are **organizational metadata only** — they record who the org chart says manages a unit. They are informational fields used for display (e.g. "manager: مدیر فروش" on a department page) and are never read by the authorization engine. **Authorization is never derived by comparing a user to a `manager_user_id` field.** The following pattern is explicitly disallowed anywhere in the codebase:

```python
# NEVER DO THIS — not an authorization check
if user.id == department.manager_user_id:
    allow()
```

The only path to "can مدیر فروش manage فروش?" is: مدیر فروش holds an active Role or User grant of the relevant permission at `DEPARTMENT: فروش` scope (or broader), evaluated through the standard engine below. Being *recorded* as a department's manager and *being authorized* to act on that department are independent facts that happen to usually coincide because the seed/admin process grants the manager role appropriate permissions — not because the field itself is checked.

## 3. Four separate concepts (unchanged)

Authentication → Permission → Scope → Delegation remain distinct, as established in v2. This revision refines Permission+Scope resolution and Delegation; Authentication and the base Scope taxonomy (`GLOBAL`/`ORGANIZATION`/`DEPARTMENT`/`TEAM`/`SELF`) are unchanged.

## 4. Two sources of grants: Role-level and User-level

**Role-level base grants** (`role_permission_scopes`) define the *default* capabilities that come with holding a role — e.g. every `sales_manager` gets `tasks.task.create/assign/read @ DEPARTMENT: فروش` by virtue of the role.

**User-level scoped grants** (`user_permission_scopes`) grant an *additional* permission+scope to one specific user, independent of their role. This is what makes targeted delegation possible without widening a whole role's default capabilities:

> مدیر فروش delegating `tasks.task.assign @ TEAM: فروش داخلی` to علی, specifically, must **not** silently hand that same permission to every other user holding علی's role (`کارشناس فروش`). A role-level grant would do exactly that — which is why this case is modeled as a row scoped to علی's `user_id`, not a change to the `کارشناس فروش` role's grants.

Both tables share the same grant shape — `(permission_id, scope_type, scope_id, is_active, granted_by_user_id)` — differing only in whether they key off `role_id` or `user_id`. This symmetry is intentional: the engine treats them identically once resolved (§5).

## 5. Effective grants & the authorization check

```
Effective Grants(user) =
      Active Role Permission Grants   (via user's active roles → role_permission_scopes)
      UNION
      Active User Permission Grants   (user_permission_scopes, directly on this user)
```

Both sets are drawn into one flat list of `(permission, scope_type, scope_id)` tuples before any check runs — there is no precedence between them and no special-casing; a permission held via a role and the same permission held via a direct user grant are equivalent once resolved.

**Full resolution order for every protected action:**
```
1. Permission Check
       — does Effective Grants(user) contain this permission, at all, from either source?
2. Scope Check
       — does at least one matching grant's scope cover the specific target resource
         (resolved from the resource itself — its department_id/team_id/owner — never
         from the acting user's own department_id)?
3. Resource Ownership / Organizational Relationship
       — for SELF-scoped grants, or any check that also depends on the resource's
         relationship to the user (e.g. "assignee must be a member of the target team"),
         verify that relationship explicitly (team_members lookup, ownership field, etc.)
4. Allow / Deny
       — all prior steps must pass; a single failure is a 403, regardless of which
         step failed or which grant source (role vs. user) was involved
```

This four-step order is the one all future modules implement — it replaces the two-step (permission, scope) description from v2 with the added explicit step 3, which matters once assignment targets (not just the acting user) need validating against the target resource's own organizational relationships.

### Worked example (mixed sources)
- مدیر فروش holds `tasks.task.assign @ DEPARTMENT: فروش` via the `sales_manager` **role**.
- علی holds `tasks.task.assign @ TEAM: فروش داخلی` via a direct **user** grant (issued by مدیر فروش through delegation).
- Both pass the identical four-step check when assigning a task — مدیر فروش's role grant covers all of فروش including فروش داخلی; علی's user grant covers only فروش داخلی. Neither is treated as more or less authoritative than the other; they're just two ways of arriving at the same kind of grant.

## 6. Delegation model — now user-targeted

Delegation creates a **User-level scoped grant** for a specific target user. Role-level delegation (granting to "everyone holding role X") is not supported in v1 — user-level delegation is the required mechanism; if a genuine need for role-level delegation emerges later, it can be added as a distinct, separately-authorized action, not folded into this one.

### `delegations` — full lifecycle record
Answers: who delegated, to which user, which permission, which scope, when, still active?, who revoked, when revoked.

| Field | Purpose |
|---|---|
| `delegator_user_id` | who granted it |
| `delegatee_user_id` | **the specific target user** (not a role) |
| `resulting_user_permission_scope_id` | FK to the `user_permission_scopes` row this delegation created |
| `delegated_at` | when granted |
| `revoked_at` | NULL while active |
| `revoked_by_user_id` | who revoked it (the original delegator, or an admin) |

Revoking a delegation deactivates (`is_active = FALSE`) the linked `user_permission_scopes` row — the grant and its audit trail stay linked and consistent by construction, not by convention.

### Delegation eligibility — five checks, all server-side, all must pass
A manager can create a user-level delegation only if:
1. **Possession** — they hold the permission themselves (via role grant or user grant — either counts), at a scope equal to or broader than the scope being delegated.
2. **Delegable** — the permission is marked `is_delegable = TRUE` in the registry.
3. **Scope containment** — the target scope is equal to or narrower than their own held scope.
4. **Target user's organizational relationship** — the delegatee actually belongs to (is a member of, per `team_members`/`department_id`) the organizational unit the delegated scope refers to. A manager cannot delegate `TEAM: فروش داخلی` access to someone who isn't a member of that team — delegation is not a way to grant access to unrelated people, only to extend a subordinate's authority within their own organizational placement.
5. **Delegation authority itself** — the delegator holds `authz.grant.delegate` at a scope covering the target (delegating is itself a permission+scope-checked action through the same four-step engine in §5, not a bypass of it).

Any single failure → `403 AUTHORIZATION_ERROR`, delegation not created, nothing written except (optionally) an audit-log entry of the attempt.

## 7. Department managers vs. Team managers — clarified with explicit examples

### Department Manager
```
User:        مدیر فروش
Role:        sales_manager
Permissions: tasks.task.create, tasks.task.assign, tasks.task.read, tasks.analytics.read
Scope:       DEPARTMENT: فروش
```
Automatically covers every team under فروش (فروش داخلی, فروش خارجی, any other current or future team under that department) — no per-team grant needed. Does not need `manager_user_id` set on those teams to work; that field, if set, is purely the org-chart label.

### Team Manager
```
User:        (team lead)
Role:        sales_team_lead
Permissions: tasks.task.create, tasks.task.assign, tasks.task.read
Scope:       TEAM: فروش داخلی
```
Can operate only inside فروش داخلی. Cannot operate on فروش خارجی, مالی, انبار, تولید, or any other unit — not because of a hardcoded exclusion list, but because no grant they hold covers those scopes. Access to another unit requires an explicit additional grant (role-level or delegated user-level).

## 8. How the Task module uses this (reaffirmed)

Task authorization is **always** resolved from the task's own `department_id`, `team_id`, and assignee(s) — **never** from the acting user's own `department_id`. A Sales manager creating a task must supply `department_id = فروش` (and optionally a `team_id` under فروش) for the create to succeed; a request with `department_id = مالی` is rejected by the scope check in step 2 of §5 even if the frontend sends it — the backend is the enforcement point, not a client-side guard. Likewise, `tasks.task.assign` additionally runs step 3 (§5) to confirm the assignee is actually a member of the task's team before the assignment is allowed.

## 9. Privilege escalation — the complete rule set

A manager (department or team level) must never be able to:
- grant a permission they don't themselves hold (blocked by §6.1)
- grant a permission marked non-delegable (blocked by §6.2) — financial, system, security, and role/permission-management permissions default `is_delegable = FALSE` and stay that way regardless of who holds them
- grant a broader scope than their own (blocked by §6.3)
- grant access to a user outside the relevant organizational unit (blocked by §6.4)
- delegate at all without holding `authz.grant.delegate` for that scope (blocked by §6.5)
- grant themselves additional permissions — delegation always requires `delegator_user_id ≠ delegatee_user_id`; self-delegation is rejected outright regardless of whether the other five checks would otherwise pass

## 10. Example authorization scenarios (updated set)

**A — role grant, in scope, allowed:** مدیر فروش (role grant, DEPARTMENT: فروش) creates a task with `department_id=فروش, team_id=فروش داخلی`. Steps 1–3 pass. Allowed.

**B — role grant, out of scope, denied:** same user attempts `department_id=مالی`. Step 1 passes, step 2 fails (no grant covers مالی). `403`.

**C — permission never held, denied:** same user attempts `finance.transaction.read`. Step 1 fails outright. `403`.

**D — user-level delegation, allowed:** مدیر فروش delegates `tasks.task.assign @ TEAM: فروش داخلی` to علی specifically. Possession ✓ (role grant covers DEPARTMENT ⊇ TEAM), delegable ✓, containment ✓, علی is a member of فروش داخلی ✓, مدیر فروش holds `authz.grant.delegate` ✓. A `user_permission_scopes` row is created for علی; a linked `delegations` row records the grant. کارشناس فروش role-mates of علی are unaffected — they gained nothing.

**E — delegation blocked, non-delegable permission:** مدیر فروش attempts to delegate `users.user.delete` to علی. Blocked at §6.2 regardless of possession. `403`.

**F — delegation blocked, scope escalation:** مدیر فروش attempts to delegate at `ORGANIZATION: دفتر مرکزی` (broader than their own `DEPARTMENT: فروش`). Blocked at §6.3. `403`.

**G — delegation blocked, unrelated target user:** مدیر فروش attempts to delegate `TEAM: فروش داخلی` access to a warehouse employee who has no membership in that team. Blocked at §6.4. `403`.

**H — delegation blocked, self-grant:** مدیر فروش attempts to delegate a permission to themself. Blocked at §9's explicit self-delegation rule, independent of the other five checks. `403`.

**I — mixed-source check, allowed:** علی (holding the user-level grant from scenario D) assigns a task whose `team_id = فروش داخلی` to a teammate who is a member of that team. Step 1 passes via the user grant, step 2 passes (TEAM scope matches), step 3 passes (assignee is a team member). Allowed.

**J — admin, unrestricted:** `admin` role holds all permissions at `GLOBAL` scope; every step passes for any resource.


## 11. Permission matrix & final-permission merge rules (per-user / per-role)

Admins manage access through a **Module × Read / Create / Edit / Delete**
matrix (`Read=read`, `Create=create`, `Edit=update`, `Delete=delete` on
`[module].[resource]` keys, e.g. `core.user.update`, `crm.customer.read`).
The matrix is only a view/bulk-editor over the existing grant tables:

```
User -> Role(s) -> role_permission_scopes          (role permissions)
User -> user_permission_scopes (effect = ALLOW)    (direct user permissions / delegations)
User -> user_permission_scopes (effect = DENY)     (direct user restrictions)
```

**Final permission of a user (one rule, enforced everywhere through
`app/permissions/service.py::get_effective_grants`)**

```
final = ( union of grants of ALL active roles  UNION  direct ALLOW grants )
        MINUS anything covered by a direct DENY
```

Precedence, highest first:

1. **User DENY** – always wins. Removes every grant of that permission whose
   scope is covered by the deny's scope (the matrix writes GLOBAL denies, i.e.
   removes the permission completely).
2. **User ALLOW** – direct grants (and delegations) add on top of role grants.
3. **Role grants** – merged (union) across all active roles; roles never deny,
   so two roles can never conflict. Inactive roles contribute nothing.

Matrix endpoints
- `GET/PUT /api/core/roles/<id>/permission-matrix` (read: `core.role.read`, write: `core.role.update`)
- `GET/PUT /api/core/users/<id>/permission-matrix` (read: `core.user.read`;
  write: `core.user.update` at the user's scope **and** `core.permission.update`)
- `GET /api/core/users/<id>/access` – roles, role grants, direct grants, merged effective permissions

Safety rules: you cannot edit your own permissions, and you can only ALLOW /
grant a permission you hold yourself (no privilege escalation). Every save is
written to the audit log.


## 12. Unit isolation for projects & tasks (hard rule, server-side)

A *project* in the UI is a department; every task belongs to exactly one department
(`tasks.department_id`, optionally a team of it). Access to projects and tasks is bounded by the
user's **unit** and enforced in `app/modules/tasks/services.py::Authority` — the single place all
task endpoints go through (tasks, notes/messages, checklist, files, assignments, mentions,
analytics, `/tasks/meta`, notifications about tasks):

| Who | What they get |
|---|---|
| user with the `admin` role | every unit: view and manage all projects/tasks |
| everybody else | only the tasks/projects of their **own unit** = `users.department_id` ∪ departments of the teams they are a member of |

* Permissions (Create / Read / Edit=`update` / Delete / Assign) are evaluated **inside** the unit.
  Grants can narrow access but never widen it — not even a `GLOBAL` grant, which is what the
  permission matrix writes for every checked box. An "Edit" holder can therefore edit only
  their own unit's tasks.
* Creating a task, or being / having been assigned to it, gives **no** access once the task is
  outside the user's unit (e.g. after a transfer). Notifications that point at such a task are
  hidden too.
* Every sub-resource (`/tasks/<id>/notes|checklist|files|assignments|mention-candidates`, file
  download by id) resolves the *task* first and applies the same rule, so changing a URL / id or
  calling the API directly cannot cross units. A file id that belongs to another task is a 404.
* Assignment rules (`/tasks/assignment-rules`): an admin manages all; a non-admin holder of
  `core.permission.update` may only see/create/delete rules whose grantor and target are users,
  departments or teams of their own unit (`ROLE` and `ALL` targets are admin-only).
* Out-of-unit access answers `403`.

Tests: `tests/modules/tasks/test_unit_isolation.py` (regular user / Edit holder / admin / transfer /
team membership / notifications / rules).
