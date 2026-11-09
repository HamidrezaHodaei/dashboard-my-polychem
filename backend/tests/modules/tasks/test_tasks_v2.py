"""Tasks: manager-only deletes, unit isolation, files, many assignees, referral chain,
recurring tasks (Jalali), @mentions, Tehran time / UTF-8."""
import io
from datetime import date

import pytest

from app.core.authorization.models import ScopeType
from app.extensions import db
from app.modules.tasks import recurrence
from app.modules.tasks.models import Task
from tests.core4.factories import (
    add_team_member, auth_headers, grant_user_permission, make_department, make_organization, make_permission,
    make_team, make_user,
)
from app.core.permissions.models import Permission

API = "/api/tasks"


def _grant(user, key, scope_type, scope_id=None):
    perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
    grant_user_permission(user, perm, scope_type, scope_id)


def _allow_assign_all(user):
    from app.modules.tasks.models import RuleSubject, RuleTarget, TaskAssignmentRule
    db.session.add(TaskAssignmentRule(grantor_type=RuleSubject.USER, grantor_id=user.id, target_type=RuleTarget.ALL))


@pytest.fixture(autouse=True)
def _upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)


@pytest.fixture
def world(app):
    """Department A: manager, creator, worker1-3.  Department B: other."""
    with app.app_context():
        org = make_organization()
        a, b = make_department(org), make_department(org)
        users = {n: make_user() for n in ("manager", "creator", "w1", "w2", "w3", "other")}
        for n in ("manager", "creator", "w1", "w2", "w3"):
            users[n].department_id = a.id
        users["other"].department_id = b.id
        for key in ("tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign", "tasks.task.delete"):
            _grant(users["manager"], key, ScopeType.DEPARTMENT, a.id)
        for key in ("tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign"):
            _grant(users["creator"], key, ScopeType.DEPARTMENT, a.id)
        for n in ("w1", "w2", "w3"):
            _grant(users[n], "tasks.task.read", ScopeType.DEPARTMENT, a.id)
        for key in ("tasks.task.read", "tasks.task.create", "tasks.task.update", "tasks.task.assign"):
            _grant(users["other"], key, ScopeType.DEPARTMENT, b.id)
        for n in ("manager", "creator", "other"):
            _allow_assign_all(users[n])
        db.session.commit()
        return {
            "dept_a": a.id, "dept_b": b.id,
            "ids": {n: u.id for n, u in users.items()},
            "h": {n: auth_headers(u) for n, u in users.items()},
        }


def _mk(client, world, who="creator", **body):
    body.setdefault("title", "تسک نمونه")
    body.setdefault("department_id", world["dept_a"])
    r = client.post(API, json=body, headers=world["h"][who])
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def _fields(r):
    assert r.status_code == 400, r.get_json()
    return {d["field"] for d in r.get_json()["error"]["details"]}


# ── 1/2/10: manager-only ─────────────────────────────────────────────
def test_title_change_and_delete_are_manager_only(client, world):
    t = _mk(client, world, assignee_user_ids=[world["ids"]["w1"]])
    h = world["h"]
    # the creator holds `update` but is not a manager: other fields yes, the title no
    assert client.patch(f"{API}/{t['id']}", json={"priority": "HIGH"}, headers=h["creator"]).status_code == 200
    assert client.patch(f"{API}/{t['id']}", json={"title": "عنوان جدید"}, headers=h["creator"]).status_code == 403
    # re-sending the SAME title (the edit form does) is not a change
    assert client.patch(f"{API}/{t['id']}", json={"title": t["title"], "priority": "LOW"}, headers=h["creator"]).status_code == 200
    r = client.patch(f"{API}/{t['id']}", json={"title": "عنوان جدید"}, headers=h["manager"])
    assert r.status_code == 200 and r.get_json()["data"]["title"] == "عنوان جدید"
    assert client.delete(f"{API}/{t['id']}", headers=h["creator"]).status_code == 403
    assert client.delete(f"{API}/{t['id']}", headers=h["manager"]).status_code == 200


def test_can_manage_flag_follows_the_manager_role(client, world):
    t = _mk(client, world)
    h = world["h"]
    assert client.get(f"{API}/{t['id']}", headers=h["manager"]).get_json()["data"]["can_manage"] is True
    assert client.get(f"{API}/{t['id']}", headers=h["creator"]).get_json()["data"]["can_manage"] is False
    rows = client.get(API, headers=h["manager"]).get_json()["data"]
    assert rows and all(r["can_manage"] for r in rows)
    assert client.get(f"{API}/meta", headers=h["manager"]).get_json()["data"]["permissions"]["manage"] is True
    assert client.get(f"{API}/meta", headers=h["creator"]).get_json()["data"]["permissions"]["manage"] is False


def test_checklist_and_notes_cannot_be_deleted_by_non_managers(client, world):
    t = _mk(client, world, assignee_user_ids=[world["ids"]["w1"]])
    h = world["h"]
    item = client.post(f"{API}/{t['id']}/checklist", json={"title": "گام ۱"}, headers=h["w1"]).get_json()["data"]
    note = client.post(f"{API}/{t['id']}/notes", json={"body": "سلام"}, headers=h["w1"]).get_json()["data"]
    for who in ("w1", "creator"):
        assert client.delete(f"{API}/{t['id']}/checklist/{item['id']}", headers=h[who]).status_code == 403
        assert client.delete(f"{API}/{t['id']}/notes/{note['id']}", headers=h[who]).status_code == 403
    assert client.delete(f"{API}/{t['id']}/checklist/{item['id']}", headers=h["manager"]).status_code == 200
    assert client.delete(f"{API}/{t['id']}/notes/{note['id']}", headers=h["manager"]).status_code == 200


# ── 3: each unit only sees its own projects and tasks ────────────────
def test_departments_only_see_their_own_projects_and_tasks(client, world):
    ta = _mk(client, world, "creator", title="کار واحد الف")
    tb = _mk(client, world, "other", title="کار واحد ب", department_id=world["dept_b"])
    h = world["h"]
    mine = {r["id"] for r in client.get(API, headers=h["creator"]).get_json()["data"]}
    assert mine == {ta["id"]}
    theirs = {r["id"] for r in client.get(API, headers=h["other"]).get_json()["data"]}
    assert theirs == {tb["id"]}
    assert client.get(f"{API}/{tb['id']}", headers=h["creator"]).status_code == 403
    assert client.get(f"{API}/{ta['id']}", headers=h["other"]).status_code == 403
    # the "projects" (departments) and teams offered in the UI are only your own
    meta = client.get(f"{API}/meta", headers=h["creator"]).get_json()["data"]
    assert [d["id"] for d in meta["departments"]] == [world["dept_a"]]
    assert all(u["department_id"] == world["dept_a"] for u in meta["assignable_users"])
    # cannot create / act in another department
    assert client.post(API, json={"title": "x", "department_id": world["dept_b"]}, headers=h["creator"]).status_code == 403
    assert client.patch(f"{API}/{tb['id']}", json={"priority": "HIGH"}, headers=h["creator"]).status_code == 403
    assert client.get(f"{API}/{tb['id']}/notes", headers=h["creator"]).status_code == 403


def test_a_task_assigned_within_the_unit_is_visible_to_its_assignee(client, world, app):
    ta = _mk(client, world, "creator", assignee_user_ids=[world["ids"]["w1"]])
    assert client.get(f"{API}/{ta['id']}", headers=world["h"]["w1"]).status_code == 200


# ── 4: any number of files ───────────────────────────────────────────
def test_attach_download_and_delete_many_files(client, world):
    t = _mk(client, world, assignee_user_ids=[world["ids"]["w1"]])
    h = world["h"]
    files = [(io.BytesIO(b"%PDF-1.4 a"), "گزارش.pdf"), (io.BytesIO(b"x" * 10), "b.xlsx"), (io.BytesIO(b"png"), "c.png")]
    r = client.post(f"{API}/{t['id']}/files", data={"files": files}, content_type="multipart/form-data", headers=h["w1"])
    assert r.status_code == 201, r.get_json()
    saved = r.get_json()["data"]
    assert [f["name"] for f in saved] == ["گزارش.pdf", "b.xlsx", "c.png"]
    more = client.post(f"{API}/{t['id']}/files", data={"files": [(io.BytesIO(b"zip"), "d.zip")]},
                       content_type="multipart/form-data", headers=h["creator"])
    assert more.status_code == 201
    assert len(client.get(f"{API}/{t['id']}/files", headers=h["manager"]).get_json()["data"]) == 4
    dl = client.get(f"{API}/{t['id']}/files/{saved[0]['id']}", headers=h["creator"])
    assert dl.status_code == 200 and dl.data == b"%PDF-1.4 a"
    assert "attachment" in dl.headers["Content-Disposition"]
    # another unit cannot reach them; a bad type is refused
    assert client.get(f"{API}/{t['id']}/files", headers=h["other"]).status_code == 403
    bad = client.post(f"{API}/{t['id']}/files", data={"files": [(io.BytesIO(b"x"), "a.exe")]},
                      content_type="multipart/form-data", headers=h["w1"])
    assert bad.status_code == 400
    # delete: the uploader may; somebody else may not; a manager may
    assert client.delete(f"{API}/{t['id']}/files/{saved[1]['id']}", headers=h["creator"]).status_code == 403
    assert client.delete(f"{API}/{t['id']}/files/{saved[1]['id']}", headers=h["w1"]).status_code == 200
    assert client.delete(f"{API}/{t['id']}/files/{saved[0]['id']}", headers=h["manager"]).status_code == 200
    assert len(client.get(f"{API}/{t['id']}/files", headers=h["manager"]).get_json()["data"]) == 2


# ── 5: several assignees at the same time ────────────────────────────
def test_set_many_assignees_in_one_call(client, world):
    ids = world["ids"]
    t = _mk(client, world, assignee_user_ids=[ids["w1"], ids["w2"]])
    assert sorted(t["assignee_ids"]) == sorted([ids["w1"], ids["w2"]])
    r = client.put(f"{API}/{t['id']}/assignees", json={"assignee_user_ids": [ids["w2"], ids["w3"]]}, headers=world["h"]["creator"])
    assert r.status_code == 200
    assert sorted(r.get_json()["data"]["assignee_ids"]) == sorted([ids["w2"], ids["w3"]])
    # someone from another department cannot be added
    r = client.put(f"{API}/{t['id']}/assignees", json={"assignee_user_ids": [ids["other"]]}, headers=world["h"]["creator"])
    assert r.status_code == 409
    # a non-assigner cannot change the list
    assert client.put(f"{API}/{t['id']}/assignees", json={"assignee_user_ids": []}, headers=world["h"]["w1"]).status_code == 403


# ── 7: referral chain ────────────────────────────────────────────────
def test_assignee_refers_onward_and_the_chain_is_kept(client, world):
    ids, h = world["ids"], world["h"]
    t = _mk(client, world, assignee_user_ids=[ids["w1"]])
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w2"]}, headers=h["w2"]).status_code == 403  # not an assignee yet
    r = client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w2"], "note": "این را شما انجام دهید"}, headers=h["w1"])
    assert r.status_code == 201
    # w2 now holds it and refers it on again
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w3"]}, headers=h["w2"]).status_code == 201
    cur = client.get(f"{API}/{t['id']}", headers=h["creator"]).get_json()["data"]
    assert cur["assignee_ids"] == [ids["w3"]]
    chain = client.get(f"{API}/{t['id']}/assignments", headers=h["creator"]).get_json()["data"]
    assert [c["assignee_user_id"] for c in chain] == [ids["w1"], ids["w2"], ids["w3"]]
    assert chain[1]["parent_assignment_id"] == chain[0]["id"] and chain[2]["parent_assignment_id"] == chain[1]["id"]
    assert [c["end_reason"] for c in chain] == ["REFERRED", "REFERRED", None]
    assert chain[1]["referral_note"] == "این را شما انجام دهید" and chain[1]["assigned_by_user_id"] == ids["w1"]
    assert [c["is_active"] for c in chain] == [False, False, True]


def test_referral_rules(client, world):
    ids, h = world["ids"], world["h"]
    t = _mk(client, world, assignee_user_ids=[ids["w1"], ids["w2"]])
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w1"]}, headers=h["w1"]).status_code == 409   # to yourself
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w2"]}, headers=h["w1"]).status_code == 409   # already on it
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["other"]}, headers=h["w1"]).status_code == 409  # other department
    client.patch(f"{API}/{t['id']}", json={"status": "DONE"}, headers=h["manager"])
    assert client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w3"]}, headers=h["w1"]).status_code == 409   # finished


# ── 8: recurring tasks (Jalali months/years, manual spans) ───────────
def _series(client, world, **rec):
    ids = world["ids"]
    t = _mk(client, world, assignee_user_ids=[ids["w1"]], due_date="2026-10-31", recurrence=rec)
    client.post(f"{API}/{t['id']}/checklist", json={"title": "گام"}, headers=world["h"]["creator"])
    return t


def _copies(template_id):
    return db.session.query(Task).filter(Task.recurrence_source_id == template_id).order_by(Task.due_date).all()


def test_daily_series_creates_copies_with_assignees_and_a_fresh_checklist(client, world, app):
    t = _series(client, world, unit="DAY", interval=1)
    assert t["recurrence"] == {"unit": "DAY", "interval": 1, "end_date": None, "next_date": "2026-11-01"}
    with app.app_context():
        assert recurrence.generate_due_recurring_tasks(date(2026, 10, 31)) == 0       # not due yet
        assert recurrence.generate_due_recurring_tasks(date(2026, 11, 2)) == 2        # Nov 1 and Nov 2
        copies = _copies(t["id"])
        assert [c.due_date for c in copies] == [date(2026, 11, 1), date(2026, 11, 2)]
        assert all(c.recurrence_unit is None and c.status.value == "TODO" for c in copies)
        assert copies[0].assignee_ids == [world["ids"]["w1"]]
        assert recurrence.generate_due_recurring_tasks(date(2026, 11, 2)) == 0        # idempotent
        from app.modules.tasks.models import TaskChecklistItem
        items = db.session.query(TaskChecklistItem).filter_by(task_id=copies[0].id).all()
        assert [i.title for i in items] == ["گام"] and not items[0].is_done


def test_weekly_manual_span_and_end_date(client, world, app):
    t = _series(client, world, unit="DAY", interval=10, end_date="2026-11-25")   # every 10 days (manual span)
    with app.app_context():
        recurrence.generate_due_recurring_tasks(date(2026, 12, 31))
        assert [c.due_date for c in _copies(t["id"])] == [date(2026, 11, 10), date(2026, 11, 20)]  # Nov 30 is past the end date
    w = _series(client, world, unit="WEEK", interval=1)
    with app.app_context():
        recurrence.generate_due_recurring_tasks(date(2026, 11, 14))
        assert [c.due_date for c in _copies(w["id"])] == [date(2026, 11, 7), date(2026, 11, 14)]


def test_monthly_and_yearly_use_jalali_calendar(client, world, app):
    # 9 Aban 1405 = 2026-10-31 -> one Jalali month later is 9 Azar 1405 = 2026-11-30
    t = _series(client, world, unit="MONTH", interval=1)
    assert t["recurrence"]["next_date"] == "2026-11-30"
    y = _series(client, world, unit="YEAR", interval=1)
    assert y["recurrence"]["next_date"] == "2027-10-31"   # 9 Aban 1406 = 2027-10-31


def test_changing_or_stopping_a_series(client, world, app):
    t = _series(client, world, unit="DAY", interval=1)
    h = world["h"]
    r = client.patch(f"{API}/{t['id']}", json={"recurrence": {"unit": "WEEK", "interval": 2}}, headers=h["creator"])
    assert r.get_json()["data"]["recurrence"]["next_date"] == "2026-11-14"
    r = client.patch(f"{API}/{t['id']}", json={"recurrence": None}, headers=h["creator"])
    assert r.get_json()["data"]["recurrence"] is None
    with app.app_context():
        assert recurrence.generate_due_recurring_tasks(date(2027, 1, 1)) == 0
    bad = client.post(API, json={"title": "x", "department_id": world["dept_a"], "recurrence": {"unit": "HOUR"}}, headers=h["creator"])
    assert bad.status_code == 400
    assert client.post(API, json={"title": "x", "department_id": world["dept_a"], "recurrence": {"unit": "DAY", "interval": 0}},
                       headers=h["creator"]).status_code == 400


# ── 9: @mentions ─────────────────────────────────────────────────────
def test_mentions_in_notes(client, world):
    ids, h = world["ids"], world["h"]
    t = _mk(client, world, assignee_user_ids=[ids["w1"]])
    r = client.post(f"{API}/{t['id']}/notes", json={"body": f"@[{ids['w2']}] لطفاً نگاه کنید"}, headers=h["w1"])
    assert r.status_code == 201, r.get_json()
    note = r.get_json()["data"]
    assert [m["id"] for m in note["mentions"]] == [ids["w2"]] and note["mentions"][0]["full_name"]
    # mentioning someone who cannot see the task is refused
    assert client.post(f"{API}/{t['id']}/notes", json={"body": f"@[{ids['other']}] hi"}, headers=h["w1"]).status_code == 409
    assert client.post(f"{API}/{t['id']}/notes", json={"body": "@[999999] hi"}, headers=h["w1"]).status_code == 409
    # candidates = people of the task's unit
    cands = client.get(f"{API}/{t['id']}/mention-candidates", headers=h["w1"]).get_json()["data"]
    assert ids["w2"] in {c["id"] for c in cands} and ids["other"] not in {c["id"] for c in cands}
    # the mentioned person finds it in their mentions; others do not
    mine = client.get(f"{API}/mentions", headers=h["w2"]).get_json()["data"]
    assert [m["id"] for m in mine] == [note["id"]] and mine[0]["task_title"] == t["title"]
    assert client.get(f"{API}/mentions", headers=h["w3"]).get_json()["data"] == []
    listed = client.get(f"{API}/{t['id']}/notes", headers=h["creator"]).get_json()["data"]
    assert listed[0]["mentions"][0]["id"] == ids["w2"]


# ── 11: Tehran time + UTF-8 ──────────────────────────────────────────
def test_timestamps_carry_an_offset_and_due_time_round_trips(client, world):
    t = _mk(client, world, due_date="2026-11-02", due_time="09:30")
    assert t["created_at"].endswith("+00:00") and t["updated_at"].endswith("+00:00")
    assert t["due_time"] == "09:30"
    note = client.post(f"{API}/{t['id']}/notes", json={"body": "یادداشت"}, headers=world["h"]["creator"]).get_json()["data"]
    assert note["created_at"].endswith("+00:00")


def test_persian_text_round_trips_as_real_utf8(client, world):
    title = "گزارش فروش ماهانه — واحد بازرگانی ✓"
    t = _mk(client, world, title=title, description="شرح کامل: پایش موجودی انبار و ارسال به مشتریان")
    r = client.get(f"{API}/{t['id']}", headers=world["h"]["creator"])
    assert r.get_json()["data"]["title"] == title
    assert title.encode("utf-8") in r.data  # sent as UTF-8 characters, not \\u escapes


# ── notifications (the header bell) ──────────────────────────────────
def _bell(client, headers, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/api/notifications?{q}", headers=headers).get_json()["data"]


def test_assigned_referred_and_mentioned_people_are_notified_in_persian(client, world):
    ids, h = world["ids"], world["h"]
    t = _mk(client, world, title="گزارش فروش", assignee_user_ids=[ids["w1"]])
    bell = _bell(client, h["w1"])
    assert bell["unread_count"] == 1 and bell["items"][0]["type"] == "TASK_ASSIGNED"
    assert "گزارش فروش" in bell["items"][0]["body"] and bell["items"][0]["link"].endswith(f"/task/{t['id']}")
    assert _bell(client, h["creator"])["unread_count"] == 0  # you are not notified about your own action

    client.post(f"{API}/{t['id']}/refer", json={"to_user_id": ids["w2"], "note": "لطفاً انجام دهید"}, headers=h["w1"])
    ref = _bell(client, h["w2"])["items"][0]
    assert ref["type"] == "TASK_REFERRED" and "لطفاً انجام دهید" in ref["body"]

    client.post(f"{API}/{t['id']}/notes", json={"body": f"@[{ids['w3']}] نگاه کنید"}, headers=h["w2"])
    assert _bell(client, h["w3"])["items"][0]["type"] == "TASK_MENTION"

    # mark one, then all, as read
    first = _bell(client, h["w1"])["items"][0]["id"]
    client.post("/api/notifications/read", json={"ids": [first]}, headers=h["w1"])
    assert _bell(client, h["w1"])["unread_count"] == 0
    client.post("/api/notifications/read", json={"all": True}, headers=h["w2"])
    assert _bell(client, h["w2"])["unread_count"] == 0
    # nobody can read someone else's notifications
    assert _bell(client, h["w3"], unread=1)["items"][0]["type"] == "TASK_MENTION"


def test_deadline_warnings_for_overdue_and_soon(client, world):
    from datetime import timedelta
    from app.utils.jalali import tehran_now
    ids, h = world["ids"], world["h"]
    now = tehran_now()
    overdue = _mk(client, world, title="گزارش قدیمی", assignee_user_ids=[ids["w1"]], due_date=(now.date() - timedelta(days=2)).isoformat())
    soon_at = now + timedelta(hours=3)
    soon = _mk(client, world, title="گزارش نزدیک", assignee_user_ids=[ids["w1"]],
               due_date=soon_at.date().isoformat(), due_time=soon_at.strftime("%H:%M"))
    far = _mk(client, world, title="گزارش دور", assignee_user_ids=[ids["w1"]], due_date=(now.date() + timedelta(days=5)).isoformat())
    items = _bell(client, h["w1"], limit=50)["items"]
    kinds = {(n["type"], n["task_id"]) for n in items}
    assert ("TASK_OVERDUE", overdue["id"]) in kinds and ("TASK_DUE_SOON", soon["id"]) in kinds
    assert not any(n["task_id"] == far["id"] and n["type"] in ("TASK_OVERDUE", "TASK_DUE_SOON") for n in items)
    soon_note = next(n for n in items if n["type"] == "TASK_DUE_SOON")
    assert "ساعت" in soon_note["body"] and "گزارش نزدیک" in soon_note["body"]
    # each warning is created once however often the bell polls
    again = _bell(client, h["w1"], limit=50)["items"]
    assert len([n for n in again if n["type"] in ("TASK_OVERDUE", "TASK_DUE_SOON")]) == 2
    # finishing the task stops further warnings for it
    client.patch(f"{API}/{overdue['id']}", json={"status": "DONE"}, headers=h["manager"])
