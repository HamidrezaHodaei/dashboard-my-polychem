"""HTTP tests for /api/crm/request-samples: workflow, rules, permissions, analytics."""
import datetime as dt

import pytest

from app.core.authorization.models import ScopeType
from app.extensions import db
from app.modules.customers.models import Customer, CustomerType
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

BASE = "/api/crm/request-samples"
CORE = ("read", "create", "update", "delete")
EXTRA = ("approve", "reject", "dispatch", "follow_up", "feedback", "convert", "export")


def _staff(*actions):
    user = make_user()
    for a in actions:
        grant_user_permission(user, make_permission(f"crm.request_sample.{a}"), ScopeType.GLOBAL, None)
    db.session.commit()
    return user, auth_headers(user)


@pytest.fixture
def rep(app):
    return _staff("read", "create", "update", "follow_up")


@pytest.fixture
def manager(app):
    return _staff("read", "approve", "reject", "dispatch", "feedback", "convert", "export")


@pytest.fixture
def customer(app):
    c = Customer(customer_type=CustomerType.LEGAL, company_name="پلیمر آریا", brand_name="آریاپلاست", factory_province="تهران")
    db.session.add(c)
    db.session.commit()
    return c.id


_REF = iter(range(1, 10_000))


def _body(customer_id, **over):
    body = {
        "customer_id": customer_id, "dispatch_ref_number": f"SMP-{next(_REF)}", "recipient_name": "علی", "delivery_address": "تهران",
        "city": "تهران", "items": [{"product_name": "پلی‌اتیلن", "grade": "HD5218", "quantity": "10", "unit": "kg"}],
    }
    body.update(over)
    return body


def _create(client, h, customer_id, **over):
    r = client.post(BASE, json=_body(customer_id, **over), headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def _go(client, h, rid, action, note=None):
    return client.post(f"{BASE}/{rid}/transition", json={"action": action, "note": note}, headers=h)


def _approved(client, rep, manager, customer):
    rid = _create(client, rep[1], customer)["id"]
    assert _go(client, rep[1], rid, "submit").status_code == 200
    assert _go(client, manager[1], rid, "approve").status_code == 200
    return rid


def _dispatch(client, manager, rid, **over):
    body = {"dispatch_date": dt.date.today().isoformat(), "reference_number": "H-1", **over}
    return client.post(f"{BASE}/{rid}/dispatches", json=body, headers=manager[1])


def _deliver(client, h, rid, **over):
    body = {"delivered_date": dt.date.today().isoformat(), **over}
    return client.post(f"{BASE}/{rid}/delivery", json=body, headers=h)


# ── permissions ──────────────────────────────────────────────────────
def test_routes_need_permissions(client, app, customer):
    none = _staff()[1]
    for method, url in [("get", BASE), ("get", f"{BASE}/analytics"), ("get", f"{BASE}/options"), ("post", BASE), ("get", f"{BASE}/export")]:
        assert getattr(client, method)(url, headers=none, json={} if method == "post" else None).status_code == 403, url
    assert client.get(BASE).status_code == 401


# ── drafts, validation ───────────────────────────────────────────────
def test_draft_is_private_and_submit_validates(client, rep, manager, customer):
    d = _create(client, rep[1], customer, dispatch_ref_number=None)
    rid = d["id"]
    assert d["status"] == "DRAFT" and d["code"].startswith("RS-")  # no dispatch reference yet -> placeholder
    d2 = _create(client, rep[1], customer, dispatch_ref_number="SMP-1405-0123")
    assert d2["code"] == "SMP-1405-0123"  # the identifier IS the dispatch reference number
    assert client.get(f"{BASE}/{rid}", headers=manager[1]).status_code == 404  # someone else's draft does not exist
    assert rid not in [x["id"] for x in client.get(BASE, headers=manager[1]).get_json()["data"]]
    r = _go(client, rep[1], rid, "submit")
    assert r.status_code == 400  # the dispatch reference number is required


def test_manager_cannot_approve_own_request(client, app, customer):
    both = _staff("read", "create", "approve", "update")
    rid = _create(client, both[1], customer)["id"]
    assert _go(client, both[1], rid, "submit").status_code == 200
    assert _go(client, both[1], rid, "approve").status_code == 403


def test_reject_needs_reason_and_closes(client, rep, manager, customer):
    rid = _create(client, rep[1], customer)["id"]
    _go(client, rep[1], rid, "submit")
    assert _go(client, manager[1], rid, "reject").status_code == 400
    r = _go(client, manager[1], rid, "reject", "قیمت نامناسب")
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "REJECTED"
    assert _go(client, manager[1], rid, "approve").status_code == 403  # terminal


# ── full cycle ───────────────────────────────────────────────────────
def test_full_cycle(client, rep, manager, customer):
    rid = _approved(client, rep, manager, customer)
    # dispatch is a manager-side right; the rep cannot
    assert _dispatch(client, rep, rid).status_code == 403
    r = _dispatch(client, manager, rid, all_shipped=False)
    assert r.status_code == 201 and r.get_json()["data"]["status"] == "APPROVED"  # partial shipment: still to be shipped
    r = _dispatch(client, manager, rid, reference_number="H-2", all_shipped=True)
    assert r.get_json()["data"]["status"] == "DISPATCHED" and len(r.get_json()["data"]["dispatches"]) == 2  # «ارسال‌شده»

    # follow-ups / feedback only after the customer received the sample
    early = {"followup_date": dt.date.today().isoformat(), "method": "PHONE"}
    assert client.post(f"{BASE}/{rid}/followups", headers=rep[1], json=early).status_code == 403
    assert _deliver(client, rep[1], rid, delivered_date=(dt.date.today() + dt.timedelta(days=2)).isoformat()).status_code == 400
    r = _deliver(client, rep[1], rid, received_by="خانم رضایی")
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "AWAITING_FEEDBACK"
    assert r.get_json()["data"]["delivered_at"] == dt.date.today().isoformat()
    assert _deliver(client, rep[1], rid).status_code == 403  # already delivered

    # several follow-ups; they never close the request
    for i in range(3):
        f = client.post(f"{BASE}/{rid}/followups", headers=rep[1], json={"followup_date": dt.date.today().isoformat(), "method": "PHONE", "result": f"call {i}"})
        assert f.status_code == 201
    assert client.get(f"{BASE}/{rid}", headers=rep[1]).get_json()["data"]["status"] == "AWAITING_FEEDBACK"

    # final feedback rules
    fb = lambda **o: client.put(f"{BASE}/{rid}/feedback", headers=manager[1], json={"feedback_status": "ACCEPTED", "feedback_date": dt.date.today().isoformat(), **o})  # noqa: E731
    assert fb(feedback_status="REJECTED").status_code == 400          # reason required
    assert fb(feedback_status="ACCEPTED_WITH_CONDITIONS").status_code == 400  # conditions required
    assert fb(feedback_date=(dt.date.today() + dt.timedelta(days=3)).isoformat()).status_code == 400
    assert fb().status_code == 200
    assert _go(client, manager[1], rid, "complete").status_code == 200
    r = client.post(f"{BASE}/{rid}/convert", headers=manager[1], json={"note": "سفارش ۱۲۳"})
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "CONVERTED"
    events = [e["action"] for e in r.get_json()["data"]["events"]]
    assert events[:2] == ["created", "submitted"] and "feedback_recorded" in events and events[-1] == "converted"


def test_rejected_feedback_closes_and_allows_a_linked_new_request(client, rep, manager, customer):
    rid = _approved(client, rep, manager, customer)
    _dispatch(client, manager, rid)
    assert client.put(f"{BASE}/{rid}/feedback", headers=manager[1], json={"feedback_status": "ACCEPTED", "feedback_date": dt.date.today().isoformat()}).status_code == 403  # not received yet
    _deliver(client, rep[1], rid)
    r = client.put(f"{BASE}/{rid}/feedback", headers=manager[1], json={"feedback_status": "REJECTED", "feedback_date": dt.date.today().isoformat(), "rejection_reason": "MFI بالا"})
    assert r.get_json()["data"]["status"] == "COMPLETED"
    assert client.post(f"{BASE}/{rid}/convert", headers=manager[1], json={}).status_code == 403  # only ACCEPTED converts
    n = client.post(f"{BASE}/{rid}/new-request", headers=rep[1])
    assert n.status_code == 201
    assert n.get_json()["data"]["parent"]["id"] == rid and n.get_json()["data"]["status"] == "DRAFT"


def test_followup_before_dispatch_is_refused(client, rep, manager, customer):
    rid = _approved(client, rep, manager, customer)
    r = client.post(f"{BASE}/{rid}/followups", headers=rep[1], json={"followup_date": dt.date.today().isoformat(), "method": "EMAIL"})
    assert r.status_code == 403


# ── list / filters / analytics ───────────────────────────────────────
def test_list_filters_search_and_analytics(client, rep, manager, customer):
    rid = _approved(client, rep, manager, customer)
    _dispatch(client, manager, rid)
    other = _create(client, rep[1], customer)
    _go(client, rep[1], other["id"], "submit")
    h = manager[1]
    # brand and company name both find the customer; so does the request code
    code = client.get(f"{BASE}/{rid}", headers=h).get_json()["data"]["code"]
    for term in ("آریاپلاست", "پلیمر", f"RS-{rid:05d}", code, "HD5218"):
        data = client.get(BASE, query_string={"search": term}, headers=h).get_json()["data"]
        assert rid in [x["id"] for x in data], term
    assert [x["id"] for x in client.get(BASE, query_string={"status": "PENDING_APPROVAL"}, headers=h).get_json()["data"]] == [other["id"]]
    a = client.get(f"{BASE}/analytics", headers=h).get_json()["data"]
    assert a["kpis"]["total"] == 2 and a["kpis"]["pending"] == 1 and a["kpis"]["approved"] == 1 and a["kpis"]["dispatched"] == 1
    assert a["top_products"][0]["product"] == "پلی‌اتیلن" and a["top_products"][0]["requests"] == 2
    assert sum(t["count"] for t in a["trend"]) == 2
    assert a["conversion"]["dispatched"] == 1


def test_export_requires_permission(client, rep, manager, customer):
    _create(client, rep[1], customer)
    assert client.get(f"{BASE}/export", headers=rep[1]).status_code == 403
    r = client.get(f"{BASE}/export", headers=manager[1])
    assert r.status_code in (200, 409)  # 409 only if openpyxl is not installed in the test environment


def test_dispatch_reference_is_unique(client, rep, customer):
    _create(client, rep[1], customer, dispatch_ref_number="SMP-DUP")
    r = client.post(BASE, json=_body(customer, dispatch_ref_number="smp-dup"), headers=rep[1])
    assert r.status_code == 409


# ── daily reminders ──────────────────────────────────────────────────
def _reminders(user):
    from app.modules.notifications.models import Notification

    return [n for n in db.session.query(Notification).filter(Notification.user_id == user.id, Notification.type.like("SAMPLE_%")).all()]


def test_daily_reminders_follow_the_stage(client, rep, manager, customer):
    from app.modules.request_samples import reminders

    user = rep[0]
    rid = _approved(client, rep, manager, customer)
    # 1) approved, not shipped -> ship reminder for the rep, once per day
    assert reminders.generate_for(user.id) == 1 and reminders.generate_for(user.id) == 0
    assert [n.type for n in _reminders(user) if n.read_at is None and n.type.startswith("SAMPLE_REMIND")] == ["SAMPLE_REMIND_SHIP"]
    assert reminders.generate_for(manager[0].id) == 0  # not the responsible user

    # 2) shipped -> the ship reminder is cleared, a delivery reminder is due
    _dispatch(client, manager, rid)
    live = [n.type for n in _reminders(user) if n.read_at is None and n.type.startswith("SAMPLE_REMIND")]
    assert "SAMPLE_REMIND_SHIP" not in live
    assert reminders.generate_for(user.id) == 1
    assert [n.type for n in _reminders(user) if n.read_at is None and n.type.startswith("SAMPLE_REMIND")] == ["SAMPLE_REMIND_DELIVER"]

    # 3) received -> follow-up reminder until a follow-up WITH a next date exists
    _deliver(client, rep[1], rid)
    assert reminders.generate_for(user.id) == 1
    assert [n.type for n in _reminders(user) if n.read_at is None and n.type.startswith("SAMPLE_REMIND")] == ["SAMPLE_REMIND_FOLLOWUP"]
    nxt = (dt.date.today() + dt.timedelta(days=5)).isoformat()
    f = client.post(f"{BASE}/{rid}/followups", headers=rep[1], json={"followup_date": dt.date.today().isoformat(), "method": "PHONE", "next_followup_date": nxt})
    assert f.status_code == 201
    assert not [n for n in _reminders(user) if n.read_at is None and n.type.startswith("SAMPLE_REMIND")]
    assert reminders.generate_for(user.id) == 0  # next follow-up is in the future: silence until that date
