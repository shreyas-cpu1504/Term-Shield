"""Neon PostgreSQL Connectivity and Schema Verification Script for Term Shield.

Safely tests asynchronous database connectivity, SSL configuration, and table schema
readiness without modifying local SQLite configuration or touching production data.

Usage:
    # 1. Inspect connection and schema without making any changes (dry-run):
    python scripts/verify_neon_connection.py

    # 2. Provide connection string via CLI argument or environment variable:
    python scripts/verify_neon_connection.py --url "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"

    # 3. Apply schema creation only when explicitly confirmed:
    python scripts/verify_neon_connection.py --init-schema
"""

import argparse
import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit, urlunsplit

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable

from app.core.database import Base, normalize_database_url
from app.models import (
    Clause,
    ClauseAnalysisRecord,
    Contract,
    PasswordResetToken,
    QAHistory,
    User,
)

EXPECTED_TABLES = [
    "users",
    "contracts",
    "clauses",
    "clause_analyses",
    "qa_history",
    "password_reset_tokens",
]


def mask_database_url(url: str) -> str:
    """Mask credentials in a database connection URL for safe logging."""
    if not url:
        return "<not set>"
    try:
        parts = urlsplit(url)
        netloc = parts.netloc
        if "@" in netloc:
            user_info, host_port = netloc.split("@", 1)
            user = user_info.split(":", 1)[0] if ":" in user_info else user_info
            masked_netloc = f"{user}:***@{host_port}"
        else:
            masked_netloc = netloc
        return urlunsplit((parts.scheme, masked_netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return "<invalid-url-format>"


def load_target_url(cli_url: str | None = None) -> tuple[str | None, str]:
    """Resolve the target Neon database URL from CLI, environment, or .env.

    Never overrides or modifies the active SQLite DATABASE_URL.
    """
    if cli_url and cli_url.strip():
        return cli_url.strip(), "CLI argument (--url)"

    # Check environment variables
    env_neon = os.environ.get("NEON_DATABASE_URL")
    if env_neon and env_neon.strip():
        return env_neon.strip(), "Environment variable (NEON_DATABASE_URL)"

    # Check backend/.env for NEON_DATABASE_URL
    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            if key == "NEON_DATABASE_URL" and val.strip():
                return val.strip(), ".env file (NEON_DATABASE_URL)"

    # If DATABASE_URL starts with postgres, allow it (e.g. on Render)
    db_url = os.environ.get("DATABASE_URL")
    if db_url and any(db_url.strip().startswith(p) for p in ("postgres://", "postgresql://", "postgresql+")):
        return db_url.strip(), "Environment variable (DATABASE_URL)"

    return None, "Not found"


async def verify_connection(db_url: str, init_schema: bool = False) -> int:
    """Verify Neon connection and inspect/initialize schema."""
    normalized_url = normalize_database_url(db_url)
    masked_url = mask_database_url(db_url)

    print("=" * 70)
    print("TERM SHIELD AI - NEON POSTGRESQL VERIFICATION")
    print("=" * 70)
    print(f"Target Database URL : {masked_url}")
    print(f"Driver              : asyncpg (SQLAlchemy 2.0 Async)")
    print(f"Action              : {'Schema Initialization (--init-schema)' if init_schema else 'Inspection Only (Dry Run)'}")
    print("-" * 70)

    # 1. Create Engine with Neon-compatible pooler resilience settings
    engine = create_async_engine(
        normalized_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # 2. Test Low-Level Connectivity
    print("\n[Step 1/3] Testing PostgreSQL connection...")
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            pg_version = result.scalar_one()

            meta_result = await conn.execute(text("SELECT current_database(), current_user, inet_server_addr();"))
            db_name, db_user, server_ip = meta_result.fetchone()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"  [OK] Successfully connected in {elapsed_ms:.1f}ms")
        print(f"  [OK] Database       : {db_name}")
        print(f"  [OK] Connected User : {db_user}")
        print(f"  [OK] Server Version : {pg_version.split(',')[0] if pg_version else 'PostgreSQL'}")
    except Exception as exc:
        print(f"  [FAIL] Connection failed: {exc}")
        print("\nTroubleshooting tips for Neon:")
        print("  - Ensure your Neon project is active (compute may take 1-2 seconds to wake).")
        print("  - Ensure '?sslmode=require' is included in your connection string.")
        print("  - Verify your password does not contain unencoded special URL characters.")
        await engine.dispose()
        return 1

    # 3. Inspect Existing Schema (Non-destructive)
    print("\n[Step 2/3] Inspecting current database schema...")
    existing_tables: dict[str, int] = {}
    async with engine.connect() as conn:
        def _inspect_tables(sync_conn):
            inspector = inspect(sync_conn)
            table_names = inspector.get_table_names(schema="public")
            counts = {}
            for name in table_names:
                try:
                    res = sync_conn.execute(text(f'SELECT COUNT(*) FROM "{name}"'))
                    counts[name] = res.scalar_one()
                except Exception:
                    counts[name] = -1
            return counts

        existing_tables = await conn.run_sync(_inspect_tables)

    missing_tables = [t for t in EXPECTED_TABLES if t not in existing_tables]
    present_tables = [t for t in EXPECTED_TABLES if t in existing_tables]

    print(f"  Found {len(present_tables)} of {len(EXPECTED_TABLES)} required Term Shield tables in database.")
    for tbl in present_tables:
        print(f"    - {tbl:<24} [PRESENT] ({existing_tables.get(tbl, 0)} rows)")

    if missing_tables:
        print(f"\n  Missing tables ({len(missing_tables)}):")
        for tbl in missing_tables:
            print(f"    - {tbl:<24} [MISSING]")

    # 4. Schema Initialization or Dry-Run Reporting
    print("\n[Step 3/3] Schema action assessment...")
    if not missing_tables:
        print("  [SUCCESS] All 6 required tables are already present in Neon!")
        print("  Database is ready for production without any schema modifications.")
        await engine.dispose()
        return 0

    if not init_schema:
        print("  [DRY-RUN] Missing tables detected, but --init-schema was NOT passed.")
        print("  No changes have been made to your database.")
        print("\n  Proposed DDL to be executed:")
        pg_dialect = postgresql.dialect()
        for tbl_name in missing_tables:
            table_obj = Base.metadata.tables.get(tbl_name)
            if table_obj is not None:
                ddl = str(CreateTable(table_obj).compile(dialect=pg_dialect)).strip()
                print(f"\n--- DDL for '{tbl_name}' ---")
                print(ddl + ";")

        print("\n" + "=" * 70)
        print("TO CREATE THESE TABLES SAFELY:")
        print("Run the command with the --init-schema flag:")
        print("  python scripts/verify_neon_connection.py --init-schema")
        print("=" * 70)
        await engine.dispose()
        return 0

    # Execute Schema Creation safely
    print("  Applying Base.metadata.create_all on Neon PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Re-verify
    async with engine.connect() as conn:
        recheck_tables = await conn.run_sync(lambda sc: inspect(sc).get_table_names(schema="public"))

    still_missing = [t for t in EXPECTED_TABLES if t not in recheck_tables]
    if still_missing:
        print(f"  [ERROR] Schema creation completed but tables still missing: {still_missing}")
        await engine.dispose()
        return 1

    print("  [SUCCESS] All 6 tables successfully initialized in Neon PostgreSQL!")
    for tbl in EXPECTED_TABLES:
        print(f"    - {tbl:<24} [CREATED]")

    await engine.dispose()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify Neon PostgreSQL connectivity and schema readiness.")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional database connection URL (defaults to NEON_DATABASE_URL from environment or backend/.env)",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Initialize missing tables in Neon PostgreSQL (dry-run without this flag)",
    )
    args = parser.parse_args()

    db_url, source = load_target_url(args.url)

    if not db_url:
        print("=" * 70)
        print("TERM SHIELD AI - NEON DATABASE URL REQUIRED")
        print("=" * 70)
        print("No Neon PostgreSQL connection URL was found.")
        print(f"Source checked : {source}")
        print("\nTo test your Neon database safely without modifying your local SQLite:")
        print("1. Open backend/.env")
        print("2. Add this line (replace with your actual Neon connection string):")
        print("     NEON_DATABASE_URL=postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require")
        print("3. Save backend/.env and re-run:")
        print("     python scripts/verify_neon_connection.py")
        print("\nAlternatively, pass the URL directly via CLI:")
        print("     python scripts/verify_neon_connection.py --url \"postgresql://...\"")
        print("=" * 70)
        sys.exit(2)

    exit_code = asyncio.run(verify_connection(db_url, init_schema=args.init_schema))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
