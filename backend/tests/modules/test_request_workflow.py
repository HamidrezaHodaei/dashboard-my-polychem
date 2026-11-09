"""The shared request-review workflow: logistics, suppliers and customers.

A CREATOR (no `update` permission at all) edits only while the request is a draft or has
been sent back; a finalised request is read-only for them (they can ask for a change); a
manager (`update` + `review`) decides: approve / reject / send back with a written reason.
"""
import io

import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user
from tests.modules.logistics.test_logistics import driver_body, national_code


def _user(*keys):
    user = make_user()
    for key in keys:
        perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
        grant_user_permission(user, perm, ScopeType.GLOBAL, None)
    db.session.commit()
    return user, auth_headers(user)


def _notifications(client, headers):
    return client.get("/api/notifications", headers=headers).get_json()["data"]


@pytest.fixture(autouse=True)
def _upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)


# ── logistics ────────────────────────────────────────────────────────
def test_logistics_creator_workflow(client, app):
    creator, c = _user("logistics.driver.read", "logistics.driver.create")
    _, other = _user("logistics.driver.read", "logistics.driver.create")
    _, m = _user("logistics.driver.read", "logistics.driver.update", "logistics.driver.review")
    base = "/api/logistics/applicants"

    # a draft: still the creator's
    r = client.post(base, json={**driver_body(), "status": "PENDING", "is_finalized": False}, headers=c)
    assert r.status_code == 201, r.get_json()
    rec = r.get_json()["data"]
    assert rec["is_finalized"] is False and rec["status"] == "PENDING"
    assert rec["my_actions"]["can_edit"] and rec["my_actions"]["can_finalize"]
    aid = rec["id"]
    area = {"area_type": "CITY", "coverage": [{"province": "قم", "cities": ["قم"]}]}
    assert client.patch(f"{base}/{aid}", json={"service_area": area}, headers=c).status_code == 200
    assert client.patch(f"{base}/{aid}", json={"service_area": area}, headers=other).status_code == 403  # not theirs
    # a manager cannot decide on a draft
    assert client.post(f"{base}/{aid}/review", json={"action": "APPROVE"}, headers=m).status_code == 409

    # ثبت نهایی -> read-only for the creator
    assert client.post(f"{base}/{aid}/finalize", headers=c).status_code == 200
    assert client.post(f"{base}/{aid}/finalize", headers=c).status_code == 409  # already submitted
    assert client.patch(f"{base}/{aid}", json={"service_area": area}, headers=c).status_code == 403
    got = client.get(f"{base}/{aid}", headers=c).get_json()["data"]
    assert not got["my_actions"]["can_edit"] and got["my_actions"]["can_request_change"]

    # the creator asks for a change (a reason is required)
    assert client.post(f"{base}/{aid}/request-change", json={"reason": " "}, headers=c).status_code == 400
    r = client.post(f"{base}/{aid}/request-change", json={"reason": "شماره موبایل اشتباه ثبت شده"}, headers=c)
    assert r.status_code == 200 and r.get_json()["data"]["change_request_note"] == "شماره موبایل اشتباه ثبت شده"
    assert client.post(f"{base}/{aid}/request-change", json={"reason": "x yz"}, headers=other).status_code == 403

    # the manager sends it back: the explanation is mandatory
    assert client.post(f"{base}/{aid}/review", json={"action": "REQUEST_EDIT"}, headers=m).status_code == 400
    r = client.post(f"{base}/{aid}/review", json={"action": "REQUEST_EDIT", "note": "موبایل را اصلاح کنید"}, headers=m)
    data = r.get_json()["data"]
    assert data["status"] == "NEEDS_EDIT" and data["review_note"] == "موبایل را اصلاح کنید"
    assert data["change_request_note"] is None  # answered

    # now the creator edits again and re-submits -> back to «در انتظار بررسی»
    assert client.patch(f"{base}/{aid}", json={"service_area": area}, headers=c).status_code == 200
    assert client.post(f"{base}/{aid}/finalize", headers=c).get_json()["data"]["status"] == "PENDING"
    assert client.patch(f"{base}/{aid}", json={"service_area": area}, headers=c).status_code == 403
    assert client.post(f"{base}/{aid}/review", json={"action": "APPROVE"}, headers=m).get_json()["data"]["status"] == "APPROVED"

    # the creator was told about each decision, in Persian
    titles = [n["title"] for n in _notifications(client, c)["items"]]
    assert any("نیازمند ویرایش" in t for t in titles) and any("تأیید" in t for t in titles)


# ── suppliers ────────────────────────────────────────────────────────
def test_supplier_creator_workflow(client, app):
    from tests.modules.suppliers.test_suppliers import _admin_payload
    _, c = _user("procurement.supplier.read", "procurement.supplier.create")
    _, m = _user("procurement.supplier.read", "procurement.supplier.update", "procurement.supplier.review")
    from app.modules.suppliers.models import SupplierCategory
    for i, name in enumerate(["پلیمر و رزین", "بسته‌بندی"], start=1):
        db.session.add(SupplierCategory(name=name, sort_order=i))
    db.session.commit()

    r = client.post("/api/suppliers", json=_admin_payload(client, c, is_finalized=False), headers=c)
    assert r.status_code == 201, r.get_json()
    sid = r.get_json()["data"]["id"]
    assert r.get_json()["data"]["review_status"] == "PENDING" and r.get_json()["data"]["is_finalized"] is False
    # the creator edits their own draft; staff-evaluation fields are ignored for them
    r = client.patch(f"/api/suppliers/{sid}", json={"website": "https://x.example", "status": "ACTIVE", "quality": "EXCELLENT"}, headers=c)
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["website"] == "https://x.example" and d["status"] == "SEMI_ACTIVE" and d["quality"] is None

    assert client.post(f"/api/suppliers/{sid}/finalize", headers=c).status_code == 200
    assert client.patch(f"/api/suppliers/{sid}", json={"website": "https://y.example"}, headers=c).status_code == 403
    assert client.post(f"/api/suppliers/{sid}/request-change", json={"reason": "آدرس سایت تغییر کرد"}, headers=c).status_code == 200
    # only a reviewer decides
    assert client.post(f"/api/suppliers/{sid}/review", json={"action": "APPROVE"}, headers=c).status_code == 403
    assert client.post(f"/api/suppliers/{sid}/review", json={"action": "REQUEST_EDIT"}, headers=m).status_code == 409  # note missing
    r = client.post(f"/api/suppliers/{sid}/review", json={"action": "REQUEST_EDIT", "note": "آدرس سایت را اصلاح کنید"}, headers=m)
    assert r.get_json()["data"]["review_status"] == "NEEDS_EDIT"
    assert client.patch(f"/api/suppliers/{sid}", json={"website": "https://y.example"}, headers=c).status_code == 200
    assert client.post(f"/api/suppliers/{sid}/finalize", headers=c).get_json()["data"]["review_status"] == "PENDING"
    assert client.post(f"/api/suppliers/{sid}/review", json={"action": "APPROVE"}, headers=m).get_json()["data"]["review_status"] == "APPROVED"


# ── customers ────────────────────────────────────────────────────────
def test_customer_creator_workflow(client, app):
    from app.modules.customers.models import CustomerCategory
    from app.modules.customers.test_customers import _body
    main = CustomerCategory(name="پلاستیک", sort_order=1)
    db.session.add(main)
    db.session.flush()
    db.session.add(CustomerCategory(name="تزریقی", parent_id=main.id, sort_order=1))
    db.session.commit()
    _, c = _user("crm.customer.read", "crm.customer.create")
    _, other = _user("crm.customer.read", "crm.customer.create")
    _, m = _user("crm.customer.read", "crm.customer.update", "crm.customer.review")

    r = client.post("/api/customers", json=_body(), headers=c)
    assert r.status_code == 201, r.get_json()
    d = r.get_json()["data"]
    cid = d["id"]
    assert d["is_finalized"] is False and d["review_status"] == "PENDING"
    assert client.patch(f"/api/customers/{cid}", json={"internal_notes": "یادداشت"}, headers=c).status_code == 200
    assert client.patch(f"/api/customers/{cid}", json={"internal_notes": "x"}, headers=other).status_code == 403
    assert client.post(f"/api/customers/{cid}/finalize", headers=c).status_code == 200
    assert client.post(f"/api/customers/{cid}/finalize", headers=c).status_code == 200  # idempotent
    assert client.patch(f"/api/customers/{cid}", json={"internal_notes": "y"}, headers=c).status_code == 403
    assert client.post(f"/api/customers/{cid}/request-change", json={"reason": "شماره تماس تغییر کرد"}, headers=c).status_code == 200
    r = client.post(f"/api/customers/{cid}/review", json={"action": "REQUEST_EDIT", "note": "شماره تماس را اصلاح کنید"}, headers=m)
    assert r.get_json()["data"]["review_status"] == "NEEDS_EDIT"
    assert client.patch(f"/api/customers/{cid}", json={"internal_notes": "z"}, headers=c).status_code == 200
    assert client.post(f"/api/customers/{cid}/finalize", headers=c).get_json()["data"]["review_status"] == "PENDING"
    assert client.post(f"/api/customers/{cid}/review", json={"action": "REJECT", "note": "مدارک ناقص"}, headers=m).get_json()["data"]["review_status"] == "REJECTED"
    assert client.post(f"/api/customers/{cid}/review", json={"action": "REOPEN"}, headers=m).get_json()["data"]["review_status"] == "PENDING"


def test_review_permission_is_a_matrix_column_for_these_modules():
    from app.permissions.registry import MATRIX_MODULES
    cols = {m.key: m.actions for m in MATRIX_MODULES}
    for key in ("crm.customer", "procurement.supplier", "logistics.company", "logistics.driver"):
        assert "review" in cols[key]
    assert "review" not in cols["tasks.task"]
