import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.v1.auth import (
    create_oauth_exchange_code,
    consume_oauth_exchange_code,
    generate_oauth_state,
    verify_oauth_state,
)
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.main import app


@pytest.mark.asyncio
async def test_oauth_providers_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/providers")
        assert response.status_code == 200
        data = response.json()
        assert list(data.keys()) == ["google"]
        assert "login_url" in data["google"]


@pytest.mark.asyncio
async def test_oauth_state_generation_and_validation():
    state = generate_oauth_state("google")
    assert verify_oauth_state(state, "google") is True
    assert verify_oauth_state(state, "unsupported_provider") is False
    assert verify_oauth_state("tampered_state_value", "google") is False


@pytest.mark.asyncio
async def test_google_login_unconfigured():
    settings = get_settings()
    settings.google_client_id = None
    settings.google_client_secret = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/google/login")
        assert response.status_code == 500
        assert "Google OAuth is not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_login_redirect_when_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_client_id", "mock-google-client-id")
    monkeypatch.setattr(settings, "google_client_secret", "mock-google-client-secret")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers.get("location")
        assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=mock-google-client-id" in location


@pytest.mark.asyncio
async def test_google_callback_invalid_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/google/callback?code=mock_code&state=bad_state", follow_redirects=False)
        assert response.status_code == 307
        assert "error=Invalid+or+expired+OAuth+state" in response.headers.get("location")


@pytest.mark.asyncio
async def test_oauth_exchange_code_lifecycle_and_single_use():
    # 1. Create a user in DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "oauth_sec_test@example.com"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="oauth_sec_test@example.com",
                full_name="OAuth Security Test User",
                hashed_password=None,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        user_id = user.id

    # 2. Mint short-lived single-use exchange code
    code = await create_oauth_exchange_code(user_id)
    assert code is not None
    assert len(code) > 20

    # 3. Exchange code via POST /oauth/exchange
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.post("/api/v1/auth/oauth/exchange", json={"code": code})
        assert res1.status_code == 200
        data1 = res1.json()
        assert "access_token" in data1
        assert data1["token_type"] == "bearer"
        assert data1["user"]["email"] == "oauth_sec_test@example.com"

        # 4. Attempt Replay attack with same code: MUST FAIL (Single-use enforcement)
        res2 = await client.post("/api/v1/auth/oauth/exchange", json={"code": code})
        assert res2.status_code == 400
        assert "Invalid or expired" in res2.json()["detail"]

        # 5. Invalid / Fake code: MUST FAIL
        res3 = await client.post("/api/v1/auth/oauth/exchange", json={"code": "completely_fake_code"})
        assert res3.status_code == 400
