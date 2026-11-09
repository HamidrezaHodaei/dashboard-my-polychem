"""Own password, profile photo, roles in /api/me, admin password reset."""
import base64

from app.core.auth import services as auth_services
from app.extensions import db
from tests.auth.factories import DEFAULT_PASSWORD, login, make_user
from tests.core4.factories import assign_role, auth_headers, grant_user_permission, make_permission, make_role
from app.core.authorization.models import ScopeType

# a real 1x1 PNG
PNG = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
).decode()


def test_me_returns_roles_and_photo_from_the_database(client):
    user = make_user()
    role = make_role(name="sales_manager", display_name="مدیر فروش")
    assign_role(user, role)
    db.session.commit()
    me = client.get("/api/me", headers=auth_headers(user)).get_json()["data"]
    assert me["full_name"] == user.full_name and me["email"] == user.email and me["username"] == user.username
    assert me["roles"] == [{"name": "sales_manager", "display_name": "مدیر فروش"}]
    assert me["avatar"] is None and "bio" not in me and "password_hash" not in me


def test_user_changes_own_photo_only_with_a_valid_image(client):
    user = make_user()
    h = auth_headers(user)
    r = client.put("/api/me/avatar", json={"image": PNG}, headers=h)
    assert r.status_code == 200 and r.get_json()["data"]["avatar"] == PNG
    assert client.get("/api/me", headers=h).get_json()["data"]["avatar"] == PNG
    svg = "data:image/svg+xml;base64," + base64.b64encode(b"<svg onload=alert(1)>").decode()
    assert client.put("/api/me/avatar", json={"image": svg}, headers=h).status_code == 409
    fake = "data:image/png;base64," + base64.b64encode(b"not a png at all, just text bytes").decode()
    assert client.put("/api/me/avatar", json={"image": fake}, headers=h).status_code == 409
    assert client.delete("/api/me/avatar", headers=h).get_json()["data"]["avatar"] is None


def test_user_changes_own_password(client):
    user = make_user()
    h = auth_headers(user)
    url = "/api/auth/change-password"
    assert client.post(url, json={"current_password": "wrong", "new_password": "N3w-Passw0rd!"}, headers=h).status_code == 409
    assert client.post(url, json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD}, headers=h).status_code == 409
    assert client.post(url, json={"current_password": DEFAULT_PASSWORD, "new_password": "short"}, headers=h).status_code == 400
    r = client.post(url, json={"current_password": DEFAULT_PASSWORD, "new_password": "N3w-Passw0rd!"}, headers=h)
    assert r.status_code == 200
    assert login(client, user.username, "N3w-Passw0rd!").status_code == 200
    assert login(client, user.username, DEFAULT_PASSWORD).status_code == 401
    assert client.post(url, json={"current_password": "x", "new_password": "N3w-Passw0rd!"}).status_code == 401  # signed in only


def test_only_an_admin_sets_another_users_password(client):
    admin, editor, target = make_user(), make_user(), make_user()
    assign_role(admin, make_role(name="admin", display_name="مدیر سیستم"))
    grant_user_permission(editor, make_permission("core.user.update"), ScopeType.GLOBAL, None)
    db.session.commit()
    url = f"/api/core/users/{target.id}/password"
    body = {"new_password": "Reset-Passw0rd!"}
    assert client.post(url, json=body, headers=auth_headers(editor)).status_code == 403   # delegated edit is not enough
    assert client.post(url, json={"new_password": "short"}, headers=auth_headers(admin)).status_code == 400
    assert client.post(url, json=body, headers=auth_headers(admin)).status_code == 200
    assert login(client, target.username, "Reset-Passw0rd!").status_code == 200
    assert login(client, target.username, DEFAULT_PASSWORD).status_code == 401
