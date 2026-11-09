"""Per-user / per-role permission matrix + allow/deny merge rules."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from app.permissions.matrix import ensure_registry_permissions
from app.permissions.service import has_permission
from tests.core4.factories import (
    assign_role,
    auth_headers,
    grant_role_permission,
    make_role,
    make_user,
)


def _admin(app_keys=("core.user.read", "core.user.update", "core.permission.update",
                     "core.role.read", "core.role.update", "crm.customer.read",
                     "crm.customer.create", "crm.customer.update", "crm.customer.delete",
                     "finance.transaction.read")):
    perms = ensure_registry_permissions()
    admin = make_user()
    role = make_role()
    assign_role(admin, role)
    for key in app_keys:
        grant_role_permission(role, perms[key], ScopeType.GLOBAL)
    return admin


def test_role_matrix_roundtrip_enforced(client, app):
    with app.app_context():
        admin = _admin()
        target_role = make_role()
        member = make_user()
        assign_role(member, target_role)
        db.session.commit()
        h, rid, mid = auth_headers(admin), target_role.id, member.id

    r = client.put(f"/api/core/roles/{rid}/permission-matrix", headers=h,
                   json={"cells": {"crm.customer": {"read": True, "create": True}}})
    assert r.status_code == 200
    cell = r.get_json()["data"]["cells"]["crm.customer"]
    assert cell["read"]["granted"] and cell["create"]["granted"] and not cell["delete"]["granted"]

    with app.app_context():
        from app.core.users.models import User
        m = db.session.get(User, mid)
        assert has_permission(m, "crm.customer.read")
        assert not has_permission(m, "crm.customer.delete")

    r = client.put(f"/api/core/roles/{rid}/permission-matrix", headers=h,
                   json={"cells": {"crm.customer": {"read": False}}})
    assert not r.get_json()["data"]["cells"]["crm.customer"]["read"]["granted"]
    with app.app_context():
        from app.core.users.models import User
        assert not has_permission(db.session.get(User, mid), "crm.customer.read")


def test_user_deny_overrides_role_and_allow_adds(client, app):
    with app.app_context():
        admin = _admin()
        role = make_role()
        perms = ensure_registry_permissions()
        grant_role_permission(role, perms["crm.customer.read"], ScopeType.GLOBAL)
        user = make_user()
        assign_role(user, role)
        db.session.commit()
        h, uid = auth_headers(admin), user.id

    # Role grants read -> user matrix shows it as inherited
    r = client.get(f"/api/core/users/{uid}/permission-matrix", headers=h)
    c = r.get_json()["data"]["cells"]["crm.customer"]
    assert c["read"]["effective"] and c["read"]["from_role"]

    # Deny read, allow delete (not in role)
    r = client.put(f"/api/core/users/{uid}/permission-matrix", headers=h,
                   json={"cells": {"crm.customer": {"read": False, "delete": True}}})
    assert r.status_code == 200
    c = r.get_json()["data"]["cells"]["crm.customer"]
    assert not c["read"]["effective"] and c["read"]["direct"] == "DENY"
    assert c["delete"]["effective"] and c["delete"]["direct"] == "ALLOW"

    with app.app_context():
        from app.core.users.models import User
        u = db.session.get(User, uid)
        assert not has_permission(u, "crm.customer.read")      # deny wins over role
        assert has_permission(u, "crm.customer.delete")        # direct allow

    # Lift deny -> role grant applies again
    r = client.put(f"/api/core/users/{uid}/permission-matrix", headers=h,
                   json={"cells": {"crm.customer": {"read": True}}})
    assert r.get_json()["data"]["cells"]["crm.customer"]["read"]["effective"]


def test_matrix_guards(client, app):
    with app.app_context():
        admin = _admin()
        limited = make_user()
        role = make_role()
        assign_role(limited, role)
        perms = ensure_registry_permissions()
        for k in ("core.user.read", "core.user.update"):
            grant_role_permission(role, perms[k], ScopeType.GLOBAL)  # no core.permission.update
        victim = make_user()
        db.session.commit()
        ha, hl, vid, aid = auth_headers(admin), auth_headers(limited), victim.id, admin.id

    body = {"cells": {"crm.customer": {"read": True}}}
    assert client.put(f"/api/core/users/{vid}/permission-matrix", headers=hl, json=body).status_code == 403
    assert client.put(f"/api/core/users/{aid}/permission-matrix", headers=ha, json=body).status_code == 403  # self
    # admin does not hold finance.transaction.update -> cannot grant it (no escalation)
    r = client.put(f"/api/core/users/{vid}/permission-matrix", headers=ha,
                   json={"cells": {"finance.transaction": {"update": True}}})
    assert r.status_code == 403
    assert client.put(f"/api/core/users/{vid}/permission-matrix", headers=ha,
                      json={"cells": {"nope.module": {"read": True}}}).status_code == 409


def test_list_users_include_inactive_and_search(client, app):
    with app.app_context():
        admin = _admin()
        inactive = make_user(full_name="Zed Inactive", is_active=False)
        db.session.commit()
        h, iid = auth_headers(admin), inactive.id
    ids = {u["id"] for u in client.get("/api/core/users", headers=h).get_json()["data"]}
    assert iid not in ids
    r = client.get("/api/core/users?include_inactive=true&q=zed", headers=h)
    assert [u["id"] for u in r.get_json()["data"]] == [iid]
