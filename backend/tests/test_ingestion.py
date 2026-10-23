import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.schemas.ingestion import InputType
from app.services.file_ingestion_service import FileIngestionService
from app.services.ingestion_service import IngestionService


def test_process_text_strips_whitespace():
    result = IngestionService.process_text(
        input_type=InputType.TEXT,
        content="   Hello contract   ",
    )

    assert result.input_type == InputType.TEXT
    assert result.content == "Hello contract"
    assert result.character_count == len("Hello contract")


def test_process_text_preserves_multiline_content():
    content = "Clause 1\nPayment shall be made within 30 days."

    result = IngestionService.process_text(
        input_type=InputType.TEXT,
        content=content,
    )

    assert result.content == content
    assert result.character_count == len(content)


@pytest.mark.parametrize(
    "filename",
    [
        "contract.txt",
        "contract.pdf",
        "contract.docx",
    ],
)
def test_validate_allowed_extensions(filename):
    extension = FileIngestionService.validate_extension(filename)

    assert extension == Path(filename).suffix.lower()


@pytest.mark.parametrize(
    "filename",
    [
        "contract.exe",
        "contract.zip",
        "contract.mp3",
        "contract.mp4",
    ],
)
def test_reject_unsupported_extensions(filename):
    with pytest.raises(ValueError, match="Unsupported file type"):
        FileIngestionService.validate_extension(filename)

@pytest.mark.parametrize(
    "filename",
    [
        "contract.png",
        "contract.jpg",
        "contract.jpeg",
    ],
)
def test_validate_image_extensions(filename):
    extension = FileIngestionService.validate_extension(filename)

    assert extension == Path(filename).suffix.lower()

def test_reject_missing_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        FileIngestionService.validate_extension("contract")


@pytest.mark.anyio
async def test_read_file_rejects_missing_filename():
    file = UploadFile(
        filename=None,
        file=io.BytesIO(b"contract"),
    )

    with pytest.raises(ValueError, match="Filename is required"):
        await FileIngestionService.read_file(file)


@pytest.mark.anyio
async def test_read_file_rejects_empty_file():
    file = UploadFile(
        filename="contract.txt",
        file=io.BytesIO(b""),
    )

    with pytest.raises(ValueError, match="Uploaded file is empty"):
        await FileIngestionService.read_file(file)


@pytest.mark.anyio
async def test_read_file_stores_valid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        FileIngestionService,
        "UPLOAD_DIR",
        tmp_path / "uploads",
    )

    file = UploadFile(
        filename="contract.txt",
        file=io.BytesIO(b"Hello contract"),
    )

    file_id, content = await FileIngestionService.read_file(file)

    assert file_id
    assert content == b"Hello contract"

    stored_files = list((tmp_path / "uploads").iterdir())

    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".txt"
    assert stored_files[0].read_bytes() == b"Hello contract"


def test_save_extracted_text(tmp_path, monkeypatch):
    monkeypatch.setattr(
        FileIngestionService,
        "EXTRACTED_DIR",
        tmp_path / "extracted",
    )

    path = FileIngestionService.save_extracted_text(
        file_id="test-file",
        extracted_text="Payment shall be made within 30 days.",
    )

    assert path.exists()
    assert path.name == "test-file.txt"
    assert (
        path.read_text(encoding="utf-8")
        == "Payment shall be made within 30 days."
    )
    