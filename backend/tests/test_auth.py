"""Focused tests for the authentication endpoints (register / login / me)."""
import uuid

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _email() -> str:
    return f"auth-{uuid.uuid4()}@example.com"


def _register_payload(email: str | None = None) -> dict:
    return {
        "full_name": "Auth Test User",
        "email": email or _email(),
        "password": "secure-password-123",
    }


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# 1. Successful registration
def test_register_success():
    c = _client()
    response = c.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"]
    assert data["user"]["full_name"] == "Auth Test User"
    assert "hashed_password" not in data["user"]


# 2. Duplicate email registration
def test_register_duplicate_email():
    c = _client()
    payload = _register_payload()

    first = c.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    duplicate = c.post("/api/v1/auth/register", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email is already registered"


# 3. Successful login
def test_login_success():
    c = _client()
    payload = _register_payload()

    register = c.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201

    login = c.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert login.status_code == 200, login.text

    data = login.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]


# 4. Invalid password login
def test_login_invalid_password():
    c = _client()
    payload = _register_payload()

    register = c.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201

    login = c.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": "wrong-password-999",
        },
    )

    assert login.status_code == 401
    assert login.json()["detail"] == "Invalid email or password"


# 5. GET /auth/me with a valid token
def test_me_with_valid_token():
    c = _client()
    register = c.post("/api/v1/auth/register", json=_register_payload())

    assert register.status_code == 201

    token = register.json()["access_token"]

    me = c.get("/api/v1/auth/me", headers=_auth_headers(token))

    assert me.status_code == 200

    data = me.json()

    assert data["email"] == register.json()["user"]["email"]
    assert data["full_name"] == "Auth Test User"
    assert "hashed_password" not in data


# 6. GET /auth/me without a token
def test_me_without_token():
    c = _client()

    me = c.get("/api/v1/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Authentication required"
    assert me.headers.get("www-authenticate") == "Bearer"


# 7. GET /auth/me with an invalid / expired token
def test_me_with_invalid_token():
    c = _client()

    me = c.get(
        "/api/v1/auth/me",
        headers=_auth_headers("not-a-real-jwt-token"),
    )

    assert me.status_code == 401
    assert me.json()["detail"] == "Invalid or expired authentication token"
