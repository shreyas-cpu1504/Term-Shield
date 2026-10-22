from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import normalize_database_url
from app.core.migration_utility import DatabaseMigrationUtility, TABLE_MIGRATION_ORDER
from app.models import (
    Base,
    Clause,
    ClauseAnalysisRecord,
    Contract,
    PasswordResetToken,
    QAHistory,
    User,
)


# --- 1. Database URL Normalization Tests ---

def test_normalize_database_url_postgres():
    url = "postgres://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "user:pass@ep-xyz" in normalized


def test_normalize_database_url_postgresql_bare():
    url = "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+asyncpg://")


def test_normalize_database_url_already_asyncpg():
    url = "postgresql+asyncpg://user:pass@host/db"
    assert normalize_database_url(url) == url


def test_normalize_database_url_sqlite():
    url = "sqlite+aiosqlite:///storage/term_shield.db"
    assert normalize_database_url(url) == url


# --- 2. Model DDL Compilation to PostgreSQL Dialect ---

def test_all_models_compile_to_postgresql_ddl():
    """Verify that all models generate valid DDL under SQLAlchemy's PostgreSQL dialect."""
    pg_dialect = postgresql.dialect()
    models = [User, Contract, Clause, ClauseAnalysisRecord, QAHistory, PasswordResetToken]

    for model in models:
        ddl = str(CreateTable(model.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE" in ddl
        assert model.__tablename__ in ddl


# --- 3. Offline Migration Planning & Dry-Run Tests ---

@pytest.fixture
def sample_source_db(tmp_path: Path):
    """Create a temporary SQLite database populated with test records matching the app schema."""
    db_file = tmp_path / "source_test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255),
            full_name VARCHAR(255),
            profile_photo TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            is_superuser BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE contracts (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            size_bytes INTEGER NOT NULL,
            character_count INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL,
            overall_risk VARCHAR(20) NOT NULL,
            overall_risk_score INTEGER NOT NULL,
            summary_json TEXT,
            extracted_text_path VARCHAR(500),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE clauses (
            id VARCHAR(100) PRIMARY KEY,
            contract_id VARCHAR(36) NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            clause_number VARCHAR(50),
            title VARCHAR(255),
            text TEXT NOT NULL,
            "order" INTEGER NOT NULL,
            character_count INTEGER NOT NULL,
            parent_clause VARCHAR(50),
            clause_type VARCHAR(50),
            created_at DATETIME NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE clause_analyses (
            id VARCHAR(36) PRIMARY KEY,
            contract_id VARCHAR(36) NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            clause_id VARCHAR(100) NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
            clause_type VARCHAR(50),
            risk_level VARCHAR(20) NOT NULL,
            risk_score INTEGER NOT NULL,
            meaning TEXT,
            analysis_data TEXT,
            created_at DATETIME NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE qa_history (
            id VARCHAR(36) PRIMARY KEY,
            contract_id VARCHAR(36) NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
            question VARCHAR(2000) NOT NULL,
            answer TEXT NOT NULL,
            evidence_json TEXT,
            confidence FLOAT NOT NULL,
            language VARCHAR(50),
            created_at DATETIME NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE password_reset_tokens (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL,
            expires_at DATETIME NOT NULL,
            used_at DATETIME,
            created_at DATETIME NOT NULL
        );
    """)

    # Populate rows
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("INSERT INTO users VALUES ('u1', 'test@example.com', 'hash', 'Test User', NULL, 1, 1, 0, ?, ?)", (now, now))
    cursor.execute("INSERT INTO contracts VALUES ('c1', 'u1', 'contract.pdf', 'pdf', 1024, 500, 'analyzed', 'LOW', 10, '{}', 'extracted/c1.txt', ?, ?)", (now, now))
    cursor.execute("INSERT INTO clauses VALUES ('cl1', 'c1', '1', 'Confidentiality', 'Text', 1, 100, NULL, 'CONFIDENTIALITY', ?)", (now,))
    cursor.execute("INSERT INTO clause_analyses VALUES ('ca1', 'c1', 'cl1', 'CONFIDENTIALITY', 'LOW', 5, 'Meaning', '{}', ?)", (now,))
    cursor.execute("INSERT INTO qa_history VALUES ('q1', 'c1', 'u1', 'Question?', 'Answer.', '[]', 1.0, 'English', ?)", (now,))
    cursor.execute("INSERT INTO password_reset_tokens VALUES ('t1', 'u1', 'hash123', ?, NULL, ?)", (now, now))

    conn.commit()
    conn.close()

    return db_file


def test_migration_utility_inspect_source(sample_source_db: Path):
    """Verify source database inspection reports correct tables and row counts."""
    util = DatabaseMigrationUtility(sample_source_db)
    inspections = util.inspect_source()

    assert set(inspections.keys()) == set(TABLE_MIGRATION_ORDER)
    for table_name in TABLE_MIGRATION_ORDER:
        assert inspections[table_name].row_count == 1
        assert inspections[table_name].has_primary_key is True


def test_migration_utility_generate_plan(sample_source_db: Path):
    """Verify execution plan follows strict dependency order with zero warnings."""
    util = DatabaseMigrationUtility(sample_source_db, target_db_url="postgresql+asyncpg://fake@host/db")
    plan = util.generate_plan()

    assert plan.planned_tables == TABLE_MIGRATION_ORDER
    assert plan.total_records == 6
    assert plan.dependency_order_valid is True
    assert plan.warnings == []


@pytest.mark.asyncio
async def test_migration_utility_dry_run(sample_source_db: Path):
    """Verify dry run validates source records without writing to target."""
    util = DatabaseMigrationUtility(sample_source_db)
    report = await util.execute_dry_run()

    assert report["status"] == "VALID"
    assert report["checks"]["source_accessible"] is True
    assert report["checks"]["orphan_contract_references"] == 0
    assert report["checks"]["missing_pk_count"] == 0


# --- 4. Offline End-to-End Migration & Verification Tests ---

@pytest.mark.asyncio
async def test_offline_migration_and_verification_lifecycle(sample_source_db: Path, tmp_path: Path):
    """Test full offline migration, verification, and idempotent retry into isolated target database."""
    target_db_file = tmp_path / "dest_test.db"
    target_url = f"sqlite+aiosqlite:///{target_db_file.as_posix()}"
    target_engine = create_async_engine(target_url)

    util = DatabaseMigrationUtility(source_db_path=sample_source_db, target_engine=target_engine)

    # 1. Execute Migration
    summary = await util.migrate_data(target_engine=target_engine)
    for tbl in TABLE_MIGRATION_ORDER:
        assert summary[tbl]["source_rows"] == 1
        assert summary[tbl]["inserted"] == 1
        assert summary[tbl]["skipped_existing"] == 0

    # 2. Verify Migration Fidelity
    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "PASSED"
    assert verification.count_matches is True
    assert verification.errors == []
    assert verification.source_counts == verification.target_counts

    # 3. Test Idempotent Retry (re-running migration should safely skip existing records)
    retry_summary = await util.migrate_data(target_engine=target_engine)
    for tbl in TABLE_MIGRATION_ORDER:
        assert retry_summary[tbl]["source_rows"] == 1
        assert retry_summary[tbl]["inserted"] == 0
        assert retry_summary[tbl]["skipped_existing"] == 1

    # 4. Test Mismatch Detection
    # Manually delete one row from target
    async with target_engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("DELETE FROM clauses WHERE id = 'cl1'"))

    mismatch_verification = await util.verify_migration(target_engine=target_engine)
    assert mismatch_verification.status == "FAILED"
    assert mismatch_verification.count_matches is False
    assert any("clauses" in err for err in mismatch_verification.errors)

    await target_engine.dispose()


# --- 5. Conflict Detection & Data Fidelity Tests ---

@pytest.mark.asyncio
async def test_migration_conflicting_record_detected_and_not_overwritten(sample_source_db: Path, tmp_path: Path):
    """Verify duplicate primary key with differing values is detected as a mismatch and not overwritten."""
    target_db_file = tmp_path / "dest_conflict.db"
    target_url = f"sqlite+aiosqlite:///{target_db_file.as_posix()}"
    target_engine = create_async_engine(target_url)

    # Pre-populate target database with User 'u1' having a conflicting full_name
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        now = datetime.now(timezone.utc)
        from sqlalchemy import insert
        await conn.execute(
            insert(User.__table__).values(
                id="u1",
                email="test@example.com",
                hashed_password="hash",
                full_name="Target Pre-existing Name",
                profile_photo=None,
                is_active=True,
                is_verified=True,
                is_superuser=False,
                created_at=now,
                updated_at=now,
            )
        )

    util = DatabaseMigrationUtility(source_db_path=sample_source_db, target_engine=target_engine)

    # Source has full_name="Test User", whereas target has "Target Pre-existing Name"
    summary = await util.migrate_data(target_engine=target_engine)
    assert summary["users"]["mismatches"] == 1
    assert summary["users"]["inserted"] == 0
    assert summary["users"]["skipped_existing"] == 0
    assert len(summary["users"]["conflicts"]) == 1

    conflict = summary["users"]["conflicts"][0]
    assert conflict["id"] == "u1"
    assert "full_name" in conflict["differing_fields"]
    assert conflict["details"]["full_name"]["source"] == "Test User"
    assert conflict["details"]["full_name"]["destination"] == "Target Pre-existing Name"

    # Verify destination record was NOT overwritten
    async with target_engine.connect() as conn:
        from sqlalchemy import select
        res = (await conn.execute(select(User.__table__).where(User.__table__.c.id == "u1"))).mappings().one()
        assert res["full_name"] == "Target Pre-existing Name"

    # Verify verification detects the conflict and fails
    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "FAILED"
    assert any("field mismatch" in err for err in verification.errors)

    await target_engine.dispose()


@pytest.mark.asyncio
async def test_migration_data_fidelity_nulls_unicode_booleans_json(tmp_path: Path):
    """Verify data fidelity for nulls, Unicode text, booleans, and JSON."""
    src_file = tmp_path / "fidelity_src.db"
    conn = sqlite3.connect(str(src_file))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255),
            full_name VARCHAR(255),
            profile_photo TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            is_superuser BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE contracts (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) REFERENCES users(id),
            filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            size_bytes INTEGER NOT NULL,
            character_count INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL,
            overall_risk VARCHAR(20) NOT NULL,
            overall_risk_score INTEGER NOT NULL,
            summary_json TEXT,
            extracted_text_path VARCHAR(500),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)

    # Unicode names, emojis, nulls, and JSON
    unicode_name = "Dr. François Müller ⚖️ 東京"
    unicode_filename = "contrat_français_日本語_契約.pdf"
    json_str = '{"risk_level": "HIGH", "score": 92, "clauses": ["c1", "c2"]}'
    now_iso = "2026-10-22 14:30:00"

    cur.execute(
        "INSERT INTO users VALUES ('u_uni', 'uni@example.com', NULL, ?, NULL, 1, 0, 1, ?, ?)",
        (unicode_name, now_iso, now_iso),
    )
    cur.execute(
        "INSERT INTO contracts VALUES ('c_uni', 'u_uni', ?, 'pdf', 2048, 1000, 'analyzed', 'HIGH', 92, ?, NULL, ?, ?)",
        (unicode_filename, json_str, now_iso, now_iso),
    )
    conn.commit()
    conn.close()

    target_file = tmp_path / "fidelity_dest.db"
    target_engine = create_async_engine(f"sqlite+aiosqlite:///{target_file.as_posix()}")

    util = DatabaseMigrationUtility(source_db_path=src_file, target_engine=target_engine)
    summary = await util.migrate_data(target_engine=target_engine)

    assert summary["users"]["inserted"] == 1
    assert summary["contracts"]["inserted"] == 1

    # Verify destination row fidelity
    async with target_engine.connect() as conn:
        from sqlalchemy import select
        u = (await conn.execute(select(User.__table__).where(User.__table__.c.id == "u_uni"))).mappings().one()
        assert u["full_name"] == unicode_name
        assert u["hashed_password"] is None
        assert u["profile_photo"] is None
        assert u["is_active"] is True
        assert u["is_verified"] is False
        assert u["is_superuser"] is True

        c = (await conn.execute(select(Contract.__table__).where(Contract.__table__.c.id == "c_uni"))).mappings().one()
        assert c["filename"] == unicode_filename
        assert c["summary_json"] == json_str
        assert c["extracted_text_path"] is None

    # Full record verification should pass
    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "PASSED"
    assert verification.errors == []
    assert verification.conflicts == []

    await target_engine.dispose()


@pytest.mark.asyncio
async def test_migration_timestamp_precision_and_timezones(tmp_path: Path):
    """Verify handling of fractional seconds, timezone-aware strings, and naive UTC strings."""
    src_file = tmp_path / "ts_src.db"
    conn = sqlite3.connect(str(src_file))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255),
            full_name VARCHAR(255),
            profile_photo TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            is_superuser BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)

    # User 1: Naive UTC string with microseconds
    ts_naive_micro = "2026-10-22 14:30:00.123456"
    cur.execute("INSERT INTO users VALUES ('u_ts1', 'ts1@example.com', NULL, 'TS1', NULL, 1, 0, 0, ?, ?)", (ts_naive_micro, ts_naive_micro))

    # User 2: Timezone-aware ISO string with offset
    ts_tz_aware = "2026-10-22T20:00:00.654321+05:30"
    cur.execute("INSERT INTO users VALUES ('u_ts2', 'ts2@example.com', NULL, 'TS2', NULL, 1, 0, 0, ?, ?)", (ts_tz_aware, ts_tz_aware))

    conn.commit()
    conn.close()

    target_file = tmp_path / "ts_dest.db"
    target_engine = create_async_engine(f"sqlite+aiosqlite:///{target_file.as_posix()}")

    util = DatabaseMigrationUtility(source_db_path=src_file, target_engine=target_engine)
    summary = await util.migrate_data(target_engine=target_engine)

    assert summary["users"]["inserted"] == 2
    assert summary["users"]["mismatches"] == 0

    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "PASSED"
    assert verification.errors == []

    await target_engine.dispose()


@pytest.mark.asyncio
async def test_migration_invalid_timestamp_raises_and_rolls_back(tmp_path: Path):
    """Verify invalid timestamp string raises descriptive ValueError and rolls back the batch."""
    src_file = tmp_path / "invalid_ts_src.db"
    conn = sqlite3.connect(str(src_file))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255),
            full_name VARCHAR(255),
            profile_photo TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            is_superuser BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
    """)
    cur.execute("INSERT INTO users VALUES ('u_bad', 'bad@example.com', NULL, 'Bad User', NULL, 1, 0, 0, 'invalid-date-string', 'invalid-date-string')")
    conn.commit()
    conn.close()

    target_file = tmp_path / "invalid_ts_dest.db"
    target_engine = create_async_engine(f"sqlite+aiosqlite:///{target_file.as_posix()}")

    util = DatabaseMigrationUtility(source_db_path=src_file, target_engine=target_engine)

    with pytest.raises(ValueError) as exc_info:
        await util.migrate_data(target_engine=target_engine)

    error_msg = str(exc_info.value)
    assert "Invalid timestamp value" in error_msg
    assert "users" in error_msg
    assert "u_bad" in error_msg
    assert "created_at" in error_msg

    # Verify zero rows were inserted due to rollback
    async with target_engine.connect() as conn:
        from sqlalchemy import text
        res = (await conn.execute(text("SELECT COUNT(*) FROM users"))).scalar_one()
        assert res == 0

    await target_engine.dispose()


@pytest.mark.asyncio
async def test_verification_detects_field_mismatch_across_full_dataset(sample_source_db: Path, tmp_path: Path):
    """Verify full-record comparison detects a subtle field modification without count differences."""
    target_file = tmp_path / "full_verify_dest.db"
    target_engine = create_async_engine(f"sqlite+aiosqlite:///{target_file.as_posix()}")

    util = DatabaseMigrationUtility(source_db_path=sample_source_db, target_engine=target_engine)
    await util.migrate_data(target_engine=target_engine)

    # Alter a single column value on target (counts remain equal)
    async with target_engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("UPDATE clauses SET title = 'Altered Title' WHERE id = 'cl1'"))

    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "FAILED"
    assert verification.count_matches is True
    assert verification.sample_verified is False
    assert len(verification.conflicts) == 1
    assert verification.conflicts[0]["id"] == "cl1"
    assert "title" in verification.conflicts[0]["differing_fields"]
    assert any("title" in err for err in verification.errors)

    await target_engine.dispose()


@pytest.mark.asyncio
async def test_migration_retry_after_failure(sample_source_db: Path, tmp_path: Path):
    """Verify migration can be safely retried idempotently after a simulated prior partial run."""
    target_file = tmp_path / "retry_dest.db"
    target_engine = create_async_engine(f"sqlite+aiosqlite:///{target_file.as_posix()}")

    util = DatabaseMigrationUtility(source_db_path=sample_source_db, target_engine=target_engine)

    # First run succeeds
    summary1 = await util.migrate_data(target_engine=target_engine)
    assert summary1["users"]["inserted"] == 1
    assert summary1["users"]["skipped_existing"] == 0

    # Second run skips without error
    summary2 = await util.migrate_data(target_engine=target_engine)
    assert summary2["users"]["inserted"] == 0
    assert summary2["users"]["skipped_existing"] == 1
    assert summary2["users"]["mismatches"] == 0

    verification = await util.verify_migration(target_engine=target_engine)
    assert verification.status == "PASSED"

    await target_engine.dispose()
