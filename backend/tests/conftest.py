"""Shared test fixtures for API tests requiring authentication."""
import os
import uuid

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-for-tests-which-is-32-bytes-long",
)

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """A TestClient authenticated as a freshly registered user."""
    register_client = TestClient(app)

    response = register_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": f"test-{uuid.uuid4()}@example.com",
            "password": "secure-password-123",
        },
    )

    assert response.status_code == 201, response.text

    token = response.json()["access_token"]

    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    return client


def _register_and_get_client() -> TestClient:
    register_client = TestClient(app)

    response = register_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other User",
            "email": f"other-{uuid.uuid4()}@example.com",
            "password": "secure-password-456",
        },
    )

    assert response.status_code == 201, response.text

    token = response.json()["access_token"]

    other_client = TestClient(app)
    other_client.headers.update({"Authorization": f"Bearer {token}"})

    return other_client


@pytest.fixture()
def other_client() -> TestClient:
    """A second, independent authenticated user (different from `client`)."""
    return _register_and_get_client()
