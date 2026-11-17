"""Tests for /api/purchases -- wizard steps, quotation rules, savings, workflow, access and dashboard.

NOTE: written alongside the module but not executed in the authoring environment (it had no
SQLAlchemy); run `pytest tests/modules/purchases` after `pip install -r requirements.txt`.
"""
import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from app.modules.suppliers.models import Supplier, SupplierCategory
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

BASE = "/api/purchases"
ALL = [f"procurement.purchase.{a}" for a in ("create", "read", "update", "delete", "approve", "export")]


def staff(*keys):
    user = make_user()
    for key in keys:
        perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
        grant_user_permission(user, perm, ScopeType.GLOBAL, None)
    db.session.commit()
    return auth_headers(user)


@pytest.fixture()
def world(app):
    """Two commodity groups and three suppliers."""
    cats = [SupplierCategory(name="پلیمر و رزین", sort_order=1), SupplierCategory(name="بسته‌بندی", sort_order=2)]
    sups = [Supplier(company_name=f"تأمین {i}", supplier_type="LEGAL", status="ACTIVE") for i in range(3)]
    db.session.add_all(cats + sups)
    db.session.commit()
    return {"cats": [c.id for c in cats], "sups": [s.id for s in sups]}


def basic(**o):
    body = {"requester_unit": "تولید", "requester_name": "علی رضایی", "request_date": "1405/08/20",
            "subject": "خرید رزین", "priority": "NORMAL", "reason": "کمبود موجودی", "complete": True}
    body.update(o)
    return body


def new_request(client, h, w, items=None, **over):
    r = client.post(BASE, json=basic(**over), headers=h)
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()["data"]["id"]
    items = items or [{"category_id": w["cats"][0], "name": "رزین PP", "quantity": 10, "unit": "کیلوگرم",
                       "estimated_unit_price": 1000}]
    r = client.put(f"{BASE}/{rid}/items", json={"items": items, "complete": True}, headers=h)
    assert r.status_code == 200, r.get_json()
    r = client.put(f"{BASE}/{rid}/budget", json={"budget_amount": 20000, "required_date": "1405/09/10",
                                                  "delivery_location": "انبار مرکزی", "complete": True}, headers=h)
    assert r.status_code == 200, r.get_json()
    assert client.post(f"{BASE}/{rid}/submit", headers=h).get_json()["data"]["status"] == "AWAITING_INQUIRY"
    return rid


def inquiry(w, idx, price, **o):
    return {"supplier_id": w["sups"][idx], "received_date": "1405/08/25", "validity_days": 10, "delivery_days": 7,
            "payment_terms": "نقدی", "lines": [{"item_id": o.pop("item_id"), "unit_price": price}], **o}


def item_id(client, h, rid):
    return client.get(f"{BASE}/{rid}", headers=h).get_json()["data"]["items"][0]["id"]


# ── wizard / workflow ────────────────────────────────────────────────
def test_full_purchase_flow_and_savings(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)

    # a reference price counts only once approved
    items = [{"id": iid, "category_id": world["cats"][0], "name": "رزین PP", "quantity": 10, "unit": "کیلوگرم",
              "estimated_unit_price": 1000, "reference_unit_price": 1100, "reference_source": "CONTRACT",
              "reference_note": "قرارداد 12"}]
    assert client.put(f"{BASE}/{rid}/items", json={"items": items}, headers=h).status_code == 200
    assert client.post(f"{BASE}/{rid}/approve-reference", json={"item_ids": [iid]}, headers=h).status_code == 200

    invs = [inquiry(world, 0, 950, item_id=iid), inquiry(world, 1, 1000, item_id=iid), inquiry(world, 2, 1050, item_id=iid)]
    d = client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": invs, "complete": True}, headers=h).get_json()["data"]
    assert d["status"] == "AWAITING_SELECTION"
    assert sum(1 for q in d["inquiries"] if q["is_lowest"]) == 1
    low = next(q for q in d["inquiries"] if q["is_lowest"])

    d = client.put(f"{BASE}/{rid}/selection", json={"inquiry_id": low["id"], "reasons": ["LOWEST_PRICE"], "complete": True},
                   headers=h).get_json()["data"]
    assert d["status"] == "PURCHASING"

    d = client.put(f"{BASE}/{rid}/result", json={
        "purchase_date": "1405/09/01", "delivery_status": "DELIVERED", "final_extra_costs": 500,
        "lines": [{"item_id": iid, "purchased_quantity": 10}], "complete": True}, headers=h).get_json()["data"]
    assert d["status"] == "COMPLETED"
    assert d["final_amount"] == 950 * 10 + 500
    assert d["savings"] == (1100 - 950) * 10          # (reference - final) x quantity
    kinds = [e["to_status"] for e in d["events"] if e["kind"] == "STATUS"]
    assert kinds[-1] == "COMPLETED" and "AWAITING_INQUIRY" in kinds


def test_savings_not_computed_without_approved_reference(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    d = client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": [inquiry(world, 0, 900, item_id=iid)],
                   "shortfall_reason": "تنها تأمین‌کنندهٔ موجود", "complete": True}, headers=h).get_json()["data"]
    client.put(f"{BASE}/{rid}/selection", json={"inquiry_id": d["inquiries"][0]["id"], "reasons": ["LOWEST_PRICE"], "complete": True}, headers=h)
    d = client.put(f"{BASE}/{rid}/result", json={"purchase_date": "1405/09/01", "delivery_status": "DELIVERED",
                   "lines": [{"item_id": iid, "purchased_quantity": 10}], "complete": True}, headers=h).get_json()["data"]
    assert d["status"] == "COMPLETED" and d["savings"] is None


def test_fewer_than_three_inquiries_need_a_reason(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    body = {"inquiries": [inquiry(world, 0, 900, item_id=iid), inquiry(world, 1, 950, item_id=iid)], "complete": True}
    r = client.put(f"{BASE}/{rid}/inquiries", json=body, headers=h)
    assert r.status_code == 400 and r.get_json()["error"]["details"][0]["field"] == "shortfall_reason"
    body["shortfall_reason"] = "دو تأمین‌کننده موجود بود"
    assert client.put(f"{BASE}/{rid}/inquiries", json=body, headers=h).status_code == 200


def test_four_inquiries_rejected(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    invs = [inquiry(world, i % 3, 900 + i, item_id=iid) for i in range(4)]
    assert client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": invs}, headers=h).status_code == 400


def test_non_lowest_supplier_requires_explanation(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    invs = [inquiry(world, 0, 900, item_id=iid), inquiry(world, 1, 1000, item_id=iid), inquiry(world, 2, 1100, item_id=iid)]
    d = client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": invs, "complete": True}, headers=h).get_json()["data"]
    dear = next(q for q in d["inquiries"] if q["total_price"] == 10000)
    r = client.put(f"{BASE}/{rid}/selection", json={"inquiry_id": dear["id"], "reasons": ["QUALITY"], "complete": True}, headers=h)
    assert r.status_code == 400 and r.get_json()["error"]["details"][0]["field"] == "note"
    r = client.put(f"{BASE}/{rid}/selection", json={"inquiry_id": dear["id"], "reasons": ["QUALITY"],
                                                      "note": "کیفیت بهتر", "complete": True}, headers=h)
    assert r.status_code == 200


def test_items_locked_once_inquiries_exist(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": [inquiry(world, 0, 900, item_id=iid)]}, headers=h)
    extra = [{"id": iid, "category_id": world["cats"][0], "name": "رزین PP", "quantity": 10, "unit": "کیلوگرم"},
             {"category_id": world["cats"][1], "name": "کیسه", "quantity": 5, "unit": "عدد"}]
    assert client.put(f"{BASE}/{rid}/items", json={"items": extra}, headers=h).status_code == 409


def test_cancel_needs_reason_and_locks_the_request(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    assert client.post(f"{BASE}/{rid}/cancel", json={}, headers=h).status_code == 400
    assert client.post(f"{BASE}/{rid}/cancel", json={"note": "منتفی شد"}, headers=h).get_json()["data"]["status"] == "CANCELLED"
    assert client.put(f"{BASE}/{rid}/basic", json={"subject": "x"}, headers=h).status_code == 409
    back = client.post(f"{BASE}/{rid}/send-back", json={"note": "بازگشایی"}, headers=h).get_json()["data"]
    assert back["status"] == "NEEDS_REVISION"


# ── access (enforced in the backend) ─────────────────────────────────
def test_access_levels(client, world):
    viewer = staff("procurement.purchase.read")
    expert = staff("procurement.purchase.read", "procurement.purchase.create", "procurement.purchase.update")
    nobody = staff()
    assert client.post(BASE, json=basic(), headers=viewer).status_code == 403
    assert client.get(BASE, headers=nobody).status_code == 403
    rid = new_request(client, expert, world)
    assert client.get(f"{BASE}/{rid}", headers=viewer).status_code == 200
    assert client.put(f"{BASE}/{rid}/basic", json={"subject": "y"}, headers=viewer).status_code == 403
    iid = item_id(client, expert, rid)
    assert client.post(f"{BASE}/{rid}/approve-reference", json={"item_ids": [iid]}, headers=expert).status_code == 403
    assert client.delete(f"{BASE}/{rid}", headers=expert).status_code == 403
    assert client.get(f"{BASE}/export?kind=requests", headers=expert).status_code == 403   # no export permission


# ── dashboard / list / export ────────────────────────────────────────
def test_dashboard_matches_the_records(client, world):
    h = staff(*ALL)
    for _ in range(2):
        rid = new_request(client, h, world)
    done = new_request(client, h, world)
    iid = item_id(client, h, done)
    d = client.put(f"{BASE}/{done}/inquiries", json={"inquiries": [inquiry(world, 0, 800, item_id=iid)],
                   "shortfall_reason": "یک تأمین‌کننده", "complete": True}, headers=h).get_json()["data"]
    client.put(f"{BASE}/{done}/selection", json={"inquiry_id": d["inquiries"][0]["id"], "reasons": ["LOWEST_PRICE"], "complete": True}, headers=h)
    client.put(f"{BASE}/{done}/result", json={"purchase_date": "1405/09/01", "delivery_status": "DELIVERED",
               "lines": [{"item_id": iid, "purchased_quantity": 10}], "complete": True}, headers=h)

    dash = client.get(f"{BASE}/dashboard", headers=h).get_json()["data"]
    assert dash["kpis"]["total"]["value"] == 3
    assert dash["kpis"]["completed"]["value"] == 1
    assert dash["kpis"]["open"]["value"] == 2
    assert dash["kpis"]["spent"]["value"] == 8000
    assert dash["kpis"]["savings"]["value"] is None                      # no approved reference price
    names = {g["name"]: g for g in dash["groups"]}
    assert names["پلیمر و رزین"]["requests"] == 3 and names["بسته‌بندی"]["requests"] == 0   # groups come from the DB

    only_done = client.get(f"{BASE}?kpi=completed", headers=h).get_json()
    assert only_done["meta"]["total"] == 1
    filtered = client.get(f"{BASE}/dashboard?category_id={world['cats'][1]}", headers=h).get_json()["data"]
    assert filtered["kpis"]["total"]["value"] == 0                       # filters reach every KPI


def test_export_follows_filters(client, world):
    h = staff(*ALL)
    new_request(client, h, world)
    r = client.get(f"{BASE}/export?kind=requests&format=xlsx", headers=h)
    assert r.status_code == 200 and r.mimetype.endswith("spreadsheetml.sheet")
    j = client.get(f"{BASE}/export?kind=requests&format=json&request_no=NOPE", headers=h).get_json()["data"]
    assert j["rows"] == []
    assert len(client.get(f"{BASE}/export?kind=requests&format=json", headers=h).get_json()["data"]["rows"]) == 1


def test_request_numbers_are_unique_and_audit_is_written(client, world):
    from app.core.audit_logs.models import AuditLog
    h = staff(*ALL)
    a, b = new_request(client, h, world), new_request(client, h, world)
    nos = {client.get(f"{BASE}/{i}", headers=h).get_json()["data"]["request_no"] for i in (a, b)}
    assert len(nos) == 2
    assert db.session.query(AuditLog).filter_by(module="procurement", action="create").count() == 2
