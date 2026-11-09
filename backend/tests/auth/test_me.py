"""GET /api/me tests -- separate from test_jwt.py, which covers token
validation; this file locks the exact response field contract."""
from .factories import login, make_user


def test_me_unauthenticated_returns_401(client, app):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_returns_exactly_the_approved_safe_fields(client, app):
    make_user(username="wendy", email="wendy@example.com")
    token = login(client, "wendy").get_json()["data"]["access_token"]

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()["data"]

    expected_keys = {
        "id",
        "full_name",
        "email",
        "username",
        "organization_id",
        "department_id",
        "is_active",
        "last_login_at",
    }
    assert set(data.keys()) == expected_keys
    assert data["username"] == "wendy"
    assert data["is_active"] is True


def test_me_never_leaks_password_hash_or_token_data(client, app):
    make_user(username="xavier", email="xavier@example.com")
    token = login(client, "xavier").get_json()["data"]["access_token"]

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    body_text = response.get_data(as_text=True)

    assert "password_hash" not in body_text
    assert "refresh_token" not in body_text
    assert "token_hash" not in body_text
