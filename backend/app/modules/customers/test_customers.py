"""HTTP tests for /api/customers -- CRM module."""
import datetime as dt

import pytest

from app.core.authorization.models import ScopeType
from app.extensions import db
from app.modules.customers.models import Customer, CustomerCategory
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

ACTIONS = ("read", "create", "update", "delete")


def _staff(app, *actions):
    """A user holding the given crm.customer.* grants (GLOBAL); returns (auth headers, user id).
    Runs in the fixture's already-active app context (a second context would open a second
    session on the shared in-memory SQLite connection while a request transaction is open)."""
    user = make_user()
    for action in actions:
        grant_user_permission(user, make_permission(f"crm.customer.{action}"), ScopeType.GLOBAL, None)
    db.session.commit()
    return auth_headers(user), user.id


@pytest.fixture
def h(app):
    return _staff(app, *ACTIONS)[0]


@pytest.fixture(autouse=True)
def _categories(app):
    with app.app_context():
        main = CustomerCategory(name="پلاستیک", sort_order=1)
        other = CustomerCategory(name="غذایی", sort_order=2)
        db.session.add_all([main, other])
        db.session.flush()
        db.session.add(CustomerCategory(name="تزریقی", parent_id=main.id, sort_order=1))
        db.session.add(CustomerCategory(name="اکسترود", parent_id=main.id, sort_order=2))
        db.session.commit()


def _body(**over):
    body = {
        "customer_type": "LEGAL",
        "company_name": "پلاستیک نمونه",
        "company_national_id": "۱۲۳۴۵۶۷۸۹۰۱",  # Persian digits on purpose
        "contacts": [{"first_name": "علی", "last_name": "رضایی", "position": "مدیر خرید", "mobile": "09121234567"}],
        "category": "پلاستیک",
        "subcategory": "تزریقی",
        "activity_types": ["PRODUCER", "EXPORTER"],
        "factory_province": "تهران",
        "factory_city": "شهریار",
        "consumed_products": [
            {"name": "پلی‌اتیلن سنگین", "grade_specs": "HD 5218", "monthly_consumption": 20, "annual_consumption": 240}
        ],
        "commercial_status": "NO_ACTION",
    }
    body.update(over)
    return body


def _create(client, h, **over):
    r = client.post("/api/customers", json=_body(**over), headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


# ── permissions ──────────────────────────────────────────────────────
def test_every_route_needs_the_matching_permission(client, app):
    none, _ = _staff(app)
    assert client.get("/api/customers", headers=none).status_code == 403
    assert client.post("/api/customers", json=_body(), headers=none).status_code == 403
    assert client.get("/api/customers/stats", headers=none).status_code == 403
    assert client.get("/api/customers").status_code == 401

    read_only, _ = _staff(app, "read")
    assert client.get("/api/customers", headers=read_only).status_code == 200
    assert client.post("/api/customers", json=_body(), headers=read_only).status_code == 403
    assert client.post("/api/customers/category-items", json={"name": "x"}, headers=read_only).status_code == 403


# ── create + validation ──────────────────────────────────────────────
def test_create_legal_customer_normalises_and_derives(client, h):
    d = _create(client, h, contact_log=[{"date": "2025-02-01"}, {"date": "2025-01-10", "note": "اولین تماس"}])
    assert d["display_name"] == "پلاستیک نمونه"
    assert d["company_national_id"] == "12345678901"  # Persian digits -> Latin
    assert d["activity_types"] == ["PRODUCER", "EXPORTER"]
    assert d["first_contact_date"] == "2025-01-10"  # earliest of the log
    assert [e["date"] for e in d["contact_log"]] == ["2025-01-10", "2025-02-01"]
    assert d["registration_date"] == dt.date.today().isoformat()
    assert d["is_finalized"] is False and d["operational_status"] == "ACTIVE"
    assert d["created_by_name"]


def test_create_individual_with_contact_birth_date_and_clears_legal_fields(client, h):
    d = _create(
        client, h, customer_type="INDIVIDUAL", first_name="سارا", last_name="احمدی", national_id="0012345678",
        company_name="should be dropped", company_national_id="12345678901",
        contacts=[{"first_name": "سارا", "last_name": "احمدی", "position": "مالک", "landline": "02122898979",
                   "birth_date": "1990-05-01"}],
    )
    assert d["display_name"] == "سارا احمدی"
    assert d["company_name"] is None and d["company_national_id"] is None
    assert d["contacts"][0]["birth_date"] == "1990-05-01"


@pytest.mark.parametrize("over", [
    {"company_name": None},  # legal: name required
    {"company_national_id": "123"},  # must be 11 digits
    {"customer_type": "INDIVIDUAL"},  # individual without names / national id
    {"contacts": []},  # at least one person
    {"contacts": [{"first_name": "a", "last_name": "b", "position": "c"}]},  # no phone number
    {"category": None},
    {"activity_types": []},
    {"factory_city": None},
    {"factory_province": ""},
    {"consumed_products": []},
    {"consumed_products": [{"name": "x", "monthly_consumption": 1}]},  # annual missing
    {"commercial_status": "BOGUS"},
    {"head_office_postal_code": "123"},
    {"acquaintance_source": "BOGUS"},
    {"acquaintance_source": "OTHER"},  # 'Other' needs a description
    {"payment_type": "CREDIT"},  # credit needs a duration
    {"payment_type": "CREDIT", "credit_months": 13},
    {"credit_rating": "BOGUS"},
    {"industries": [], "category": None},  # at least one industry
    {"industries": [{"category": "پلاستیک"}, {"subcategory": "تزریقی"}]},
    {"activity_start_date": "2999-01-01"},
])
def test_create_validation_rejects(client, h, over):
    r = client.post("/api/customers", json=_body(**over), headers=h)
    assert r.status_code in (400, 422), (over, r.get_json())


def test_category_must_exist_and_subcategory_must_belong_to_it(client, h):
    assert client.post("/api/customers", json=_body(category="ناموجود"), headers=h).status_code == 409
    assert client.post("/api/customers", json=_body(subcategory="ناموجود"), headers=h).status_code == 409
    # "تزریقی" is a sub-category of پلاستیک, not of غذایی
    assert client.post("/api/customers", json=_body(category="غذایی"), headers=h).status_code == 409


def test_current_supplier_link_fills_name_and_unknown_link_is_rejected(client, h, app):
    from app.modules.suppliers.models import Supplier, SupplierType
    s = Supplier(supplier_type=SupplierType.LEGAL, company_name="تأمین نمونه", contacts=[], phones=[],
                 products=[], catalog_files=[])
    db.session.add(s)
    db.session.commit()
    sid = s.id
    d = _create(client, h, current_suppliers=[{"supplier_id": sid}, {"name": "بازار آزاد"}])
    assert d["current_suppliers"] == [
        {"name": "تأمین نمونه", "supplier_id": sid, "grades": []}, {"name": "بازار آزاد", "supplier_id": None, "grades": []},
    ]
    assert client.post("/api/customers", json=_body(current_suppliers=[{"supplier_id": 9999}]), headers=h).status_code == 409


def test_finalize_on_create_and_endpoint_is_idempotent(client, h):
    d = _create(client, h, finalize=True)
    assert d["is_finalized"] is True and d["finalized_at"]
    other = _create(client, h, company_name="دیگری")
    r1 = client.post(f"/api/customers/{other['id']}/finalize", headers=h).get_json()["data"]
    r2 = client.post(f"/api/customers/{other['id']}/finalize", headers=h).get_json()["data"]
    assert r1["is_finalized"] and r1["finalized_at"] == r2["finalized_at"]


# ── update ───────────────────────────────────────────────────────────
def test_patch_status_terms_and_followup(client, h):
    c = _create(client, h)
    r = client.patch(f"/api/customers/{c['id']}", headers=h, json={
        "commercial_status": "SALES_NEGOTIATION", "purchase_method": "OFFICIAL", "approved_credit_limit": 500000000,
        "next_follow_up_date": "2025-03-01", "payment_terms": "۳۰ روزه", "credit_rating": "GOOD",
    })
    d = r.get_json()["data"]
    assert r.status_code == 200
    assert d["commercial_status"] == "SALES_NEGOTIATION" and d["purchase_method"] == "OFFICIAL"
    assert d["credit_rating"] == "GOOD" and d["approved_credit_limit"] == 500000000
    assert "expected_price_min" not in d


def test_patch_merged_rules_and_non_nullable_fields(client, h):
    c = _create(client, h)
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"category": None}).status_code in (400, 422)
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"consumed_products": []}).status_code in (400, 422)
    # first/last purchase ordering uses the stored value too
    client.patch(f"/api/customers/{c['id']}", headers=h, json={"first_purchase_date": "2025-01-10"})
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"last_purchase_date": "2025-01-01"}).status_code in (400, 409, 422)


def test_changing_industry_drops_old_subcategory(client, h):
    c = _create(client, h)
    d = client.patch(f"/api/customers/{c['id']}", headers=h, json={"category": "غذایی"}).get_json()["data"]
    assert d["category"] == "غذایی" and d["subcategory"] is None


def test_switching_type_requires_new_identity_then_clears_old(client, h):
    c = _create(client, h)
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"customer_type": "INDIVIDUAL"}).status_code == 409
    d = client.patch(f"/api/customers/{c['id']}", headers=h, json={
        "customer_type": "INDIVIDUAL", "first_name": "رضا", "last_name": "کریمی", "national_id": "0012345678",
    }).get_json()["data"]
    assert d["display_name"] == "رضا کریمی" and d["company_name"] is None


def test_assignee_must_be_an_active_user(client, h, app):
    c = _create(client, h)
    _, uid = _staff(app)
    ok = client.patch(f"/api/customers/{c['id']}", headers=h, json={"assigned_to_user_id": uid})
    assert ok.status_code == 200 and ok.get_json()["data"]["assigned_to_name"]
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"assigned_to_user_id": 99999}).status_code == 409


def test_contact_log_replace_rederives_first_contact(client, h):
    c = _create(client, h, contact_log=[{"date": "2025-01-10"}])
    d = client.patch(f"/api/customers/{c['id']}", headers=h, json={
        "contact_log": [{"date": "2025-03-05"}, {"date": "2025-02-01", "note": "تماس دوم"}]
    }).get_json()["data"]
    assert d["first_contact_date"] == "2025-02-01"
    d = client.patch(f"/api/customers/{c['id']}", headers=h, json={"contact_log": []}).get_json()["data"]
    assert d["first_contact_date"] is None


def test_delete_is_soft(client, h, app):
    c = _create(client, h)
    assert client.delete(f"/api/customers/{c['id']}", headers=h).status_code == 200
    assert client.get(f"/api/customers/{c['id']}", headers=h).status_code == 404
    db.session.expire_all()
    assert db.session.get(Customer, c["id"]).deleted_at is not None


# ── list / filters / search ──────────────────────────────────────────
def _ids(client, h, qs=""):
    r = client.get(f"/api/customers?{qs}", headers=h)
    assert r.status_code == 200, r.get_json()
    return [x["id"] for x in r.get_json()["data"]], r.get_json()["meta"]["total"]


def test_list_filters(client, h, app):
    a = _create(client, h, company_name="آلفا", commercial_status="ACQUIRED", factory_city="شهریار")
    b = _create(client, h, company_name="بتا", commercial_status="POTENTIAL", factory_province="اصفهان",
                factory_city="کاشان", category="غذایی", subcategory=None, activity_types=["DISTRIBUTOR"])
    c = _create(client, h, company_name="گاما", commercial_status="INACTIVE_LOST", next_follow_up_date="2020-01-01")
    d = _create(client, h, company_name="دلتا", commercial_status="NO_ACTION", next_follow_up_date="2020-01-01",
                finalize=True)
    assert _ids(client, h)[1] == 4
    assert set(_ids(client, h, "commercial_status=ACQUIRED,POTENTIAL")[0]) == {a["id"], b["id"]}
    assert set(_ids(client, h, "commercial_status=ACQUIRED&commercial_status=POTENTIAL")[0]) == {a["id"], b["id"]}
    assert _ids(client, h, "province=اصفهان")[0] == [b["id"]]
    assert _ids(client, h, "province=اصفهان&city=کاشان")[0] == [b["id"]]
    assert _ids(client, h, "category=غذایی")[0] == [b["id"]]
    assert set(_ids(client, h, "category=پلاستیک&subcategory=تزریقی")[0]) == {a["id"], c["id"], d["id"]}
    assert _ids(client, h, "activity_type=DISTRIBUTOR")[0] == [b["id"]]
    assert set(_ids(client, h, "activity_type=EXPORTER")[0]) == {a["id"], c["id"], d["id"]}
    assert _ids(client, h, "is_finalized=true")[0] == [d["id"]]
    # overdue follow-ups skip lost customers
    assert _ids(client, h, "follow_up_due=true")[0] == [d["id"]]
    assert _ids(client, h, "assigned_to=none")[1] == 4
    # unknown values are ignored rather than erroring
    assert _ids(client, h, "commercial_status=BOGUS")[1] == 4


def test_search_covers_names_products_contacts_places_and_persian_variants(client, h):
    a = _create(client, h, company_name="کیمیا پلیمر", produced_products=[{"name": "گرانول پلی‌پروپیلن", "amount": 5}])
    b = _create(client, h, company_name="بسته بندی نو", factory_city="کاشان",
                consumed_products=[{"name": "فیلم BOPP", "monthly_consumption": 1, "annual_consumption": 12}],
                contacts=[{"first_name": "مریم", "last_name": "کاظمی", "position": "خرید", "mobile": "09351112233"}])
    assert _ids(client, h, "search=کیمیا")[0] == [a["id"]]
    assert _ids(client, h, "search=گرانول")[0] == [a["id"]]  # produced product
    assert _ids(client, h, "search=BOPP")[0] == [b["id"]]  # consumed product
    assert _ids(client, h, "search=کاظمی")[0] == [b["id"]]  # contact person
    assert _ids(client, h, "search=۰۹۳۵۱۱۱۲۲۳۳")[0] == [b["id"]]  # Persian digits -> phone
    assert _ids(client, h, "search=کاشان")[0] == [b["id"]]  # city
    assert _ids(client, h, "search=%D9%83%D9%8A%D9%85%D9%8A%D8%A7")[0] == [a["id"]]  # Arabic ك/ي spelling
    assert _ids(client, h, "search=هیچی")[1] == 0


def test_sort_by_next_follow_up(client, h):
    late = _create(client, h, company_name="دیر", next_follow_up_date="2030-01-01")
    soon = _create(client, h, company_name="زود", next_follow_up_date="2025-01-01")
    none = _create(client, h, company_name="بی‌تاریخ")
    assert _ids(client, h, "sort=next_follow_up_date")[0] == [soon["id"], late["id"], none["id"]]


def test_pagination_meta(client, h):
    for i in range(3):
        _create(client, h, company_name=f"شرکت {i}")
    r = client.get("/api/customers?page=2&per_page=2", headers=h).get_json()
    assert r["meta"] == {"page": 2, "per_page": 2, "total": 3} and len(r["data"]) == 1


# ── stats / locations / options ──────────────────────────────────────
def test_stats_locations_options(client, h):
    _create(client, h, commercial_status="ACQUIRED")
    _create(client, h, company_name="دو", commercial_status="POTENTIAL", factory_city="کرج",
            next_follow_up_date="2020-01-01")
    s = client.get("/api/customers/stats", headers=h).get_json()["data"]
    assert s["total"] == 2 and s["by_commercial_status"]["ACQUIRED"] == 1 and s["follow_up_due"] == 1
    assert s["unassigned"] == 2 and s["not_finalized"] == 2 and set(s["by_commercial_status"]) >= {"NO_ACTION", "POTENTIAL"}
    loc = client.get("/api/customers/locations", headers=h).get_json()["data"]
    assert loc == [{"province": "تهران", "count": 2, "cities": [{"city": "شهریار", "count": 1}, {"city": "کرج", "count": 1}]}]
    o = client.get("/api/customers/options", headers=h).get_json()["data"]
    assert len(o["commercial_statuses"]) == 9 and [x["value"] for x in o["activity_types"]] == ["PRODUCER", "DISTRIBUTOR", "EXPORTER"]


def test_assignable_users_needs_only_customer_read(client, app):
    reader, uid = _staff(app, "read")
    r = client.get("/api/customers/assignable-users", headers=reader)
    assert r.status_code == 200 and any(u["id"] == uid for u in r.get_json()["data"])
    none, _ = _staff(app)
    assert client.get("/api/customers/assignable-users", headers=none).status_code == 403


# ── categories ───────────────────────────────────────────────────────
def test_category_management_rename_propagates_and_delete_cascades(client, h):
    items = client.get("/api/customers/category-items", headers=h).get_json()["data"]
    main = next(i for i in items if i["name"] == "پلاستیک")
    c = _create(client, h)

    new_sub = client.post("/api/customers/category-items", headers=h, json={"name": "فوم", "parent_id": main["id"]})
    assert new_sub.status_code == 201
    assert client.post("/api/customers/category-items", headers=h, json={"name": "فوم", "parent_id": main["id"]}).status_code == 409
    # same sub name under a different parent is fine; sub-of-sub is not
    other = next(i for i in items if i["name"] == "غذایی")
    assert client.post("/api/customers/category-items", headers=h, json={"name": "فوم", "parent_id": other["id"]}).status_code == 201
    assert client.post("/api/customers/category-items", headers=h,
                       json={"name": "عمیق", "parent_id": new_sub.get_json()["data"]["id"]}).status_code == 409

    # renaming a sub-category rewrites the customers that use it
    items = client.get("/api/customers/category-items", headers=h).get_json()["data"]
    main = next(i for i in items if i["name"] == "پلاستیک")
    sub = next(i for i in items if i["name"] == "تزریقی")
    assert sub["customer_count"] == 1 and main["customer_count"] == 1
    client.patch(f"/api/customers/category-items/{sub['id']}", headers=h, json={"name": "تزریق پلاستیک"})
    assert client.get(f"/api/customers/{c['id']}", headers=h).get_json()["data"]["subcategory"] == "تزریق پلاستیک"
    # ...and renaming the main category does too
    client.patch(f"/api/customers/category-items/{main['id']}", headers=h, json={"name": "پلاستیک و پلیمر"})
    got = client.get(f"/api/customers/{c['id']}", headers=h).get_json()["data"]
    assert got["category"] == "پلاستیک و پلیمر" and got["subcategory"] == "تزریق پلاستیک"

    # hidden entries are no longer selectable but existing customers keep their values
    client.patch(f"/api/customers/category-items/{main['id']}", headers=h, json={"is_active": False})
    assert client.post("/api/customers", json=_body(category="پلاستیک و پلیمر", subcategory=None), headers=h).status_code == 409
    assert client.patch(f"/api/customers/{c['id']}", headers=h, json={"internal_notes": "ok"}).status_code == 200

    # deleting the main category removes its sub-categories from the list
    assert client.delete(f"/api/customers/category-items/{main['id']}", headers=h).status_code == 200
    names = [i["name"] for i in client.get("/api/customers/category-items", headers=h).get_json()["data"]]
    assert "تزریق پلاستیک" not in names and "اکسترود" not in names
    assert "پلاستیک و پلیمر" in client.get("/api/customers/categories", headers=h).get_json()["data"]  # still used -> still filterable

# ── revision: birth date, source, payment, rating, grades, purchase method, industries ──
def test_contact_birth_date_is_kept_for_legal_customers_too(client, h):
    d = _create(client, h, contacts=[{"first_name": "علی", "last_name": "رضایی", "position": "مدیر خرید",
                                       "mobile": "09121234567", "birth_date": "1985-03-02"}])
    assert d["customer_type"] == "LEGAL" and d["contacts"][0]["birth_date"] == "1985-03-02"


def test_acquaintance_source_list_and_other_text(client, h):
    d = _create(client, h, acquaintance_source="EXHIBITION", acquaintance_source_other="ignored")
    assert d["acquaintance_source"] == "EXHIBITION" and d["acquaintance_source_other"] is None
    d = _create(client, h, company_name="دو", acquaintance_source="OTHER", acquaintance_source_other="دوست خانوادگی")
    assert d["acquaintance_source"] == "OTHER" and d["acquaintance_source_other"] == "دوست خانوادگی"
    # leaving 'Other' clears the text; switching to 'Other' without text is refused
    r = client.patch(f"/api/customers/{d['id']}", headers=h, json={"acquaintance_source": "WEBSITE"})
    assert r.get_json()["data"]["acquaintance_source_other"] is None
    assert client.patch(f"/api/customers/{d['id']}", headers=h, json={"acquaintance_source": "OTHER"}).status_code == 409


def test_payment_type_and_credit_duration(client, h):
    cash = _create(client, h, payment_type="CASH", credit_months=3, credit_other="x")
    assert cash["payment_type"] == "CASH" and cash["credit_months"] is None and cash["credit_other"] is None
    credit = _create(client, h, company_name="اعتباری", payment_type="CREDIT", credit_months=6)
    assert credit["credit_months"] == 6 and credit["credit_other"] is None
    mixed = _create(client, h, company_name="ترکیبی", payment_type="CASH_CREDIT", credit_other="۱۸ ماهه")
    assert mixed["credit_months"] is None and mixed["credit_other"] == "۱۸ ماهه"
    # PATCH: credit without a duration is refused; going back to cash clears it
    assert client.patch(f"/api/customers/{cash['id']}", headers=h, json={"payment_type": "CREDIT"}).status_code == 409
    d = client.patch(f"/api/customers/{credit['id']}", headers=h, json={"payment_type": "CASH"}).get_json()["data"]
    assert d["credit_months"] is None


def test_purchase_method_both_and_credit_rating_filter(client, h):
    a = _create(client, h, purchase_method="BOTH", credit_rating="EXCELLENT")
    b = _create(client, h, company_name="بتا", credit_rating="BAD_DEBTOR")
    assert a["purchase_method"] == "BOTH"
    assert _ids(client, h, "credit_rating=EXCELLENT")[0] == [a["id"]]
    assert _ids(client, h, "credit_rating=BOGUS")[1] == 2  # unknown values are ignored
    o = client.get("/api/customers/options", headers=h).get_json()["data"]
    assert [x["value"] for x in o["purchase_methods"]] == ["OFFICIAL", "UNOFFICIAL", "BOTH"]
    assert [x["value"] for x in o["credit_ratings"]][0] == "EXCELLENT" and len(o["credit_ratings"]) == 7
    assert len(o["acquaintance_sources"]) == 15 and o["credit_months"] == list(range(1, 13))
    assert [x["value"] for x in o["payment_types"]] == ["CASH", "CREDIT", "CASH_CREDIT"]
    assert b["credit_rating"] == "BAD_DEBTOR"


def test_current_supplier_grades_are_stored(client, h):
    grades = [{"product": "پلی‌اتیلن سنگین", "grade": "HD 5218"}, {"product": "پلی‌اتیلن سنگین", "grade": "HD 5218"}]
    d = _create(client, h, current_suppliers=[{"name": "بازار آزاد", "grades": grades}, {"name": "بی‌گرید"}])
    assert d["current_suppliers"][0]["grades"] == [{"product": "پلی‌اتیلن سنگین", "grade": "HD 5218"}]  # de-duplicated
    assert d["current_suppliers"][1]["grades"] == []


def test_multiple_industries(client, h):
    d = _create(client, h, category=None, subcategory=None, industries=[
        {"category": "پلاستیک", "subcategory": "تزریقی"}, {"category": "غذایی"},
        {"category": "پلاستیک", "subcategory": "تزریقی"},  # duplicate is dropped
    ])
    assert d["industries"] == [{"category": "پلاستیک", "subcategory": "تزریقی"}, {"category": "غذایی", "subcategory": None}]
    assert d["category"] == "پلاستیک" and d["subcategory"] == "تزریقی"  # mirror of the first
    only_food = _create(client, h, company_name="فقط غذایی", category="غذایی", subcategory=None)
    assert only_food["industries"] == [{"category": "غذایی", "subcategory": None}]  # single-category shorthand
    # a customer is found through ANY of its industries
    assert set(_ids(client, h, "category=غذایی")[0]) == {d["id"], only_food["id"]}
    assert _ids(client, h, "category=پلاستیک&subcategory=تزریقی")[0] == [d["id"]]
    assert _ids(client, h, "category=غذایی&subcategory=تزریقی")[1] == 0  # sub must belong to the same industry entry
    # every industry must be selectable
    assert client.post("/api/customers", json=_body(industries=[{"category": "پلاستیک"}, {"category": "ناموجود"}]),
                       headers=h).status_code == 409
    # PATCH replaces the whole list and re-mirrors the first
    r = client.patch(f"/api/customers/{d['id']}", headers=h, json={"industries": [{"category": "غذایی"}, {"category": "پلاستیک"}]})
    got = r.get_json()["data"]
    assert [i["category"] for i in got["industries"]] == ["غذایی", "پلاستیک"] and got["category"] == "غذایی"
    # the older single-industry PATCH only replaces the first entry
    got = client.patch(f"/api/customers/{d['id']}", headers=h, json={"category": "پلاستیک", "subcategory": "اکسترود"}).get_json()["data"]
    assert got["industries"] == [{"category": "پلاستیک", "subcategory": "اکسترود"}, {"category": "پلاستیک", "subcategory": None}]


def test_category_rename_and_counts_cover_every_industry(client, h):
    c = _create(client, h, category=None, subcategory=None, industries=[{"category": "غذایی"}, {"category": "پلاستیک", "subcategory": "تزریقی"}])
    items = client.get("/api/customers/category-items", headers=h).get_json()["data"]
    food = next(i for i in items if i["name"] == "غذایی")
    plastic = next(i for i in items if i["name"] == "پلاستیک")
    assert food["customer_count"] == 1 and plastic["customer_count"] == 1
    client.patch(f"/api/customers/category-items/{plastic['id']}", headers=h, json={"name": "پلیمر"})
    got = client.get(f"/api/customers/{c['id']}", headers=h).get_json()["data"]
    assert got["industries"] == [{"category": "غذایی", "subcategory": None}, {"category": "پلیمر", "subcategory": "تزریقی"}]
    assert got["category"] == "غذایی"


# ── revision 2: brand name, TON/KG whole-number amounts, yearly production, derived capacity ──
def test_individual_customer_can_have_a_brand_name_and_legal_cannot(client, h):
    ind = _create(client, h, customer_type="INDIVIDUAL", first_name="رضا", last_name="کریمی", national_id="1234567890",
                  brand_name="  برند پارس  ", company_name=None, company_national_id=None)
    assert ind["brand_name"] == "برند پارس"
    assert _ids(client, h, "search=پارس")[0] == [ind["id"]]
    legal = _create(client, h, company_name="شرکت دیگر", brand_name="نباید ذخیره شود")
    assert legal["brand_name"] is None
    # switching an individual to legal clears it; setting it on a legal customer is ignored
    d = client.patch(f"/api/customers/{ind['id']}", headers=h, json={
        "customer_type": "LEGAL", "company_name": "پارس", "company_national_id": "12345678901"}).get_json()["data"]
    assert d["brand_name"] is None


def test_amounts_are_whole_numbers_with_ton_default_and_kg_option(client, h):
    d = _create(client, h, produced_products=[{"name": "الف", "amount": 5}, {"name": "ب", "amount": 500, "unit": "KG"}],
                consumed_products=[{"name": "پلی‌اتیلن", "monthly_consumption": 20, "annual_consumption": 240}])
    assert [p["unit"] for p in d["produced_products"]] == ["TON", "KG"]
    assert d["consumed_products"][0]["unit"] == "TON"
    assert "period" not in d["produced_products"][0]
    assert d["production_capacity"] == 5.5  # 5 t + 500 kg, per year
    # decimals and unknown units are rejected
    assert client.post("/api/customers", headers=h, json=_body(
        produced_products=[{"name": "x", "amount": 1.5}])).status_code in (400, 422)
    assert client.post("/api/customers", headers=h, json=_body(
        consumed_products=[{"name": "x", "monthly_consumption": 2.5, "annual_consumption": 30}])).status_code in (400, 422)
    assert client.post("/api/customers", headers=h, json=_body(
        produced_products=[{"name": "x", "amount": 1, "unit": "LB"}])).status_code in (400, 422)
    # Persian / English spellings of the unit are understood; a stale `period` key is ignored
    ok = _create(client, h, produced_products=[{"name": "x", "amount": 2000, "unit": "کیلوگرم", "period": "MONTHLY"}])
    assert ok["produced_products"] == [{"name": "x", "amount": 2000, "unit": "KG"}]
    assert ok["production_capacity"] == 2


def test_capacity_follows_produced_products_and_clients_cannot_set_it(client, h):
    d = _create(client, h, produced_products=[], production_capacity=999)
    assert d["production_capacity"] is None
    d = client.patch(f"/api/customers/{d['id']}", headers=h, json={
        "production_capacity": 999, "produced_products": [{"name": "a", "amount": 3}, {"name": "b", "amount": 4}],
    }).get_json()["data"]
    assert d["production_capacity"] == 7
    d = client.patch(f"/api/customers/{d['id']}", headers=h, json={"internal_notes": "x"}).get_json()["data"]
    assert d["production_capacity"] == 7  # untouched by an unrelated edit


def test_options_list_units_and_contact_positions(client, h):
    o = client.get("/api/customers/options", headers=h).get_json()["data"]
    assert [u["value"] for u in o["quantity_units"]] == ["TON", "KG"]
    assert len(o["contact_positions"]) == 22 and o["contact_positions"][0] == "مالک / مؤسس"
    # a position outside the list ("سایر" typed by hand) is stored as typed
    d = _create(client, h, contacts=[{"first_name": "الف", "last_name": "ب", "position": "مدیر پروژه", "mobile": "09121234567"}])
    assert d["contacts"][0]["position"] == "مدیر پروژه"


def test_sort_by_industry(client, h):
    a = _create(client, h, company_name="الف", category="غذایی", subcategory=None)
    b = _create(client, h, company_name="ب", category="پلاستیک", subcategory="تزریقی")
    c = _create(client, h, company_name="ج", category="پلاستیک", subcategory="اکسترود")
    asc = _ids(client, h, "sort=category")[0]
    desc = _ids(client, h, "sort=-category")[0]
    assert asc == [a["id"], c["id"], b["id"]]  # by industry name, then sub-category (SQLite code-point order)
    assert desc == [b["id"], c["id"], a["id"]]


# ── production line names ────────────────────────────────────────────
def test_production_line_names_are_a_free_list_and_the_count_follows(client, h):
    d = _create(client, h, production_line_names=["خط ۱", " خط  ۲ ", "", "خط ۳"])
    assert d["production_line_names"] == ["خط ۱", "خط ۲", "خط ۳"]  # trimmed, blank rows dropped
    assert d["production_lines_count"] == 3
    # add more names than any earlier count: allowed, the count follows
    r = client.patch(f"/api/customers/{d['id']}", json={"production_line_names": ["a", "b", "c", "d", "e"]}, headers=h)
    assert r.status_code == 200 and r.get_json()["data"]["production_lines_count"] == 5
    # remove some by hand
    r = client.patch(f"/api/customers/{d['id']}", json={"production_line_names": ["a"]}, headers=h)
    assert r.get_json()["data"]["production_lines_count"] == 1
    # remove all: names empty, count cleared by the client
    r = client.patch(f"/api/customers/{d['id']}", json={"production_line_names": [], "production_lines_count": None}, headers=h)
    assert r.get_json()["data"]["production_line_names"] == [] and r.get_json()["data"]["production_lines_count"] is None
    # no count sent -> the count follows the names
    d2 = _create(client, h, company_national_id="12345678902", production_line_names=["الف", "ب"])
    assert d2["production_lines_count"] == 2
    assert _create(client, h, company_national_id="12345678903")["production_line_names"] == []


# ── product / grade pick-lists ───────────────────────────────────────
def test_option_items_crud_and_rename_rewrites_customers(client, h):
    r = client.post("/api/customers/option-items", json={"kind": "GRADE", "name": "HD 5218"}, headers=h)
    assert r.status_code == 201
    gid = r.get_json()["data"]["id"]
    assert client.post("/api/customers/option-items", json={"kind": "GRADE", "name": "HD 5218"}, headers=h).status_code == 409
    assert client.post("/api/customers/option-items", json={"kind": "PRODUCT", "name": "HD 5218"}, headers=h).status_code == 201
    listed = client.get("/api/customers/option-items?kind=GRADE", headers=h).get_json()["data"]
    assert [o["name"] for o in listed] == ["HD 5218"]

    c = _create(client, h)  # consumed grade_specs == "HD 5218"
    r = client.patch(f"/api/customers/option-items/{gid}", json={"name": "HD 5218 BM"}, headers=h)
    assert r.status_code == 200
    got = client.get(f"/api/customers/{c['id']}", headers=h).get_json()["data"]
    assert got["consumed_products"][0]["grade_specs"] == "HD 5218 BM"

    assert client.delete(f"/api/customers/option-items/{gid}", headers=h).status_code == 200
    assert client.get("/api/customers/option-items?kind=GRADE", headers=h).get_json()["data"] == []


def test_option_items_need_permissions(client, app):
    read_only, _ = _staff(app, "read")
    assert client.get("/api/customers/option-items", headers=read_only).status_code == 200
    assert client.post("/api/customers/option-items", json={"kind": "GRADE", "name": "x"}, headers=read_only).status_code == 403
    creator, _ = _staff(app, "read", "create")  # may add entries inline from the wizard, not rename/delete
    assert client.post("/api/customers/option-items", json={"kind": "GRADE", "name": "x"}, headers=creator).status_code == 201

def test_production_lines_count_can_be_typed_independently_of_names(client, h):
    d = _create(client, h, production_lines_count=4, production_line_names=["الف"])
    assert d["production_lines_count"] == 4  # typed count is kept; names are optional
    assert d["production_line_names"] == ["الف"]

    r = client.patch(f"/api/customers/{d['id']}", json={"production_lines_count": 7}, headers=h)
    assert r.status_code == 200 and r.get_json()["data"]["production_lines_count"] == 7
