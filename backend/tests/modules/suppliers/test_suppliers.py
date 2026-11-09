"""HTTP tests for /api/suppliers -- Procurement module."""
import pytest

from app.core.authorization.models import ScopeType
from app.extensions import db
from app.modules.suppliers.models import SupplierCategory
from tests.core4.factories import auth_headers, grant_user_permission, make_permission, make_user


@pytest.fixture(autouse=True)
def _seed_categories(app):
    with app.app_context():
        for i, name in enumerate(["پلیمر و رزین", "بسته‌بندی"], start=1):
            db.session.add(SupplierCategory(name=name, sort_order=i))
        db.session.commit()


def _admin_payload(client, headers, **overrides):
    """Payload for POST /api/suppliers: staff products must carry an image."""
    import io as _io
    r = client.post(
        "/api/suppliers/files",
        data={"file": (_io.BytesIO(b"\x89PNG fake"), "product.png")},
        content_type="multipart/form-data", headers=headers,
    )
    image = r.get_json()["data"]
    body = _payload(products=[{"name": "Masterbatch", "payment": "cash", "image": image}])
    body.update(overrides)
    return body


def _grant(user, key, scope_type=ScopeType.GLOBAL, scope_id=None):
    permission = make_permission(key)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def _payload(**overrides):
    body = {
        "supplier_type": "LEGAL",
        "company_name": "Polymer Example Co.",
        "company_national_id": "12345678901",
        "email": "info@example.com",
        "category": "پلیمر و رزین",
        "phones": [
            {"type": "landline", "number": "02122898979"},
            {"type": "mobile", "number": "09121234567"},
        ],
        "contacts": [{
            "first_name": "Ali", "last_name": "Rezaei", "position": "Sales manager",
            "email": "ali@example.com", "mobile": "09121234567", "landline": "02122898979",
        }],
        "products": [{"name": "Masterbatch", "payment": "cash"}],
        "catalog_files": ["catalog.pdf"],
    }
    body.update(overrides)
    return body


def test_public_submission_requires_no_auth_and_creates_semi_active_supplier(client, app):
    r = client.post("/api/suppliers/public", json=_payload())
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert data["status"] == "SEMI_ACTIVE"
    assert data["is_public_submission"] is True
    assert data["display_name"] == "Polymer Example Co."


def test_public_submission_requires_both_phone_types(client, app):
    bad = _payload(contacts=[], phones=[{"type": "mobile", "number": "09121234567"}])
    r = client.post("/api/suppliers/public", json=bad)
    assert r.status_code == 400


def test_list_requires_permission(client, app):
    with app.app_context():
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)
    assert client.get("/api/suppliers", headers=headers).status_code == 403


def test_admin_can_review_status_and_quality(client, app):
    with app.app_context():
        reviewer = make_user()
        _grant(reviewer, "procurement.supplier.read")
        _grant(reviewer, "procurement.supplier.update")
        db.session.commit()
        headers = auth_headers(reviewer)

    r = client.post("/api/suppliers/public", json=_payload())
    supplier_id = r.get_json()["data"]["id"]

    r2 = client.patch(f"/api/suppliers/{supplier_id}", json={"status": "ACTIVE", "quality": "EXCELLENT"}, headers=headers)
    assert r2.status_code == 200
    data = r2.get_json()["data"]
    assert data["status"] == "ACTIVE"
    assert data["quality"] == "EXCELLENT"
    assert data["reviewed_by_user_id"] is not None


def test_review_without_update_permission_is_denied(client, app):
    with app.app_context():
        reader = make_user()
        _grant(reader, "procurement.supplier.read")
        db.session.commit()
        headers = auth_headers(reader)

    r = client.post("/api/suppliers/public", json=_payload())
    supplier_id = r.get_json()["data"]["id"]
    r2 = client.patch(f"/api/suppliers/{supplier_id}", json={"status": "ACTIVE"}, headers=headers)
    assert r2.status_code == 403


def test_admin_can_add_supplier_directly_with_search_and_category_filter(client, app):
    with app.app_context():
        staff = make_user()
        _grant(staff, "procurement.supplier.read")
        _grant(staff, "procurement.supplier.create")
        db.session.commit()
        headers = auth_headers(staff)

    body = _admin_payload(client, headers, company_name="Searchable Unique Co.", category="بسته‌بندی")
    r = client.post("/api/suppliers", json=body, headers=headers)
    assert r.status_code == 201
    assert r.get_json()["data"]["is_public_submission"] is False

    r2 = client.get("/api/suppliers?search=Searchable", headers=headers)
    assert r2.status_code == 200
    assert any(s["company_name"] == "Searchable Unique Co." for s in r2.get_json()["data"])

    r3 = client.get("/api/suppliers?category=بسته‌بندی", headers=headers)
    assert all(s["category"] == "بسته‌بندی" for s in r3.get_json()["data"])

    r4 = client.get("/api/suppliers/categories", headers=headers)
    assert "بسته‌بندی" in r4.get_json()["data"]


def test_delete_requires_its_own_permission(client, app):
    with app.app_context():
        updater = make_user()
        _grant(updater, "procurement.supplier.read")
        _grant(updater, "procurement.supplier.update")
        db.session.commit()
        headers = auth_headers(updater)

    r = client.post("/api/suppliers/public", json=_payload())
    supplier_id = r.get_json()["data"]["id"]
    assert client.delete(f"/api/suppliers/{supplier_id}", headers=headers).status_code == 403


def test_public_categories_lists_only_active_and_needs_no_auth(client, app):
    with app.app_context():
        db.session.add(SupplierCategory(name="Hidden", sort_order=9, is_active=False))
        db.session.commit()
    r = client.get("/api/suppliers/categories/public")
    assert r.status_code == 200
    assert r.get_json()["data"] == ["پلیمر و رزین", "بسته‌بندی"]


def test_public_submission_rejects_unknown_category(client, app):
    r = client.post("/api/suppliers/public", json=_payload(category="Not in list"))
    assert r.status_code == 409


def test_admin_adds_renames_and_removes_category(client, app):
    with app.app_context():
        staff = make_user()
        _grant(staff, "procurement.supplier.read")
        _grant(staff, "procurement.supplier.update")
        db.session.commit()
        headers = auth_headers(staff)

    r = client.post("/api/suppliers/category-items", json={"name": "  مواد   اولیه "}, headers=headers)
    assert r.status_code == 201
    cat = r.get_json()["data"]
    assert cat["name"] == "مواد اولیه"
    assert client.post("/api/suppliers/category-items", json={"name": "مواد اولیه"}, headers=headers).status_code == 409
    assert "مواد اولیه" in client.get("/api/suppliers/categories/public").get_json()["data"]

    # a supplier using it follows a rename
    sid = client.post("/api/suppliers/public", json=_payload(category="مواد اولیه")).get_json()["data"]["id"]
    r = client.patch(f"/api/suppliers/category-items/{cat['id']}", json={"name": "مواد خام"}, headers=headers)
    assert r.status_code == 200 and r.get_json()["data"]["supplier_count"] == 1
    assert client.get(f"/api/suppliers/{sid}", headers=headers).get_json()["data"]["category"] == "مواد خام"

    # removing keeps the supplier row intact but stops offering the name
    assert client.delete(f"/api/suppliers/category-items/{cat['id']}", headers=headers).status_code == 200
    assert "مواد خام" not in client.get("/api/suppliers/categories/public").get_json()["data"]
    assert client.get(f"/api/suppliers/{sid}", headers=headers).get_json()["data"]["category"] == "مواد خام"
    assert "مواد خام" in client.get("/api/suppliers/categories", headers=headers).get_json()["data"]


def test_category_management_needs_update_permission(client, app):
    with app.app_context():
        reader = make_user()
        _grant(reader, "procurement.supplier.read")
        db.session.commit()
        headers = auth_headers(reader)
    assert client.get("/api/suppliers/category-items", headers=headers).status_code == 200
    assert client.post("/api/suppliers/category-items", json={"name": "X"}, headers=headers).status_code == 403


def test_admin_edit_keeps_all_product_fields(client, app, upload_dir):
    with app.app_context():
        staff = make_user()
        _grant(staff, "procurement.supplier.read")
        _grant(staff, "procurement.supplier.update")
        db.session.commit()
        headers = auth_headers(staff)
    image = _upload(client, "/api/suppliers/files", name="pe.png", headers=headers).get_json()["data"]
    sid = client.post("/api/suppliers/public", json=_payload()).get_json()["data"]["id"]
    products = [{"name": "PE Masterbatch", "specs": "MFI 20", "payment": "credit", "creditMonths": 3,
                 "description": "25kg bags", "datasheet": "pe.pdf", "image": image}]
    r = client.patch(
        f"/api/suppliers/{sid}",
        json={"products": products, "activity_type": "تولید کننده,وارد کننده", "company_type": "سهامی خاص",
              "established_date": "2015-03-01", "experience": "۵ تا ۱۰ سال", "capacity": "20t"},
        headers=headers,
    )
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["products"][0]["creditMonths"] == 3 and d["products"][0]["specs"] == "MFI 20"
    assert d["activity_type"] == "تولید کننده,وارد کننده" and d["experience"] == "۵ تا ۱۰ سال"


# ---------------------------------------------------------------------
# File uploads (catalog / datasheet) + "added by"
# ---------------------------------------------------------------------
import io


@pytest.fixture()
def upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)
    return tmp_path


def _upload(client, url, name="catalog.pdf", data=b"%PDF-1.4 test", headers=None):
    return client.post(
        url, data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data", headers=headers or {}
    )


def _staff(app, *actions):
    with app.app_context():
        user = make_user()
        for a in actions:
            _grant(user, f"procurement.supplier.{a}")
        db.session.commit()
        return auth_headers(user), user.full_name


def test_public_upload_then_submit_keeps_real_file_reference(client, app, upload_dir):
    r = _upload(client, "/api/suppliers/files/public", name="کاتالوگ.pdf")
    assert r.status_code == 201
    ref = r.get_json()["data"]
    assert ref["name"] == "کاتالوگ.pdf" and ref["size"] > 0
    assert (upload_dir / f"{ref['id']}.pdf").exists()

    body = _payload(
        catalog_files=[ref], products=[{"name": "MB", "payment": "cash", "datasheet": ref}],
    )
    r2 = client.post("/api/suppliers/public", json=body)
    assert r2.status_code == 201
    data = r2.get_json()["data"]
    assert data["catalog_files"][0]["id"] == ref["id"]
    assert data["products"][0]["datasheet"]["id"] == ref["id"]
    assert data["created_by_name"] is None  # public form -> no staff user


def test_submit_with_unknown_file_id_is_rejected(client, app, upload_dir):
    bad = {"id": "00000000-0000-0000-0000-000000000000", "name": "x.pdf", "size": 1}
    r = client.post("/api/suppliers/public", json=_payload(catalog_files=[bad]))
    assert r.status_code == 409


def test_client_cannot_spoof_file_name_in_reference(client, app, upload_dir):
    ref = _upload(client, "/api/suppliers/files/public", name="real.pdf").get_json()["data"]
    spoof = {**ref, "name": "evil.exe", "size": 999999}
    r = client.post("/api/suppliers/public", json=_payload(catalog_files=[spoof]))
    assert r.get_json()["data"]["catalog_files"][0]["name"] == "real.pdf"


def test_legacy_filename_strings_still_work(client, app, upload_dir):
    r = client.post("/api/suppliers/public", json=_payload(catalog_files=["old.pdf"]))
    assert r.status_code == 201
    assert r.get_json()["data"]["catalog_files"] == ["old.pdf"]


def test_upload_rejects_disallowed_type_empty_and_too_large(client, app, upload_dir):
    assert _upload(client, "/api/suppliers/files/public", name="run.exe").status_code == 400
    assert _upload(client, "/api/suppliers/files/public", data=b"").status_code == 400
    app.config["MAX_UPLOAD_MB"] = 1
    assert _upload(client, "/api/suppliers/files/public", data=b"x" * (1024 * 1024 + 1)).status_code == 413


def test_staff_upload_needs_auth_and_permission(client, app, upload_dir):
    # users are created before the first request (in-memory SQLite test setup)
    with app.app_context():
        nobody = make_user()
        db.session.commit()
        h = auth_headers(nobody)
    h2, _ = _staff(app, "create")
    assert _upload(client, "/api/suppliers/files").status_code == 401
    assert _upload(client, "/api/suppliers/files", headers=h).status_code == 403
    assert _upload(client, "/api/suppliers/files", headers=h2).status_code == 201


def test_download_is_staff_only_and_served_as_attachment(client, app, upload_dir):
    headers, _ = _staff(app, "read")
    ref = _upload(client, "/api/suppliers/files/public", name="datasheet.pdf", data=b"hello").get_json()["data"]
    url = f"/api/suppliers/files/{ref['id']}"
    assert client.get(url).status_code == 401

    r = client.get(url, headers=headers)
    assert r.status_code == 200
    assert r.data == b"hello"
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/suppliers/files/nope", headers=headers).status_code == 404


def test_staff_created_supplier_reports_who_added_it(client, app, upload_dir):
    headers, full_name = _staff(app, "read", "create")
    ref = _upload(client, "/api/suppliers/files", headers=headers).get_json()["data"]
    r = client.post("/api/suppliers", json=_admin_payload(client, headers, catalog_files=[ref]), headers=headers)
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert data["created_by_name"] == full_name
    assert data["is_public_submission"] is False

    listed = client.get("/api/suppliers", headers=headers).get_json()["data"]
    assert listed[0]["created_by_name"] == full_name


def test_editing_supplier_can_replace_catalog_files(client, app, upload_dir):
    headers, _ = _staff(app, "read", "create", "update")
    ref = _upload(client, "/api/suppliers/files", name="new.pdf", headers=headers).get_json()["data"]
    sid = client.post("/api/suppliers/public", json=_payload(catalog_files=["old.pdf"])).get_json()["data"]["id"]
    r = client.patch(f"/api/suppliers/{sid}", json={"catalog_files": [ref]}, headers=headers)
    assert r.status_code == 200
    assert r.get_json()["data"]["catalog_files"][0]["name"] == "new.pdf"


def test_admin_product_requires_image(client, app, upload_dir):
    headers, _ = _staff(app, "read", "create", "update")
    # no image -> rejected
    r = client.post("/api/suppliers", json=_payload(), headers=headers)
    assert r.status_code == 400
    # with image -> ok, and the reference comes back on the product
    r2 = client.post("/api/suppliers", json=_admin_payload(client, headers), headers=headers)
    assert r2.status_code == 201
    assert r2.get_json()["data"]["products"][0]["image"]["name"] == "product.png"
    # editing products without an image is rejected too
    sid = r2.get_json()["data"]["id"]
    r3 = client.patch(f"/api/suppliers/{sid}", json={"products": [{"name": "X"}]}, headers=headers)
    assert r3.status_code == 400


def test_product_image_must_be_an_image_file(client, app, upload_dir):
    headers, _ = _staff(app, "read", "create")
    pdf = _upload(client, "/api/suppliers/files", name="not-image.pdf", headers=headers).get_json()["data"]
    body = _payload(products=[{"name": "MB", "payment": "cash", "image": pdf}])
    assert client.post("/api/suppliers", json=body, headers=headers).status_code == 409


def test_public_form_still_works_without_product_image(client, app, upload_dir):
    assert client.post("/api/suppliers/public", json=_payload()).status_code == 201


def test_contact_requires_name_position_and_a_number(client, app):
    for bad_contact in (
        {"first_name": "Ali", "last_name": "", "position": "CEO", "mobile": "0912"},
        {"first_name": "Ali", "last_name": "R", "position": "", "mobile": "0912"},
        {"first_name": "Ali", "last_name": "R", "position": "CEO"},
    ):
        r = client.post("/api/suppliers/public", json=_payload(contacts=[bad_contact]))
        assert r.status_code == 400


def test_phones_are_derived_from_contacts(client, app):
    r = client.post("/api/suppliers/public", json=_payload(phones=[]))
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert data["contacts"][0]["position"] == "Sales manager"
    assert {p["type"] for p in data["phones"]} == {"mobile", "landline"}


# ── bank accounts (optional, any number) ─────────────────────────────
def _luhn_card(p15: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(p15 + "0")):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return p15 + str((10 - total % 10) % 10)


def _sheba(bban22: str) -> str:
    return "IR" + f"{98 - int(bban22 + '182700') % 97:02d}" + bban22


def test_supplier_without_bank_accounts_still_works_and_defaults_to_empty(client, app):
    sid = client.post("/api/suppliers/public", json=_payload()).get_json()["data"]["id"]
    headers, _ = _staff(app, "read")
    assert client.get(f"/api/suppliers/{sid}", headers=headers).get_json()["data"]["bank_accounts"] == []


def test_admin_adds_any_number_of_bank_accounts_all_fields_optional(client, app, upload_dir):
    headers, _ = _staff(app, "read", "create", "update")
    card, sheba = _luhn_card("603799189997123"), _sheba("0170000000123456789012")
    accounts = [
        {"holder_name": "  شرکت   نمونه ", "bank_name": "ملی", "card_number": " ".join([card[i:i + 4] for i in range(0, 16, 4)]),
         "account_number": "0201234567001", "sheba": sheba.lower()},
        {"sheba": sheba[2:]},                    # only a Sheba (written without IR)
        {"holder_name": "علی رضایی"},            # only a name
        {},                                      # fully blank -> dropped
        {"bank_name": "  "},                     # blank after trimming -> dropped
    ]
    r = client.post("/api/suppliers", json=_admin_payload(client, headers, bank_accounts=accounts), headers=headers)
    assert r.status_code == 201, r.get_json()
    saved = r.get_json()["data"]["bank_accounts"]
    assert len(saved) == 3
    assert saved[0] == {"holder_name": "شرکت نمونه", "bank_name": "ملی", "card_number": card,
                        "account_number": "0201234567001", "sheba": sheba}
    assert saved[1]["sheba"] == sheba and saved[1]["card_number"] is None
    # editing replaces the whole list; an empty list clears it
    sid = r.get_json()["data"]["id"]
    one = client.patch(f"/api/suppliers/{sid}", json={"bank_accounts": [{"bank_name": "ملت"}, {"bank_name": "پاسارگاد"}]}, headers=headers)
    assert [a["bank_name"] for a in one.get_json()["data"]["bank_accounts"]] == ["ملت", "پاسارگاد"]
    cleared = client.patch(f"/api/suppliers/{sid}", json={"bank_accounts": []}, headers=headers)
    assert cleared.get_json()["data"]["bank_accounts"] == []
    # an edit that does not mention bank_accounts leaves them alone
    client.patch(f"/api/suppliers/{sid}", json={"bank_accounts": [{"bank_name": "ملت"}]}, headers=headers)
    other = client.patch(f"/api/suppliers/{sid}", json={"website": "https://x.example"}, headers=headers)
    assert len(other.get_json()["data"]["bank_accounts"]) == 1


def test_bank_account_fields_are_validated_when_filled(client, app, upload_dir):
    headers, _ = _staff(app, "read", "create")
    good_card, good_sheba = _luhn_card("603799189997123"), _sheba("0170000000123456789012")
    bad_card = good_card[:-1] + str((int(good_card[-1]) + 1) % 10)
    bad_sheba = good_sheba[:-1] + str((int(good_sheba[-1]) + 1) % 10)
    for field, value in [("card_number", bad_card), ("card_number", "1234"), ("sheba", bad_sheba),
                         ("sheba", "IR12"), ("account_number", "abc"), ("account_number", "12")]:
        r = client.post("/api/suppliers", json=_admin_payload(client, headers, bank_accounts=[{field: value}]), headers=headers)
        assert r.status_code == 400, (field, value)
        assert f"bank_accounts.0.{field}" in {d["field"] for d in r.get_json()["error"]["details"]}


def test_bank_accounts_are_not_written_to_the_audit_log_values(client, app, upload_dir):
    from app.core.audit_logs.models import AuditLog
    headers, _ = _staff(app, "read", "create", "update")
    sid = client.post("/api/suppliers", json=_admin_payload(client, headers), headers=headers).get_json()["data"]["id"]
    card = _luhn_card("603799189997123")
    client.patch(f"/api/suppliers/{sid}", json={"bank_accounts": [{"card_number": card}]}, headers=headers)
    with app.app_context():
        logs = db.session.query(AuditLog).filter_by(module="procurement", action="update").all()
        assert logs
        assert all(card not in str(l.event_metadata) for l in logs)  # only field NAMES are logged
        assert any("bank_accounts" in l.event_metadata["changed_fields"] for l in logs)
