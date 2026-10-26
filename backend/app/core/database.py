from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

def normalize_database_url(url: str) -> str:
    """Normalize standard PostgreSQL connection schemes and parameters to SQLAlchemy's asyncpg dialect.

    - Replaces postgres:// and postgresql:// schemes with postgresql+asyncpg://
    - Converts 'sslmode' query parameter (e.g. sslmode=require) to asyncpg's supported 'ssl' parameter
    - Strips unsupported libpq-only parameters (e.g. channel_binding, endpoint, gssencmode)
    - Preserves SQLite and non-PostgreSQL URLs completely unchanged
    - Enforces SSL/TLS security on Neon databases
    """
    if not url or "sqlite" in url:
        return url

    is_postgres = (
        url.startswith("postgres://")
        or url.startswith("postgresql://")
        or url.startswith("postgresql+")
    )
    if not is_postgres:
        return url

    parts = urlsplit(url)

    # 1. Normalize scheme to postgresql+asyncpg
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    elif scheme in ("postgresql+psycopg2", "postgresql+pg8000"):
        scheme = "postgresql+asyncpg"

    # 2. Normalize query parameters for asyncpg compatibility
    query_params = dict(parse_qsl(parts.query, keep_blank_values=True))

    # asyncpg expects 'ssl' rather than libpq's 'sslmode'
    sslmode = query_params.pop("sslmode", None)
    if sslmode:
        # Preserve the exact security setting (e.g. 'require', 'verify-ca', 'verify-full')
        query_params["ssl"] = sslmode
    elif "neon.tech" in parts.netloc and "ssl" not in query_params:
        # Neon strictly requires SSL
        query_params["ssl"] = "require"

    # Strip libpq-specific parameters unsupported by asyncpg
    for param in ("channel_binding", "endpoint", "gssencmode"):
        query_params.pop(param, None)

    new_query = urlencode(query_params)
    return urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))


db_url = normalize_database_url(
    settings.effective_database_url if hasattr(settings, "effective_database_url") else settings.database_url
)

# Ensure local storage directory exists for SQLite database files
if "sqlite" in db_url:
    clean_path = db_url.split(":///", 1)[-1] if ":///" in db_url else ""
    if clean_path and not clean_path.startswith(":memory:"):
        db_file = Path(clean_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

connect_args = {}
engine_kwargs = {
    "echo": settings.debug,
}

if "sqlite" in db_url:
    connect_args["check_same_thread"] = False
else:
    # Serverless / Neon pooler resilience settings with bounded memory footprint
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 3
    engine_kwargs["pool_timeout"] = 30.0

engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)

# Enforce foreign key constraints for SQLite
if "sqlite" in db_url:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables safely during application startup."""
    # Import models so all tables are registered with Base.metadata
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _migrate_profile_photo(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            if "users" in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns("users")]
                if "profile_photo" not in cols:
                    sync_conn.execute(text("ALTER TABLE users ADD COLUMN profile_photo TEXT"))

        await conn.run_sync(_migrate_profile_photo)


async def close_db() -> None:
    """Dispose of the database engine and connection pool cleanly."""
    await engine.dispose()

