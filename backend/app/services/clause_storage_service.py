import json
from pathlib import Path

from app.schemas.clause import Clause


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

        cls.CLAUSES_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = cls._get_path(file_id)

        data = {
            "file_id": file_id,
            "clause_count": len(clauses),
            "clauses": [
                clause.model_dump()
                for clause in clauses
            ],
        }

        output_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return output_path

    @classmethod
    def load_clauses(
        cls,
        file_id: str,
    ) -> list[Clause]:

        try:
            file_path = cls._get_path(file_id)
        except ValueError:
            return []

        if not file_path.exists():
            return []

        data = json.loads(
            file_path.read_text(
                encoding="utf-8",
            )
        )

        return [
            Clause(**clause)
            for clause in data["clauses"]
        ]
