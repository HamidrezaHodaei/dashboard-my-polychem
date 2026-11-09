"""
Phase 0 test suite — application startup, health endpoint, error envelope
shape, request ID propagation, and CORS configuration.

Deliberately does not require a live MySQL server (see TestingConfig in
app/config.py) — these tests validate the application foundation itself.
"""
import json


# 1. Application startup
def test_app_starts_and_has_expected_config(app):
    assert app is not None
    assert app.config["TESTING"] is True


# 2 & 3. GET /api/health + response structure
def test_health_endpoint_returns_success_envelope(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["status"] in ("ok", "degraded")
    assert "database" in body["data"]


# 4. 404 returns JSON in the standard error envelope
def test_404_returns_json_error_envelope(client):
    response = client.get("/api/this-route-does-not-exist")
    assert response.status_code == 404
    assert response.content_type.startswith("application/json")

    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


# 5. 405 returns JSON in the standard error envelope
def test_405_returns_json_error_envelope(client):
    # /api/health only supports GET
    response = client.post("/api/health")
    assert response.status_code == 405
    assert response.content_type.startswith("application/json")

    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"


# 6. X-Request-ID exists, and is preserved if supplied by the client
def test_request_id_header_present_and_generated(client):
    response = client.get("/api/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_header_is_preserved_when_supplied(client):
    custom_id = "test-correlation-id-123"
    response = client.get("/api/health", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id


# 7 & 8. CORS allows localhost:3000, never wildcard
def test_cors_allows_configured_local_origin(client):
    response = client.get(
        "/api/health", headers={"Origin": "http://localhost:3000"}
    )
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_cors_does_not_use_wildcard(client):
    response = client.get(
        "/api/health", headers={"Origin": "http://localhost:3000"}
    )
    assert response.headers.get("Access-Control-Allow-Origin") != "*"

    # An origin that was never configured must not be reflected back.
    response_other = client.get(
        "/api/health", headers={"Origin": "http://evil.example.com"}
    )
    assert response_other.headers.get("Access-Control-Allow-Origin") != "http://evil.example.com"
    assert response_other.headers.get("Access-Control-Allow-Origin") != "*"


# Bonus: unhandled exceptions never leak internals to the client
def test_unexpected_error_does_not_leak_internals(app, client):
    @app.route("/api/__boom")
    def _boom():
        raise RuntimeError("sensitive internal detail: db password=hunter2")

    response = client.get("/api/__boom")
    assert response.status_code == 500

    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    raw_text = json.dumps(body)
    assert "hunter2" not in raw_text
    assert "RuntimeError" not in raw_text
