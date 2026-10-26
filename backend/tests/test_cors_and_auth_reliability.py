"""Comprehensive tests for CORS preflight, origin validation, authentication reliability, and memory safety."""
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app, resolve_cors_origins


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# 1. Application startup and health check
def test_app_health_endpoint(client: TestClient):
    """Verify application starts and /health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


# 2. CORS Preflight OPTIONS for all production and development origins
@pytest.mark.parametrize(
    "origin",
    [
        "https://term-shield.in",
        "https://www.term-shield.in",
        "https://term-shield-ten.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
def test_preflight_registration_allowed_origins(client: TestClient, origin: str):
    """Verify that legitimate preflight OPTIONS requests for /api/v1/auth/register return 200 OK

    with correct Access-Control-Allow-Origin, Methods, and Headers.
    """
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type, authorization",
    }
    response = client.options("/api/v1/auth/register", headers=headers)

    assert response.status_code == 200, f"Preflight failed for allowed origin {origin}: {response.text}"
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "OPTIONS" in allow_methods


# 3. Disallowed origin CORS preflight rejection
def test_preflight_disallowed_origin_rejected(client: TestClient):
    """Verify that unknown/disallowed origin preflight requests return 400 Bad Request

    and do NOT grant access to the requested origin.
    """
    disallowed_origin = "https://unauthorized-malicious-domain.com"
    headers = {
        "Origin": disallowed_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/v1/auth/register", headers=headers)

    # Starlette CORSMiddleware rejects disallowed origins on preflight with 400 PlainTextResponse
    assert response.status_code == 400
    assert "Disallowed CORS" in response.text
    assert response.headers.get("access-control-allow-origin") is None


# 4. Disallowed origin actual request does not receive CORS header
def test_actual_request_disallowed_origin_no_cors_headers(client: TestClient):
    """Verify that non-preflight requests from disallowed origins do not get Access-Control-Allow-Origin."""
    disallowed_origin = "https://unauthorized-malicious-domain.com"
    response = client.get("/health", headers={"Origin": disallowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


# 5. Normalization of configured origins (trailing slashes, comma-separated lists)
def test_resolve_cors_origins_normalization():
    """Verify origin normalization strips trailing slashes, trims whitespace, and rejects wildcards."""
    class DummySettings:
        cors_origins = " https://term-shield.in/ , https://preview-deploy.vercel.app/ , * , invalid "
        frontend_url = "https://custom-portal.in/"

    resolved = resolve_cors_origins(DummySettings())

    assert "https://term-shield.in" in resolved
    assert "https://term-shield.in/" not in resolved
    assert "https://preview-deploy.vercel.app" in resolved
    assert "https://preview-deploy.vercel.app/" not in resolved
    assert "https://custom-portal.in" in resolved
    assert "https://custom-portal.in/" not in resolved
    assert "*" not in resolved
    assert "invalid" not in resolved


# 6. Input validation on registration
@pytest.mark.parametrize(
    "invalid_payload,expected_err_field",
    [
        ({"full_name": "A", "email": "valid@example.com", "password": "password123"}, "full_name"),
        ({"full_name": "Valid Name", "email": "not-an-email", "password": "password123"}, "email"),
        ({"full_name": "Valid Name", "email": "valid@example.com", "password": "short"}, "password"),
        ({"email": "valid@example.com", "password": "password123"}, "full_name"),
    ],
)
def test_registration_validation_errors(client: TestClient, invalid_payload: dict, expected_err_field: str):
    """Verify Pydantic schema validation cleanly rejects invalid registration payloads."""
    response = client.post("/api/v1/auth/register", json=invalid_payload)
    assert response.status_code == 422
    details = str(response.json()["detail"])
    assert expected_err_field in details


# 7. Duplicate registrations safely return 409
def test_duplicate_registration_handled_safely(client: TestClient):
    """Verify duplicate account creation returns a 409 conflict error."""
    unique_email = f"cors-test-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Unique User",
        "email": unique_email,
        "password": "secure-password-123",
    }

    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Email is already registered"


# 8. Login success and invalid credentials handling
def test_login_success_and_invalid_credentials(client: TestClient):
    """Verify login succeeds for valid accounts and returns clean 401 for invalid credentials."""
    email = f"login-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "valid-password-123"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Login User", "email": email, "password": password},
    )
    assert reg_resp.status_code == 201

    # Successful login
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"]
    assert login_resp.json()["user"]["email"] == email

    # Invalid password
    bad_pw_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
    assert bad_pw_resp.status_code == 401
    assert bad_pw_resp.json()["detail"] == "Invalid email or password"

    # Nonexistent email
    bad_email_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": password},
    )
    assert bad_email_resp.status_code == 401
    assert bad_email_resp.json()["detail"] == "Invalid email or password"


# 9. Database connection failure returns controlled response
def test_registration_database_failure_returns_controlled_response(client: TestClient):
    """Verify database failures during registration rollback cleanly and return controlled 500 without leaking traces."""
    unique_email = f"db-fail-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "DB Fail User",
        "email": unique_email,
        "password": "secure-password-123",
    }

    with patch("sqlalchemy.ext.asyncio.AsyncSession.commit", side_effect=RuntimeError("Simulated database connection failure")):
        response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 500
    assert "Unable to complete registration" in response.json()["detail"]
    # Verify internal DB stack trace is never exposed
    assert "Simulated database connection failure" not in response.json()["detail"]
