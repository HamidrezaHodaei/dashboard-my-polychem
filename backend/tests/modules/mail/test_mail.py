"""HTTP tests for /api/mail (مکاتبات سازمانی): access control, sending, threads, privacy, attachments."""
import io

import pytest

from app.core.authorization.models import PermissionEffect, ScopeType, UserPermissionScope
from app.extensions import db
from app.modules.mail.models import MailParticipant, MailUnitAccess
from tests.core4.factories import (
    add_team_member, auth_headers, grant_user_permission, make_department, make_organization, make_permission,
    make_team, make_user,
)

BASE = "/api/mail"
ACTIONS = ("read", "create", "update", "delete")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF = b"%PDF-1.4\n%test\n"
_PERMS: dict[str, object] = {}


@pytest.fixture(autouse=True)
def _uploads(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)
    _PERMS.clear()


def _perm(action):
    key = f"correspondence.mail.{action}"
    if key not in _PERMS:
        _PERMS[key] = make_permission(key, is_delegable=True)
    return _PERMS[key]


def _staff(*actions, **user_overrides):
    user = make_user(**user_overrides)
    for a in actions or ACTIONS:
        grant_user_permission(user, _perm(a), ScopeType.GLOBAL, None)
    db.session.commit()
    return user, auth_headers(user)


def _send(client, h, to, subject="سلام", body="متن نامه", **extra):
    payload = {"to": [u.id for u in to], "subject": subject, "body": body, **extra}
    r = client.post(f"{BASE}/messages", json=payload, headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]["message"]


def _threads(client, h, **params):
    r = client.get(f"{BASE}/threads", query_string=params, headers=h)
    assert r.status_code == 200, r.get_json()
    return r.get_json()["data"]["items"]


# ── access control (server side) ─────────────────────────────────────
def test_requires_authentication(client):
    assert client.get(f"{BASE}/threads").status_code == 401


def test_user_without_permission_is_denied_everywhere(client):
    user, h = _staff()  # no actions granted? -> _staff grants all when empty, so build one manually
    outsider = make_user()
    db.session.commit()
    ho = auth_headers(outsider)
    assert client.get(f"{BASE}/threads", headers=ho).status_code == 403
    assert client.get(f"{BASE}/counters", headers=ho).status_code == 403
    assert client.get(f"{BASE}/recipients", headers=ho).status_code == 403
    assert client.post(f"{BASE}/messages", json={"to": [user.id], "body": "x"}, headers=ho).status_code == 403
    assert client.get(f"{BASE}/access/units", headers=ho).status_code == 403


def test_read_only_user_cannot_send(client):
    _, h_reader = _staff("read")
    target, _ = _staff()
    r = client.post(f"{BASE}/messages", json={"to": [target.id], "body": "x"}, headers=h_reader)
    assert r.status_code == 403
    assert client.get(f"{BASE}/threads", headers=h_reader).status_code == 200


def test_user_direct_deny_beats_role_or_unit_access(client):
    org = make_organization()
    dept = make_department(org)
    user, h = _staff("read", "create", "update", "delete", department_id=dept.id)
    db.session.add(MailUnitAccess(department_id=dept.id))
    db.session.add(UserPermissionScope(
        user_id=user.id, permission_id=_perm("read").id, scope_type=ScopeType.GLOBAL, scope_id=None,
        is_active=True, effect=PermissionEffect.DENY,
    ))
    db.session.commit()
    assert client.get(f"{BASE}/threads", headers=h).status_code == 403


# ── organizational units ─────────────────────────────────────────────
def test_unit_access_lets_members_use_mail_and_team_members_too(client):
    org = make_organization()
    dept = make_department(org)
    other = make_department(org)
    team = make_team(dept)
    member = make_user(department_id=dept.id)
    via_team = make_user(department_id=other.id)
    add_team_member(team, via_team)
    stranger = make_user(department_id=other.id)
    admin, h_admin = _staff()  # holds the four mail permissions
    manager = make_user()
    grant_user_permission(manager, make_permission("core.permission.update"), ScopeType.GLOBAL, None)
    db.session.commit()

    assert client.get(f"{BASE}/threads", headers=auth_headers(member)).status_code == 403
    r = client.put(f"{BASE}/access/units", json={"department_ids": [dept.id]}, headers=auth_headers(manager))
    assert r.status_code == 200
    enabled = {u["id"]: u["enabled"] for u in r.get_json()["data"]}
    assert enabled[dept.id] is True and enabled[other.id] is False

    assert client.get(f"{BASE}/threads", headers=auth_headers(member)).status_code == 200
    assert client.get(f"{BASE}/threads", headers=auth_headers(via_team)).status_code == 200
    assert client.get(f"{BASE}/threads", headers=auth_headers(stranger)).status_code == 403
    # and the unit member now shows up as a possible recipient
    found = client.get(f"{BASE}/recipients", query_string={"q": member.username}, headers=h_admin).get_json()["data"]
    assert [p["id"] for p in found] == [member.id]
    nav = client.get("/api/me/navigation", headers=auth_headers(member))
    if nav.status_code == 200:
        assert "correspondence" in [e["key"] for e in nav.get_json()["data"]]

    # switching the unit off removes access again
    assert client.put(f"{BASE}/access/units", json={"department_ids": []}, headers=auth_headers(manager)).status_code == 200
    assert client.get(f"{BASE}/threads", headers=auth_headers(member)).status_code == 403


def test_only_permission_managers_change_unit_access(client):
    _, h = _staff()
    assert client.put(f"{BASE}/access/units", json={"department_ids": []}, headers=h).status_code == 403


def test_unknown_unit_is_rejected(client):
    manager = make_user()
    grant_user_permission(manager, make_permission("core.permission.update"), ScopeType.GLOBAL, None)
    db.session.commit()
    r = client.put(f"{BASE}/access/units", json={"department_ids": [99999]}, headers=auth_headers(manager))
    assert r.status_code == 400


def test_matrix_and_registry_know_correspondence():
    from app.permissions.registry import MATRIX_MODULES, REGISTRY
    assert all(f"correspondence.mail.{a}" in REGISTRY for a in ACTIONS)
    assert "correspondence.mail" in {m.key for m in MATRIX_MODULES}


# ── recipients ───────────────────────────────────────────────────────
def test_recipient_search_by_name_username_email_and_avatar(client):
    me, h = _staff()
    ali, _ = _staff(full_name="علی رضایی", username="ali.r", email="ali@corp.test")
    ali.avatar_data = "data:image/png;base64,AAAA"
    sara, _ = _staff(full_name="سارا احمدی", username="sara", email="sara@corp.test")
    no_access = make_user(full_name="علی بدون دسترسی", username="noacc", email="noacc@corp.test")
    inactive, _ = _staff(full_name="علی غیرفعال", username="gone", email="gone@corp.test")
    inactive.is_active = False
    db.session.commit()

    def ids(q):
        r = client.get(f"{BASE}/recipients", query_string={"q": q}, headers=h)
        assert r.status_code == 200
        return [p["id"] for p in r.get_json()["data"]]

    assert ids("علی") == [ali.id]            # first name; no-access and inactive users are not offered
    assert ids("رضایی") == [ali.id]          # last name
    assert ids("ali.r") == [ali.id]          # username
    assert ids("sara@corp") == [sara.id]     # e-mail
    assert ids("علی رضایی") == [ali.id]      # several words
    assert me.id not in ids("")
    card = client.get(f"{BASE}/recipients", query_string={"q": "ali.r"}, headers=h).get_json()["data"][0]
    assert card["avatar"] == "data:image/png;base64,AAAA"
    assert card["first_name"] == "علی" and card["last_name"] == "رضایی" and card["email"] == "ali@corp.test"
    assert ids("علی") != [no_access.id]
    # people already chosen can be excluded from the suggestions
    r = client.get(f"{BASE}/recipients", query_string={"q": "علی", "exclude": str(ali.id)}, headers=h)
    assert r.get_json()["data"] == []


def test_arabic_letters_match_persian_search(client):
    _, h = _staff()
    kamran, _ = _staff(full_name="كامران يوسفي", username="kam")  # stored with Arabic kaf / yeh
    r = client.get(f"{BASE}/recipients", query_string={"q": "کامران یوسفی"}, headers=h)
    assert [p["id"] for p in r.get_json()["data"]] == [kamran.id]


# ── sending, inbox, threads ──────────────────────────────────────────
def test_send_lands_in_recipient_inbox_and_sender_sent(client):
    alice, ha = _staff()
    bob, hb = _staff()
    carol, hc = _staff()
    msg = _send(client, ha, [bob], subject="گزارش", body="سلام بابک", cc=[carol.id])

    inbox_b = _threads(client, hb)
    assert len(inbox_b) == 1 and inbox_b[0]["subject"] == "گزارش" and inbox_b[0]["is_read"] is False
    assert inbox_b[0]["sender_id"] == alice.id and inbox_b[0]["to"] == [bob.id] and inbox_b[0]["cc"] == [carol.id]
    assert len(_threads(client, hc)) == 1
    sent = _threads(client, ha, folder="sent")
    assert len(sent) == 1 and sent[0]["id"] == msg["id"] and _threads(client, ha) == []
    # the people map carries name / e-mail for every participant
    data = client.get(f"{BASE}/threads", headers=hb).get_json()["data"]
    assert data["people"][str(alice.id)]["full_name"] == alice.full_name

    counters = client.get(f"{BASE}/counters", headers=hb).get_json()["data"]
    assert counters["folders"]["inbox"] == {"total": 1, "unread": 1}


def test_unlimited_cc_recipients(client):
    _, ha = _staff()
    to, _ = _staff()
    ccs = [_staff()[0] for _ in range(30)]
    msg = _send(client, ha, [to], cc=[u.id for u in ccs])
    assert len(msg["cc"]) == 30
    for u in ccs[:3] + ccs[-2:]:
        assert len(_threads(client, auth_headers(u))) == 1


def test_recipient_must_exist_have_access_and_not_be_sender(client):
    alice, ha = _staff()
    no_access = make_user()
    db.session.commit()
    for to in ([no_access.id], [alice.id], [99999], []):
        r = client.post(f"{BASE}/messages", json={"to": to, "body": "x"}, headers=ha)
        assert r.status_code == 400, (to, r.get_json())


def test_body_or_attachment_required(client):
    _, ha = _staff()
    bob, _ = _staff()
    r = client.post(f"{BASE}/messages", json={"to": [bob.id], "body": "  "}, headers=ha)
    assert r.status_code == 400


def test_reading_marks_read_and_thread_endpoint(client):
    alice, ha = _staff()
    bob, hb = _staff()
    msg = _send(client, ha, [bob])
    thread = client.get(f"{BASE}/messages/{msg['id']}/thread", headers=hb).get_json()["data"]
    assert thread["messages"][0]["body"] == "متن نامه" and thread["folder"] == "inbox"
    r = client.patch(f"{BASE}/messages/{msg['id']}/flags", json={"is_read": True, "is_starred": True}, headers=hb)
    assert r.status_code == 200 and r.get_json()["data"]["is_starred"] is True
    row = _threads(client, hb)[0]
    assert row["is_read"] is True and row["is_starred"] is True
    assert _threads(client, hb, unread="1") == []
    assert len(_threads(client, hb, starred="1")) == 1


def test_reply_and_reply_all_build_one_conversation(client):
    alice, ha = _staff()
    bob, hb = _staff()
    carol, hc = _staff()
    first = _send(client, ha, [bob], subject="پروژه", cc=[carol.id])
    r = client.post(f"{BASE}/messages/{first['id']}/reply", json={"body": "باشه", "reply_all": True}, headers=hb)
    assert r.status_code == 201
    reply = r.get_json()["data"]["message"]
    assert reply["thread_id"] == first["thread_id"] and reply["subject"] == "Re: پروژه"
    assert reply["to"] == [alice.id] and reply["cc"] == [carol.id]

    inbox_a = _threads(client, ha)
    assert len(inbox_a) == 1 and inbox_a[0]["id"] == reply["id"] and inbox_a[0]["thread_count"] == 2 and inbox_a[0]["is_read"] is False
    assert len(_threads(client, hc)) == 1 and _threads(client, hc)[0]["thread_count"] == 2
    thread = client.get(f"{BASE}/messages/{first['id']}/thread", headers=ha).get_json()["data"]
    assert [m["id"] for m in thread["messages"]] == [first["id"], reply["id"]]

    # plain reply goes only to the sender
    r2 = client.post(f"{BASE}/messages/{first['id']}/reply", json={"body": "فقط شما"}, headers=hc)
    assert r2.get_json()["data"]["message"]["to"] == [alice.id] and r2.get_json()["data"]["message"]["cc"] == []


def test_search_and_sort(client):
    alice, ha = _staff(full_name="مدیر فروش")
    bob, hb = _staff()
    _send(client, ha, [bob], subject="قرارداد خرید", body="پیش‌نویس")
    _send(client, ha, [bob], subject="جلسه هفتگی", body="ساعت ده")
    assert [t["subject"] for t in _threads(client, hb, q="قرارداد")] == ["قرارداد خرید"]
    assert len(_threads(client, hb, q="مدیر فروش")) == 2          # by sender name
    assert [t["subject"] for t in _threads(client, hb, sort="oldest")] == ["قرارداد خرید", "جلسه هفتگی"]
    assert [t["subject"] for t in _threads(client, hb)] == ["جلسه هفتگی", "قرارداد خرید"]


# ── privacy ──────────────────────────────────────────────────────────
def test_outsider_cannot_open_or_change_someone_elses_mail(client):
    alice, ha = _staff()
    bob, hb = _staff()
    eve, he = _staff()
    msg = _send(client, ha, [bob])
    mid = msg["id"]
    assert client.get(f"{BASE}/messages/{mid}/thread", headers=he).status_code == 404
    assert client.patch(f"{BASE}/messages/{mid}/flags", json={"is_read": True}, headers=he).status_code == 404
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "trash"}, headers=he).status_code == 404
    assert client.post(f"{BASE}/messages/{mid}/reply", json={"body": "x"}, headers=he).status_code == 404
    assert client.delete(f"{BASE}/messages/{mid}", headers=he).status_code == 404
    assert _threads(client, he) == []


# ── folders ──────────────────────────────────────────────────────────
def test_archive_spam_trash_restore_and_private_state(client):
    alice, ha = _staff()
    bob, hb = _staff()
    msg = _send(client, ha, [bob])
    mid = msg["id"]
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "archive"}, headers=hb).status_code == 200
    assert _threads(client, hb) == [] and len(_threads(client, hb, folder="archive")) == 1
    assert len(_threads(client, ha, folder="sent")) == 1          # the sender's copy is untouched
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "spam"}, headers=hb).status_code == 200
    assert len(_threads(client, hb, folder="spam")) == 1
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "trash"}, headers=hb).status_code == 200
    assert len(_threads(client, hb, folder="trash")) == 1
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "inbox"}, headers=hb).status_code == 200
    assert len(_threads(client, hb)) == 1
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "nowhere"}, headers=hb).status_code == 400
    # the sender can restore a trashed sent message to Sent
    client.post(f"{BASE}/messages/{mid}/move", json={"folder": "trash"}, headers=ha)
    client.post(f"{BASE}/messages/{mid}/move", json={"folder": "inbox"}, headers=ha)
    assert len(_threads(client, ha, folder="sent")) == 1


def test_permanent_delete_only_from_trash_and_only_for_me(client):
    alice, ha = _staff()
    bob, hb = _staff()
    mid = _send(client, ha, [bob])["id"]
    assert client.delete(f"{BASE}/messages/{mid}", headers=hb).status_code == 409   # still in the inbox
    client.post(f"{BASE}/messages/{mid}/move", json={"folder": "trash"}, headers=hb)
    assert client.delete(f"{BASE}/messages/{mid}", headers=hb).status_code == 200
    assert client.get(f"{BASE}/messages/{mid}/thread", headers=hb).status_code == 404
    assert _threads(client, hb, folder="trash") == []
    assert len(_threads(client, ha, folder="sent")) == 1                              # alice still has it
    assert db.session.query(MailParticipant).filter_by(user_id=bob.id).one().purged_at is not None


def test_delete_permission_needed_for_trash_but_not_archive(client):
    alice, ha = _staff()
    bob, hb = _staff("read", "update")
    mid = _send(client, ha, [bob])["id"]
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "trash"}, headers=hb).status_code == 403
    assert client.post(f"{BASE}/messages/{mid}/move", json={"folder": "archive"}, headers=hb).status_code == 200


def test_labels_mute_and_label_counters(client):
    alice, ha = _staff()
    bob, hb = _staff()
    mid = _send(client, ha, [bob])["id"]
    r = client.put(f"{BASE}/messages/{mid}/labels", json={"labels": ["urgent", "work"]}, headers=hb)
    assert r.status_code == 200 and r.get_json()["data"]["labels"] == ["urgent", "work"]
    assert client.put(f"{BASE}/messages/{mid}/labels", json={"labels": ["bogus"]}, headers=hb).status_code == 400
    assert len(_threads(client, hb, label="urgent")) == 1 and _threads(client, hb, label="finance") == []
    assert client.get(f"{BASE}/counters", headers=hb).get_json()["data"]["labels"]["work"] == 1

    # a muted conversation raises no bell notification for new replies
    client.patch(f"{BASE}/messages/{mid}/flags", json={"is_muted": True}, headers=hb)
    client.post(f"{BASE}/messages/{mid}/reply", json={"body": "ادامه"}, headers=ha)
    from app.modules.notifications.models import Notification
    mine = db.session.query(Notification).filter_by(user_id=bob.id, type="MAIL").count()
    assert mine == 1                                              # only the first message notified


def test_new_mail_creates_notification_with_link(client):
    alice, ha = _staff(full_name="سارا")
    bob, hb = _staff()
    msg = _send(client, ha, [bob], subject="فوری")
    items = client.get("/api/notifications", headers=hb).get_json()["data"]["items"]
    mail = [n for n in items if n["type"] == "MAIL"]
    assert len(mail) == 1 and mail[0]["link"] == f"/mail?thread={msg['id']}" and "سارا" in mail[0]["title"]


# ── drafts ───────────────────────────────────────────────────────────
def test_draft_lifecycle_and_privacy(client):
    alice, ha = _staff()
    bob, hb = _staff()
    r = client.post(f"{BASE}/drafts", json={"to": [bob.id], "subject": "پیش‌نویس", "body": "هنوز کامل نیست"}, headers=ha)
    assert r.status_code == 201
    draft = r.get_json()["data"]["message"]
    assert draft["is_draft"] is True and draft["to"] == [bob.id]
    assert len(_threads(client, ha, folder="drafts")) == 1
    assert _threads(client, hb) == [] and _threads(client, hb, folder="drafts") == []   # recipients see nothing yet
    assert client.get(f"{BASE}/messages/{draft['id']}/thread", headers=hb).status_code == 404

    r = client.put(f"{BASE}/drafts/{draft['id']}", json={"to": [bob.id], "subject": "نهایی", "body": "کامل"}, headers=ha)
    assert r.get_json()["data"]["message"]["subject"] == "نهایی"
    r = client.post(f"{BASE}/drafts/{draft['id']}/send", json={"to": [bob.id], "subject": "نهایی", "body": "کامل"}, headers=ha)
    assert r.status_code == 200 and r.get_json()["data"]["message"]["is_draft"] is False
    assert _threads(client, ha, folder="drafts") == [] and len(_threads(client, ha, folder="sent")) == 1
    assert len(_threads(client, hb)) == 1
    assert client.put(f"{BASE}/drafts/{draft['id']}", json={"body": "x"}, headers=ha).status_code == 404   # no longer a draft


def test_discard_draft_and_cannot_touch_others_drafts(client):
    alice, ha = _staff()
    bob, hb = _staff()
    d = client.post(f"{BASE}/drafts", json={"body": "x"}, headers=ha).get_json()["data"]["message"]
    assert client.delete(f"{BASE}/drafts/{d['id']}", headers=hb).status_code == 404
    assert client.put(f"{BASE}/drafts/{d['id']}", json={"body": "hack"}, headers=hb).status_code == 404
    assert client.delete(f"{BASE}/drafts/{d['id']}", headers=ha).status_code == 200
    assert _threads(client, ha, folder="drafts") == []


# ── attachments ──────────────────────────────────────────────────────
def _upload(client, h, content=PDF, name="report.pdf"):
    return client.post(f"{BASE}/attachments", data={"file": (io.BytesIO(content), name)},
                       content_type="multipart/form-data", headers=h)


def test_multiple_attachments_are_sent_and_downloadable_by_participants_only(client):
    alice, ha = _staff()
    bob, hb = _staff()
    eve, he = _staff()
    up1 = _upload(client, ha).get_json()["data"]
    up2 = _upload(client, ha, PNG, "scan.png").get_json()["data"]
    assert up1["name"] == "report.pdf" and up1["size"] == len(PDF)
    msg = _send(client, ha, [bob], attachment_ids=[up1["id"], up2["id"]])
    assert [a["name"] for a in msg["attachments"]] == ["report.pdf", "scan.png"]
    thread = client.get(f"{BASE}/messages/{msg['id']}/thread", headers=hb).get_json()["data"]
    assert len(thread["messages"][0]["attachments"]) == 2
    assert _threads(client, hb)[0]["has_attachments"] is True

    r = client.get(f"{BASE}/attachments/{up1['id']}", headers=hb)
    assert r.status_code == 200 and r.data == PDF
    assert r.headers["X-Content-Type-Options"] == "nosniff" and "attachment" in r.headers["Content-Disposition"]
    assert client.get(f"{BASE}/attachments/{up1['id']}", headers=he).status_code == 404


def test_orphan_upload_is_private_and_cannot_be_stolen(client):
    alice, ha = _staff()
    bob, hb = _staff()
    eve, he = _staff()
    up = _upload(client, ha).get_json()["data"]
    assert client.get(f"{BASE}/attachments/{up['id']}", headers=hb).status_code == 404
    r = client.post(f"{BASE}/messages", json={"to": [bob.id], "body": "x", "attachment_ids": [up["id"]]}, headers=he)
    assert r.status_code == 400                                     # eve cannot attach alice's upload
    assert client.delete(f"{BASE}/attachments/{up['id']}", headers=he).status_code == 404
    assert client.delete(f"{BASE}/attachments/{up['id']}", headers=ha).status_code == 200


@pytest.mark.parametrize("name,content", [
    ("run.exe", b"MZ\x90\x00"), ("page.html", b"<script>alert(1)</script>"), ("pic.svg", b"<svg onload=x>"),
    ("macro.bat", b"echo hi"), ("noext", b"abc"),
])
def test_dangerous_types_are_rejected(client, name, content):
    _, h = _staff()
    assert _upload(client, h, content, name).status_code == 400


def test_content_must_match_extension(client):
    _, h = _staff()
    assert _upload(client, h, b"MZ\x90\x00 not a pdf", "fake.pdf").status_code == 400
    assert _upload(client, h, b"plain text, not a png", "fake.png").status_code == 400
    assert _upload(client, h, b"\x00\x01binary", "notes.txt").status_code == 400
    assert _upload(client, h, "متن فارسی".encode("utf-8"), "notes.txt").status_code == 201
    assert _upload(client, h, b"", "empty.pdf").status_code == 400


def test_file_size_limit(client, app):
    _, h = _staff()
    app.config["MAIL_MAX_ATTACHMENT_MB"] = 1
    assert _upload(client, h, PDF + b"0" * (1024 * 1024 + 10), "big.pdf").status_code == 413
    assert _upload(client, h, PDF + b"0" * 1000, "ok.pdf").status_code == 201


def test_file_count_and_total_size_limits(client, app):
    _, ha = _staff()
    bob, _ = _staff()
    ids = [_upload(client, ha, PDF + bytes([i]), f"f{i}.pdf").get_json()["data"]["id"] for i in range(11)]
    r = client.post(f"{BASE}/messages", json={"to": [bob.id], "body": "x", "attachment_ids": ids}, headers=ha)
    assert r.status_code == 400
    assert client.post(f"{BASE}/messages", json={"to": [bob.id], "body": "x", "attachment_ids": ids[:10]}, headers=ha).status_code == 201

    app.config["MAIL_MAX_ATTACHMENT_MB"] = 12
    big = [_upload(client, ha, PDF + b"0" * (9 * 1024 * 1024), f"b{i}.pdf").get_json()["data"]["id"] for i in range(3)]
    r = client.post(f"{BASE}/messages", json={"to": [bob.id], "body": "x", "attachment_ids": big}, headers=ha)
    assert r.status_code == 400                                     # 27 MB > 25 MB per message


def test_forward_copies_attachments_of_a_readable_message_only(client):
    alice, ha = _staff()
    bob, hb = _staff()
    carol, hc = _staff()
    eve, he = _staff()
    up = _upload(client, ha).get_json()["data"]
    first = _send(client, ha, [bob], attachment_ids=[up["id"]])
    original = first["attachments"][0]["id"]
    fwd = _send(client, hb, [carol], subject="Fwd: x", attachment_ids=[original])
    assert fwd["attachments"][0]["name"] == "report.pdf" and fwd["attachments"][0]["id"] != original
    assert fwd["thread_id"] == fwd["id"]                            # a forward starts a new conversation
    assert client.get(f"{BASE}/attachments/{fwd['attachments'][0]['id']}", headers=hc).status_code == 200
    r = client.post(f"{BASE}/messages", json={"to": [carol.id], "body": "x", "attachment_ids": [original]}, headers=he)
    assert r.status_code == 400


def test_draft_attachment_removal_deletes_file(client, app):
    import os
    alice, ha = _staff()
    up = _upload(client, ha).get_json()["data"]
    d = client.post(f"{BASE}/drafts", json={"body": "x", "attachment_ids": [up["id"]]}, headers=ha).get_json()["data"]["message"]
    stored = os.path.join(app.config["UPLOAD_DIR"], "mail")
    assert len(os.listdir(stored)) == 1
    r = client.put(f"{BASE}/drafts/{d['id']}", json={"body": "x", "attachment_ids": []}, headers=ha)
    assert r.get_json()["data"]["message"]["attachments"] == [] and os.listdir(stored) == []


def test_sent_attachment_cannot_be_deleted(client):
    alice, ha = _staff()
    bob, hb = _staff()
    up = _upload(client, ha).get_json()["data"]
    _send(client, ha, [bob], attachment_ids=[up["id"]])
    assert client.delete(f"{BASE}/attachments/{up['id']}", headers=ha).status_code == 409


# ── meta ─────────────────────────────────────────────────────────────
def test_meta_reports_access_labels_and_limits(client):
    _, h = _staff("read")
    data = client.get(f"{BASE}/meta", headers=h).get_json()["data"]
    assert data["access"] == {"read": True, "create": False, "update": False, "delete": False}
    assert data["can_manage_access"] is False and "urgent" in data["labels"] and data["limits"]["max_files"] == 10
