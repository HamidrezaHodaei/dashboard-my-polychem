"""Tests for the item-based purchase flow (/api/purchases/flow): warehouse -> procurement -> manager -> finance ->
delivery, where EVERY goods line has its own quotations, approval, payment, shipping, delivery and warehouse receipt.

NOTE: written alongside the module but not executed in the authoring environment (it had no SQLAlchemy / Flask);
run `pytest tests/modules/purchases/test_purchase_flow.py` after `pip install -r requirements.txt`.
"""
import io
from datetime import datetime, timedelta

import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from app.modules.purchases.models import PurchaseOption, PurchaseProduct, PurchaseRequest
from app.modules.suppliers.models import Supplier, SupplierCategory
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

BASE = "/api/purchases/flow"
P = "procurement.purchase."


def staff(*actions):
    user = make_user()
    for a in actions:
        key = P + a
        perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
        grant_user_permission(user, perm, ScopeType.GLOBAL, None)
    db.session.commit()
    return auth_headers(user)


@pytest.fixture()
def world(app):
    cats = [SupplierCategory(name="پلیمر و رزین", sort_order=1), SupplierCategory(name="بسته‌بندی", sort_order=2)]
    sups = [Supplier(company_name=f"تأمین {i}", supplier_type="LEGAL", status="ACTIVE") for i in range(3)]
    db.session.add_all(cats + sups)
    db.session.flush()
    prods = [PurchaseProduct(name="رزین PP", code="RS-1", unit="کیلوگرم", category_id=cats[0].id),
             PurchaseProduct(name="کیسه", code="K-7", unit=None, category_id=None),
             PurchaseProduct(name="پالت", code="PL-3", unit="عدد", category_id=cats[1].id)]
    db.session.add_all(prods)
    db.session.add_all([PurchaseOption(kind="UNIT", label="تولید"), PurchaseOption(kind="UNIT", label="فروش"),
                        PurchaseOption(kind="REQUEST_TYPE", label="خرید جدید")])
    db.session.commit()
    return {"cats": [c.id for c in cats], "sups": [s.id for s in sups], "prods": [p.id for p in prods]}


_n = iter(range(1, 10_000))


def line(w, prod=0, **o):
    d = {"product_id": w["prods"][prod], "quantity": 10, "current_stock": 3, "request_type": "خرید جدید",
         "purchase_subject": "GENERAL", "priority": "NORMAL"}
    if prod == 1:                       # a product without group / unit: the user fills them in
        d.update({"category_id": w["cats"][1], "unit": "بسته"})
    d.update(o)
    return d


def head(w, items, **o):
    body = {"request_no": f"F-{next(_n)}", "requester_unit": "تولید", "requester_name": "علی رضایی",
            "required_date": (datetime.utcnow() + timedelta(days=30)).date().isoformat(), "items": items}
    body.update(o)
    return body


def register(client, h, w, items=None, **o):
    r = client.post(f"{BASE}/requests", json=head(w, items or [line(w, 0), line(w, 1), line(w, 2)], **o), headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def upload(client, h, name="x.pdf"):
    r = client.post("/api/purchases/files", data={"file": (io.BytesIO(b"%PDF-1.4 test"), name)}, headers=h,
                    content_type="multipart/form-data")
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]["id"]


def quote(client, h, rid, iid, price, sup=None, **o):
    body = {"supplier_name": sup or f"فروشنده {price}", "unit_price": price, "payment_method": "CASH", **o}
    r = client.post(f"{BASE}/requests/{rid}/items/{iid}/quotes", json=body, headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def get(client, h, rid):
    return client.get(f"{BASE}/requests/{rid}", headers=h).get_json()["data"]


def by_name(d, name):
    return next(i for i in d["items"] if i["name"] == name)


# ── registration ─────────────────────────────────────────────────────
def test_registration_fields_and_defaults(client, world):
    wh = staff("warehouse")
    d = register(client, wh, world)
    assert d["status"] == "UNDER_REVIEW" and d["status_label"] == "در حال بررسی"      # the first status is automatic
    assert d["request_date"] and d["required_date"]
    assert [i["status"] for i in d["items"]] == ["PENDING"] * 3
    resin = by_name(d, "رزین PP")
    assert resin["unit"] == "کیلوگرم" and resin["category_name"] == "پلیمر و رزین" and resin["product_code"] == "RS-1"
    assert by_name(d, "کیسه")["unit"] == "بسته"                                           # filled by hand when the catalog has none
    assert "quotes" not in resin                                                          # warehouse never sees prices


def test_registration_validation(client, world):
    wh = staff("warehouse")
    w = world
    ok = lambda **o: client.post(f"{BASE}/requests", json=head(w, [line(w)], **o), headers=wh)   # noqa: E731
    assert ok(required_date=None).status_code == 400                                       # تاریخ نیاز اجباری
    assert ok(requester_unit="ناشناس").status_code == 400                                 # must come from the list
    assert ok(requester_name=None).status_code == 400
    assert client.post(f"{BASE}/requests", json=head(w, []), headers=wh).status_code == 400
    for missing in ("current_stock", "purchase_subject", "priority", "request_type", "quantity"):
        bad = line(w)
        bad.pop(missing)
        assert client.post(f"{BASE}/requests", json=head(w, [bad]), headers=wh).status_code == 400, missing
    assert client.post(f"{BASE}/requests", json=head(w, [line(w, purchase_subject="OTHER")]), headers=wh).status_code == 400
    # reorder point is optional
    assert ok().status_code == 201
    # a typed request number must be unique
    first = head(w, [line(w)], request_no="DUP-1")
    assert client.post(f"{BASE}/requests", json=first, headers=wh).status_code == 201
    assert client.post(f"{BASE}/requests", json=first, headers=wh).status_code == 400


def test_only_warehouse_registers(client, world):
    for who in (staff("procure"), staff("finance"), staff("read"), staff()):
        assert client.post(f"{BASE}/requests", json=head(world, [line(world)]), headers=who).status_code == 403


# ── the whole path with independent items ────────────────────────────
def test_multi_item_request_end_to_end(client, world):
    wh, pr, mg, fin = staff("warehouse"), staff("procure", "read"), staff("manager"), staff("finance")
    d = register(client, wh, world)
    rid = d["id"]
    a, b, c = (by_name(d, n)["id"] for n in ("رزین PP", "کیسه", "پالت"))

    # procurement: first status, then sourcing
    r = client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr).get_json()["data"]
    assert r["status"] == "SOURCING" and {i["status"] for i in r["items"]} == {"INQUIRY"}
    for iid, place in ((a, "LOCAL"), (b, "NON_LOCAL"), (c, "LOCAL")):
        assert client.put(f"{BASE}/requests/{rid}/items/{iid}/supply-place", json={"supply_place": place}, headers=pr).status_code == 200
    # every item has its own suppliers and prices (several quotes for one item)
    quote(client, pr, rid, a, 1000, "الف")
    quote(client, pr, rid, a, 900, "ب", payment_method="CHEQUE")
    quote(client, pr, rid, b, 5000, "ج")
    d = quote(client, pr, rid, c, 700, "د")
    assert [by_name(d, n)["quotes_count"] for n in ("رزین PP", "کیسه", "پالت")] == [2, 1, 1]

    # an item without a quote / supply place cannot go to the manager
    assert client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [a, b, c]}, headers=pr).status_code == 200
    d = get(client, mg, rid)
    assert {i["status"] for i in d["items"]} == {"AWAITING_APPROVAL"}

    # manager decides item by item: approve a, approve c, send b back
    qa = by_name(d, "رزین PP")["quotes"]
    low = next(q for q in qa if q["is_lowest"])
    dear = next(q for q in qa if not q["is_lowest"])
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/decision", json={"action": "APPROVE", "quote_id": dear["id"]}, headers=mg).status_code == 400   # not the cheapest: reason needed
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/decision", json={"action": "APPROVE", "quote_id": low["id"]}, headers=mg).status_code == 200
    qc = by_name(d, "پالت")["quotes"][0]["id"]
    assert client.post(f"{BASE}/requests/{rid}/items/{c}/decision", json={"action": "APPROVE", "quote_id": qc}, headers=mg).status_code == 200
    assert client.post(f"{BASE}/requests/{rid}/items/{b}/decision", json={"action": "RETURN"}, headers=mg).status_code == 400       # reason required
    d = client.post(f"{BASE}/requests/{rid}/items/{b}/decision", json={"action": "RETURN", "note": "قیمت بالا"}, headers=mg).get_json()["data"]
    assert by_name(d, "کیسه")["status"] == "INQUIRY" and by_name(d, "رزین PP")["status"] == "IN_FINANCE"
    assert d["status"] == "REFERRED_FINANCE"                                                  # automatic

    # a manager cannot pay, finance cannot approve
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/payment", json={"method": "CASH"}, headers=mg).status_code == 403
    assert client.post(f"{BASE}/requests/{rid}/items/{b}/decision", json={"action": "RETURN", "note": "x"}, headers=fin).status_code == 403

    # finance: cash needs date + id + receipt; cheque needs the cheque data
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/payment", json={"method": "CASH", "paid_date": "1405/09/01"}, headers=fin).status_code == 400
    cash = {"method": "CASH", "paid_date": "1405/09/01", "payment_ref": "TRX-9", "receipt_file_id": upload(client, fin)}
    d = client.post(f"{BASE}/requests/{rid}/items/{a}/payment", json=cash, headers=fin).get_json()["data"]
    assert by_name(d, "رزین PP")["payment"]["method"] == "CASH" and by_name(d, "رزین PP")["payment"]["payment_ref"] == "TRX-9"
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/payment", json=cash, headers=fin).status_code == 409   # never overwritten
    bad_chq = {"method": "CHEQUE", "cheque_no": "123", "cheque_amount": 7000}
    assert client.post(f"{BASE}/requests/{rid}/items/{c}/payment", json=bad_chq, headers=fin).status_code == 400
    chq = {**bad_chq, "cheque_file_id": upload(client, fin, "c.png"), "cheque_issue_date": "1405/09/01",
           "cheque_due_date": "1405/08/01"}
    assert client.post(f"{BASE}/requests/{rid}/items/{c}/payment", json=chq, headers=fin).status_code == 400   # due before issue
    chq["cheque_due_date"] = "1405/10/01"
    assert client.post(f"{BASE}/requests/{rid}/items/{c}/payment", json=chq, headers=fin).status_code == 200

    d = client.post(f"{BASE}/requests/{rid}/finance-return", json={}, headers=fin).get_json()["data"]
    assert by_name(d, "رزین PP")["status"] == "PAID" and by_name(d, "پالت")["status"] == "PAID"
    assert by_name(d, "کیسه")["status"] == "INQUIRY"

    # shipping / delivery are per item; delivering one does not close the request
    assert client.post(f"{BASE}/requests/{rid}/items/{a}/status", json={"status": "SHIPPING"}, headers=pr).status_code == 200
    assert client.post(f"{BASE}/requests/{rid}/items/{b}/status", json={"status": "DELIVERED"}, headers=pr).status_code == 400   # not paid yet
    d = client.post(f"{BASE}/requests/{rid}/items/{c}/status", json={"status": "DELIVERED"}, headers=pr).get_json()["data"]
    assert d["status"] == "PARTIAL_DELIVERY" and d["missing_receipts"] == 1
    assert by_name(d, "پالت")["receipt_missing"] is True and by_name(d, "رزین PP")["status"] == "SHIPPING"

    # the warehouse uploads the receipt of THAT item, once
    rec = upload(client, wh, "receipt.pdf")
    d = client.post(f"{BASE}/requests/{rid}/items/{c}/receipt", json={"file_id": rec}, headers=wh).get_json()["data"]
    assert by_name(d, "پالت")["receipt"]["name"] == "receipt.pdf" and d["missing_receipts"] == 0
    assert client.post(f"{BASE}/requests/{rid}/items/{c}/receipt", json={"file_id": upload(client, wh)}, headers=wh).status_code == 409

    # re-quote b, approve, pay, deliver the rest -> the request closes only when EVERY item is delivered
    quote(client, pr, rid, b, 4500, "ه")
    client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [b]}, headers=pr)
    qb = by_name(get(client, mg, rid), "کیسه")["quotes"]
    best = next(q for q in qb if q["is_lowest"])["id"]
    client.post(f"{BASE}/requests/{rid}/items/{b}/decision", json={"action": "APPROVE", "quote_id": best}, headers=mg)
    client.post(f"{BASE}/requests/{rid}/items/{b}/payment", json={**cash, "receipt_file_id": upload(client, fin)}, headers=fin)
    client.post(f"{BASE}/requests/{rid}/finance-return", json={}, headers=fin)
    for iid in (a, b):
        d = client.post(f"{BASE}/requests/{rid}/items/{iid}/status", json={"status": "DELIVERED", "file_id": upload(client, wh)}, headers=wh).get_json()["data"]
    assert d["status"] == "COMPLETED" and d["status_label"] == "تحویل داده‌شده – بسته"
    # the history records the status changes of each item
    assert any(e["scope"] == "ITEM" and e["item_name"] == "کیسه" for e in d["events"])


def test_quotes_lock_after_sending_and_unpaid_data_is_not_overwritten(client, world):
    wh, pr = staff("warehouse"), staff("procure")
    rid = register(client, wh, world, [line(world)])["id"]
    iid = get(client, pr, rid)["items"][0]["id"]
    assert client.post(f"{BASE}/requests/{rid}/items/{iid}/quotes", json={"supplier_name": "x", "unit_price": 1, "payment_method": "CASH"}, headers=pr).status_code == 409   # not in sourcing yet
    client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr)
    qid = quote(client, pr, rid, iid, 100)["items"][0]["quotes"][0]["id"]
    client.put(f"{BASE}/requests/{rid}/items/{iid}/supply-place", json={"supply_place": "LOCAL"}, headers=pr)
    client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [iid]}, headers=pr)
    r = client.put(f"{BASE}/requests/{rid}/items/{iid}/quotes/{qid}", json={"supplier_name": "y", "unit_price": 1, "payment_method": "CASH"}, headers=pr)
    assert r.status_code == 409
    assert client.delete(f"{BASE}/requests/{rid}/items/{iid}/quotes/{qid}", headers=pr).status_code == 409


def test_submit_needs_quote_and_supply_place(client, world):
    wh, pr = staff("warehouse"), staff("procure")
    rid = register(client, wh, world, [line(world)])["id"]
    iid = get(client, pr, rid)["items"][0]["id"]
    client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr)
    assert client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [iid]}, headers=pr).status_code == 400
    quote(client, pr, rid, iid, 100)
    assert client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [iid]}, headers=pr).status_code == 400   # supply place missing
    client.put(f"{BASE}/requests/{rid}/items/{iid}/supply-place", json={"supply_place": "NON_LOCAL"}, headers=pr)
    assert client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [iid]}, headers=pr).status_code == 200


# ── returned for correction / void ───────────────────────────────────
def test_return_for_correction_and_void(client, world):
    wh, pr = staff("warehouse"), staff("procure")
    d = register(client, wh, world, [line(world), line(world, 2)])
    rid = d["id"]
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "RETURNED"}, headers=pr).status_code == 400   # reason needed
    r = client.post(f"{BASE}/requests/{rid}/status", json={"status": "RETURNED", "note": "تعداد نادرست"}, headers=pr).get_json()["data"]
    assert r["status"] == "RETURNED" and r["status_note"] == "تعداد نادرست"
    # only a returned request can be edited, and only by the warehouse
    keep = [{"id": d["items"][0]["id"], **line(world, quantity=25)}, {"id": d["items"][1]["id"], **line(world, 2)}]
    body = head(world, keep, request_no=d["request_no"])
    assert client.put(f"{BASE}/requests/{rid}", json=body, headers=pr).status_code == 403
    r = client.put(f"{BASE}/requests/{rid}", json=body, headers=wh).get_json()["data"]
    assert r["status"] == "UNDER_REVIEW" and r["items"][0]["quantity"] == 25 and len(r["items"]) == 2
    assert client.put(f"{BASE}/requests/{rid}", json=body, headers=wh).status_code == 409        # no longer returned
    # void cancels the open items and keeps the record
    r = client.post(f"{BASE}/requests/{rid}/status", json={"status": "VOID", "note": "لغو شد"}, headers=pr).get_json()["data"]
    assert r["status"] == "VOID" and {i["status"] for i in r["items"]} == {"CANCELLED"}
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr).status_code == 409


def test_status_cannot_be_forced_after_finance(client, world):
    wh, pr, mg = staff("warehouse"), staff("procure"), staff("manager")
    rid = register(client, wh, world, [line(world)])["id"]
    iid = get(client, pr, rid)["items"][0]["id"]
    client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr)
    q = quote(client, pr, rid, iid, 100)["items"][0]["quotes"][0]["id"]
    client.put(f"{BASE}/requests/{rid}/items/{iid}/supply-place", json={"supply_place": "LOCAL"}, headers=pr)
    client.post(f"{BASE}/requests/{rid}/submit-to-manager", json={"item_ids": [iid]}, headers=pr)
    client.post(f"{BASE}/requests/{rid}/items/{iid}/decision", json={"action": "APPROVE", "quote_id": q}, headers=mg)
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "VOID", "note": "x"}, headers=pr).status_code == 409
    # …but the single item can still be cancelled (nothing paid yet), with a reason
    assert client.post(f"{BASE}/requests/{rid}/items/{iid}/status", json={"status": "CANCELLED"}, headers=pr).status_code == 400
    d = client.post(f"{BASE}/requests/{rid}/items/{iid}/status", json={"status": "CANCELLED", "note": "منتفی"}, headers=pr).get_json()["data"]
    assert d["status"] == "VOID"


# ── access levels ────────────────────────────────────────────────────
def test_each_unit_only_sees_and_does_its_own_part(client, world):
    wh, pr, mg, fin, viewer, nobody = (staff("warehouse"), staff("procure"), staff("manager"), staff("finance"), staff("read"), staff())
    rid = register(client, wh, world, [line(world)])["id"]
    iid = get(client, wh, rid)["items"][0]["id"]
    assert client.get(f"{BASE}/requests", headers=nobody).status_code == 403
    assert client.get(f"{BASE}/requests", headers=wh).get_json()["meta"]["total"] == 1
    # finance sees nothing until a request reaches it
    assert client.get(f"{BASE}/requests", headers=fin).get_json()["meta"]["total"] == 0
    assert client.get(f"{BASE}/requests/{rid}", headers=fin).status_code == 404
    # warehouse cannot change the procurement status or supply place; read-only user cannot change anything
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=wh).status_code == 403
    assert client.put(f"{BASE}/requests/{rid}/items/{iid}/supply-place", json={"supply_place": "LOCAL"}, headers=wh).status_code == 403
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=viewer).status_code == 403
    assert client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=mg).status_code == 403
    assert client.get(f"{BASE}/requests/{rid}", headers=viewer).status_code == 200
    assert client.put(f"{BASE}/sla", json={"rows": [{"priority": "NORMAL", "amount": 3, "unit": "DAYS"}]}, headers=pr).status_code == 403
    assert client.post(f"{BASE}/options", json={"kind": "UNIT", "label": "مالی"}, headers=pr).status_code == 403


# ── settings: pick lists + allowed time ──────────────────────────────
def test_admin_manages_unit_list_and_it_drives_the_form(client, world):
    admin, wh = staff("settings"), staff("warehouse")
    r = client.post(f"{BASE}/options", json={"kind": "UNIT", "label": "کنترل کیفیت"}, headers=admin)
    assert r.status_code == 201
    assert client.post(f"{BASE}/options", json={"kind": "UNIT", "label": "کنترل کیفیت"}, headers=admin).status_code == 400
    assert "کنترل کیفیت" in client.get(f"{BASE}/meta", headers=wh).get_json()["data"]["units"]
    d = register(client, wh, world, [line(world)], requester_unit="کنترل کیفیت")
    oid = r.get_json()["data"]["id"]
    assert client.delete(f"{BASE}/options/{oid}", headers=admin).status_code == 409              # used: deactivate instead
    assert client.patch(f"{BASE}/options/{oid}", json={"is_active": False}, headers=admin).status_code == 200
    assert "کنترل کیفیت" not in client.get(f"{BASE}/meta", headers=wh).get_json()["data"]["units"]
    assert client.post(f"{BASE}/requests", json=head(world, [line(world)], requester_unit="کنترل کیفیت"), headers=wh).status_code == 400
    assert d["requester_unit"] == "کنترل کیفیت"                                                  # the old request keeps its unit


# ── KPI ──────────────────────────────────────────────────────────────
def test_sla_and_kpi_calculation(client, world):
    wh, pr, mg, fin, admin = staff("warehouse"), staff("procure", "read", "export"), staff("manager"), staff("finance"), staff("settings")
    d = register(client, wh, world, [line(world, 0, priority="NORMAL"), line(world, 2, priority="EMERGENCY")])
    rid = d["id"]
    a, c = d["items"][0]["id"], d["items"][1]["id"]
    # 1 day for «normal» and 12 hours for «very urgent»
    r = client.put(f"{BASE}/sla", json={"rows": [{"priority": "NORMAL", "amount": 1, "unit": "DAYS"},
                                                {"priority": "URGENT", "amount": 2, "unit": "DAYS"},
                                                {"priority": "EMERGENCY", "amount": 12, "unit": "HOURS"}]}, headers=admin)
    assert r.status_code == 200
    assert client.put(f"{BASE}/sla", json={"rows": [{"priority": "NORMAL", "amount": 0, "unit": "DAYS"}]}, headers=admin).status_code == 400

    # move the registration moment two days back: both items are late by now
    req = db.session.get(PurchaseRequest, rid)
    req.submitted_at = datetime.utcnow() - timedelta(days=2)
    db.session.commit()
    k = client.get(f"{BASE}/kpi", headers=pr).get_json()["data"]
    assert k["overall"]["items"] == 2 and k["overall"]["open_overdue"] == 2 and k["overall"]["attainment_pct"] == 0.0
    by = {p["priority"]: p for p in k["by_priority"]}
    assert by["NORMAL"]["items"] == 1 and by["EMERGENCY"]["items"] == 1 and by["URGENT"]["items"] == 0
    assert by["EMERGENCY"]["avg_delay_hours"] > by["NORMAL"]["avg_delay_hours"] > 0           # 36 h vs 24 h late
    row = next(r_ for r_ in k["rows"] if r_["item_id"] == c)
    assert row["state"] == "OVERDUE" and row["priority_label"] == "خیلی فوری" and row["remaining_hours"] < 0

    # deliver the «normal» item on time: put the registration moment inside its allowed time
    req = db.session.get(PurchaseRequest, rid)
    req.submitted_at = datetime.utcnow() - timedelta(hours=2)
    db.session.commit()
    client.post(f"{BASE}/requests/{rid}/status", json={"status": "SOURCING"}, headers=pr)
    k = client.get(f"{BASE}/kpi?priority=NORMAL", headers=pr).get_json()["data"]
    assert k["overall"]["items"] == 1 and k["overall"]["open_in_time"] == 1 and k["overall"]["open_overdue"] == 0
    assert client.get(f"{BASE}/kpi?priority=BAD", headers=pr).status_code == 400
    assert client.get(f"{BASE}/kpi", headers=wh).status_code == 403                           # warehouse has no report access
    assert client.get(f"{BASE}/kpi/export", headers=pr).status_code == 200
    assert client.get(f"{BASE}/kpi/export", headers=staff("read")).status_code == 403          # export permission needed
