"""HTTP tests for /api/tasks -- Phase 4a (IMPLEMENTATION_PLAN.md)."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    add_team_member,
    auth_headers,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_team,
    make_user,
)


def _grant(user, key, scope_type, scope_id=None):
    """Grant a permission AND place the user in the unit the grant refers to.

    Unit isolation is strict: a grant only ever works inside the user's own department /
    teams (it can narrow access, never widen it), so a user granted `X @ DEPARTMENT d` must
    actually belong to `d` for the grant to be usable."""
    from app.core.teams.models import Team

    if user.department_id is None and scope_id is not None:
        if scope_type == ScopeType.DEPARTMENT:
            user.department_id = scope_id
        elif scope_type == ScopeType.TEAM:
            user.department_id = db.session.get(Team, scope_id).department_id
    permission = make_permission(key)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def _allow_assign_all(user):
    """Task assignment rule: `user` may assign tasks to everyone."""
    from app.modules.tasks.models import RuleSubject, RuleTarget, TaskAssignmentRule

    db.session.add(TaskAssignmentRule(
        grantor_type=RuleSubject.USER, grantor_id=user.id, target_type=RuleTarget.ALL,
    ))


# --- CREATE -----------------------------------------------------------


def test_create_task_within_department_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.post(
        "/api/tasks", json={"title": "Follow up with client", "department_id": dept_id},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["department_id"] == dept_id
    assert body["status"] == "TODO"
    assert body["priority"] == "MEDIUM"


def test_create_task_denied_outside_department_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept_a.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_b_id = dept_b.id

    resp = client.post(
        "/api/tasks", json={"title": "Wrong dept", "department_id": dept_b_id}, headers=headers
    )
    assert resp.status_code == 403


def test_create_task_within_team_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id, team_id = dept.id, team.id

    resp = client.post(
        "/api/tasks",
        json={"title": "Team task", "department_id": dept_id, "team_id": team_id},
        headers=headers,
    )
    assert resp.status_code == 201


def test_create_task_team_scope_does_not_cover_whole_department(client, app):
    """A TEAM-scoped grant must not let a user create a department-level
    (no team_id) task -- AUTHORIZATION.md §7: team managers "cannot
    operate on ... any other unit ... not because of a hardcoded
    exclusion, but because no grant they hold covers those scopes"."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.post(
        "/api/tasks", json={"title": "No team", "department_id": dept_id}, headers=headers
    )
    assert resp.status_code == 403


def test_create_task_rejects_team_not_belonging_to_department(client, app):
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        team_of_b = make_team(dept_b)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept_a.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_a_id, team_of_b_id = dept_a.id, team_of_b.id

    resp = client.post(
        "/api/tasks",
        json={"title": "Mismatched", "department_id": dept_a_id, "team_id": team_of_b_id},
        headers=headers,
    )
    assert resp.status_code == 409


# --- READ / LIST (scope-filtered) --------------------------------------


def test_department_manager_sees_tasks_across_all_teams_in_department(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        creator = make_user()
        manager = make_user()
        _grant(creator, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.read", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        creator_headers = auth_headers(creator)
        manager_headers = auth_headers(manager)
        dept_id, team_id = dept.id, team.id

    client.post(
        "/api/tasks",
        json={"title": "Dept-level", "department_id": dept_id},
        headers=creator_headers,
    )
    client.post(
        "/api/tasks",
        json={"title": "Team-level", "department_id": dept_id, "team_id": team_id},
        headers=creator_headers,
    )

    resp = client.get("/api/tasks", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 2


def test_team_lead_sees_only_own_team_tasks(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team_a = make_team(dept)
        team_b = make_team(dept)
        creator = make_user()
        lead = make_user()
        _grant(creator, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(lead, "tasks.task.read", ScopeType.TEAM, team_a.id)
        db.session.commit()
        creator_headers = auth_headers(creator)
        lead_headers = auth_headers(lead)
        dept_id, team_a_id, team_b_id = dept.id, team_a.id, team_b.id

    client.post(
        "/api/tasks",
        json={"title": "Team A task", "department_id": dept_id, "team_id": team_a_id},
        headers=creator_headers,
    )
    client.post(
        "/api/tasks",
        json={"title": "Team B task", "department_id": dept_id, "team_id": team_b_id},
        headers=creator_headers,
    )

    resp = client.get("/api/tasks", headers=lead_headers)
    body = resp.get_json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["title"] == "Team A task"


def test_get_single_task_denied_outside_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        creator = make_user()
        outsider = make_user()
        _grant(creator, "tasks.task.create", ScopeType.DEPARTMENT, dept_a.id)
        _grant(outsider, "tasks.task.read", ScopeType.DEPARTMENT, dept_b.id)
        db.session.commit()
        creator_headers = auth_headers(creator)
        outsider_headers = auth_headers(outsider)
        dept_a_id = dept_a.id

    create_resp = client.post(
        "/api/tasks", json={"title": "Private", "department_id": dept_a_id}, headers=creator_headers
    )
    task_id = create_resp.get_json()["data"]["id"]

    resp = client.get(f"/api/tasks/{task_id}", headers=outsider_headers)
    assert resp.status_code == 403


# --- ASSIGN (step 3: organizational-relationship check) ---------------


def test_assign_task_to_team_member_succeeds(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        manager = make_user()
        assignee = make_user()
        add_team_member(team, assignee)
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        _allow_assign_all(manager)
        db.session.commit()
        manager_headers = auth_headers(manager)
        dept_id, team_id, assignee_id = dept.id, team.id, assignee.id

    create_resp = client.post(
        "/api/tasks",
        json={"title": "Assign me", "department_id": dept_id, "team_id": team_id},
        headers=manager_headers,
    )
    task_id = create_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/api/tasks/{task_id}/assign", json={"assignee_user_id": assignee_id}, headers=manager_headers
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["assignee_user_id"] == assignee_id


def test_assign_task_to_non_team_member_rejected(client, app):
    """AUTHORIZATION.md §8: tasks.task.assign additionally confirms the
    assignee is actually a member of the task's team."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        manager = make_user()
        non_member = make_user()
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        manager_headers = auth_headers(manager)
        dept_id, team_id, non_member_id = dept.id, team.id, non_member.id

    create_resp = client.post(
        "/api/tasks",
        json={"title": "Assign me", "department_id": dept_id, "team_id": team_id},
        headers=manager_headers,
    )
    task_id = create_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/api/tasks/{task_id}/assign",
        json={"assignee_user_id": non_member_id},
        headers=manager_headers,
    )
    assert resp.status_code == 409


def test_assign_denied_without_permission(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        creator = make_user()
        assignee = make_user()
        _grant(creator, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        creator_headers = auth_headers(creator)
        dept_id, assignee_id = dept.id, assignee.id

    create_resp = client.post(
        "/api/tasks", json={"title": "No assign perm", "department_id": dept_id},
        headers=creator_headers,
    )
    task_id = create_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/api/tasks/{task_id}/assign", json={"assignee_user_id": assignee_id}, headers=creator_headers
    )
    assert resp.status_code == 403


def test_unassign_task(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        manager = make_user()
        assignee = make_user()
        add_team_member(team, assignee)
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        _allow_assign_all(manager)
        db.session.commit()
        headers = auth_headers(manager)
        dept_id, team_id, assignee_id = dept.id, team.id, assignee.id

    create_resp = client.post(
        "/api/tasks",
        json={"title": "Unassign me", "department_id": dept_id, "team_id": team_id},
        headers=headers,
    )
    task_id = create_resp.get_json()["data"]["id"]
    client.post(f"/api/tasks/{task_id}/assign", json={"assignee_user_id": assignee_id}, headers=headers)

    resp = client.delete(f"/api/tasks/{task_id}/assign/{assignee_id}", headers=headers)
    assert resp.status_code == 200

    # Re-assigning the same user after unassign must succeed (no stale
    # "already assigned" conflict from the unassigned row).
    resp2 = client.post(
        f"/api/tasks/{task_id}/assign", json={"assignee_user_id": assignee_id}, headers=headers
    )
    assert resp2.status_code == 201


# --- UPDATE / DELETE ----------------------------------------------------


def test_update_and_delete_task(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(user, "tasks.task.update", ScopeType.DEPARTMENT, dept.id)
        _grant(user, "tasks.task.delete", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    create_resp = client.post(
        "/api/tasks", json={"title": "Original", "department_id": dept_id}, headers=headers
    )
    task_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/api/tasks/{task_id}", json={"status": "IN_PROGRESS"}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "IN_PROGRESS"

    resp = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert resp.status_code == 404


# --- ANALYTICS ----------------------------------------------------------


def test_analytics_requires_dedicated_permission(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        # Holds tasks.task.read but NOT tasks.analytics.read.
        _grant(user, "tasks.task.read", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/tasks/analytics", headers=headers)
    assert resp.status_code == 403


def test_analytics_counts_by_status_within_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(user, "tasks.analytics.read", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    client.post("/api/tasks", json={"title": "A", "department_id": dept_id}, headers=headers)
    client.post(
        "/api/tasks",
        json={"title": "B", "department_id": dept_id, "status": "DONE"},
        headers=headers,
    )

    resp = client.get("/api/tasks/analytics", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total"] == 2
    assert data["by_status"]["TODO"] == 1
    assert data["by_status"]["DONE"] == 1


# --- End-to-end scenario from IMPLEMENTATION_PLAN.md Phase 4a's own
# test description, using the actual seeded roles/scopes -------------


def test_sales_manager_and_specialist_seeded_scenario(client, app):
    """مدیر فروش can create/assign within فروش and its teams; denied
    outside. sales_specialist (closest existing role to کارشناس فروش
    داخلی -- see scripts/seed_roles_permissions.py) can assign only
    within فروش داخلی."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seedmod", "scripts/seed_roles_permissions.py"
    )
    seedmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seedmod)

    with app.app_context():
        roles_by_name = seedmod.seed_roles()
        orgs_by_name = seedmod.seed_organizations()
        depts_by_name = seedmod.seed_departments(orgs_by_name)
        teams_by_name = seedmod.seed_teams(depts_by_name)
        seedmod.seed_admin_global_grant(roles_by_name)
        seedmod.seed_registry_permissions_and_admin_grants(roles_by_name)
        seedmod.seed_task_scoped_grants(roles_by_name, depts_by_name, teams_by_name)

        from tests.core4.factories import assign_role

        sales_manager_user = make_user()
        assign_role(sales_manager_user, roles_by_name["sales_manager"])
        specialist_user = make_user()
        assign_role(specialist_user, roles_by_name["sales_specialist"])

        finance_dept = depts_by_name["مالی"]
        db.session.commit()

        manager_headers = auth_headers(sales_manager_user)
        specialist_headers = auth_headers(specialist_user)
        sales_dept_id = depts_by_name["فروش"].id
        sales_internal_team_id = teams_by_name["فروش داخلی"].id
        finance_dept_id = finance_dept.id

    # مدیر فروش creates within فروش -> allowed.
    resp = client.post(
        "/api/tasks",
        json={"title": "Quarter close", "department_id": sales_dept_id},
        headers=manager_headers,
    )
    assert resp.status_code == 201

    # مدیر فروش creates within مالی -> denied (no grant covers it).
    resp = client.post(
        "/api/tasks",
        json={"title": "Finance task", "department_id": finance_dept_id},
        headers=manager_headers,
    )
    assert resp.status_code == 403

    # sales_specialist creates within فروش داخلی team -> allowed.
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Internal sales follow-up",
            "department_id": sales_dept_id,
            "team_id": sales_internal_team_id,
        },
        headers=specialist_headers,
    )
    assert resp.status_code == 201

    # sales_specialist creates a department-level (no team) task -> denied,
    # their grant only covers the one team, not the whole department.
    resp = client.post(
        "/api/tasks",
        json={"title": "Whole-dept task", "department_id": sales_dept_id},
        headers=specialist_headers,
    )
    assert resp.status_code == 403


# --- ASSIGNMENT RULES -------------------------------------------------


def test_assign_blocked_without_rule_then_allowed_with_rule(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        manager = make_user()
        target = make_user()
        target.department_id = dept.id
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(manager)
        dept_id, target_id, manager_id = dept.id, target.id, manager.id

    r = client.post("/api/tasks", json={"title": "x", "department_id": dept_id}, headers=headers)
    task_id = r.get_json()["data"]["id"]
    r = client.post(f"/api/tasks/{task_id}/assign", json={"assignee_user_id": target_id}, headers=headers)
    assert r.status_code == 403

    # creating a task for another user is also blocked atomically
    r = client.post("/api/tasks", json={"title": "y", "department_id": dept_id,
                                        "assignee_user_ids": [target_id]}, headers=headers)
    assert r.status_code == 403

    with app.app_context():
        from app.modules.tasks.models import RuleSubject, RuleTarget, TaskAssignmentRule
        db.session.add(TaskAssignmentRule(grantor_type=RuleSubject.USER, grantor_id=manager_id,
                                          target_type=RuleTarget.DEPARTMENT, target_id=dept_id))
        db.session.commit()

    r = client.post(f"/api/tasks/{task_id}/assign", json={"assignee_user_id": target_id}, headers=headers)
    assert r.status_code == 201
    r = client.post("/api/tasks", json={"title": "z", "department_id": dept_id,
                                        "assignee_user_ids": [target_id]}, headers=headers)
    assert r.status_code == 201
    assert r.get_json()["data"]["assignee_ids"] == [target_id]


def test_only_admin_or_permission_holder_can_manage_rules(client, app):
    with app.app_context():
        plain = make_user()
        manager = make_user()
        other = make_user()
        _grant(manager, "core.permission.update", ScopeType.GLOBAL)
        db.session.commit()
        plain_h, mgr_h = auth_headers(plain), auth_headers(manager)
        manager_id, other_id = manager.id, other.id

    body = {"grantor_type": "USER", "grantor_id": manager_id, "target_type": "USER", "target_id": other_id}
    assert client.post("/api/tasks/assignment-rules", json=body, headers=plain_h).status_code == 403
    r = client.post("/api/tasks/assignment-rules", json=body, headers=mgr_h)
    assert r.status_code == 201
    rule_id = r.get_json()["data"]["id"]
    assert client.post("/api/tasks/assignment-rules", json=body, headers=mgr_h).status_code == 409
    assert client.delete(f"/api/tasks/assignment-rules/{rule_id}", headers=plain_h).status_code == 403
    assert client.delete(f"/api/tasks/assignment-rules/{rule_id}", headers=mgr_h).status_code == 200


# --- ASSIGNEE STATUS TRANSITIONS ---------------------------------------


def test_assignee_can_only_request_completion_approval(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        creator = make_user()
        worker = make_user()
        worker.department_id = dept.id
        _grant(creator, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(creator, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        _grant(creator, "tasks.task.update", ScopeType.DEPARTMENT, dept.id)
        _grant(worker, "tasks.task.update", ScopeType.DEPARTMENT, dept.id)
        _allow_assign_all(creator)
        db.session.commit()
        creator_h, worker_h = auth_headers(creator), auth_headers(worker)
        dept_id, worker_id = dept.id, worker.id

    r = client.post("/api/tasks", json={"title": "t", "department_id": dept_id,
                                        "assignee_user_ids": [worker_id]}, headers=creator_h)
    assert r.status_code == 201
    task_id = r.get_json()["data"]["id"]

    for blocked in ("DONE", "CANCELLED", "IN_PROGRESS"):
        r = client.patch(f"/api/tasks/{task_id}", json={"status": blocked}, headers=worker_h)
        assert r.status_code == 403, blocked

    r = client.patch(f"/api/tasks/{task_id}", json={"status": "REVIEW"}, headers=worker_h)
    assert r.status_code == 200
    assert r.get_json()["data"]["status"] == "REVIEW"

    # Re-sending the current status is a no-op, not a violation.
    r = client.patch(f"/api/tasks/{task_id}", json={"status": "REVIEW", "title": "t2"}, headers=worker_h)
    assert r.status_code == 200

    # Non-assignees keep their existing behaviour (no new permission rules).
    r = client.patch(f"/api/tasks/{task_id}", json={"status": "DONE"}, headers=creator_h)
    assert r.status_code == 200


def test_assignee_cannot_create_task_already_done_for_self(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(user, "tasks.task.update", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id, uid = dept.id, user.id

    r = client.post("/api/tasks", json={"title": "x", "department_id": dept_id, "status": "DONE",
                                        "assignee_user_ids": [uid]}, headers=headers)
    assert r.status_code == 403


# --- ASSIGNEE APPROVAL REQUEST / NOTES / CHECKLIST --------------------


def _task_with_assignee(client, app):
    """creator (create+assign+update) -> task assigned to `worker`
    (worker holds NO tasks.task.update). Returns ids + auth headers."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        creator = make_user()
        worker = make_user()
        outsider = make_user()
        worker.department_id = dept.id
        for key in ("tasks.task.create", "tasks.task.assign", "tasks.task.update", "tasks.task.read"):
            _grant(creator, key, ScopeType.DEPARTMENT, dept.id)
        _grant(worker, "tasks.task.read", ScopeType.DEPARTMENT, dept.id)
        _allow_assign_all(creator)
        db.session.commit()
        creator_h, worker_h, outsider_h = auth_headers(creator), auth_headers(worker), auth_headers(outsider)
        dept_id, worker_id = dept.id, worker.id

    r = client.post("/api/tasks", json={"title": "t", "department_id": dept_id,
                                        "assignee_user_ids": [worker_id]}, headers=creator_h)
    assert r.status_code == 201
    return r.get_json()["data"]["id"], creator_h, worker_h, outsider_h


def _manager_headers(app, task_id):
    """A «مدیر» of the task's department: holds tasks.task.delete (+ read) there."""
    from app.modules.tasks.models import Task

    with app.app_context():
        dept_id = db.session.get(Task, task_id).department_id
        mgr = make_user()
        mgr.department_id = dept_id
        for key in ("tasks.task.read", "tasks.task.delete"):
            _grant(mgr, key, ScopeType.DEPARTMENT, dept_id)
        db.session.commit()
        return auth_headers(mgr)


def test_assignee_without_update_permission_can_only_request_approval(client, app):
    task_id, creator_h, worker_h, _ = _task_with_assignee(client, app)

    for blocked in ("DONE", "CANCELLED", "IN_PROGRESS"):
        r = client.patch(f"/api/tasks/{task_id}", json={"status": blocked}, headers=worker_h)
        assert r.status_code == 403, blocked
    r = client.patch(f"/api/tasks/{task_id}", json={"title": "hack"}, headers=worker_h)
    assert r.status_code == 403

    r = client.patch(f"/api/tasks/{task_id}", json={"status": "REVIEW", "progress": 80}, headers=worker_h)
    assert r.status_code == 200
    assert r.get_json()["data"]["status"] == "REVIEW"

    # the approver (not the assignee) can complete it
    r = client.patch(f"/api/tasks/{task_id}", json={"status": "DONE"}, headers=creator_h)
    assert r.status_code == 200


def test_task_notes(client, app):
    task_id, creator_h, worker_h, outsider_h = _task_with_assignee(client, app)

    assert client.get(f"/api/tasks/{task_id}/notes", headers=outsider_h).status_code == 403
    assert client.post(f"/api/tasks/{task_id}/notes", json={"body": "x"}, headers=outsider_h).status_code == 403
    assert client.post(f"/api/tasks/{task_id}/notes", json={"body": "   "}, headers=creator_h).status_code == 400

    r = client.post(f"/api/tasks/{task_id}/notes", json={"body": "client wants blue"}, headers=worker_h)
    assert r.status_code == 201
    note_id = r.get_json()["data"]["id"]

    r = client.get(f"/api/tasks/{task_id}/notes", headers=creator_h)
    assert r.status_code == 200
    assert [n["body"] for n in r.get_json()["data"]] == ["client wants blue"]

    # only a manager («tasks.task.delete») may delete a message -- not the outsider, not the
    # note's own author, not even the task's creator
    assert client.delete(f"/api/tasks/{task_id}/notes/{note_id}", headers=outsider_h).status_code == 403
    assert client.delete(f"/api/tasks/{task_id}/notes/{note_id}", headers=worker_h).status_code == 403
    assert client.delete(f"/api/tasks/{task_id}/notes/{note_id}", headers=creator_h).status_code == 403
    assert client.delete(f"/api/tasks/{task_id}/notes/{note_id}", headers=_manager_headers(app, task_id)).status_code == 200
    assert client.get(f"/api/tasks/{task_id}/notes", headers=creator_h).get_json()["data"] == []


def test_task_checklist(client, app):
    task_id, creator_h, worker_h, outsider_h = _task_with_assignee(client, app)

    r = client.post(f"/api/tasks/{task_id}/checklist", json={"title": "step 1"}, headers=creator_h)
    assert r.status_code == 201
    item_id = r.get_json()["data"]["id"]
    assert client.post(f"/api/tasks/{task_id}/checklist", json={"title": "step 2"}, headers=worker_h).status_code == 201
    assert client.post(f"/api/tasks/{task_id}/checklist", json={"title": "no"}, headers=outsider_h).status_code == 403

    # assignee ticks the item, but cannot rename or delete it
    r = client.patch(f"/api/tasks/{task_id}/checklist/{item_id}", json={"is_done": True}, headers=worker_h)
    assert r.status_code == 200
    assert r.get_json()["data"]["is_done"] is True
    assert r.get_json()["data"]["completed_at"] is not None
    assert client.patch(f"/api/tasks/{task_id}/checklist/{item_id}", json={"title": "x"}, headers=worker_h).status_code == 403
    assert client.delete(f"/api/tasks/{task_id}/checklist/{item_id}", headers=worker_h).status_code == 403
    assert client.patch(f"/api/tasks/{task_id}/checklist/{item_id}", json={"is_done": True}, headers=outsider_h).status_code == 403

    r = client.get(f"/api/tasks/{task_id}/checklist", headers=creator_h)
    assert [i["title"] for i in r.get_json()["data"]] == ["step 1", "step 2"]

    assert client.delete(f"/api/tasks/{task_id}/checklist/{item_id}", headers=creator_h).status_code == 403  # creator is not a manager
    assert client.delete(f"/api/tasks/{task_id}/checklist/{item_id}", headers=_manager_headers(app, task_id)).status_code == 200
    r = client.get(f"/api/tasks/{task_id}/checklist", headers=creator_h)
    assert [i["title"] for i in r.get_json()["data"]] == ["step 2"]


def test_create_only_rule_does_not_grant_assign(client, app):
    """action=CREATE lets X pre-assign a new task to Y, but X still cannot
    assign an EXISTING task to Y without a separate ASSIGN (or BOTH) rule."""
    with app.app_context():
        from app.modules.tasks.models import RuleAction, RuleSubject, RuleTarget, TaskAssignmentRule

        dept = make_department(make_organization())
        manager = make_user()
        target = make_user()
        target.department_id = dept.id
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        db.session.add(TaskAssignmentRule(
            grantor_type=RuleSubject.USER, grantor_id=manager.id,
            target_type=RuleTarget.DEPARTMENT, target_id=dept.id, action=RuleAction.CREATE,
        ))
        db.session.commit()
        headers = auth_headers(manager)
        dept_id, target_id = dept.id, target.id

    r = client.post("/api/tasks", json={"title": "x", "department_id": dept_id,
                                        "assignee_user_ids": [target_id]}, headers=headers)
    assert r.status_code == 201
    task_id = r.get_json()["data"]["id"]

    r2 = client.post("/api/tasks", json={"title": "y", "department_id": dept_id}, headers=headers)
    task2_id = r2.get_json()["data"]["id"]
    r3 = client.post(f"/api/tasks/{task2_id}/assign", json={"assignee_user_id": target_id}, headers=headers)
    assert r3.status_code == 403

    # the first task's own creation-time assignment is unaffected
    assert client.get(f"/api/tasks/{task_id}", headers=headers).get_json()["data"]["assignee_ids"] == [target_id]


def test_assign_only_rule_does_not_grant_create_with_assignee(client, app):
    """The mirror image: action=ASSIGN lets X assign existing tasks to Y but
    not create a new task pre-assigned to Y."""
    with app.app_context():
        from app.modules.tasks.models import RuleAction, RuleSubject, RuleTarget, TaskAssignmentRule

        dept = make_department(make_organization())
        manager = make_user()
        target = make_user()
        target.department_id = dept.id
        _grant(manager, "tasks.task.create", ScopeType.DEPARTMENT, dept.id)
        _grant(manager, "tasks.task.assign", ScopeType.DEPARTMENT, dept.id)
        db.session.add(TaskAssignmentRule(
            grantor_type=RuleSubject.USER, grantor_id=manager.id,
            target_type=RuleTarget.DEPARTMENT, target_id=dept.id, action=RuleAction.ASSIGN,
        ))
        db.session.commit()
        headers = auth_headers(manager)
        dept_id, target_id = dept.id, target.id

    r = client.post("/api/tasks", json={"title": "x", "department_id": dept_id,
                                        "assignee_user_ids": [target_id]}, headers=headers)
    assert r.status_code == 403

    r2 = client.post("/api/tasks", json={"title": "y", "department_id": dept_id}, headers=headers)
    task2_id = r2.get_json()["data"]["id"]
    r3 = client.post(f"/api/tasks/{task2_id}/assign", json={"assignee_user_id": target_id}, headers=headers)
    assert r3.status_code == 201


def test_rule_action_field_round_trips_and_dedup_respects_action(client, app):
    with app.app_context():
        manager = make_user()
        other = make_user()
        _grant(manager, "core.permission.update", ScopeType.GLOBAL)
        db.session.commit()
        headers, manager_id, other_id = auth_headers(manager), manager.id, other.id

    body = {"grantor_type": "USER", "grantor_id": manager_id, "target_type": "USER",
            "target_id": other_id, "action": "CREATE"}
    r = client.post("/api/tasks/assignment-rules", json=body, headers=headers)
    assert r.status_code == 201
    assert r.get_json()["data"]["action"] == "CREATE"

    # same grantor/target but a different action is NOT a duplicate
    r2 = client.post("/api/tasks/assignment-rules", json={**body, "action": "ASSIGN"}, headers=headers)
    assert r2.status_code == 201

    # same grantor/target/action again IS a duplicate
    r3 = client.post("/api/tasks/assignment-rules", json=body, headers=headers)
    assert r3.status_code == 409
