"""End-to-end multi-account verification for Edit Profile:
A. Log in as User A, change name and photo, save, refresh (re-fetch), and log in again.
B. Log out and log in as User B.
C. Verify User B sees their own name, email, and photo—not User A's.
D. Change User B's photo and confirm User A's photo remains unchanged.
E. Test Remove Photo and verify it affects only the current account.
"""
import uuid
from fastapi.testclient import TestClient

from app.main import app


def test_full_two_account_profile_lifecycle_and_switching():
    client = TestClient(app)

    # 1. Setup credentials for User A and User B
    email_a = f"usera-{uuid.uuid4()}@example.com"
    email_b = f"userb-{uuid.uuid4()}@example.com"
    password = "SecurePassword-123!"

    # A1. Register and Log in as User A
    res_reg_a = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Original Name A",
            "email": email_a,
            "password": password,
        },
    )
    assert res_reg_a.status_code == 201
    token_a = res_reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Initial profile check for User A
    me_a_initial = client.get("/api/v1/auth/me", headers=headers_a).json()
    assert me_a_initial["full_name"] == "Original Name A"
    assert me_a_initial["email"] == email_a
    assert me_a_initial["profile_photo"] is None

    # A2. User A changes name and photo, then saves
    photo_a = "data:image/png;base64,UserAPhotoData123456789"
    update_a = client.patch(
        "/api/v1/auth/profile",
        json={
            "full_name": "Adithya Updated Name",
            "profile_photo": photo_a,
        },
        headers=headers_a,
    )
    assert update_a.status_code == 200
    assert update_a.json()["full_name"] == "Adithya Updated Name"
    assert update_a.json()["profile_photo"] == photo_a

    # A3. Refresh (re-fetching /auth/me with User A's session)
    refresh_a = client.get("/api/v1/auth/me", headers=headers_a)
    assert refresh_a.status_code == 200
    me_a_refreshed = refresh_a.json()
    assert me_a_refreshed["full_name"] == "Adithya Updated Name"
    assert me_a_refreshed["email"] == email_a
    assert me_a_refreshed["profile_photo"] == photo_a

    # A4. User A logs in again via /login and gets refreshed JWT
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": email_a, "password": password},
    )
    assert login_a.status_code == 200
    token_a_new = login_a.json()["access_token"]
    assert login_a.json()["user"]["full_name"] == "Adithya Updated Name"
    assert login_a.json()["user"]["profile_photo"] == photo_a

    # B. Log out User A (drop session), and register/login as User B
    res_reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Original Name B",
            "email": email_b,
            "password": password,
        },
    )
    assert res_reg_b.status_code == 201
    token_b = res_reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # C. Verify User B sees their own name, email, and photo—NOT User A's
    me_b = client.get("/api/v1/auth/me", headers=headers_b).json()
    assert me_b["email"] == email_b
    assert me_b["full_name"] == "Original Name B"
    assert me_b["profile_photo"] is None
    assert me_b["full_name"] != "Adithya Updated Name"
    assert me_b["profile_photo"] != photo_a

    # D. Change User B's photo and name, confirm User A's profile remains unchanged
    photo_b = "data:image/png;base64,UserBPhotoData987654321"
    update_b = client.patch(
        "/api/v1/auth/profile",
        json={
            "full_name": "User B Custom",
            "profile_photo": photo_b,
        },
        headers=headers_b,
    )
    assert update_b.status_code == 200
    assert update_b.json()["full_name"] == "User B Custom"
    assert update_b.json()["profile_photo"] == photo_b

    # Confirm User A's profile is completely unchanged
    headers_a_new = {"Authorization": f"Bearer {token_a_new}"}
    me_a_check = client.get("/api/v1/auth/me", headers=headers_a_new).json()
    assert me_a_check["full_name"] == "Adithya Updated Name"
    assert me_a_check["email"] == email_a
    assert me_a_check["profile_photo"] == photo_a

    # E. Test Remove Photo for User B and verify it affects only User B
    remove_b = client.patch(
        "/api/v1/auth/profile",
        json={
            "full_name": "User B Custom",
            "profile_photo": None,
        },
        headers=headers_b,
    )
    assert remove_b.status_code == 200
    assert remove_b.json()["profile_photo"] is None

    # Verify User B's photo is removed (restored to default initials/avatar)
    me_b_final = client.get("/api/v1/auth/me", headers=headers_b).json()
    assert me_b_final["profile_photo"] is None
    assert me_b_final["full_name"] == "User B Custom"

    # Verify User A's photo is STILL intact!
    me_a_final = client.get("/api/v1/auth/me", headers=headers_a_new).json()
    assert me_a_final["profile_photo"] == photo_a
    assert me_a_final["full_name"] == "Adithya Updated Name"
