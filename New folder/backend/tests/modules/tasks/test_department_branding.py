"""Worklist (کارتابل واحد) pictures: admin-only writes, the same picture for the whole unit."""
import io

import pytest

from app.core.authorization.models import ScopeType
from app.core.permissions.models import Permission
from app.extensions import db
from tests.core4.factories import (
    assign_role, auth_headers, grant_user_permission, make_department, make_organization,
    make_permission, make_role, make_user,
)

API = "/api/tasks"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _read(user):
    perm = db.session.query(Permission).filter_by(key="tasks.task.read").first() or make_permission("tasks.task.read")
    grant_user_permission(user, perm, ScopeType.GLOBAL)


@pytest.fixture(autouse=True)
def _upload_dir(app, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)


@pytest.fixture
def world(app):
    with app.app_context():
        org = make_organization()
        a, b = make_department(org), make_department(org)
        admin, a1, a2, b1 = make_user(), make_user(), make_user(), make_user()
        a1.department_id = a2.department_id = a.id
        b1.department_id = b.id
        admin.department_id = b.id
        assign_role(admin, make_role(name="admin", display_name="Admin"))
        for u in (admin, a1, a2, b1):
            _read(u)
        db.session.commit()
        return {"a": a.id, "b": b.id, "h": {n: auth_headers(u) for n, u in
                                              {"admin": admin, "a1": a1, "a2": a2, "b1": b1}.items()}}


def _put(client, world, who, dept, kind, data=PNG, name="x.png"):
    return client.put(
        f"{API}/departments/{world[dept]}/branding/{kind}",
        data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data", headers=world["h"][who],
    )


def test_only_admin_can_change_a_picture(client, world):
    assert _put(client, world, "a1", "a", "logo").status_code == 403
    assert _put(client, world, "admin", "a", "logo").status_code == 200
    r = client.delete(f"{API}/departments/{world['a']}/branding/logo", headers=world["h"]["a1"])
    assert r.status_code == 403


def test_every_member_of_the_unit_gets_the_same_picture_and_other_units_do_not(client, world):
    assert _put(client, world, "admin", "a", "logo").status_code == 200
    assert _put(client, world, "admin", "a", "header").status_code == 200
    for who in ("a1", "a2", "admin"):
        for kind in ("logo", "header"):
            r = client.get(f"{API}/departments/{world['a']}/branding/{kind}", headers=world["h"][who])
            assert r.status_code == 200 and r.data == PNG and r.mimetype == "image/png"
    assert client.get(f"{API}/departments/{world['a']}/branding/logo", headers=world["h"]["b1"]).status_code == 403
    meta = client.get(f"{API}/meta", headers=world["h"]["a2"]).get_json()["data"]
    dept = next(d for d in meta["departments"] if d["id"] == world["a"])
    assert dept["has_logo"] and dept["has_header"] and dept["branding_version"] == 2


def test_replace_and_remove(client, world):
    _put(client, world, "admin", "a", "logo")
    other = PNG + b"\x01"
    assert _put(client, world, "admin", "a", "logo", data=other).get_json()["data"]["branding_version"] == 2
    assert client.get(f"{API}/departments/{world['a']}/branding/logo", headers=world["h"]["a1"]).data == other
    r = client.delete(f"{API}/departments/{world['a']}/branding/logo", headers=world["h"]["admin"])
    assert r.status_code == 200 and r.get_json()["data"]["has_logo"] is False
    assert client.get(f"{API}/departments/{world['a']}/branding/logo", headers=world["h"]["a1"]).status_code == 404


def test_only_real_raster_pictures_are_accepted(client, world):
    assert _put(client, world, "admin", "a", "logo", data=b"<svg onload=alert(1)/>", name="x.svg").status_code == 400
    assert _put(client, world, "admin", "a", "logo", data=b"not an image", name="x.png").status_code == 400
    assert _put(client, world, "admin", "a", "banner").status_code == 404
