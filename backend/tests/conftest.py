"""Shared test fixtures for API tests requiring authentication."""
import asyncio
import os
from pathlib import Path
import tempfile
import uuid

# 1. Configure an isolated temporary SQLite database before importing application modules
_IS_EXPLICIT_DB_URL = "DATABASE_URL" in os.environ
_TEST_DB_FILE = Path(tempfile.gettempdir()) / f"term_shield_test_{uuid.uuid4().hex[:8]}.db"

if not _IS_EXPLICIT_DB_URL:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_FILE.as_posix()}"

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-for-tests-which-is-32-bytes-long",
)

# 2. Configure isolated temporary filesystem storage before importing application modules
_TEST_STORAGE_DIR = Path(tempfile.gettempdir()) / f"term_shield_test_storage_{uuid.uuid4().hex[:8]}"
_TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

import shutil
from fastapi.testclient import TestClient
import pytest

from app.core.database import close_db, init_db
from app.main import app
from app.services.storage_service import (
    LocalStorageService,
    get_storage_service,
    set_storage_service,
)
from app.services.file_ingestion_service import FileIngestionService
from app.services.clause_storage_service import ClauseStorageService

# Record original storage configurations to guarantee reversible restoration
_ORIG_STORAGE_SERVICE = get_storage_service()
_ORIG_FILE_INGESTION_BASE = FileIngestionService.BASE_STORAGE_DIR
_ORIG_FILE_INGESTION_UPLOAD = FileIngestionService.UPLOAD_DIR
_ORIG_FILE_INGESTION_EXTRACTED = FileIngestionService.EXTRACTED_DIR
_ORIG_CLAUSE_STORAGE_DIR = ClauseStorageService.CLAUSES_DIR

# Redirect default storage to unique test directory
_TEST_STORAGE_SERVICE = LocalStorageService(base_dir=_TEST_STORAGE_DIR)
set_storage_service(_TEST_STORAGE_SERVICE)
FileIngestionService.BASE_STORAGE_DIR = _TEST_STORAGE_DIR
FileIngestionService.UPLOAD_DIR = _TEST_STORAGE_DIR / "uploads"
FileIngestionService.EXTRACTED_DIR = _TEST_STORAGE_DIR / "extracted"
ClauseStorageService.CLAUSES_DIR = _TEST_STORAGE_DIR / "clauses"


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure database schema is created on the isolated test database before tests run,

    and ensure strict try/finally cleanup of database and temporary storage.
    """
    db_initialized = False
    try:
        asyncio.run(init_db())
        db_initialized = True
        yield
    finally:
        # 1. Clean up database resources
        if db_initialized:
            try:
                asyncio.run(close_db())
            except Exception:
                pass
        if not _IS_EXPLICIT_DB_URL:
            try:
                if _TEST_DB_FILE.exists():
                    _TEST_DB_FILE.unlink()
            except OSError:
                pass

        # 2. Restore original storage configuration
        try:
            set_storage_service(_ORIG_STORAGE_SERVICE)
            FileIngestionService.BASE_STORAGE_DIR = _ORIG_FILE_INGESTION_BASE
            FileIngestionService.UPLOAD_DIR = _ORIG_FILE_INGESTION_UPLOAD
            FileIngestionService.EXTRACTED_DIR = _ORIG_FILE_INGESTION_EXTRACTED
            ClauseStorageService.CLAUSES_DIR = _ORIG_CLAUSE_STORAGE_DIR
        except Exception:
            pass

        # 3. Clean up temporary storage directory
        try:
            if _TEST_STORAGE_DIR.exists():
                shutil.rmtree(_TEST_STORAGE_DIR, ignore_errors=True)
        except Exception:
            pass



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
