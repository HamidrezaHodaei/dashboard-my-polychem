"""Tests for /api/purchases -- wizard steps, quotation rules, savings, workflow, access and dashboard.

NOTE: written alongside the module but not executed in the authoring environment (it had no
SQLAlchemy); run `pytest tests/modules/purchases` after `pip install -r requirements.txt`.
"""
import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from app.modules.purchases.models import PurchaseProduct
from app.modules.suppliers.models import Supplier, SupplierCategory
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

BASE = "/api/purchases"
ALL = [f"procurement.purchase.{a}" for a in ("create", "read", "update", "delete", "approve", "export", "manage_catalog")]


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
    db.session.flush()
    prods = [PurchaseProduct(name="رزین PP", code="RS-0012/A", category_id=cats[0].id),
             PurchaseProduct(name="کیسه", code="007", category_id=cats[1].id)]
    db.session.add_all(prods)
    db.session.commit()
    return {"cats": [c.id for c in cats], "sups": [s.id for s in sups], "prods": [p.id for p in prods]}


_seq = iter(range(1, 10_000))


def basic(**o):
    body = {"request_no": f"P-{next(_seq)}/ب", "requester_unit": "تولید", "requester_name": "علی رضایی", "request_date": "1405/08/20",
            "subject": "خرید رزین", "priority": "NORMAL", "reason": "کمبود موجودی", "complete": True}
    body.update(o)
    return body


def new_request(client, h, w, items=None, **over):
    r = client.post(BASE, json=basic(**over), headers=h)
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()["data"]["id"]
    items = items or [{"product_id": w["prods"][0], "category_id": w["cats"][0], "quantity": 10, "unit": "کیلوگرم",
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
    d = client.post(f"{BASE}/{rid}/send-to-finance", headers=h).get_json()["data"]
    assert d["status"] == "SENT_TO_FINANCE" and d["pipeline_status"] == "SENT_TO_FINANCE"

    d = client.put(f"{BASE}/{rid}/result", json={
        "purchase_date": "1405/09/01", "delivery_status": "DELIVERED", "final_extra_costs": 500,
        "lines": [{"item_id": iid, "purchased_quantity": 10}], "complete": True}, headers=h).get_json()["data"]
    assert d["status"] == "COMPLETED" and d["status_label"] == "پایان‌یافته"
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
    client.post(f"{BASE}/{rid}/send-to-finance", headers=h)
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
             {"product_id": world["prods"][1], "category_id": world["cats"][1], "quantity": 5, "unit": "عدد"}]
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
    client.post(f"{BASE}/{done}/send-to-finance", headers=h)
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


def test_request_numbers_are_typed_by_the_expert(client, world):
    from app.core.audit_logs.models import AuditLog
    h = staff(*ALL)
    r = client.post(BASE, json=basic(request_no=""), headers=h)
    assert r.status_code == 400 and r.get_json()["error"]["details"][0]["field"] == "request_no"   # never auto-numbered
    a = client.post(BASE, json=basic(request_no="ک-1405/17"), headers=h).get_json()["data"]
    assert a["request_no"] == "ک-1405/17"
    assert client.post(BASE, json=basic(request_no="ک-1405/17"), headers=h).status_code == 400    # duplicate
    b = client.post(BASE, json=basic(request_no="77"), headers=h).get_json()["data"]
    assert client.put(f"{BASE}/{b['id']}/basic", json={"request_no": "ک-1405/17"}, headers=h).status_code == 400
    ok = client.put(f"{BASE}/{b['id']}/basic", json={"request_no": "  78  "}, headers=h).get_json()["data"]
    assert ok["request_no"] == "78"                                                                  # editable afterwards
    assert db.session.query(AuditLog).filter_by(module="procurement", action="update_basic").count() == 1


def test_review_status_cartable_and_rejected_stay(client, world):
    h = staff(*ALL)
    viewer = staff("procurement.purchase.read")
    rid = new_request(client, h, world)
    d = client.get(f"{BASE}/{rid}", headers=h).get_json()["data"]
    assert d["review_status"] == "PENDING_REVIEW" and d["review_label"] == "در انتظار بررسی"
    assert client.post(f"{BASE}/{rid}/review", json={"status": "APPROVED"}, headers=viewer).status_code == 403
    assert client.post(f"{BASE}/{rid}/review", json={"status": "NEEDS_REVISION"}, headers=h).status_code == 400   # reason needed
    d = client.post(f"{BASE}/{rid}/review", json={"status": "NEEDS_REVISION", "note": "فرم کاغذی ناقص بود"}, headers=h).get_json()["data"]
    assert d["review_status"] == "NEEDS_REVISION" and d["review_note"] == "فرم کاغذی ناقص بود"
    d = client.post(f"{BASE}/{rid}/review", json={"status": "REJECTED", "note": "بودجه ندارد"}, headers=h).get_json()["data"]
    assert d["review_status"] == "REJECTED" and any(e["kind"] == "REVIEW" for e in d["events"])
    # rejected: still listed, filterable, counted, but frozen until the expert changes the status
    assert client.get(f"{BASE}?review_status=REJECTED", headers=h).get_json()["meta"]["total"] == 1
    assert client.put(f"{BASE}/{rid}/basic", json={"subject": "x"}, headers=h).status_code == 409
    dash = client.get(f"{BASE}/dashboard", headers=h).get_json()["data"]
    assert {c["status"]: c["count"] for c in dash["review_counts"]}["REJECTED"] == 1
    assert dash["kpis"]["total"]["value"] == 1 and dash["kpis"]["open"]["value"] == 0      # counted in total, not "open"
    client.post(f"{BASE}/{rid}/review", json={"status": "PENDING_REVIEW"}, headers=h)
    assert client.put(f"{BASE}/{rid}/basic", json={"subject": "x"}, headers=h).status_code == 200


def test_direct_purchase_without_request_feeds_the_dashboard(client, world):
    h = staff(*ALL)
    body = {"doc_no": "D-17/الف", "purchase_date": "1405/08/10", "title": "تعمیر پمپ", "supplier_id": world["sups"][0],
            "amount": 12500000, "usage_place": "سالن تولید ۲", "category_id": world["cats"][0]}
    made = client.post(f"{BASE}/direct", json=body, headers=h).get_json()["data"]
    assert made["amount"] == 12500000 and made["supplier_name"] == "تأمین 0"
    assert client.post(f"{BASE}/direct", json=body, headers=h).status_code == 400            # same document number
    free = {**body, "doc_no": "D-18", "supplier_id": None, "supplier_name": "فروشگاه محلی", "amount": 500000}
    assert client.post(f"{BASE}/direct", json=free, headers=h).status_code == 201            # vendor outside the supplier bank
    assert client.post(f"{BASE}/direct", json={**free, "doc_no": "D-19", "amount": 10.5}, headers=h).status_code == 400
    lst = client.get(f"{BASE}/direct", headers=h).get_json()
    assert lst["meta"]["total"] == 2 and lst["meta"]["total_amount"] == 13000000

    dash = client.get(f"{BASE}/dashboard", headers=h).get_json()["data"]
    assert dash["kpis"]["direct"] == {"value": 2, "amount": 13000000}
    assert dash["kpis"]["spent"]["value"] == 13000000 and dash["kpis"]["total"]["value"] == 0   # no request was needed
    grp = {g["name"]: g for g in dash["groups"]}["پلیمر و رزین"]
    assert grp["direct_count"] == 2 and grp["spent"] == 13000000
    assert {s["name"]: s["direct_amount"] for s in dash["suppliers"]}["فروشگاه محلی"] == 500000
    # request-only filters leave them out; date / group / supplier filters apply to them
    assert client.get(f"{BASE}/dashboard?status=COMPLETED", headers=h).get_json()["data"]["kpis"]["direct"]["value"] == 0
    assert client.get(f"{BASE}/dashboard?supplier=محلی", headers=h).get_json()["data"]["kpis"]["direct"]["value"] == 1
    j = client.get(f"{BASE}/export?kind=direct&format=json", headers=h).get_json()["data"]
    assert len(j["rows"]) == 2
    upd = client.put(f"{BASE}/direct/{made['id']}", json={"amount": 99000}, headers=h).get_json()["data"]
    assert upd["amount"] == 99000
    assert client.delete(f"{BASE}/direct/{made['id']}", headers=staff("procurement.purchase.read")).status_code == 403
    assert client.delete(f"{BASE}/direct/{made['id']}", headers=h).status_code == 200


# ── catalog, codes, units, finance step, IRR ─────────────────────────
def test_catalog_is_admin_managed_and_code_is_free_text(client, world):
    admin, expert = staff(*ALL), staff("procurement.purchase.read", "procurement.purchase.create", "procurement.purchase.update")
    body = {"name": "گریس صنعتی", "code": "0045-B/تست"}
    assert client.post(f"{BASE}/products", json=body, headers=expert).status_code == 403
    made = client.post(f"{BASE}/products", json=body, headers=admin).get_json()["data"]
    assert made["code"] == "0045-B/تست"                                  # leading zeros / letters / separators kept as typed
    assert client.post(f"{BASE}/products", json={"name": "گریس صنعتی"}, headers=admin).status_code == 400   # duplicate name
    assert client.post(f"{BASE}/products", json={"name": "دیگر", "code": "0045-b/تست"}, headers=admin).status_code == 400  # duplicate code
    assert client.post(f"{BASE}/products", json={"name": "بد", "code": "ab$%"}, headers=admin).status_code == 400
    assert client.post(f"{BASE}/products", json={"name": "بدون کد"}, headers=admin).status_code == 201
    found = client.get(f"{BASE}/products?q=گریس", headers=expert).get_json()["data"]    # the wizard can search it
    assert [p["code"] for p in found] == ["0045-B/تست"]


def test_item_must_come_from_catalog_and_keeps_its_code(client, world):
    h = staff(*ALL)
    rid = client.post(BASE, json=basic(), headers=h).get_json()["data"]["id"]
    free = [{"category_id": world["cats"][0], "name": "آزاد", "quantity": 1, "unit": "عدد"}]
    assert client.put(f"{BASE}/{rid}/items", json={"items": free}, headers=h).status_code == 400
    ok = [{"product_id": world["prods"][0], "category_id": world["cats"][0], "name": "هرچه", "quantity": 1, "unit": "بسته ۲۵ کیلویی"}]
    d = client.put(f"{BASE}/{rid}/items", json={"items": ok}, headers=h).get_json()["data"]
    assert d["items"][0]["name"] == "رزین PP" and d["items"][0]["product_code"] == "RS-0012/A"
    assert d["items"][0]["unit"] == "بسته ۲۵ کیلویی"                     # any unit is accepted
    assert "بسته ۲۵ کیلویی" in client.get(f"{BASE}/units?q=بسته", headers=h).get_json()["data"]
    used = client.delete(f"{BASE}/products/{world['prods'][0]}", headers=h)
    assert used.status_code == 409                                       # in use: deactivate instead


def test_result_needs_send_to_finance_and_statuses(client, world):
    h = staff(*ALL)
    rid = new_request(client, h, world)
    iid = item_id(client, h, rid)
    d = client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": [inquiry(world, 0, 900, item_id=iid)],
                   "shortfall_reason": "یک تأمین‌کننده", "complete": True}, headers=h).get_json()["data"]
    assert client.put(f"{BASE}/{rid}/inquiries", json={"inquiries": [inquiry(world, 0, 900, item_id=iid)]}, headers=h).get_json()["data"]["status"] in ("INQUIRING", "AWAITING_SELECTION")
    client.put(f"{BASE}/{rid}/selection", json={"inquiry_id": d["inquiries"][0]["id"], "reasons": ["QUALITY"], "complete": True}, headers=h)
    res = {"purchase_date": "1405/09/01", "delivery_status": "NOT_DELIVERED", "lines": [{"item_id": iid, "purchased_quantity": 10}], "complete": True}
    r = client.put(f"{BASE}/{rid}/result", json=res, headers=h)
    assert r.status_code == 400                                          # not sent to finance yet
    assert client.post(f"{BASE}/{rid}/send-to-finance", headers=h).get_json()["data"]["status_label"] == "ارسال به مالی"
    d = client.put(f"{BASE}/{rid}/result", json=res, headers=h).get_json()["data"]
    assert d["status"] == "AWAITING_DELIVERY" and d["status_label"] == "در حال تحویل و حمل"


def test_prices_are_whole_rials(client, world):
    h = staff(*ALL)
    rid = client.post(BASE, json=basic(), headers=h).get_json()["data"]["id"]
    bad = [{"product_id": world["prods"][0], "category_id": world["cats"][0], "quantity": 1, "unit": "عدد", "estimated_unit_price": 10.5}]
    assert client.put(f"{BASE}/{rid}/items", json={"items": bad}, headers=h).status_code == 400
