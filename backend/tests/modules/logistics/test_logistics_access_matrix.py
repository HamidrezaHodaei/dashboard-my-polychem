"""Logistics rows in the per-role / per-user permission matrix (including the `review` column)."""
from app.core.authorization.models import ScopeType
from app.core.users.models import User
from app.extensions import db
from app.permissions.matrix import ensure_registry_permissions
from app.permissions.service import has_permission
from tests.core4.factories import assign_role, auth_headers, grant_role_permission, make_role, make_user
from tests.modules.logistics.test_logistics import company_body, driver_body

KEYS = (
    "core.user.read", "core.user.update", "core.permission.update", "core.role.read", "core.role.update",
    "logistics.company.read", "logistics.company.review", "logistics.company.update",
    "logistics.driver.read", "logistics.driver.review",
)


def _admin():
    perms = ensure_registry_permissions()
    admin, role = make_user(), make_role()
    assign_role(admin, role)
    for key in KEYS:
        grant_role_permission(role, perms[key], ScopeType.GLOBAL)
    return admin


def test_only_logistics_rows_expose_review(client, app):
    with app.app_context():
        admin = _admin()
        target = make_user()
        db.session.commit()
        h, uid = auth_headers(admin), target.id
    mods = {m["key"]: m["actions"] for m in
            client.get(f"/api/core/users/{uid}/permission-matrix", headers=h).get_json()["data"]["modules"]}
    assert mods["logistics.company"] == ["read", "create", "update", "delete", "review"]
    assert mods["logistics.driver"] == ["read", "create", "update", "delete", "review"]
    assert mods["procurement.supplier"] == ["read", "create", "update", "delete"]
    # review is not a valid cell for other rows
    r = client.put(f"/api/core/users/{uid}/permission-matrix", headers=h,
                   json={"cells": {"crm.customer": {"review": True}}})
    assert r.status_code == 409


def test_user_matrix_sets_logistics_access_per_user_and_per_type(client, app):
    with app.app_context():
        admin = _admin()
        a, b = make_user(), make_user()
        db.session.commit()
        h, aid, bid = auth_headers(admin), a.id, b.id

    # user A: read + review on drivers only; user B: read companies only
    r = client.put(f"/api/core/users/{aid}/permission-matrix", headers=h,
                   json={"cells": {"logistics.driver": {"read": True, "review": True}}})
    assert r.status_code == 200
    cell = r.get_json()["data"]["cells"]["logistics.driver"]
    assert cell["review"]["effective"] and cell["review"]["direct"] == "ALLOW"
    r = client.put(f"/api/core/users/{bid}/permission-matrix", headers=h,
                   json={"cells": {"logistics.company": {"read": True}}})
    assert r.status_code == 200

    with app.app_context():
        ua, ub = db.session.get(User, aid), db.session.get(User, bid)
        assert has_permission(ua, "logistics.driver.review") and not has_permission(ua, "logistics.company.read")
        assert has_permission(ub, "logistics.company.read") and not has_permission(ub, "logistics.company.review")
        ha, hb = auth_headers(ua), auth_headers(ub)

    c_id = client.post("/api/logistics/public/register", json=company_body()).get_json()["data"]["id"]
    d_id = client.post("/api/logistics/public/register", json=driver_body()).get_json()["data"]["id"]
    # A may review the driver, but cannot even see the company
    assert client.post(f"/api/logistics/applicants/{d_id}/review", json={"action": "APPROVE"}, headers=ha).status_code == 200
    assert client.get(f"/api/logistics/applicants/{c_id}", headers=ha).status_code == 403
    # B sees companies, cannot review them, and has no access to drivers
    assert client.get(f"/api/logistics/applicants/{c_id}", headers=hb).status_code == 200
    assert client.post(f"/api/logistics/applicants/{c_id}/review", json={"action": "APPROVE"}, headers=hb).status_code == 403
    assert client.get(f"/api/logistics/applicants/{d_id}", headers=hb).status_code == 403

    # a per-user DENY removes review again, even though it was granted directly
    client.put(f"/api/core/users/{aid}/permission-matrix", headers=h,
               json={"cells": {"logistics.driver": {"review": False}}})
    assert client.post(f"/api/logistics/applicants/{d_id}/review", json={"action": "SUSPEND", "note": "ناقص"},
                       headers=ha).status_code == 403


def test_role_matrix_covers_logistics_review(client, app):
    with app.app_context():
        admin = _admin()
        role = make_role()
        member = make_user()
        assign_role(member, role)
        db.session.commit()
        h, rid, mid = auth_headers(admin), role.id, member.id
    r = client.put(f"/api/core/roles/{rid}/permission-matrix", headers=h,
                   json={"cells": {"logistics.company": {"read": True, "review": True}}})
    assert r.status_code == 200
    assert r.get_json()["data"]["cells"]["logistics.company"]["review"]["granted"]
    with app.app_context():
        assert has_permission(db.session.get(User, mid), "logistics.company.review")
