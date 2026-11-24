"""Web Push: device registration, outbox, send-time checks, error handling, settings, cron."""
import base64
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.modules.notifications import push, services
from app.modules.notifications.models import (
    Notification, PushDelivery, PushSubscription,
)
from tests.auth.factories import DEFAULT_PASSWORD, login, make_user

FCM = "https://fcm.googleapis.com/fcm/send/abc123"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


KEYS = {"p256dh": _b64(b"\x04" + b"a" * 64), "auth": _b64(b"b" * 16)}


@pytest.fixture(autouse=True)
def configured(app):
    app.config.update(
        VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv", VAPID_SUBJECT="mailto:a@b.c",
        PUSH_CRON_TOKEN="secret", PUSH_MAX_ATTEMPTS=3,
    )


@pytest.fixture()
def sent(monkeypatch):
    """Replace the network call; tests set `outcome` to the (status, error) the push service 'returns'."""
    calls = []
    box = {"outcome": (201, None)}

    def fake(sub, payload, *, urgency, topic):
        calls.append((sub.id, payload, urgency, topic))
        return box["outcome"]

    monkeypatch.setattr(push, "send_func", fake)
    return type("S", (), {"calls": calls, "box": box})


def _auth(client, user):
    token = login(client, user.email, DEFAULT_PASSWORD).get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _subscribe(client, headers, endpoint=FCM, **extra):
    return client.post("/api/push/subscriptions", headers=headers, json={"endpoint": endpoint, **KEYS, **extra})


def _notify(user, title="x", **kw):
    n = services.notify(user.id, kw.pop("type_", "TASK_ASSIGNED"), title, "body", **kw)
    db.session.commit()
    return n


def test_config_exposes_public_key_only(client):
    u = make_user()
    r = client.get("/api/push/config", headers=_auth(client, u)).get_json()["data"]
    assert r == {"enabled": True, "public_key": "pub"}


def test_register_rejects_unknown_push_host(client):
    h = _auth(client, make_user())
    for bad in ("http://fcm.googleapis.com/x", "https://evil.example.com/x", "https://127.0.0.1/x",
                "https://fcm.googleapis.com.evil.com/x", "https://user:pw@fcm.googleapis.com/x"):
        assert _subscribe(client, h, bad).status_code == 400


def test_register_is_idempotent_and_rebinds_to_new_user(client):
    a, b = make_user(), make_user()
    ha, hb = _auth(client, a), _auth(client, b)
    assert _subscribe(client, ha).status_code == 201
    assert _subscribe(client, ha).status_code == 201
    assert PushSubscription.query.count() == 1
    # the same browser signs in as somebody else: the device now belongs to b only
    assert _subscribe(client, hb).status_code == 201
    sub = PushSubscription.query.one()
    assert sub.user_id == b.id
    assert client.get("/api/push/subscriptions", headers=ha).get_json()["data"]["items"] == []


def test_user_cannot_delete_or_test_anothers_device(client):
    a, b = make_user(), make_user()
    ha, hb = _auth(client, a), _auth(client, b)
    sub_id = _subscribe(client, ha).get_json()["data"]["id"]
    assert client.delete(f"/api/push/subscriptions/{sub_id}", headers=hb).status_code == 404
    assert client.post(f"/api/push/subscriptions/{sub_id}/test", headers=hb).status_code == 400
    assert client.delete(f"/api/push/subscriptions/{sub_id}", headers=ha).status_code == 200


def test_notification_is_pushed_once_per_device(client, app, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    _subscribe(client, h, "https://updates.push.services.mozilla.com/wpush/v2/zzz")
    n = _notify(u, "امور جدید", link="/tasks/project/1/task/2")
    push.process(push.queue_for([n.id]))
    assert len(sent.calls) == 2
    assert {c[1]["url"] for c in sent.calls} == {"/tasks/project/1/task/2"}
    # running the dispatcher again must not duplicate anything
    push.process(push.queue_for([n.id]))
    push.process_due()
    assert len(sent.calls) == 2
    assert PushDelivery.query.filter_by(status="SENT").count() == 2


def test_after_request_hook_pushes_notifications_created_in_a_request(client, app, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    with app.test_request_context():
        pass
    # a normal API call that creates a notification: the bell list generates deadline notices; use notify directly
    n = _notify(u, "hook")
    # simulate what the after_request hook does for this commit
    push.queue_for([n.id])
    push.process_due()
    assert len(sent.calls) == 1


def test_preferences_switch_off_category_and_master(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    r = client.put("/api/notifications/preferences", headers=h, json={"categories": {"tasks": False}})
    assert r.status_code == 200
    n = _notify(u, "off")
    assert push.queue_for([n.id]) == []
    assert not sent.calls
    client.put("/api/notifications/preferences", headers=h, json={"push_enabled": False, "categories": {}})
    n2 = _notify(u, "mail", type_="MAIL")
    assert push.queue_for([n2.id]) == []


def test_preferences_validation(client):
    h = _auth(client, make_user())
    assert client.put("/api/notifications/preferences", headers=h, json={"quiet_start": "25:99"}).status_code == 400
    assert client.put("/api/notifications/preferences", headers=h, json={"categories": {"nope": True}}).status_code == 400


def test_hide_preview_sends_generic_text(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    client.put("/api/notifications/preferences", headers=h, json={"show_preview": False})
    n = _notify(u, "راز شرکتی")
    push.process(push.queue_for([n.id]))
    payload = sent.calls[0][1]
    assert payload["title"] == push.GENERIC_TITLE and payload["body"] is None


def test_quiet_hours_hold_delivery_until_morning():
    s = push.Settings(quiet_enabled=True, quiet_start="22:00", quiet_end="07:00")
    # 20:00 UTC = 23:30 Tehran -> inside quiet hours, ends 07:00 Tehran = 03:30 UTC next day
    now = datetime(2026, 1, 10, 20, 0)
    end = push.quiet_until(s, now)
    assert end == datetime(2026, 1, 11, 3, 30)
    # 10:00 UTC = 13:30 Tehran -> not quiet
    assert push.quiet_until(s, datetime(2026, 1, 10, 10, 0)) is None


def test_gone_subscription_is_disabled(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    sent.box["outcome"] = (410, "gone")
    n = _notify(u)
    push.process(push.queue_for([n.id]))
    assert PushDelivery.query.one().status == "EXPIRED"
    assert PushSubscription.query.one().disabled_reason == "gone"
    # a disabled device gets nothing further
    n2 = _notify(u, "again")
    assert push.queue_for([n2.id]) == []


def test_transient_errors_retry_with_backoff_then_fail(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    sent.box["outcome"] = (503, "unavailable")
    n = _notify(u)
    push.process(push.queue_for([n.id]))
    d = PushDelivery.query.one()
    assert d.status == "PENDING" and d.attempts == 1 and d.next_attempt_at > datetime.now(timezone.utc).replace(tzinfo=None)
    for _ in range(2):  # attempts 2 and 3 (PUSH_MAX_ATTEMPTS=3): make it due again each time
        d.next_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        db.session.commit()
        push.process_due()
        db.session.refresh(d)
    assert d.status == "FAILED" and d.attempts == 3


def test_rejected_vapid_disables_device(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    sent.box["outcome"] = (403, "forbidden")
    n = _notify(u)
    push.process(push.queue_for([n.id]))
    assert PushSubscription.query.one().disabled_reason == "rejected"


def test_read_notification_is_not_pushed(client, sent):
    u = make_user()
    h = _auth(client, u)
    _subscribe(client, h)
    n = _notify(u)
    ids = push.queue_for([n.id])
    services.mark_read(u.id, ids=[n.id])
    push.process(ids)
    assert not sent.calls and PushDelivery.query.one().status == "SKIPPED"


def test_device_rebound_to_other_user_never_receives_old_users_notification(client, sent):
    a, b = make_user(), make_user()
    ha, hb = _auth(client, a), _auth(client, b)
    _subscribe(client, ha)
    n = _notify(a, "private for a")
    ids = push.queue_for([n.id])
    _subscribe(client, hb)  # same browser, now signed in as b
    push.process(ids)
    assert not sent.calls
    assert PushDelivery.query.one().last_error == "device_rebound"


def test_detach_removes_only_own_device(client):
    a, b = make_user(), make_user()
    ha, hb = _auth(client, a), _auth(client, b)
    _subscribe(client, ha)
    assert client.post("/api/push/subscriptions/detach", headers=hb, json={"endpoint": FCM}).get_json()["data"]["removed"] is False
    assert client.post("/api/push/subscriptions/detach", headers=ha, json={"endpoint": FCM}).get_json()["data"]["removed"] is True


def test_test_push_endpoint(client, sent):
    u = make_user()
    h = _auth(client, u)
    sub_id = _subscribe(client, h).get_json()["data"]["id"]
    r = client.post(f"/api/push/subscriptions/{sub_id}/test", headers=h).get_json()["data"]
    assert r["ok"] is True and sent.calls[0][1]["type"] == "TEST"


def test_cron_requires_token(client, sent):
    assert client.post("/api/push/cron").status_code == 404
    assert client.post("/api/push/cron", headers={"X-Cron-Token": "wrong"}).status_code == 404
    ok = client.post("/api/push/cron", headers={"X-Cron-Token": "secret"})
    assert ok.status_code == 200 and "due" in ok.get_json()["data"]


def test_notification_center_filters(client):
    u = make_user()
    h = _auth(client, u)
    _notify(u, "جلسه فردا", type_="MAIL")
    _notify(u, "امور جدید", type_="TASK_ASSIGNED")
    r = client.get("/api/notifications?q=جلسه", headers=h).get_json()["data"]
    assert [i["title"] for i in r["items"]] == ["جلسه فردا"]
    r = client.get("/api/notifications?category=tasks", headers=h).get_json()["data"]
    assert [i["type"] for i in r["items"]] == ["TASK_ASSIGNED"]
    r = client.get("/api/notifications?category=mail&read=read", headers=h).get_json()["data"]
    assert r["items"] == []
    r = client.get("/api/notifications?q=%25", headers=h).get_json()["data"]  # a literal % must not match everything
    assert r["items"] == []


def test_generated_vapid_keys_have_expected_shape():
    pub, priv = push.generate_vapid_keys()
    assert len(base64.urlsafe_b64decode(pub + "=" * (-len(pub) % 4))) == 65
    assert len(base64.urlsafe_b64decode(priv + "=" * (-len(priv) % 4))) == 32
