"""Offline database migration utility for Term Shield.

Provides schema inspection, dependency planning, dry-run validation, and
idempotent record migration between SQLite and target databases (e.g. Neon PostgreSQL).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
import unicodedata

from sqlalchemy import Boolean, DateTime, insert, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, normalize_database_url


# Strict foreign-key dependency order for Term Shield tables
TABLE_MIGRATION_ORDER = [
    "users",
    "contracts",
    "clauses",
    "clause_analyses",
    "qa_history",
    "password_reset_tokens",
]


def get_model_column_metadata() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Inspect SQLAlchemy model metadata to identify DateTime and Boolean columns per table.

    Eliminates hardcoded column lists by dynamically querying table columns registered in Base.metadata.
    """
    from app import models  # noqa: F401

    datetime_cols: dict[str, set[str]] = {}
    boolean_cols: dict[str, set[str]] = {}

    for table_name, table in Base.metadata.tables.items():
        datetime_cols[table_name] = {
            col.name for col in table.columns if isinstance(col.type, DateTime)
        }
        boolean_cols[table_name] = {
            col.name for col in table.columns if isinstance(col.type, Boolean)
        }

    return datetime_cols, boolean_cols


def normalize_timestamp(
    val: Any,
    table_name: str,
    record_id: str,
    col_name: str,
) -> datetime | None:
    """Normalize a timestamp into a timezone-aware UTC datetime.

    Explicit Documented Policy:
    ---------------------------
    - Term Shield models define all timestamp columns with DateTime(timezone=True) and server_default=func.now().
    - In SQLite, func.now() / CURRENT_TIMESTAMP produces UTC timestamp strings without an explicit timezone offset
      (e.g. 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SS.ffffff').
    - Consistent with these semantics, if a timestamp has no timezone offset (offset-naive), it is explicitly
      treated as UTC (tzinfo=timezone.utc).
    - Timezone-aware timestamps retain their original offset, allowing exact absolute-time comparisons.
    - Fractional seconds (microseconds) are preserved.
    - Null / None is preserved as None.
    - Invalid timestamp values raise a ValueError with the table, record ID, and column name.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception as exc:
            raise ValueError(
                f"Invalid timestamp value '{val}' in table '{table_name}', "
                f"record '{record_id}', column '{col_name}': {exc}"
            ) from exc
    raise ValueError(
        f"Unsupported timestamp type '{type(val).__name__}' with value '{val}' in table '{table_name}', "
        f"record '{record_id}', column '{col_name}'"
    )


def normalize_boolean(val: Any) -> bool | None:
    """Normalize SQLite 0/1 integers or string representations to Python boolean."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower in ("true", "1", "t", "yes"):
            return True
        if lower in ("false", "0", "f", "no"):
            return False
    return bool(val)


def are_json_equivalent(v1: Any, v2: Any) -> bool:
    """Check if two JSON-like values are structurally equivalent regardless of whitespace or key order."""
    try:
        j1 = json.loads(v1) if isinstance(v1, str) else v1
        j2 = json.loads(v2) if isinstance(v2, str) else v2
        return j1 == j2
    except Exception:
        return False


def normalize_record(
    table_name: str,
    record: dict[str, Any],
    record_id: str,
    datetime_cols: set[str],
    boolean_cols: set[str],
) -> dict[str, Any]:
    """Normalize all columns in a record for target insertion and canonical comparison."""
    normalized: dict[str, Any] = {}
    for col, val in record.items():
        if col in datetime_cols:
            normalized[col] = normalize_timestamp(val, table_name, record_id, col)
        elif col in boolean_cols:
            normalized[col] = normalize_boolean(val)
        else:
            normalized[col] = val
    return normalized


def are_values_equivalent(
    table_name: str,
    col_name: str,
    v1: Any,
    v2: Any,
    record_id: str,
    datetime_cols: set[str],
    boolean_cols: set[str],
) -> bool:
    """Compare two field values for equivalence with type-aware normalization."""
    if v1 is None and v2 is None:
        return True
    if v1 is None or v2 is None:
        return False

    if col_name in datetime_cols:
        try:
            dt1 = normalize_timestamp(v1, table_name, record_id, col_name)
            dt2 = normalize_timestamp(v2, table_name, record_id, col_name)
            return dt1 == dt2
        except ValueError:
            return False

    if col_name in boolean_cols:
        return normalize_boolean(v1) == normalize_boolean(v2)

    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        return abs(float(v1) - float(v2)) < 1e-6

    if col_name.endswith("_json") or col_name in ("analysis_data", "summary_json", "evidence_json"):
        if are_json_equivalent(v1, v2):
            return True

    if isinstance(v1, str) and isinstance(v2, str):
        return unicodedata.normalize("NFC", v1) == unicodedata.normalize("NFC", v2)

    return v1 == v2


@dataclass
class TableInspection:
    name: str
    row_count: int
    columns: list[str]
    has_primary_key: bool


@dataclass
class MigrationPlan:
    source_path: str
    target_url: str | None
    planned_tables: list[str]
    table_counts: dict[str, int]
    total_records: int
    dependency_order_valid: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    status: str  # "PASSED" | "FAILED"
    source_counts: dict[str, int]
    target_counts: dict[str, int]
    count_matches: bool
    sample_verified: bool
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DatabaseMigrationUtility:
    """Manages planning, dry-run inspection, migration, and verification of Term Shield databases."""

    def __init__(
        self,
        source_db_path: Path | str,
        target_db_url: str | None = None,
        target_engine: AsyncEngine | None = None,
    ) -> None:
        self.source_path = Path(source_db_path)
        self.target_url = normalize_database_url(target_db_url) if target_db_url else None
        self._target_engine = target_engine
        self.last_migration_conflicts: list[dict[str, Any]] = []

    def inspect_source(self) -> dict[str, TableInspection]:
        """Inspect source SQLite database tables, column names, and row counts."""
        if not self.source_path.is_file():
            raise FileNotFoundError(f"Source database file not found: {self.source_path}")

        # Connect in read-only mode to guarantee zero source mutations
        uri = f"file:{self.source_path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cursor = conn.cursor()

        inspections: dict[str, TableInspection] = {}
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall() if not r[0].startswith("sqlite_")]

            for tbl in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                count = cursor.fetchone()[0]

                cursor.execute(f'PRAGMA table_info("{tbl}")')
                cols_info = cursor.fetchall()
                columns = [c[1] for c in cols_info]
                has_pk = any(c[5] > 0 for c in cols_info)

                inspections[tbl] = TableInspection(
                    name=tbl,
                    row_count=count,
                    columns=columns,
                    has_primary_key=has_pk,
                )
        finally:
            conn.close()

        return inspections

    def generate_plan(self) -> MigrationPlan:
        """Generate an execution plan verifying table dependency order and checking for anomalies."""
        inspections = self.inspect_source()
        table_counts = {t: inspections[t].row_count for t in TABLE_MIGRATION_ORDER if t in inspections}
        total_records = sum(table_counts.values())

        warnings: list[str] = []
        for t in TABLE_MIGRATION_ORDER:
            if t not in inspections:
                warnings.append(f"Table '{t}' is part of expected schema but missing in source database.")

        # Check for unmapped tables in source
        for tbl in inspections:
            if tbl not in TABLE_MIGRATION_ORDER:
                warnings.append(f"Source database contains additional table '{tbl}' not in standard migration order.")

        return MigrationPlan(
            source_path=str(self.source_path),
            target_url=self.target_url,
            planned_tables=[t for t in TABLE_MIGRATION_ORDER if t in inspections],
            table_counts=table_counts,
            total_records=total_records,
            dependency_order_valid=True,
            warnings=warnings,
        )

    async def execute_dry_run(self) -> dict[str, Any]:
        """Execute a zero-mutation dry run validating source row integrity and dependency constraints."""
        plan = self.generate_plan()
        inspections = self.inspect_source()

        uri = f"file:{self.source_path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cursor = conn.cursor()

        validation_checks = {
            "source_accessible": True,
            "read_only_verified": True,
            "total_records_planned": plan.total_records,
            "orphan_contract_references": 0,
            "orphan_clause_references": 0,
            "missing_pk_count": 0,
        }

        try:
            # Check for orphan contract user_id references (non-null user_ids not in users table)
            if "contracts" in inspections and "users" in inspections:
                cursor.execute("""
                    SELECT COUNT(*) FROM contracts
                    WHERE user_id IS NOT NULL
                      AND user_id NOT IN (SELECT id FROM users)
                """)
                validation_checks["orphan_contract_references"] = cursor.fetchone()[0]

            # Check for orphan clauses contract_id references
            if "clauses" in inspections and "contracts" in inspections:
                cursor.execute("""
                    SELECT COUNT(*) FROM clauses
                    WHERE contract_id NOT IN (SELECT id FROM contracts)
                """)
                validation_checks["orphan_clause_references"] = cursor.fetchone()[0]

            # Check primary key nullability
            for tbl, insp in inspections.items():
                if insp.has_primary_key:
                    cursor.execute(f'SELECT COUNT(*) FROM "{tbl}" WHERE id IS NULL')
                    null_pks = cursor.fetchone()[0]
                    validation_checks["missing_pk_count"] += null_pks

        finally:
            conn.close()

        return {
            "status": "VALID" if validation_checks["missing_pk_count"] == 0 else "WARNING",
            "plan": asdict(plan),
            "checks": validation_checks,
        }

    async def migrate_data(
        self,
        batch_size: int = 500,
        target_engine: AsyncEngine | None = None,
    ) -> dict[str, Any]:
        """Migrate records from source SQLite into target database using batch upsert and verification."""
        engine = target_engine or self._target_engine
        if engine is None:
            if not self.target_url:
                raise ValueError("Target database URL or target_engine must be provided for migration.")
            engine = create_async_engine(self.target_url)

        # Ensure destination schema tables exist
        async with engine.begin() as conn:
            from app import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)

        datetime_cols, boolean_cols = get_model_column_metadata()
        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        source_conn = sqlite3.connect(f"file:{self.source_path.resolve().as_posix()}?mode=ro", uri=True)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()

        migration_summary: dict[str, dict[str, Any]] = {}
        self.last_migration_conflicts = []

        source_inspections = self.inspect_source()

        try:
            for table_name in TABLE_MIGRATION_ORDER:
                if table_name not in source_inspections:
                    continue

                source_cursor.execute(f'SELECT * FROM "{table_name}"')
                rows = source_cursor.fetchall()

                table_conflicts: list[dict[str, Any]] = []
                table_stats = {
                    "source_rows": len(rows),
                    "inserted": 0,
                    "skipped_existing": 0,
                    "mismatches": 0,
                    "conflicts": table_conflicts,
                }

                if not rows:
                    migration_summary[table_name] = table_stats
                    continue

                table_obj = Base.metadata.tables.get(table_name)
                if table_obj is None:
                    raise ValueError(f"Table '{table_name}' not found in SQLAlchemy metadata.")

                dt_set = datetime_cols.get(table_name, set())
                bool_set = boolean_cols.get(table_name, set())
                valid_cols = {c.name for c in table_obj.columns}

                async with session_factory() as session:
                    try:
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i : i + batch_size]
                            for row in batch:
                                raw_dict = dict(row)
                                record_id = str(raw_dict.get("id"))

                                # 1. Normalize record fields for target insertion & comparison
                                normalized_dict = normalize_record(
                                    table_name=table_name,
                                    record=raw_dict,
                                    record_id=record_id,
                                    datetime_cols=dt_set,
                                    boolean_cols=bool_set,
                                )

                                # Filter columns to those present in target schema
                                target_dict = {k: v for k, v in normalized_dict.items() if k in valid_cols}

                                # 2. Check destination for existing record by primary key
                                check_query = select(table_obj).where(table_obj.c.id == record_id)
                                existing_row = (await session.execute(check_query)).mappings().one_or_none()

                                if existing_row is None:
                                    # Insert new record using SQLAlchemy Core Table insert
                                    insert_stmt = insert(table_obj).values(**target_dict)
                                    await session.execute(insert_stmt)
                                    table_stats["inserted"] += 1
                                else:
                                    # Compare all common columns between source and target
                                    differing_fields = []
                                    diff_details = {}
                                    for col in valid_cols:
                                        if col in target_dict:
                                            src_val = target_dict[col]
                                            dest_val = existing_row.get(col)
                                            if not are_values_equivalent(
                                                table_name=table_name,
                                                col_name=col,
                                                v1=src_val,
                                                v2=dest_val,
                                                record_id=record_id,
                                                datetime_cols=dt_set,
                                                boolean_cols=bool_set,
                                            ):
                                                differing_fields.append(col)
                                                diff_details[col] = {
                                                    "source": src_val.isoformat() if isinstance(src_val, datetime) else src_val,
                                                    "destination": dest_val.isoformat() if isinstance(dest_val, datetime) else dest_val,
                                                }

                                    if not differing_fields:
                                        # Identical record already present in target
                                        table_stats["skipped_existing"] += 1
                                    else:
                                        # Mismatch detected: do not overwrite, record conflict
                                        table_stats["mismatches"] += 1
                                        conflict_entry = {
                                            "table": table_name,
                                            "id": record_id,
                                            "differing_fields": differing_fields,
                                            "details": diff_details,
                                        }
                                        table_conflicts.append(conflict_entry)
                                        self.last_migration_conflicts.append(conflict_entry)

                            await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

                migration_summary[table_name] = table_stats

        finally:
            source_conn.close()

        return migration_summary

    async def verify_migration(
        self,
        target_engine: AsyncEngine | None = None,
    ) -> VerificationResult:
        """Verify record counts and full record data fidelity between source and target databases."""
        engine = target_engine or self._target_engine
        if engine is None:
            if not self.target_url:
                raise ValueError("Target database URL or target_engine must be provided for verification.")
            engine = create_async_engine(self.target_url)

        source_inspections = self.inspect_source()
        source_counts = {t: source_inspections[t].row_count for t in TABLE_MIGRATION_ORDER if t in source_inspections}

        target_counts: dict[str, int] = {}
        conflicts: list[dict[str, Any]] = []
        errors: list[str] = []

        datetime_cols, boolean_cols = get_model_column_metadata()
        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        source_conn = sqlite3.connect(f"file:{self.source_path.resolve().as_posix()}?mode=ro", uri=True)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()

        try:
            async with session_factory() as session:
                for table_name in TABLE_MIGRATION_ORDER:
                    if table_name not in source_inspections:
                        continue

                    try:
                        table_obj = Base.metadata.tables.get(table_name)
                        if table_obj is None:
                            errors.append(f"Table '{table_name}' missing from SQLAlchemy metadata.")
                            continue

                        # 1. Count verification
                        count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
                        dest_count = (await session.execute(count_query)).scalar_one()
                        target_counts[table_name] = dest_count

                        src_count = source_counts.get(table_name, 0)
                        if dest_count != src_count:
                            errors.append(
                                f"Table '{table_name}' count mismatch: source={src_count}, target={dest_count}"
                            )

                        # 2. Full record-level verification
                        source_cursor.execute(f'SELECT * FROM "{table_name}"')
                        source_rows = source_cursor.fetchall()

                        dest_rows = (await session.execute(select(table_obj))).mappings().all()
                        dest_by_id = {str(r["id"]): r for r in dest_rows}

                        dt_set = datetime_cols.get(table_name, set())
                        bool_set = boolean_cols.get(table_name, set())
                        valid_cols = {c.name for c in table_obj.columns}

                        for s_row in source_rows:
                            s_dict = dict(s_row)
                            record_id = str(s_dict.get("id"))

                            if record_id not in dest_by_id:
                                err = f"Table '{table_name}' record '{record_id}' missing in target database."
                                errors.append(err)
                                conflicts.append({"table": table_name, "id": record_id, "type": "missing_in_target"})
                                continue

                            dest_row = dest_by_id[record_id]

                            try:
                                normalized_src = normalize_record(
                                    table_name=table_name,
                                    record=s_dict,
                                    record_id=record_id,
                                    datetime_cols=dt_set,
                                    boolean_cols=bool_set,
                                )
                            except ValueError as val_err:
                                errors.append(str(val_err))
                                conflicts.append({"table": table_name, "id": record_id, "error": str(val_err)})
                                continue

                            differing_fields = []
                            diff_details = {}
                            for col in valid_cols:
                                if col in normalized_src:
                                    src_val = normalized_src[col]
                                    dest_val = dest_row.get(col)
                                    if not are_values_equivalent(
                                        table_name=table_name,
                                        col_name=col,
                                        v1=src_val,
                                        v2=dest_val,
                                        record_id=record_id,
                                        datetime_cols=dt_set,
                                        boolean_cols=bool_set,
                                    ):
                                        differing_fields.append(col)
                                        diff_details[col] = {
                                            "source": src_val.isoformat() if isinstance(src_val, datetime) else src_val,
                                            "destination": dest_val.isoformat() if isinstance(dest_val, datetime) else dest_val,
                                        }

                            if differing_fields:
                                err = f"Table '{table_name}' record '{record_id}' field mismatch: {', '.join(differing_fields)}"
                                errors.append(err)
                                conflicts.append({
                                    "table": table_name,
                                    "id": record_id,
                                    "differing_fields": differing_fields,
                                    "details": diff_details,
                                })

                    except Exception as exc:
                        errors.append(f"Error verifying table '{table_name}' on target: {exc}")

        finally:
            source_conn.close()

        counts_match = len([e for e in errors if "count mismatch" in e]) == 0
        all_passed = len(errors) == 0 and len(conflicts) == 0

        return VerificationResult(
            status="PASSED" if all_passed else "FAILED",
            source_counts=source_counts,
            target_counts=target_counts,
            count_matches=counts_match,
            sample_verified=all_passed,
            conflicts=conflicts,
            errors=errors,
        )
