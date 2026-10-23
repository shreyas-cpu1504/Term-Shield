"""Unit tests for Neon PostgreSQL connection verification script and URL normalization."""

import os
from pathlib import Path
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.engine.url import make_url
from sqlalchemy.schema import CreateTable

from app.core.database import normalize_database_url
from app.models import (
    Base,
    Clause,
    ClauseAnalysisRecord,
    Contract,
    PasswordResetToken,
    QAHistory,
    User,
)
from scripts.verify_neon_connection import (
    EXPECTED_TABLES,
    load_target_url,
    mask_database_url,
)


def test_mask_database_url_hides_password():
    raw = "postgresql://myuser:secretpassword123@ep-cool-fog-1234.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    masked = mask_database_url(raw)
    assert "secretpassword123" not in masked
    assert "myuser:***@ep-cool-fog-1234.us-east-2.aws.neon.tech/neondb" in masked
    assert "sslmode=require" in masked
    assert "channel_binding=require" in masked


def test_mask_database_url_handles_empty_or_none():
    assert mask_database_url("") == "<not set>"
    assert mask_database_url(None) == "<not set>"


def test_load_target_url_cli_takes_precedence(monkeypatch):
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://envuser:envpass@host/db")
    cli_url = "postgresql://cliuser:clipass@host/db"
    url, source = load_target_url(cli_url)
    assert url == cli_url
    assert "CLI" in source


def test_load_target_url_env_takes_precedence_over_sqlite(monkeypatch):
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://envuser:envpass@neonhost/neondb")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///storage/term_shield.db")
    url, source = load_target_url()
    assert url == "postgresql://envuser:envpass@neonhost/neondb"
    assert "NEON_DATABASE_URL" in source


def test_expected_tables_matches_base_metadata():
    model_tables = set(Base.metadata.tables.keys())
    assert set(EXPECTED_TABLES) == model_tables
    assert len(EXPECTED_TABLES) == 6


def test_all_expected_tables_compile_to_postgresql_ddl():
    pg_dialect = postgresql.dialect()
    for table_name in EXPECTED_TABLES:
        table_obj = Base.metadata.tables[table_name]
        ddl = str(CreateTable(table_obj).compile(dialect=pg_dialect))
        assert "CREATE TABLE" in ddl
        assert table_name in ddl


# --- URL Normalization & SSL Conversion Tests ---

def test_normalize_database_url_converts_sslmode_and_removes_channel_binding():
    """Verify that sslmode=require and channel_binding=require are correctly translated for asyncpg."""
    raw = "postgresql://myuser:mypassword@ep-dry-lake-1234.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    normalized = normalize_database_url(raw)

    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=require" in normalized
    assert "sslmode=" not in normalized
    assert "channel_binding=" not in normalized

    # Verify that SQLAlchemy asyncpg dialect parses connect_args without unexpected kwargs
    dialect = PGDialect_asyncpg()
    _, opts = dialect.create_connect_args(make_url(normalized))
    assert opts.get("ssl") == "require"
    assert "sslmode" not in opts
    assert "channel_binding" not in opts


def test_normalize_database_url_preserves_verify_full():
    raw = "postgres://user:pass@host/db?sslmode=verify-full"
    normalized = normalize_database_url(raw)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=verify-full" in normalized
    assert "sslmode=" not in normalized


def test_normalize_database_url_neon_auto_ssl():
    raw = "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb"
    normalized = normalize_database_url(raw)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=require" in normalized


def test_normalize_database_url_leaves_sqlite_untouched():
    raw = "sqlite+aiosqlite:///storage/term_shield.db"
    assert normalize_database_url(raw) == raw
