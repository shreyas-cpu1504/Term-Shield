from pathlib import Path
import re
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class FileIngestionService:
    ALLOWED_EXTENSIONS = {
        ".txt",
        ".pdf",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
    }

    BASE_STORAGE_DIR = Path("storage")
    UPLOAD_DIR = BASE_STORAGE_DIR / "uploads"
    EXTRACTED_DIR = BASE_STORAGE_DIR / "extracted"

    @staticmethod
    def sanitize_filename(filename: str | None) -> str:
        """Sanitize client-supplied filenames to prevent path traversal and retain safe display names."""
        if not filename:
            return "unnamed_contract.txt"

        # Normalize slashes and take the basename
        clean = filename.replace("\\", "/").rstrip("/").split("/")[-1].strip()

        # Remove control characters, null bytes, etc.
        clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)

        # Strip leading dots to prevent hidden files or traversal remnants
        clean = clean.lstrip(".")

        # If empty or only spaces/dots remain, provide safe default
        if not clean or clean.strip(". ") == "":
            extension = Path(filename).suffix.lower()
            if extension in FileIngestionService.ALLOWED_EXTENSIONS:
                return f"contract{extension}"
            return "unnamed_contract.txt"

        return clean

    @staticmethod
    def validate_file_id(file_id: str) -> str:
        """Ensure file_id does not contain path traversal characters."""
        if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id:
            raise ValueError("Invalid file identifier.")
        return file_id

    @staticmethod
    def validate_extension(filename: str) -> str:
        extension = Path(filename).suffix.lower()

        if extension not in FileIngestionService.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension or 'unknown'}"
            )

        return extension

    @staticmethod
    async def read_file(file: UploadFile) -> tuple[str, bytes]:
        if not file.filename:
            raise ValueError("Filename is required.")

        extension = FileIngestionService.validate_extension(
            file.filename
        )

        content = await file.read()

        if not content:
            raise ValueError("Uploaded file is empty.")

        settings = get_settings()
        max_file_size = settings.max_upload_size_mb * 1024 * 1024

        if len(content) > max_file_size:
            raise ValueError(
                f"File size exceeds the {settings.max_upload_size_mb} MB limit."
            )

        file_id = str(uuid4())

        FileIngestionService.UPLOAD_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        stored_filename = f"{file_id}{extension}"
        stored_path = (
            FileIngestionService.UPLOAD_DIR / stored_filename
        ).resolve()

        if not stored_path.is_relative_to(FileIngestionService.UPLOAD_DIR.resolve()):
            raise ValueError("Invalid storage path destination.")

        stored_path.write_bytes(content)

        return file_id, content

    @staticmethod
    def save_extracted_text(
        file_id: str,
        extracted_text: str,
    ) -> Path:
        clean_file_id = FileIngestionService.validate_file_id(file_id)

        FileIngestionService.EXTRACTED_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        extracted_path = (
            FileIngestionService.EXTRACTED_DIR
            / f"{clean_file_id}.txt"
        ).resolve()

        if not extracted_path.is_relative_to(FileIngestionService.EXTRACTED_DIR.resolve()):
            raise ValueError("Invalid storage path destination.")

        extracted_path.write_text(
            extracted_text,
            encoding="utf-8",
        )

        return extracted_path