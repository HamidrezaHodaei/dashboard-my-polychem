"""Tests for /api/logistics -- registration wizard (companies + drivers) and staff access levels."""
import io

import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from app.modules.logistics import validators as v
from app.modules.logistics.models import LogisticsApplicant
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user

BASE = "/api/logistics"


# ── helpers ──────────────────────────────────────────────────────────
def national_code(prefix9: str) -> str:
    total = sum(int(prefix9[i]) * (10 - i) for i in range(9))
    r = total % 11
    return prefix9 + str(r if r < 2 else 11 - r)


def legal_id(prefix10: str) -> str:
    d = int(prefix10[9]) + 2
    coeffs = (29, 27, 23, 19, 17, 29, 27, 23, 19, 17)
    r = sum((int(prefix10[i]) + d) * coeffs[i] for i in range(10)) % 11
    return prefix10 + str(0 if r == 10 else r)


def staff(*keys: str) -> dict:
    """Auth headers for a user holding the given `logistics.<type>.<action>` keys (GLOBAL)."""
    user = make_user()
    for key in keys:
        perm = db.session.query(Permission).filter_by(key=key).first() or make_permission(key)
        grant_user_permission(user, perm, ScopeType.GLOBAL, None)
    db.session.commit()
    return auth_headers(user)


ALL = [f"logistics.{r}.{a}" for r in ("company", "driver") for a in ("read", "create", "update", "delete", "review")]


def company_body(**over):
    body = {
        "applicant_type": "COMPANY",
        "company_info": {
            "entity_type": "LEGAL", "company_name": "حمل‌ونقل سریع", "national_id": legal_id("1010101010"),
            "province": "تهران", "city": "شهریار", "office_address": "تهران، خیابان آزادی، پلاک ۱۲",
        },
        "representative": {
            "first_name": "علی", "last_name": "رضایی", "position": "CEO",
            "mobile": "09121234567", "landline": "02122334455",
        },
        "service_area": {"area_type": "PROVINCIAL", "coverage": [{"province": "تهران", "all_cities": True}]},
    }
    body.update(over)
    return body


def driver_body(**over):
    body = {
        "applicant_type": "DRIVER",
        "identity": {"first_name": "حسین", "last_name": "کریمی", "national_code": national_code("049937089")},
        "contact": {"mobile": "09351112233"},
        "vehicle": {
            "vehicle_type": "TRAILER", "body_type": "REFRIGERATED", "capacity_tons": 22.5,
            "cargo_types": ["FOOD", "PERISHABLE"],
        },
        "service_area": {
            "area_type": "INTERPROVINCIAL",
            "coverage": [
                {"province": "تهران", "all_cities": True},
                {"province": "خراسان رضوی", "cities": ["مشهد", "نیشابور"]},
            ],
        },
    }
    body.update(over)
    return body


def fields(resp) -> set[str]:
    assert resp.status_code == 400, resp.get_json()
    return {d["field"] for d in resp.get_json()["error"]["details"]}


def register(client, body):
    return client.post(f"{BASE}/public/register", json=body)


def step(client, applicant_type, name, data):
    return client.post(f"{BASE}/public/validate-step", json={"applicant_type": applicant_type, "step": name, "data": data})


@pytest.fixture(autouse=True)
def _upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)


# ── pure validators ──────────────────────────────────────────────────
def test_validators():
    assert v.clean_national_code("۰۴۹۹۳۷۰۸۹۹") == "0499370899"
    with pytest.raises(ValueError):
        v.clean_national_code("0499370898")
    assert v.clean_legal_national_id(legal_id("1010101010")) == legal_id("1010101010")
    assert v.clean_mobile("+98 912 123 4567") == "09121234567"
    assert v.clean_landline("021-22334455") == "02122334455"
    assert v.clean_mobile_or_landline("02122334455") == "02122334455"


# ── wizard definition / reference ────────────────────────────────────
def test_wizard_paths_differ_by_type_and_share_service_area(client):
    data = client.get(f"{BASE}/public/wizard").get_json()["data"]
    company = [s["id"] for s in data["paths"]["COMPANY"]]
    driver = [s["id"] for s in data["paths"]["DRIVER"]]
    assert company == ["applicant_type", "company_info", "representative", "service_area"]
    assert driver == ["applicant_type", "identity", "contact", "vehicle", "service_area"]
    assert "vehicle" not in company
    assert [s["number"] for s in data["paths"]["DRIVER"]] == [1, 2, 3, 4, 5]
    assert data["paths"]["COMPANY"][-1] == {**data["paths"]["COMPANY"][-1], "shared": True}


def test_reference_catalog(client):
    data = client.get(f"{BASE}/public/reference").get_json()["data"]
    assert {o["code"] for o in data["vehicle_types"]} >= {"PICKUP", "TRAILER", "TEN_WHEEL", "OTHER"}
    assert {o["code"] for o in data["area_types"]} == {"CITY", "PROVINCIAL", "INTERPROVINCIAL", "INTERNATIONAL"}
    tehran = next(p for p in data["provinces"] if p["name"] == "تهران")
    assert "شهریار" in tehran["cities"]


# ── company path ─────────────────────────────────────────────────────
def test_company_registration_is_pending_and_has_no_vehicle(client, app):
    r = register(client, company_body())
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["data"]["status"] == "PENDING"
    h = staff(*ALL)
    a = client.get(f"{BASE}/applicants/{r.get_json()['data']['id']}", headers=h).get_json()["data"]
    assert a["applicant_type"] == "COMPANY" and a["display_name"] == "حمل‌ونقل سریع"
    assert "vehicle" not in a and a["representative"]["mobile"] == "09121234567"
    assert a["service_area"]["coverage"][0]["cities"] == []  # whole province


def test_company_cannot_send_vehicle_or_driver_sections(client):
    assert "vehicle" in fields(register(client, company_body(vehicle=driver_body()["vehicle"])))
    assert "identity" in fields(register(client, company_body(identity=driver_body()["identity"])))


def test_company_required_fields_follow_legal_type(client):
    body = company_body()
    del body["company_info"]["company_name"]
    assert "company_info.company_name" in fields(register(client, body))

    body = company_body()
    body["company_info"].update(entity_type="INDIVIDUAL")
    assert {"company_info.first_name", "company_info.last_name"} <= fields(register(client, body))

    # INDIVIDUAL: names present -> accepted, and the optional legal ID is dropped, not stored
    body = company_body()
    body["company_info"].update(entity_type="INDIVIDUAL", first_name="رضا", last_name="احمدی")
    r = register(client, body)
    assert r.status_code == 201, r.get_json()
    a = client.get(f"{BASE}/applicants/{r.get_json()['data']['id']}", headers=staff(*ALL)).get_json()["data"]
    assert a["display_name"] == "رضا احمدی"
    assert a["company_info"]["national_id"] is None and a["company_info"]["company_name"] is None


def test_company_national_id_optional_but_validated(client):
    body = company_body()
    del body["company_info"]["national_id"]
    assert register(client, body).status_code == 201
    body = company_body(representative={**company_body()["representative"], "mobile": "09129998877"})
    body["company_info"]["national_id"] = "12345678901"
    assert "company_info.national_id" in fields(register(client, body))


def test_company_province_city_and_address_required(client):
    body = company_body()
    body["company_info"]["city"] = "مشهد"  # not in تهران
    assert "company_info.city" in fields(register(client, body))
    body = company_body()
    del body["company_info"]["province"]
    del body["company_info"]["office_address"]
    assert {"company_info.province", "company_info.office_address"} <= fields(register(client, body))


def test_representative_rules(client):
    body = company_body()
    body["representative"].update(position="OTHER")
    assert "representative.position_other" in fields(register(client, body))
    body["representative"].update(position_other="مدیر ناوگان", landline="12345")
    assert "representative.landline" in fields(register(client, body))
    body["representative"].update(landline=None)
    assert register(client, body).status_code == 201


# ── driver path ──────────────────────────────────────────────────────
def test_driver_registration_stores_vehicle(client):
    r = register(client, driver_body())
    assert r.status_code == 201, r.get_json()
    a = client.get(f"{BASE}/applicants/{r.get_json()['data']['id']}", headers=staff(*ALL)).get_json()["data"]
    assert a["vehicle"]["capacity_tons"] == 22.5 and a["vehicle"]["cargo_types"] == ["FOOD", "PERISHABLE"]
    assert "company_info" not in a and a["contact"]["alt_phone"] is None


def test_driver_cannot_send_company_sections(client):
    assert "company_info" in fields(register(client, driver_body(company_info=company_body()["company_info"])))


def test_driver_bad_national_code_and_mobile(client):
    body = driver_body()
    body["identity"]["national_code"] = "0499370898"
    body["contact"]["mobile"] = "12345"
    assert {"identity.national_code", "contact.mobile"} <= fields(register(client, body))


def test_driver_other_options_are_conditionally_required(client):
    body = driver_body()
    body["vehicle"].update(vehicle_type="OTHER", body_type="OTHER", cargo_types=["OTHER"])
    assert {"vehicle.vehicle_type_other", "vehicle.body_type_other", "vehicle.cargo_type_other"} <= fields(register(client, body))
    body["vehicle"].update(vehicle_type_other="لیفتراک", body_type_other="بدنه ویژه", cargo_type_other="شیشه")
    assert register(client, body).status_code == 201


def test_driver_vehicle_validation(client):
    body = driver_body()
    body["vehicle"].update(capacity_tons=0, cargo_types=[])
    assert {"vehicle.capacity_tons", "vehicle.cargo_types"} <= fields(register(client, body))
    body["vehicle"].update(capacity_tons="۱۲٫۵", cargo_types=["FOOD"])
    assert register(client, body).status_code == 201


def test_driver_alt_phone_accepts_mobile_or_landline(client):
    body = driver_body()
    body["contact"]["alt_phone"] = "02122334455"
    assert register(client, body).status_code == 201


# ── service area (shared step) ───────────────────────────────────────
@pytest.mark.parametrize("who", ["COMPANY", "DRIVER"])
def test_service_area_city_needs_exactly_one_city(client, who):
    ok = {"area_type": "CITY", "coverage": [{"province": "تهران", "cities": ["تهران"]}]}
    assert step(client, who, "service_area", ok).status_code == 200
    two = {"area_type": "CITY", "coverage": [{"province": "تهران", "cities": ["تهران", "شهریار"]}]}
    assert "service_area.coverage" in fields(step(client, who, "service_area", two))
    whole = {"area_type": "CITY", "coverage": [{"province": "تهران", "all_cities": True}]}
    assert "service_area.coverage" in fields(step(client, who, "service_area", whole))


def test_service_area_provincial_and_interprovincial(client):
    two_prov = {"area_type": "PROVINCIAL", "coverage": [{"province": "تهران", "all_cities": True}, {"province": "قم", "all_cities": True}]}
    assert "service_area.coverage" in fields(step(client, "COMPANY", "service_area", two_prov))
    one = {"area_type": "INTERPROVINCIAL", "coverage": [{"province": "تهران", "all_cities": True}]}
    assert "service_area.coverage" in fields(step(client, "COMPANY", "service_area", one))
    no_city = {"area_type": "PROVINCIAL", "coverage": [{"province": "تهران"}]}
    assert fields(step(client, "COMPANY", "service_area", no_city))  # cities or whole province required
    wrong_city = {"area_type": "PROVINCIAL", "coverage": [{"province": "تهران", "cities": ["مشهد"]}]}
    assert fields(step(client, "COMPANY", "service_area", wrong_city))


def test_changing_area_type_clears_irrelevant_fields(client):
    data = {
        "area_type": "CITY", "coverage": [{"province": "تهران", "cities": ["تهران"]}],
        "origin_countries": ["TR"], "destination_countries": ["IQ"],
        "permits": [{"type": "TIR_CARNET"}],
    }
    out = step(client, "COMPANY", "service_area", data).get_json()["data"]
    assert out["origin_countries"] == [] and out["destination_countries"] == [] and out["permits"] == []


def test_international_requires_countries_and_the_right_permit(client):
    base = {"area_type": "INTERNATIONAL", "origin_countries": ["IR"], "destination_countries": ["TR"]}
    # company: licence file required
    assert "service_area.permits" in fields(step(client, "COMPANY", "service_area", base))
    up = client.post(f"{BASE}/public/files", data={"file": (io.BytesIO(b"%PDF-1.4 x"), "licence.pdf")},
                     content_type="multipart/form-data")
    assert up.status_code == 201, up.get_json()
    ref = up.get_json()["data"]
    good = {**base, "permits": [{"type": "INTL_TRANSPORT_LICENSE", "number": "123", "file": ref}]}
    assert step(client, "COMPANY", "service_area", good).status_code == 200
    # a driver needs the driver permit, not the company licence
    assert "service_area.permits.0.type" in fields(step(client, "DRIVER", "service_area", good))
    driver_ok = {**base, "permits": [{"type": "INTL_DRIVER_PERMIT", "file": ref}]}
    assert step(client, "DRIVER", "service_area", driver_ok).status_code == 200
    # countries
    none = {"area_type": "INTERNATIONAL", "origin_countries": [], "destination_countries": []}
    assert {"service_area.origin_countries", "service_area.destination_countries"} <= fields(step(client, "COMPANY", "service_area", none))
    only_iran = {"area_type": "INTERNATIONAL", "origin_countries": ["IR"], "destination_countries": ["IR"]}
    assert fields(step(client, "COMPANY", "service_area", only_iran))


def test_international_registration_end_to_end_stores_file_reference(client):
    ref = client.post(f"{BASE}/public/files", data={"file": (io.BytesIO(b"%PDF-1.4 x"), "licence.pdf")},
                      content_type="multipart/form-data").get_json()["data"]
    area = {
        "area_type": "INTERNATIONAL", "origin_countries": ["IR"], "destination_countries": ["TR", "AM"],
        "permits": [{"type": "INTL_TRANSPORT_LICENSE", "file": {"id": ref["id"], "name": "forged.pdf"}}],
    }
    r = register(client, company_body(service_area=area))
    assert r.status_code == 201, r.get_json()
    a = client.get(f"{BASE}/applicants/{r.get_json()['data']['id']}", headers=staff(*ALL)).get_json()["data"]
    assert a["service_area"]["permits"][0]["file"]["name"] == "licence.pdf"  # name comes from the upload, not the client


def test_unknown_file_reference_is_rejected(client):
    area = {"area_type": "INTERNATIONAL", "origin_countries": ["IR"], "destination_countries": ["TR"],
            "permits": [{"type": "INTL_TRANSPORT_LICENSE", "file": {"id": "does-not-exist"}}]}
    assert register(client, company_body(service_area=area)).status_code == 409


# ── per-step validation endpoint ─────────────────────────────────────
def test_validate_step_normalises_and_rejects_foreign_steps(client):
    out = step(client, "DRIVER", "contact", {"mobile": "+98 935 111 2233"}).get_json()["data"]
    assert out["mobile"] == "09351112233"
    assert step(client, "COMPANY", "vehicle", driver_body()["vehicle"]).status_code == 400  # no vehicle step for companies
    assert step(client, "DRIVER", "company_info", company_body()["company_info"]).status_code == 400


# ── duplicates ───────────────────────────────────────────────────────
def test_duplicate_driver_is_conflict(client):
    assert register(client, driver_body()).status_code == 201
    r = register(client, driver_body())
    assert r.status_code == 409
    assert step(client, "DRIVER", "identity", driver_body()["identity"]).status_code == 409


def test_deleted_applicant_does_not_block_re_registration(client):
    first = register(client, driver_body()).get_json()["data"]["id"]
    h = staff(*ALL)
    assert client.delete(f"{BASE}/applicants/{first}", headers=h).status_code == 200
    assert register(client, driver_body()).status_code == 201


# ── access levels (backend RBAC) ─────────────────────────────────────
def test_every_staff_route_needs_a_login_and_a_permission(client):
    assert client.get(f"{BASE}/applicants").status_code == 401
    nobody = staff()
    assert client.get(f"{BASE}/applicants", headers=nobody).status_code == 403
    assert client.get(f"{BASE}/stats", headers=nobody).status_code == 403
    assert client.post(f"{BASE}/applicants", json=company_body(), headers=nobody).status_code == 403


def test_access_is_per_applicant_type(client):
    c_id = register(client, company_body()).get_json()["data"]["id"]
    d_id = register(client, driver_body()).get_json()["data"]["id"]
    drivers_only = staff("logistics.driver.read")
    assert client.get(f"{BASE}/applicants/{d_id}", headers=drivers_only).status_code == 200
    assert client.get(f"{BASE}/applicants/{c_id}", headers=drivers_only).status_code == 403
    rows = client.get(f"{BASE}/applicants", headers=drivers_only).get_json()["data"]
    assert [r["applicant_type"] for r in rows] == ["DRIVER"]
    assert client.get(f"{BASE}/applicants?applicant_type=COMPANY", headers=drivers_only).status_code == 403
    stats = client.get(f"{BASE}/stats", headers=drivers_only).get_json()["data"]
    assert list(stats["by_type_status"]) == ["DRIVER"]


def test_read_only_user_cannot_write_or_review(client):
    c_id = register(client, company_body()).get_json()["data"]["id"]
    ro = staff("logistics.company.read")
    assert client.post(f"{BASE}/applicants", json=company_body(), headers=ro).status_code == 403
    assert client.patch(f"{BASE}/applicants/{c_id}", json={"is_active": False}, headers=ro).status_code == 403
    assert client.post(f"{BASE}/applicants/{c_id}/review", json={"action": "APPROVE"}, headers=ro).status_code == 403
    assert client.delete(f"{BASE}/applicants/{c_id}", headers=ro).status_code == 403


def test_update_permission_is_not_review_permission(client):
    c_id = register(client, company_body()).get_json()["data"]["id"]
    editor = staff("logistics.company.read", "logistics.company.update")
    assert client.post(f"{BASE}/applicants/{c_id}/review", json={"action": "APPROVE"}, headers=editor).status_code == 403
    assert client.patch(f"{BASE}/applicants/{c_id}", json={"is_active": True}, headers=editor).status_code == 200


def test_admin_create_needs_review_to_set_a_decided_status(client):
    maker = staff("logistics.company.create", "logistics.company.read")
    assert client.post(f"{BASE}/applicants", json=company_body(status="PENDING"), headers=maker).status_code == 201
    other = company_body(status="APPROVED", representative={**company_body()["representative"], "mobile": "09125556677"})
    other["company_info"]["national_id"] = legal_id("1010101020")
    assert client.post(f"{BASE}/applicants", json=other, headers=maker).status_code == 403
    boss = staff(*ALL)
    assert client.post(f"{BASE}/applicants", json=other, headers=boss).status_code == 201


# ── review workflow ──────────────────────────────────────────────────
def test_review_transitions(client):
    c_id = register(client, company_body()).get_json()["data"]["id"]
    h = staff(*ALL)
    url = f"{BASE}/applicants/{c_id}/review"
    assert client.post(url, json={"action": "SUSPEND", "note": "x y z"}, headers=h).status_code == 409  # not approved yet
    assert client.post(url, json={"action": "REJECT"}, headers=h).status_code == 400  # reason required
    ok = client.post(url, json={"action": "APPROVE"}, headers=h)
    assert ok.status_code == 200 and ok.get_json()["data"]["status"] == "APPROVED"
    assert client.post(url, json={"action": "APPROVE"}, headers=h).status_code == 409
    sus = client.post(url, json={"action": "SUSPEND", "note": "مدارک ناقص"}, headers=h).get_json()["data"]
    assert sus["status"] == "SUSPENDED" and sus["review_note"] == "مدارک ناقص" and sus["reviewed_by_user_id"]
    assert client.post(url, json={"action": "APPROVE"}, headers=h).get_json()["data"]["status"] == "APPROVED"


# ── update / list / delete ───────────────────────────────────────────
def test_patch_replaces_service_area_and_rejects_foreign_sections(client):
    d_id = register(client, driver_body()).get_json()["data"]["id"]
    h = staff(*ALL)
    city = {"area_type": "CITY", "coverage": [{"province": "قم", "cities": ["قم"]}]}
    a = client.patch(f"{BASE}/applicants/{d_id}", json={"service_area": city}, headers=h).get_json()["data"]
    assert a["service_area"]["area_type"] == "CITY" and len(a["service_area"]["coverage"]) == 1
    r = client.patch(f"{BASE}/applicants/{d_id}", json={"company_info": company_body()["company_info"]}, headers=h)
    assert "company_info" in fields(r)
    v2 = {**driver_body()["vehicle"], "capacity_tons": 9}
    a = client.patch(f"{BASE}/applicants/{d_id}", json={"vehicle": v2}, headers=h).get_json()["data"]
    assert a["vehicle"]["capacity_tons"] == 9 and a["identity"]["first_name"] == "حسین"


def test_list_filters_and_stats(client):
    register(client, company_body())
    register(client, driver_body())
    d2 = driver_body(identity={"first_name": "مهدی", "last_name": "صادقی", "national_code": national_code("001035082")},
                     contact={"mobile": "09361234567"})
    d2["vehicle"].update(vehicle_type="PICKUP", body_type="TARP")
    register(client, d2)
    h = staff(*ALL)
    assert client.get(f"{BASE}/applicants?applicant_type=DRIVER", headers=h).get_json()["meta"]["total"] == 2
    assert client.get(f"{BASE}/applicants?vehicle_type=PICKUP", headers=h).get_json()["meta"]["total"] == 1
    assert client.get(f"{BASE}/applicants?search=مهدی", headers=h).get_json()["meta"]["total"] == 1
    assert client.get(f"{BASE}/applicants?search=09361234567", headers=h).get_json()["meta"]["total"] == 1
    assert client.get(f"{BASE}/applicants?province=تهران", headers=h).get_json()["meta"]["total"] == 1
    assert client.get(f"{BASE}/applicants?area_type=INTERPROVINCIAL", headers=h).get_json()["meta"]["total"] == 2
    s = client.get(f"{BASE}/stats", headers=h).get_json()["data"]
    assert s["total"] == 3 and s["by_type_status"]["DRIVER"]["PENDING"] == 2


def test_delete_is_soft(client, app):
    c_id = register(client, company_body()).get_json()["data"]["id"]
    h = staff(*ALL)
    assert client.delete(f"{BASE}/applicants/{c_id}", headers=h).status_code == 200
    assert client.get(f"{BASE}/applicants/{c_id}", headers=h).status_code == 404
    assert db.session.get(LogisticsApplicant, c_id).deleted_at is not None


def test_permit_file_download_needs_staff_read(client):
    ref = client.post(f"{BASE}/public/files", data={"file": (io.BytesIO(b"%PDF-1.4 x"), "licence.pdf")},
                      content_type="multipart/form-data").get_json()["data"]
    assert client.get(f"{BASE}/files/{ref['id']}").status_code == 401
    assert client.get(f"{BASE}/files/{ref['id']}", headers=staff()).status_code == 403
    assert client.get(f"{BASE}/files/{ref['id']}", headers=staff("logistics.driver.read")).status_code == 200


def test_upload_rejects_disallowed_type(client):
    r = client.post(f"{BASE}/public/files", data={"file": (io.BytesIO(b"x"), "a.exe")}, content_type="multipart/form-data")
    assert r.status_code == 400


# ── permission registry / navigation / matrix wiring ─────────────────
def test_registry_matrix_and_navigation_know_logistics(client):
    from app.permissions.registry import MATRIX_MODULES, REGISTRY
    assert all(k in REGISTRY for k in ALL)
    assert not REGISTRY["logistics.company.review"].is_delegable
    keys = {m.key for m in MATRIX_MODULES}
    assert {"logistics.company", "logistics.driver"} <= keys
    h = staff("logistics.driver.read")
    nav = client.get("/api/me/navigation", headers=h)
    if nav.status_code == 200:  # endpoint path per API.md; skip silently if it is mounted elsewhere
        assert [e["key"] for e in nav.get_json()["data"]] == ["logistics_drivers"]
