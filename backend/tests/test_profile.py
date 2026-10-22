"""Tests for authenticated User Profile management (display name, profile photo, isolation)."""
import uuid
from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_user(name: str = "Test User") -> tuple[TestClient, dict, str]:
    c = _client()
    email = f"user-{uuid.uuid4()}@example.com"
    res = c.post(
        "/api/v1/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": "secure-password-123",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    return c, data["user"], data["access_token"]


# 1. Update display name successfully
def test_update_display_name_success():
    c, user, token = _register_user("Original Name")
    headers = _auth_headers(token)

    update_res = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Updated Name"},
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    data = update_res.json()
    assert data["full_name"] == "Updated Name"

    # Verify persistence via GET /auth/me
    me_res = c.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["full_name"] == "Updated Name"


# 2. Update profile photo and verify persistence
def test_update_profile_photo_success():
    c, user, token = _register_user("Photo Tester")
    headers = _auth_headers(token)
    sample_photo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

    update_res = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Photo Tester", "profile_photo": sample_photo},
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    data = update_res.json()
    assert data["profile_photo"] == sample_photo

    # Verify persistence via GET /auth/me
    me_res = c.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["profile_photo"] == sample_photo


# 3. Remove profile photo (sets to null)
def test_remove_profile_photo():
    c, user, token = _register_user("Remove Photo Tester")
    headers = _auth_headers(token)
    sample_photo = "data:image/png;base64,sample123"

    # Set photo
    c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Remove Photo Tester", "profile_photo": sample_photo},
        headers=headers,
    )

    # Remove photo
    remove_res = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Remove Photo Tester", "profile_photo": None},
        headers=headers,
    )
    assert remove_res.status_code == 200
    assert remove_res.json()["profile_photo"] is None

    # Verify persistence
    me_res = c.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["profile_photo"] is None


# 4. Validation: reject empty and excessively long display names
def test_display_name_validation():
    c, user, token = _register_user("Validation Tester")
    headers = _auth_headers(token)

    # Empty / whitespace only
    res_empty = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "   "},
        headers=headers,
    )
    assert res_empty.status_code == 422

    # Too short (< 2 characters)
    res_short = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "A"},
        headers=headers,
    )
    assert res_short.status_code == 422

    # Excessively long (> 100 characters)
    res_long = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "X" * 101},
        headers=headers,
    )
    assert res_long.status_code == 422


# 5. User isolation between Account A and Account B
def test_user_isolation_and_no_data_leakage():
    # User A
    cA, userA, tokenA = _register_user("User Alpha")
    photoA = "data:image/png;base64,alpha_photo"
    cA.patch(
        "/api/v1/auth/profile",
        json={"full_name": "User Alpha Custom", "profile_photo": photoA},
        headers=_auth_headers(tokenA),
    )

    # User B
    cB, userB, tokenB = _register_user("User Beta")
    photoB = "data:image/png;base64,beta_photo"
    cB.patch(
        "/api/v1/auth/profile",
        json={"full_name": "User Beta Custom", "profile_photo": photoB},
        headers=_auth_headers(tokenB),
    )

    # Verify User A still has User A's data
    meA = cA.get("/api/v1/auth/me", headers=_auth_headers(tokenA)).json()
    assert meA["full_name"] == "User Alpha Custom"
    assert meA["email"] == userA["email"]
    assert meA["profile_photo"] == photoA

    # Verify User B has User B's data
    meB = cB.get("/api/v1/auth/me", headers=_auth_headers(tokenB)).json()
    assert meB["full_name"] == "User Beta Custom"
    assert meB["email"] == userB["email"]
    assert meB["profile_photo"] == photoB

    # User B removes photo -> User A's photo must remain unchanged
    cB.patch(
        "/api/v1/auth/profile",
        json={"full_name": "User Beta Custom", "profile_photo": None},
        headers=_auth_headers(tokenB),
    )

    meB_after = cB.get("/api/v1/auth/me", headers=_auth_headers(tokenB)).json()
    assert meB_after["profile_photo"] is None

    meA_after = cA.get("/api/v1/auth/me", headers=_auth_headers(tokenA)).json()
    assert meA_after["profile_photo"] == photoA


# 6. Unauthenticated update is rejected
def test_unauthenticated_profile_update_rejected():
    c = _client()
    res = c.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Hacker Name"},
    )
    assert res.status_code == 401
