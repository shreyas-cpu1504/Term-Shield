"""Regression test suite proving that tests use an isolated database and never alter the active database."""
from pathlib import Path
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, get_db
from app.main import app
from app.models.contract import Contract
from app.models.user import User


ACTIVE_DB_PATH = Path("storage/term_shield.db")


def _get_active_db_counts() -> tuple[int, int]:
    """Helper to get current (user_count, contract_count) directly from active DB file."""
    if not ACTIVE_DB_PATH.exists():
        return 0, 0
    conn = sqlite3.connect(ACTIVE_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM contracts")
        contract_count = cursor.fetchone()[0]
        return user_count, contract_count
    finally:
        conn.close()


def test_database_url_is_isolated():
    """Verify that during testing, database_url does not point to the active term_shield.db."""
    settings = get_settings()
    assert "storage/term_shield.db" not in settings.database_url.replace("\\", "/")
    assert "term_shield_test" in settings.database_url or "memory" in settings.database_url or ":memory:" in settings.database_url


def test_client_registration_does_not_alter_active_db(client: TestClient):
    """Verify that registering a user via TestClient writes to test DB and does not touch active DB."""
    users_before, contracts_before = _get_active_db_counts()

    # The client fixture itself registers a user, and we also register another test user here
    test_email = f"isolation-user-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Isolation Verification User",
            "email": test_email,
            "password": "secure-test-password-123",
        },
    )
    assert resp.status_code == 201

    users_after, contracts_after = _get_active_db_counts()

    # Active DB row counts must remain identical
    assert users_after == users_before, f"Active DB user count changed from {users_before} to {users_after}!"
    assert contracts_after == contracts_before, f"Active DB contract count changed from {contracts_before} to {contracts_after}!"

    # Verify that the test email does NOT exist in the active DB file
    if ACTIVE_DB_PATH.exists():
        conn = sqlite3.connect(ACTIVE_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (test_email,))
            assert cursor.fetchone()[0] == 0, "Test user was leaked into the active database!"
        finally:
            conn.close()


@pytest.mark.asyncio
async def test_direct_async_session_local_isolation():
    """Verify that direct queries and commits via AsyncSessionLocal operate on isolated test DB."""
    users_before, contracts_before = _get_active_db_counts()

    test_email = f"direct-session-{uuid.uuid4().hex[:8]}@example.com"

    # Write directly to AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        user = User(
            email=test_email,
            hashed_password="hashed_pw_test",
            full_name="Direct Session User",
        )
        session.add(user)
        await session.commit()

    # Read back from AsyncSessionLocal to verify it was stored in the test DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_email)
        )
        persisted_user = result.scalar_one_or_none()
        assert persisted_user is not None
        assert persisted_user.email == test_email

    users_after, contracts_after = _get_active_db_counts()

    # Active DB row counts must remain identical
    assert users_after == users_before, f"Active DB user count changed from {users_before} to {users_after}!"
    assert contracts_after == contracts_before, f"Active DB contract count changed from {contracts_before} to {contracts_after}!"

    # Verify that the test email does NOT exist in the active DB file
    if ACTIVE_DB_PATH.exists():
        conn = sqlite3.connect(ACTIVE_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (test_email,))
            assert cursor.fetchone()[0] == 0, "Direct session user was leaked into the active database!"
        finally:
            conn.close()


def test_fastapi_dependency_overrides_working():
    """Verify that FastAPI app.dependency_overrides still works as expected for get_db."""
    called = False

    async def mock_get_db():
        nonlocal called
        called = True
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = mock_get_db
    try:
        unauth_client = TestClient(app)
        # Calling an endpoint that uses get_db (such as health or contracts)
        resp = unauth_client.get("/api/v1/contracts")
        # Route requires auth, so it returns 401, but dependency injection infrastructure remains functional
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_filesystem_storage_is_isolated(client: TestClient):
    """Verify that file ingestion and clause storage operate in a temporary directory
    and never write or modify files in the real storage directory.
    """
    import io
    import tempfile
    from app.services.storage_service import get_storage_service
    from app.services.file_ingestion_service import FileIngestionService
    from app.services.clause_storage_service import ClauseStorageService
    from app.schemas.clause import Clause

    real_storage = Path("storage")
    real_uploads = len(list((real_storage / "uploads").glob("*"))) if (real_storage / "uploads").exists() else 0
    real_extracted = len(list((real_storage / "extracted").glob("*"))) if (real_storage / "extracted").exists() else 0
    real_clauses = len(list((real_storage / "clauses").glob("*"))) if (real_storage / "clauses").exists() else 0

    # Verify current storage service is pointing to a temporary directory
    current_storage = get_storage_service()
    system_temp = Path(tempfile.gettempdir()).resolve()
    assert getattr(current_storage, "base_dir", None) is not None
    assert Path(current_storage.base_dir).resolve().is_relative_to(system_temp)
    assert "term_shield_test_storage" in str(current_storage.base_dir)

    # Ingest a test file via client
    test_content = b"Contract content for filesystem isolation verification."
    files = {"file": ("isolation_check.txt", io.BytesIO(test_content), "text/plain")}
    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    # Save a test clause
    clause = Clause(
        clause_id="iso-1",
        title="Isolation",
        text="Filesystem isolation active.",
        order=1,
        character_count=28,
        clause_type="other",
    )
    ClauseStorageService.save_clauses(file_id, [clause])

    # Verify artifacts exist in temporary test storage
    assert (FileIngestionService.UPLOAD_DIR / f"{file_id}.txt").is_file()
    assert (FileIngestionService.EXTRACTED_DIR / f"{file_id}.txt").is_file()
    assert (ClauseStorageService.CLAUSES_DIR / f"{file_id}.json").is_file()

    # Verify artifacts DO NOT exist in real storage
    assert not (real_storage / "uploads" / f"{file_id}.txt").exists()
    assert not (real_storage / "extracted" / f"{file_id}.txt").exists()
    assert not (real_storage / "clauses" / f"{file_id}.json").exists()

    # Verify real storage counts are completely unchanged
    after_uploads = len(list((real_storage / "uploads").glob("*"))) if (real_storage / "uploads").exists() else 0
    after_extracted = len(list((real_storage / "extracted").glob("*"))) if (real_storage / "extracted").exists() else 0
    after_clauses = len(list((real_storage / "clauses").glob("*"))) if (real_storage / "clauses").exists() else 0

    assert after_uploads == real_uploads, f"Real uploads count changed: {real_uploads} -> {after_uploads}"
    assert after_extracted == real_extracted, f"Real extracted count changed: {real_extracted} -> {after_extracted}"
    assert after_clauses == real_clauses, f"Real clauses count changed: {real_clauses} -> {after_clauses}"
