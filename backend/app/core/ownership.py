"""Shared helpers for enforcing per-user data isolation on contract data."""
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract
from app.models.user import User


def _validate_file_id(file_id: str) -> str:
    if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id:
        return ""
    return file_id


def _extracted_path(file_id: str) -> Path:
    safe_id = _validate_file_id(file_id)
    if not safe_id:
        return Path("storage") / "extracted" / "invalid_nonexistent.txt"
    return Path("storage") / "extracted" / f"{safe_id}.txt"


def _clauses_path(file_id: str) -> Path:
    safe_id = _validate_file_id(file_id)
    if not safe_id:
        return Path("storage") / "clauses" / "invalid_nonexistent.json"
    return Path("storage") / "clauses" / f"{safe_id}.json"


def _uploaded_contract_glob(file_id: str) -> list[Path]:
    safe_id = _validate_file_id(file_id)
    if not safe_id:
        return []
    return list((Path("storage") / "uploads").glob(f"{safe_id}.*"))


def contract_exists(file_id: str) -> bool:
    """True if a contract with the given file_id has any data stored."""
    return (
        _extracted_path(file_id).exists()
        or _clauses_path(file_id).exists()
        or bool(_uploaded_contract_glob(file_id))
    )


async def require_owned_contract(
    db: AsyncSession,
    current_user: User,
    file_id: str,
) -> Contract | None:
    """
    Enforce that the authenticated user owns the contract for `file_id`.

    Returns the Contract row if one exists, or None when there is no contract
    data at all (so callers can raise their own 404). Raises 404 if the data
    exists but belongs to a different user (do not leak existence).
    """
    result = await db.execute(
        Contract.__table__.select().where(Contract.id == file_id)
    )
    contract = result.mappings().first()

    if contract is None:
        return None

    if contract["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted document not found.",
        )

    return contract
