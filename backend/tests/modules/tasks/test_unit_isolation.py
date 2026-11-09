"""Unit (department) isolation for projects & tasks -- regular user / Edit holder / Admin.

Rules under test (all enforced server-side, so changing a URL / id or calling the API directly
cannot bypass them):

  * a user sees and manages only the tasks of their own department (or teams' departments);
  * only a user holding the `admin` role sees / manages every unit;
  * Create / Read / Edit / Delete permissions apply inside the user's own unit -- even when the
    permission matrix gave them a GLOBAL grant (it writes GLOBAL grants for every checked box);
  * files, checklist, messages (notes), assignment history and mentions follow the same rule;
  * being the creator / an assignee of a task does not keep access once it is outside the unit.
"""
import io

import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from app.modules.tasks.models import RuleSubject, RuleTarget, TaskAssignmentRule
from tests.core4.factories import (
    add_team_member, assign_role, auth_headers, grant_user_permission, make_department,
    make_organization, make_permission, make_role, make_team, make_user,
)

API = "/api/tasks"
ALL_KEYS = ("tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign", "tasks.task.delete")


def _global(user, *keys):
    """What the permission matrix writes: the permission at GLOBAL scope."""
    for key in keys:
        perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
        grant_user_permission(user, perm, ScopeType.GLOBAL)


def _assign_everyone(user):
    db.session.add(TaskAssignmentRule(grantor_type=RuleSubject.USER, grantor_id=user.id, target_type=RuleTarget.ALL))


@pytest.fixture(autouse=True)
def _upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)


@pytest.fixture
def world(app):
    """Dept A: a_user (read only), a_editor (read/create/update/assign), a_boss (+delete), a_worker.
    Dept B: b_editor (same rights as a_editor).  Plus a real admin.  All grants are GLOBAL, exactly
    like the permission matrix writes them."""
    with app.app_context():
        org = make_organization()
        a, b = make_department(org), make_department(org)
        team_a, team_b = make_team(a), make_team(b)

        users = {n: make_user() for n in ("a_user", "a_editor", "a_boss", "a_worker", "b_editor", "admin", "loner")}
        for n in ("a_user", "a_editor", "a_boss", "a_worker"):
            users[n].department_id = a.id
        users["b_editor"].department_id = b.id
        users["admin"].department_id = a.id  # admin's own placement must not matter

        _global(users["a_user"], "tasks.task.read")
        _global(users["a_worker"], "tasks.task.read")
        _global(users["a_editor"], "tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign")
        _global(users["a_boss"], *ALL_KEYS)
        _global(users["b_editor"], "tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign")
        _global(users["loner"], *ALL_KEYS)  # holds everything but belongs to no department
        admin_role = make_role(name="admin", display_name="Admin")
        assign_role(users["admin"], admin_role)
        _global(users["admin"], *ALL_KEYS, "tasks.analytics.read")
        for n in ("a_editor", "a_boss", "b_editor", "admin"):
            _assign_everyone(users[n])
        db.session.commit()
        return {
            "a": a.id, "b": b.id, "team_a": team_a.id, "team_b": team_b.id,
            "ids": {n: u.id for n, u in users.items()},
            "h": {n: auth_headers(u) for n, u in users.items()},
        }


def _mk(client, world, who, dept, **body):
    body.setdefault("title", f"task of {dept}")
    r = client.post(API, json={"department_id": world[dept], **body}, headers=world["h"][who])
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


# ---------------------------------------------------------------------------
# listing / reading
# ---------------------------------------------------------------------------
def test_regular_user_sees_only_own_unit_even_with_a_global_read_grant(client, world):
    ta = _mk(client, world, "a_editor", "a")
    tb = _mk(client, world, "b_editor", "b")
    h = world["h"]
    assert {t["id"] for t in client.get(API, headers=h["a_user"]).get_json()["data"]} == {ta["id"]}
    assert {t["id"] for t in client.get(API, headers=h["b_editor"]).get_json()["data"]} == {tb["id"]}
    # direct access by id from the wrong unit
    assert client.get(f"{API}/{tb['id']}", headers=h["a_user"]).status_code == 403
    assert client.get(f"{API}/{ta['id']}", headers=h["b_editor"]).status_code == 403


def test_user_without_a_department_sees_nothing(client, world):
    _mk(client, world, "a_editor", "a")
    r = client.get(API, headers=world["h"]["loner"])
    assert r.status_code == 200 and r.get_json()["data"] == []


def test_admin_sees_every_unit(client, world):
    ta = _mk(client, world, "a_editor", "a")
    tb = _mk(client, world, "b_editor", "b")
    got = {t["id"] for t in client.get(API, headers=world["h"]["admin"]).get_json()["data"]}
    assert {ta["id"], tb["id"]} <= got
    assert client.get(f"{API}/{tb['id']}", headers=world["h"]["admin"]).status_code == 200


def test_meta_lists_only_own_projects_teams_and_people(client, world):
    meta = client.get(f"{API}/meta", headers=world["h"]["a_editor"]).get_json()["data"]
    assert [d["id"] for d in meta["departments"]] == [world["a"]]
    assert {t["id"] for t in meta["teams"]} == {world["team_a"]}
    assert all(u["department_id"] == world["a"] for u in meta["assignable_users"])
    admin_meta = client.get(f"{API}/meta", headers=world["h"]["admin"]).get_json()["data"]
    assert {d["id"] for d in admin_meta["departments"]} >= {world["a"], world["b"]}


def test_analytics_is_clamped_to_the_unit(client, world, app):
    with app.app_context():
        from app.core.users.models import User
        _global(db.session.get(User, world["ids"]["a_boss"]), "tasks.analytics.read")
        db.session.commit()
    _mk(client, world, "a_editor", "a")
    _mk(client, world, "b_editor", "b")
    mine = client.get(f"{API}/analytics", headers=world["h"]["a_boss"]).get_json()["data"]
    assert mine["total"] == 1
    assert client.get(f"{API}/analytics", headers=world["h"]["admin"]).get_json()["data"]["total"] >= 2


# ---------------------------------------------------------------------------
# create / edit / delete
# ---------------------------------------------------------------------------
def test_create_is_limited_to_the_users_unit(client, world):
    h = world["h"]
    r = client.post(API, json={"title": "x", "department_id": world["b"]}, headers=h["a_editor"])
    assert r.status_code == 403
    # a team of another department cannot be smuggled in either
    r = client.post(API, json={"title": "x", "department_id": world["a"], "team_id": world["team_b"]}, headers=h["a_editor"])
    assert r.status_code in (403, 409)
    assert client.post(API, json={"title": "x", "department_id": world["b"]}, headers=h["admin"]).status_code == 201


def test_edit_holder_manages_only_own_unit(client, world):
    ta = _mk(client, world, "a_editor", "a")
    tb = _mk(client, world, "b_editor", "b")
    h = world["h"]
    assert client.patch(f"{API}/{ta['id']}", json={"priority": "HIGH"}, headers=h["a_editor"]).status_code == 200
    assert client.patch(f"{API}/{tb['id']}", json={"priority": "HIGH"}, headers=h["a_editor"]).status_code == 403
    assert client.patch(f"{API}/{ta['id']}", json={"priority": "LOW"}, headers=h["b_editor"]).status_code == 403
    # admin may edit anywhere
    assert client.patch(f"{API}/{tb['id']}", json={"priority": "LOW"}, headers=h["admin"]).status_code == 200


def test_read_only_user_cannot_edit_even_inside_the_unit(client, world):
    ta = _mk(client, world, "a_editor", "a")
    assert client.patch(f"{API}/{ta['id']}", json={"priority": "HIGH"}, headers=world["h"]["a_user"]).status_code == 403


def test_a_department_cannot_be_changed_through_update(client, world):
    ta = _mk(client, world, "a_editor", "a")
    r = client.patch(f"{API}/{ta['id']}", json={"department_id": world["b"]}, headers=world["h"]["a_editor"])
    # unknown fields are ignored by the schema: the task must still live in A
    assert r.status_code in (200, 400)
    assert client.get(f"{API}/{ta['id']}", headers=world["h"]["admin"]).get_json()["data"]["department_id"] == world["a"]


def test_delete_is_limited_to_the_unit(client, world):
    tb = _mk(client, world, "b_editor", "b")
    assert client.delete(f"{API}/{tb['id']}", headers=world["h"]["a_boss"]).status_code == 403
    assert client.get(f"{API}/{tb['id']}", headers=world["h"]["admin"]).status_code == 200  # still there
    assert client.delete(f"{API}/{tb['id']}", headers=world["h"]["admin"]).status_code == 200


# ---------------------------------------------------------------------------
# sub-resources: notes (messages), checklist, files, assignments, mentions
# ---------------------------------------------------------------------------
def test_notes_checklist_files_and_assignments_follow_the_unit_rule(client, world):
    tb = _mk(client, world, "b_editor", "b")
    tid = tb["id"]
    hb, ha, hadm = world["h"]["b_editor"], world["h"]["a_boss"], world["h"]["admin"]

    note = client.post(f"{API}/{tid}/notes", json={"body": "hello"}, headers=hb).get_json()["data"]
    item = client.post(f"{API}/{tid}/checklist", json={"title": "step"}, headers=hb).get_json()["data"]
    up = client.post(
        f"{API}/{tid}/files", data={"files": (io.BytesIO(b"secret"), "plan.txt")},
        headers=hb, content_type="multipart/form-data",
    )
    assert up.status_code == 201, up.get_json()
    fid = up.get_json()["data"][0]["id"]

    forbidden = [
        client.get(f"{API}/{tid}/notes", headers=ha),
        client.post(f"{API}/{tid}/notes", json={"body": "intruder"}, headers=ha),
        client.delete(f"{API}/{tid}/notes/{note['id']}", headers=ha),
        client.get(f"{API}/{tid}/checklist", headers=ha),
        client.post(f"{API}/{tid}/checklist", json={"title": "x"}, headers=ha),
        client.patch(f"{API}/{tid}/checklist/{item['id']}", json={"is_done": True}, headers=ha),
        client.delete(f"{API}/{tid}/checklist/{item['id']}", headers=ha),
        client.get(f"{API}/{tid}/files", headers=ha),
        client.get(f"{API}/{tid}/files/{fid}", headers=ha),
        client.post(f"{API}/{tid}/files", data={"files": (io.BytesIO(b"x"), "x.txt")}, headers=ha,
                    content_type="multipart/form-data"),
        client.delete(f"{API}/{tid}/files/{fid}", headers=ha),
        client.get(f"{API}/{tid}/assignments", headers=ha),
        client.get(f"{API}/{tid}/mention-candidates", headers=ha),
        client.post(f"{API}/{tid}/assign", json={"assignee_user_id": world["ids"]["a_worker"]}, headers=ha),
        client.put(f"{API}/{tid}/assignees", json={"assignee_user_ids": [world["ids"]["a_worker"]]}, headers=ha),
        client.delete(f"{API}/{tid}/assign/{world['ids']['b_editor']}", headers=ha),
        client.post(f"{API}/{tid}/refer", json={"to_user_id": world["ids"]["a_worker"]}, headers=ha),
    ]
    assert [r.status_code for r in forbidden] == [403] * len(forbidden)

    # the owner unit and the admin still get through
    assert client.get(f"{API}/{tid}/files/{fid}", headers=hb).status_code == 200
    assert client.get(f"{API}/{tid}/files/{fid}", headers=hadm).status_code == 200
    assert client.get(f"{API}/{tid}/notes", headers=hadm).status_code == 200


def test_a_file_id_from_another_task_cannot_be_reached_through_my_task(client, world):
    ta = _mk(client, world, "a_editor", "a")
    tb = _mk(client, world, "b_editor", "b")
    up = client.post(
        f"{API}/{tb['id']}/files", data={"files": (io.BytesIO(b"b-secret"), "b.txt")},
        headers=world["h"]["b_editor"], content_type="multipart/form-data",
    )
    fid = up.get_json()["data"][0]["id"]
    # Right task id (mine), wrong unit's file id -> 404, never the bytes.
    assert client.get(f"{API}/{ta['id']}/files/{fid}", headers=world["h"]["a_editor"]).status_code == 404


def test_cannot_assign_someone_from_another_unit(client, world):
    ta = _mk(client, world, "a_editor", "a")
    r = client.post(f"{API}/{ta['id']}/assign", json={"assignee_user_id": world["ids"]["b_editor"]},
                    headers=world["h"]["a_editor"])
    assert r.status_code in (403, 409)
    r = client.post(API, json={"title": "x", "department_id": world["a"],
                               "assignee_user_ids": [world["ids"]["b_editor"]]}, headers=world["h"]["a_editor"])
    assert r.status_code in (403, 409)


def test_mentioning_a_user_outside_the_unit_is_rejected(client, world):
    ta = _mk(client, world, "a_editor", "a")
    r = client.post(f"{API}/{ta['id']}/notes", json={"body": f"hi @[{world['ids']['b_editor']}]"},
                    headers=world["h"]["a_editor"])
    assert r.status_code == 409
    cands = client.get(f"{API}/{ta['id']}/mention-candidates", headers=world["h"]["a_editor"]).get_json()["data"]
    assert world["ids"]["b_editor"] not in {c["id"] for c in cands}


# ---------------------------------------------------------------------------
# losing the unit loses the access (creator / assignee shortcuts no longer work)
# ---------------------------------------------------------------------------
def test_creator_and_assignee_lose_access_when_they_leave_the_unit(client, world, app):
    t = _mk(client, world, "a_editor", "a", assignee_user_ids=[world["ids"]["a_worker"]])
    tid = t["id"]
    h = world["h"]
    assert client.get(f"{API}/{tid}", headers=h["a_worker"]).status_code == 200
    assert client.get(f"{API}/{tid}/notes", headers=h["a_worker"]).status_code == 200

    with app.app_context():  # transfer both people to department B
        from app.core.users.models import User
        for n in ("a_editor", "a_worker"):
            db.session.get(User, world["ids"][n]).department_id = world["b"]
        db.session.commit()

    for who in ("a_editor", "a_worker"):
        assert client.get(f"{API}/{tid}", headers=h[who]).status_code == 403
        assert client.get(f"{API}/{tid}/notes", headers=h[who]).status_code == 403
        assert client.get(f"{API}/{tid}/checklist", headers=h[who]).status_code == 403
        assert client.get(f"{API}/{tid}/files", headers=h[who]).status_code == 403
        assert client.patch(f"{API}/{tid}", json={"status": "REVIEW"}, headers=h[who]).status_code == 403
        assert tid not in {x["id"] for x in client.get(API, headers=h[who]).get_json()["data"]}
        assert client.post(f"{API}/{tid}/refer", json={"to_user_id": world["ids"]["a_user"]}, headers=h[who]).status_code == 403
    meta = client.get(f"{API}/meta", headers=h["a_editor"]).get_json()["data"]
    assert [d["id"] for d in meta["departments"]] == [world["b"]]


def test_team_membership_extends_the_unit_to_that_teams_department(client, world, app):
    tb = _mk(client, world, "b_editor", "b")
    assert client.get(f"{API}/{tb['id']}", headers=world["h"]["a_user"]).status_code == 403
    with app.app_context():
        from app.core.teams.models import Team
        from app.core.users.models import User
        add_team_member(db.session.get(Team, world["team_b"]), db.session.get(User, world["ids"]["a_user"]))
        db.session.commit()
    assert client.get(f"{API}/{tb['id']}", headers=world["h"]["a_user"]).status_code == 200


def test_notifications_about_a_task_outside_the_unit_are_hidden(client, world, app):
    t = _mk(client, world, "a_editor", "a", assignee_user_ids=[world["ids"]["a_worker"]])
    items = client.get("/api/notifications", headers=world["h"]["a_worker"]).get_json()["data"]["items"]
    assert any(n["task_id"] == t["id"] for n in items)
    with app.app_context():
        from app.core.users.models import User
        db.session.get(User, world["ids"]["a_worker"]).department_id = world["b"]
        db.session.commit()
    items = client.get("/api/notifications", headers=world["h"]["a_worker"]).get_json()["data"]["items"]
    assert not any(n["task_id"] == t["id"] for n in items)


# ---------------------------------------------------------------------------
# assignment rules are unit-bound for non-admins
# ---------------------------------------------------------------------------
def test_rule_management_is_unit_bound_for_non_admins(client, world, app):
    with app.app_context():
        from app.core.users.models import User
        perm = db.session.query(Permission).filter_by(key="core.permission.update").first() or make_permission("core.permission.update")
        read = db.session.query(Permission).filter_by(key="core.permission.read").first() or make_permission("core.permission.read")
        grant_user_permission(db.session.get(User, world["ids"]["a_boss"]), perm, ScopeType.GLOBAL)
        grant_user_permission(db.session.get(User, world["ids"]["a_boss"]), read, ScopeType.GLOBAL)
        db.session.commit()
    h = world["h"]
    inside = {"grantor_type": "USER", "grantor_id": world["ids"]["a_editor"], "target_type": "USER",
              "target_id": world["ids"]["a_worker"], "action": "BOTH"}
    cross_user = {**inside, "target_id": world["ids"]["b_editor"]}
    cross_dept = {**inside, "target_type": "DEPARTMENT", "target_id": world["b"]}
    everyone = {**inside, "target_type": "ALL", "target_id": None}
    assert client.post(f"{API}/assignment-rules", json=inside, headers=h["a_boss"]).status_code == 201
    for body in (cross_user, cross_dept, everyone):
        assert client.post(f"{API}/assignment-rules", json=body, headers=h["a_boss"]).status_code == 403
    assert client.post(f"{API}/assignment-rules", json=cross_dept, headers=h["admin"]).status_code == 201
    # a non-admin only lists rules inside their own unit
    listed = client.get(f"{API}/assignment-rules", headers=h["a_boss"]).get_json()["data"]
    assert all(r["target_type"] in ("USER", "DEPARTMENT", "TEAM") for r in listed)
    assert not any(r["target_type"] == "DEPARTMENT" and r["target_id"] == world["b"] for r in listed)
    # ...and cannot delete a rule that is outside it
    admin_rules = client.get(f"{API}/assignment-rules", headers=h["admin"]).get_json()["data"]
    outside = next(r for r in admin_rules if r["target_type"] == "DEPARTMENT" and r["target_id"] == world["b"])
    assert client.delete(f"{API}/assignment-rules/{outside['id']}", headers=h["a_boss"]).status_code == 403
