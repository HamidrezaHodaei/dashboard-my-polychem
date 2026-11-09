"""HTTP tests for /api/crm -- sales, filters, analytics, permissions, import, customer-bank link."""
import datetime as dt

import pytest

from app.core.authorization.models import ScopeType
from app.extensions import db
from app.modules.crm.models import CrmPaymentMethod, CrmSale
from app.modules.customers.models import Customer, CustomerOptionItem, CustomerType, OptionKind
from app.utils.jalali import from_jalali
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

SALE = ("read", "create", "update", "delete")


def _staff(*grants):
    """grants: ("sale", "read") pairs -> auth headers."""
    user = make_user()
    for resource, action in grants:
        grant_user_permission(user, make_permission(f"crm.{resource}.{action}"), ScopeType.GLOBAL, None)
    db.session.commit()
    return auth_headers(user)


@pytest.fixture
def h(app):
    return _staff(*[(r, a) for r in ("sale", "product") for a in SALE])


@pytest.fixture
def world(app):
    """Two customers in the customer bank (different provinces), one grade, one payment method."""
    a = Customer(customer_type=CustomerType.LEGAL, company_name="پلاستیک آلفا", factory_province="تهران", category="پلاستیک")
    b = Customer(customer_type=CustomerType.LEGAL, company_name="غذایی بتا", factory_province="فارس", category="غذایی")
    # what a sale sells is a GRADE of the customer bank's pick-list (customer_option_items, kind=GRADE)
    p = CustomerOptionItem(kind=OptionKind.GRADE, name="پلی‌اتیلن")
    m = CrmPaymentMethod(name="نقدی")
    db.session.add_all([a, b, p, m])
    db.session.commit()
    return {"a": a.id, "b": b.id, "p": p.id, "m": m.id}


def _sale(client, h, world, *, customer="a", date="1405/05/10", qty=1000, price=100, **over):
    body = {"customer_id": world[customer], "product_id": world["p"], "payment_method_id": world["m"],
            "quantity_kg": qty, "unit_price": price, "date": date, **over}
    r = client.post("/api/crm/sales", json=body, headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


# ── permissions ──────────────────────────────────────────────────────
def test_every_route_needs_its_permission(client, app, world):
    none = _staff()
    for method, url in [("get", "/api/crm/sales"), ("get", "/api/crm/analytics"), ("get", "/api/crm/options"),
                        ("get", "/api/crm/customers"), ("get", "/api/crm/products"),
                        ("post", "/api/crm/sales"),
                        ("post", "/api/crm/payment-methods"), ("post", "/api/crm/sales/import")]:
        assert getattr(client, method)(url, headers=none, json={} if method == "post" else None).status_code == 403, url
    assert client.get("/api/crm/sales").status_code == 401


def test_crud_actions_are_independent(client, app, world):
    reader = _staff(("sale", "read"))
    creator = _staff(("sale", "read"), ("sale", "create"))
    sale = _sale(client, creator, world)
    sid = sale["id"]
    assert client.get(f"/api/crm/sales/{sid}", headers=reader).status_code == 200
    assert client.patch(f"/api/crm/sales/{sid}", json={"description": "x"}, headers=creator).status_code == 403
    assert client.delete(f"/api/crm/sales/{sid}", headers=creator).status_code == 403
    # payment-method catalogue writes need crm.product.*, not crm.sale.*
    assert client.post("/api/crm/payment-methods", json={"name": "n"}, headers=creator).status_code == 403
    # CRM no longer owns products: there is no write route for them at all
    assert client.post("/api/crm/products", json={"name": "n"}, headers=creator).status_code in (404, 405)


def test_navigation_shows_crm_entries_only_with_permission(client, app):
    keys = lambda hd: {i["key"] for i in client.get("/api/me/navigation", headers=hd).get_json()["data"]["navigation"]}
    assert "crm_sales" not in keys(_staff())
    assert {"crm_sales", "crm_dashboard"} <= keys(_staff(("sale", "read")))


# ── customer bank link ───────────────────────────────────────────────
def test_sale_requires_existing_bank_customer_and_no_customer_is_created(client, h, world):
    r = client.post("/api/crm/sales", headers=h, json={
        "customer_id": 999999, "product_id": world["p"], "quantity_kg": 1, "unit_price": 1})
    assert r.status_code == 409
    before = db.session.query(Customer).count()
    _sale(client, h, world)
    assert db.session.query(Customer).count() == before


def test_sale_exposes_customer_from_bank_and_syncs_purchase_dates(client, h, world):
    s = _sale(client, h, world, date="1405/05/10")
    assert s["customer"]["id"] == world["a"] and s["customer"]["name"] == "پلاستیک آلفا"
    assert s["customer"]["province"] == "تهران"
    _sale(client, h, world, date="1405/07/01")
    c = db.session.get(Customer, world["a"])
    assert c.first_purchase_date == from_jalali(1405, 5, 10) and c.last_purchase_date == from_jalali(1405, 7, 1)
    assert client.delete(f"/api/crm/sales/{s['id']}", headers=h).status_code == 200
    db.session.expire_all()
    assert db.session.get(Customer, world["a"]).first_purchase_date == from_jalali(1405, 7, 1)


def test_customer_picker_reads_the_bank(client, h, world):
    names = [c["name"] for c in client.get("/api/crm/customers?search=آلفا", headers=h).get_json()["data"]]
    assert names == ["پلاستیک آلفا"]


# ── dates ────────────────────────────────────────────────────────────
def test_jalali_and_gregorian_dates_are_the_same_day(client, h, world):
    j = _sale(client, h, world, date="1405/08/15")
    g = _sale(client, h, world, date="2026-11-06")
    assert j["date_iso"] == g["date_iso"] == "2026-11-06" and j["date"] == "1405/08/15"
    assert (j["jalali_year"], j["jalali_month"]) == (1405, 8)
    p = _sale(client, h, world, date="۱۴۰۵/۸/۵")  # Persian digits, non-padded
    assert p["date"] == "1405/08/05"


def test_invalid_dates_are_rejected(client, h, world):
    for bad in ("1405/13/01", "1405/07/31", "nonsense"):
        r = client.post("/api/crm/sales", headers=h, json={
            "customer_id": world["a"], "product_id": world["p"], "quantity_kg": 1, "unit_price": 1, "date": bad})
        assert r.status_code == 400, bad


def test_range_filter_is_inclusive_and_accepts_both_calendars(client, h, world):
    for d in ("1405/01/31", "1405/02/01", "1405/02/15", "1405/02/31", "1405/03/01"):
        _sale(client, h, world, date=d)
    total = lambda q: client.get(f"/api/crm/sales?{q}", headers=h).get_json()["meta"]["total"]
    assert total("date_from=1405/02/01&date_to=1405/02/31") == 3
    g_from, g_to = from_jalali(1405, 2, 1).isoformat(), from_jalali(1405, 2, 31).isoformat()
    assert total(f"date_from={g_from}&date_to={g_to}") == 3            # Gregorian == Jalali
    assert total(f"date_from=1405/02/01&date_to={g_to}") == 3          # mixed calendars
    assert total("date_from=1405/02/15") == 3 and total("date_to=1405/02/01") == 2
    assert total("year=1405&month=2") == 3


def test_bad_or_inverted_range_is_a_400(client, h, world):
    assert client.get("/api/crm/sales?date_from=1405/05/10&date_to=1405/05/01", headers=h).status_code == 400
    assert client.get("/api/crm/sales?date_from=garbage", headers=h).status_code == 400
    assert client.get("/api/crm/analytics?date_to=1405/14/01", headers=h).status_code == 400
    assert client.get("/api/crm/sales?preset=forever", headers=h).status_code == 400


def test_preset_and_explicit_dates_combine_with_other_filters(client, h, world):
    from app.utils.jalali import tehran_today
    today = tehran_today().isoformat()
    _sale(client, h, world, date=today, customer="a")
    _sale(client, h, world, date=today, customer="b")
    _sale(client, h, world, date="1380/01/01", customer="a")
    total = lambda q: client.get(f"/api/crm/sales?{q}", headers=h).get_json()["meta"]["total"]
    assert total("preset=last_1m") == 2
    assert total(f"preset=last_1m&customer_id={world['a']}") == 1
    assert total("preset=last_1m&province=فارس") == 1                  # province comes from the bank
    assert total("preset=last_1m&date_from=1380/01/01") == 3           # explicit dates win over the preset


# ── analytics follow the same filters ────────────────────────────────
def test_returns_are_negative_and_analytics_match_the_list(client, h, world):
    _sale(client, h, world, qty=1000, price=100)                       # +100,000
    _sale(client, h, world, qty=100, price=100, document_type="RETURN")  # -10,000
    _sale(client, h, world, customer="b", qty=500, price=200, date="1405/06/01")  # +100,000 (other month)
    a = client.get("/api/crm/analytics", headers=h).get_json()["data"]
    assert a["kpis"]["net_amount"] == 190000 and a["kpis"]["net_quantity_kg"] == 1400
    assert (a["kpis"]["invoice_count"], a["kpis"]["return_count"], a["kpis"]["customer_count"]) == (2, 1, 2)
    assert [m["month"] for m in a["monthly"]] == [5, 6] and a["monthly"][0]["amount"] == 90000

    f = client.get(f"/api/crm/analytics?customer_id={world['a']}", headers=h).get_json()["data"]
    assert f["kpis"]["net_amount"] == 90000 and f["kpis"]["customer_count"] == 1
    assert f["filters"]["customer_id"] == world["a"]
    assert [r["name"] for r in f["by_customer"]] == ["پلاستیک آلفا"]
    assert f["by_province"][0]["name"] == "تهران"

    only_returns = client.get("/api/crm/analytics?document_type=RETURN", headers=h).get_json()["data"]
    assert only_returns["kpis"]["net_amount"] == -10000


def test_monthly_series_fills_gaps(client, h, world):
    _sale(client, h, world, date="1405/01/10")
    _sale(client, h, world, date="1405/04/10")
    months = client.get("/api/crm/analytics", headers=h).get_json()["data"]["monthly"]
    assert [m["month"] for m in months] == [1, 2, 3, 4] and months[1]["amount"] == 0


def test_update_recomputes_amount_and_pagination_is_capped(client, h, world):
    s = _sale(client, h, world, qty=10, price=5)
    assert s["amount"] == 50
    u = client.patch(f"/api/crm/sales/{s['id']}", json={"quantity_kg": 20}, headers=h).get_json()["data"]
    assert u["amount"] == 100
    r = client.get("/api/crm/sales?per_page=100000", headers=h).get_json()
    assert r["meta"]["per_page"] == 100


# ── import ───────────────────────────────────────────────────────────
def test_import_matches_customers_by_name_and_never_creates_customers(client, h, world):
    rows = [
        {"customer": "پلاستيك آلفا", "product": "پلی‌اتیلن", "quantity_kg": 100, "unit_price": 10,
         "date": "1405/05/01", "payment": "نقدی"},                    # Arabic letters still match
        {"customer": "ناشناس", "product": "پلی‌اتیلن", "quantity_kg": 1, "unit_price": 1, "date": "1405/05/01"},
        {"customer": "غذایی بتا", "product": "محصول جدید", "quantity_kg": 50, "amount": 500,
         "date": "1405/05/02", "document_type": "RETURN"},
    ]
    before = db.session.query(Customer).count()
    dry = client.post("/api/crm/sales/import", json={"rows": rows, "dry_run": True}, headers=h).get_json()["data"]
    assert (dry["created"], dry["rejected"]) == (1, 2) and db.session.query(Customer).count() == before
    assert client.get("/api/crm/sales", headers=h).get_json()["meta"]["total"] == 0

    res = client.post("/api/crm/sales/import", json={"rows": rows}, headers=h).get_json()["data"]
    assert (res["created"], res["rejected"]) == (1, 2) and [e["row"] for e in res["errors"]] == [2, 3]
    assert db.session.query(Customer).count() == before
    # an unknown product is rejected -- import must never create a second product list
    assert db.session.query(CustomerOptionItem).filter_by(name="محصول جدید").count() == 0


# ── grades come from the customer bank ────────────────────────────
def test_grades_are_the_customer_banks_pick_list(client, h, world):
    db.session.add(CustomerOptionItem(kind=OptionKind.GRADE, name="پلی‌پروپیلن", is_active=False))
    db.session.add(CustomerOptionItem(kind=OptionKind.PRODUCT, name="محصول ۱"))  # products are not grades
    db.session.commit()
    names = [p["name"] for p in client.get("/api/crm/products", headers=h).get_json()["data"]]
    assert names == ["پلی‌اتیلن"]  # inactive + non-grade entries are not offered
    all_names = [p["name"] for p in client.get("/api/crm/products?include_inactive=1", headers=h).get_json()["data"]]
    assert set(all_names) == {"پلی‌اتیلن", "پلی‌پروپیلن"}


def test_sale_rejects_a_non_grade_option_item(client, h, world):
    grade = CustomerOptionItem(kind=OptionKind.PRODUCT, name="محصول ۲")
    db.session.add(grade)
    db.session.commit()
    r = client.post("/api/crm/sales", headers=h, json={
        "customer_id": world["a"], "product_id": grade.id, "quantity_kg": 1, "unit_price": 1})
    assert r.status_code == 409


def test_renaming_a_grade_in_the_bank_shows_on_existing_sales(client, h, world):
    s = _sale(client, h, world)
    item = db.session.get(CustomerOptionItem, world["p"])
    item.name = "پلی‌اتیلن سنگین"
    db.session.commit()
    got = client.get(f"/api/crm/sales/{s['id']}", headers=h).get_json()["data"]
    assert got["product"]["name"] == "پلی‌اتیلن سنگین"


# ── delete ───────────────────────────────────────────────────────────
def test_sale_can_be_deleted_and_disappears_from_lists_and_totals(client, h, world):
    s = _sale(client, h, world, qty=10, price=5)
    assert client.delete(f"/api/crm/sales/{s['id']}", headers=h).status_code == 200
    assert client.get(f"/api/crm/sales/{s['id']}", headers=h).status_code == 404
    assert client.get("/api/crm/sales", headers=h).get_json()["meta"]["total"] == 0
    assert client.get("/api/crm/analytics", headers=h).get_json()["data"]["kpis"]["document_count"] == 0


def test_payment_method_unused_can_be_deleted(client, h, world):
    r = client.post("/api/crm/payment-methods", json={"name": "کارتخوان"}, headers=h)
    mid = r.get_json()["data"]["id"]
    assert client.delete(f"/api/crm/payment-methods/{mid}", headers=h).status_code == 200
    assert db.session.get(CrmPaymentMethod, mid) is None


def test_payment_method_in_use_needs_confirmation_then_detaches_sales(client, h, world):
    s = _sale(client, h, world)
    listed = client.get("/api/crm/payment-methods", headers=h).get_json()["data"]
    assert next(m for m in listed if m["id"] == world["m"])["sales_count"] == 1
    # without force: refused, nothing changes
    assert client.delete(f"/api/crm/payment-methods/{world['m']}", headers=h).status_code == 409
    assert db.session.get(CrmPaymentMethod, world["m"]) is not None
    # with force: the method goes, the sale stays and simply has no payment method
    assert client.delete(f"/api/crm/payment-methods/{world['m']}?force=1", headers=h).status_code == 200
    db.session.expire_all()
    assert db.session.get(CrmPaymentMethod, world["m"]) is None
    kept = client.get(f"/api/crm/sales/{s['id']}", headers=h).get_json()["data"]
    assert kept["payment_method"] is None and kept["amount"] == s["amount"]
    assert db.session.get(CrmSale, s["id"]) is not None


def test_payment_method_delete_needs_crm_product_delete_permission(client, h, world):
    reader = _staff(("sale", "read"), ("product", "read"))
    assert client.delete(f"/api/crm/payment-methods/{world['m']}?force=1", headers=reader).status_code == 403
