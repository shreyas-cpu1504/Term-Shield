import json
from pathlib import Path

from app.schemas.clause import Clause
from app.services.storage_service import get_storage_service


class ClauseStorageService:

    CLAUSES_DIR = Path("storage/clauses")

    @classmethod
    def _get_path(cls, file_id: str) -> Path:
        if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id:
            raise ValueError("Invalid file identifier.")
        path = (cls.CLAUSES_DIR / f"{file_id}.json").resolve()
        if not path.is_relative_to(cls.CLAUSES_DIR.resolve()):
            raise ValueError("Path escapes clauses storage boundary.")
        return path

    @classmethod
    def save_clauses(
        cls,
        file_id: str,
        clauses: list[Clause],
    ) -> Path:
        data = {
            "file_id": file_id,
            "clause_count": len(clauses),
            "clauses": [
                clause.model_dump()
                for clause in clauses
            ],
        }
        saved_path = get_storage_service().save_clauses_json(file_id, data)
        return Path(saved_path)

    @classmethod
    def load_clauses(
        cls,
        file_id: str,
    ) -> list[Clause]:
        data = get_storage_service().load_clauses_json(file_id)
        if not data or "clauses" not in data:
            return []

        return [
            Clause(**clause)
            for clause in data["clauses"]
        ]
