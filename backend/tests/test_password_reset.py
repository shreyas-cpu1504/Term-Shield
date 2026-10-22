import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def _client() -> TestClient:
    return TestClient(app)


def _unique_email() -> str:
    return f"reset-test-{uuid.uuid4()}@example.com"


def _register_user(client: TestClient, email: str, password: str = "InitialPassword123!") -> dict:
    payload = {
        "full_name": "Reset Test User",
        "email": email,
        "password": password,
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# 1. forgot-password existing email
def test_forgot_password_existing_email():
    c = _client()
    email = _unique_email()
    _register_user(c, email)

    with patch("app.api.v1.auth.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = c.post("/api/v1/auth/forgot-password", json={"email": email})

        assert response.status_code == 200
        data = response.json()
        assert "If an account exists for this email" in data["message"]
        assert mock_send.await_count == 1
        call_args = mock_send.await_args
        assert call_args.kwargs["to_email"] == email
        assert len(call_args.kwargs["reset_token"]) > 20


# 2. forgot-password non-existing email
def test_forgot_password_non_existing_email():
    c = _client()
    non_existing = f"ghost-{uuid.uuid4()}@example.com"

    with patch("app.api.v1.auth.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        response = c.post("/api/v1/auth/forgot-password", json={"email": non_existing})

        assert response.status_code == 200
        data = response.json()
        assert "If an account exists for this email" in data["message"]
        assert mock_send.await_count == 0


# 3. same external response for both existing and non-existing
def test_same_external_response_for_both():
    c = _client()
    email = _unique_email()
    _register_user(c, email)
    non_existing = f"ghost-{uuid.uuid4()}@example.com"

    with patch("app.api.v1.auth.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        resp_existing = c.post("/api/v1/auth/forgot-password", json={"email": email})
        resp_non_existing = c.post("/api/v1/auth/forgot-password", json={"email": non_existing})

        assert resp_existing.status_code == resp_non_existing.status_code == 200
        assert resp_existing.json() == resp_non_existing.json()


# 4 & 5. reset token generated, saved, and raw token NOT stored
@pytest.mark.asyncio
async def test_reset_token_generated_and_raw_token_not_stored():
    c = _client()
    email = _unique_email()
    _register_user(c, email)

    captured_raw_token = None

    async def fake_send(to_email: str, reset_token: str):
        nonlocal captured_raw_token
        captured_raw_token = reset_token
        return True

    with patch("app.api.v1.auth.send_password_reset_email", side_effect=fake_send):
        resp = c.post("/api/v1/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200

    assert captured_raw_token is not None
    expected_hash = hashlib.sha256(captured_raw_token.encode("utf-8")).hexdigest()

    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.email == email))
        user = user_res.scalar_one()

        token_res = await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        tokens = token_res.scalars().all()

        assert len(tokens) >= 1
        token_record = tokens[-1]

        # Raw token MUST NOT be stored
        assert token_record.token_hash != captured_raw_token
        # Token hash MUST match SHA-256 hash
        assert token_record.token_hash == expected_hash
        assert token_record.used_at is None
        exp = token_record.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        assert exp > datetime.now(timezone.utc)


# 6, 10, 11. valid token resets password, old password fails, new password works
def test_valid_token_resets_password_flow():
    c = _client()
    email = _unique_email()
    old_pw = "OldPassword123!"
    new_pw = "BrandNewPassword456!"
    _register_user(c, email, old_pw)

    captured_token = None

    async def fake_send(to_email: str, reset_token: str):
        nonlocal captured_token
        captured_token = reset_token
        return True

    with patch("app.api.v1.auth.send_password_reset_email", side_effect=fake_send):
        c.post("/api/v1/auth/forgot-password", json={"email": email})

    assert captured_token is not None

    # Reset password with valid token
    reset_resp = c.post(
        "/api/v1/auth/reset-password",
        json={"token": captured_token, "new_password": new_pw},
    )
    assert reset_resp.status_code == 200
    assert "Password reset successfully" in reset_resp.json()["message"]

    # 10. Old password fails
    old_login = c.post("/api/v1/auth/login", json={"email": email, "password": old_pw})
    assert old_login.status_code == 401

    # 11. New password succeeds
    new_login = c.post("/api/v1/auth/login", json={"email": email, "password": new_pw})
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


# 7. invalid token rejected
def test_invalid_token_rejected():
    c = _client()
    resp = c.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally-bogus-token-xyz", "new_password": "ValidPassword999!"},
    )
    assert resp.status_code == 400
    assert "Invalid or already used" in resp.json()["detail"]


# 8. expired token rejected
@pytest.mark.asyncio
async def test_expired_token_rejected():
    c = _client()
    email = _unique_email()
    _register_user(c, email)

    captured_token = None

    async def fake_send(to_email: str, reset_token: str):
        nonlocal captured_token
        captured_token = reset_token
        return True

    with patch("app.api.v1.auth.send_password_reset_email", side_effect=fake_send):
        c.post("/api/v1/auth/forgot-password", json={"email": email})

    assert captured_token is not None
    token_hash = hashlib.sha256(captured_token.encode("utf-8")).hexdigest()

    # Artificially expire the token in database
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        record = result.scalar_one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        await session.commit()

    resp = c.post(
        "/api/v1/auth/reset-password",
        json={"token": captured_token, "new_password": "AnotherPassword123!"},
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


# 9 & 12. used token rejected & second use of same token rejected
def test_second_use_of_same_token_rejected():
    c = _client()
    email = _unique_email()
    _register_user(c, email)

    captured_token = None

    async def fake_send(to_email: str, reset_token: str):
        nonlocal captured_token
        captured_token = reset_token
        return True

    with patch("app.api.v1.auth.send_password_reset_email", side_effect=fake_send):
        c.post("/api/v1/auth/forgot-password", json={"email": email})

    # First reset should succeed
    first = c.post(
        "/api/v1/auth/reset-password",
        json={"token": captured_token, "new_password": "FirstNewPassword123!"},
    )
    assert first.status_code == 200

    # Second reset with SAME token MUST fail
    second = c.post(
        "/api/v1/auth/reset-password",
        json={"token": captured_token, "new_password": "SecondNewPassword123!"},
    )
    assert second.status_code == 400
    assert "Invalid or already used" in second.json()["detail"]


# 13. previous reset token invalidated when new one is requested
def test_previous_reset_token_invalidated():
    c = _client()
    email = _unique_email()
    _register_user(c, email)

    tokens = []

    async def fake_send(to_email: str, reset_token: str):
        tokens.append(reset_token)
        return True

    with patch("app.api.v1.auth.send_password_reset_email", side_effect=fake_send):
        # Request 1
        c.post("/api/v1/auth/forgot-password", json={"email": email})
        # Request 2
        c.post("/api/v1/auth/forgot-password", json={"email": email})

    assert len(tokens) == 2
    token1, token2 = tokens[0], tokens[1]

    # Token 1 must now be invalidated
    resp1 = c.post(
        "/api/v1/auth/reset-password",
        json={"token": token1, "new_password": "AttemptPassword123!"},
    )
    assert resp1.status_code == 400
    assert "Invalid or already used" in resp1.json()["detail"]

    # Token 2 must succeed
    resp2 = c.post(
        "/api/v1/auth/reset-password",
        json={"token": token2, "new_password": "SuccessPassword123!"},
    )
    assert resp2.status_code == 200


# 14. existing login still works
def test_existing_login_still_works():
    c = _client()
    email = _unique_email()
    password = "ConsistentPassword123!"
    _register_user(c, email, password)

    login_resp = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"]


# 15. existing register still works
def test_existing_register_still_works():
    c = _client()
    email = _unique_email()
    reg = c.post(
        "/api/v1/auth/register",
        json={"full_name": "Standard User", "email": email, "password": "StandardPassword123!"},
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["email"] == email
