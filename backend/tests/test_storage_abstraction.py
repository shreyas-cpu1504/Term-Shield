import json
from pathlib import Path
import pytest

from app.schemas.clause import Clause
from app.services.storage_service import (
    BaseStorageService,
    LocalStorageService,
    get_storage_service,
    set_storage_service,
)
from app.services.file_ingestion_service import FileIngestionService
from app.services.clause_storage_service import ClauseStorageService
from app.core.ownership import contract_exists


@pytest.fixture
def temp_storage(tmp_path: Path):
    """Provide an isolated LocalStorageService backed by a temporary directory."""
    service = LocalStorageService(base_dir=tmp_path)
    original_service = get_storage_service()
    set_storage_service(service)
    yield service
    set_storage_service(original_service)


def test_interface_compliance(temp_storage: LocalStorageService):
    """Verify that LocalStorageService implements BaseStorageService."""
    assert isinstance(temp_storage, BaseStorageService)


def test_upload_lifecycle(temp_storage: LocalStorageService):
    """Test saving, checking existence, reading, and deleting raw uploaded files."""
    file_id = "test-upload-uuid"
    content = b"Contract raw content for upload test"

    # Initially does not exist
    assert not temp_storage.upload_exists(file_id)
    assert not temp_storage.upload_exists(file_id, ".pdf")
    assert temp_storage.read_upload(file_id, ".pdf") is None

    # Save upload
    saved_path = temp_storage.save_upload(file_id, ".pdf", content)
    assert Path(saved_path).is_file()
    assert Path(saved_path).name == f"{file_id}.pdf"

    # Existence checks
    assert temp_storage.upload_exists(file_id)
    assert temp_storage.upload_exists(file_id, ".pdf")
    assert not temp_storage.upload_exists(file_id, ".docx")

    # Read content
    read_data = temp_storage.read_upload(file_id, ".pdf")
    assert read_data == content

    # Extension without dot should also work
    assert temp_storage.upload_exists(file_id, "pdf")
    assert temp_storage.read_upload(file_id, "pdf") == content

    # Delete upload
    deleted = temp_storage.delete_upload(file_id, ".pdf")
    assert deleted is True
    assert not temp_storage.upload_exists(file_id)
    assert temp_storage.read_upload(file_id, ".pdf") is None

    # Deleting again returns False (missing file handling)
    assert temp_storage.delete_upload(file_id, ".pdf") is False


def test_extracted_text_lifecycle(temp_storage: LocalStorageService):
    """Test saving, checking existence, reading, and deleting extracted text."""
    file_id = "test-extracted-uuid"
    sample_text = "This is a sample extracted contract text.\nSection 1: Confidentiality."

    # Initially does not exist
    assert not temp_storage.extracted_text_exists(file_id)
    assert temp_storage.read_extracted_text(file_id) is None

    # Save extracted text
    saved_path = temp_storage.save_extracted_text(file_id, sample_text)
    assert Path(saved_path).is_file()
    assert Path(saved_path).name == f"{file_id}.txt"

    # Check existence
    assert temp_storage.extracted_text_exists(file_id)

    # Read extracted text
    loaded_text = temp_storage.read_extracted_text(file_id)
    assert loaded_text == sample_text

    # Delete extracted text
    deleted = temp_storage.delete_extracted_text(file_id)
    assert deleted is True
    assert not temp_storage.extracted_text_exists(file_id)
    assert temp_storage.read_extracted_text(file_id) is None

    # Repeated delete returns False without error
    assert temp_storage.delete_extracted_text(file_id) is False


def test_clause_json_lifecycle(temp_storage: LocalStorageService):
    """Test saving, checking existence, loading, and deleting clause JSON data."""
    file_id = "test-clauses-uuid"
    clauses_data = [
        {
            "clause_id": "c1",
            "clause_title": "Confidentiality",
            "clause_text": "Both parties agree to hold information in confidence.",
            "clause_type": "confidentiality",
        },
        {
            "clause_id": "c2",
            "clause_title": "Termination",
            "clause_text": "Either party may terminate upon 30 days notice.",
            "clause_type": "termination",
        },
    ]

    # Initially does not exist
    assert not temp_storage.clauses_json_exists(file_id)
    assert temp_storage.load_clauses_json(file_id) is None

    # Save clause JSON
    saved_path = temp_storage.save_clauses_json(file_id, clauses_data)
    assert Path(saved_path).is_file()
    assert Path(saved_path).name == f"{file_id}.json"

    # Check existence
    assert temp_storage.clauses_json_exists(file_id)

    # Load clause JSON
    loaded_data = temp_storage.load_clauses_json(file_id)
    assert loaded_data is not None
    assert loaded_data["file_id"] == file_id
    assert loaded_data["clause_count"] == 2
    assert len(loaded_data["clauses"]) == 2
    assert loaded_data["clauses"][0]["clause_id"] == "c1"

    # Delete clause JSON
    deleted = temp_storage.delete_clauses_json(file_id)
    assert deleted is True
    assert not temp_storage.clauses_json_exists(file_id)
    assert temp_storage.load_clauses_json(file_id) is None

    # Deleting again returns False without crashing
    assert temp_storage.delete_clauses_json(file_id) is False


def test_missing_file_handling(temp_storage: LocalStorageService):
    """Verify that operations on non-existent files return None or False without crashing."""
    missing_id = "non-existent-file-id-12345"

    assert temp_storage.read_upload(missing_id, ".pdf") is None
    assert temp_storage.delete_upload(missing_id, ".pdf") is False
    assert temp_storage.upload_exists(missing_id) is False

    assert temp_storage.read_extracted_text(missing_id) is None
    assert temp_storage.delete_extracted_text(missing_id) is False
    assert temp_storage.extracted_text_exists(missing_id) is False

    assert temp_storage.load_clauses_json(missing_id) is None
    assert temp_storage.delete_clauses_json(missing_id) is False
    assert temp_storage.clauses_json_exists(missing_id) is False

    assert temp_storage.has_contract_data(missing_id) is False


def test_path_traversal_protection(temp_storage: LocalStorageService):
    """Verify that path traversal attempts raise ValueError or return safe falsy responses."""
    malicious_ids = [
        "../etc/passwd",
        "..\\windows\\system32",
        "sub/../../secret",
        "file\x00name",
        "",
        "/absolute/path",
    ]

    for bad_id in malicious_ids:
        with pytest.raises(ValueError):
            temp_storage.save_upload(bad_id, ".pdf", b"test")

        with pytest.raises(ValueError):
            temp_storage.save_extracted_text(bad_id, "test")

        with pytest.raises(ValueError):
            temp_storage.save_clauses_json(bad_id, {})

        # Reads and deletes should handle gracefully without crashing or escaping boundary
        assert temp_storage.read_upload(bad_id, ".pdf") is None
        assert temp_storage.delete_upload(bad_id, ".pdf") is False
        assert temp_storage.upload_exists(bad_id) is False
        assert temp_storage.read_extracted_text(bad_id) is None
        assert temp_storage.delete_extracted_text(bad_id) is False
        assert temp_storage.extracted_text_exists(bad_id) is False
        assert temp_storage.load_clauses_json(bad_id) is None
        assert temp_storage.delete_clauses_json(bad_id) is False
        assert temp_storage.has_contract_data(bad_id) is False


def test_has_contract_data(temp_storage: LocalStorageService):
    """Verify has_contract_data returns True when any piece of data exists."""
    file_id = "test-composite-uuid"

    assert not temp_storage.has_contract_data(file_id)

    # 1. Extracted text only
    temp_storage.save_extracted_text(file_id, "Sample extracted text")
    assert temp_storage.has_contract_data(file_id)
    temp_storage.delete_extracted_text(file_id)
    assert not temp_storage.has_contract_data(file_id)

    # 2. Clause JSON only
    temp_storage.save_clauses_json(file_id, {"file_id": file_id, "clauses": []})
    assert temp_storage.has_contract_data(file_id)
    temp_storage.delete_clauses_json(file_id)
    assert not temp_storage.has_contract_data(file_id)

    # 3. Raw upload only
    temp_storage.save_upload(file_id, ".txt", b"raw content")
    assert temp_storage.has_contract_data(file_id)
    temp_storage.delete_upload(file_id, ".txt")
    assert not temp_storage.has_contract_data(file_id)


def test_file_ingestion_service_delegation(temp_storage: LocalStorageService):
    """Verify FileIngestionService.save_extracted_text delegates to storage service."""
    file_id = "delegation-file-id"
    text = "Extracted legal terms and conditions."

    saved_path = FileIngestionService.save_extracted_text(file_id, text)
    assert isinstance(saved_path, Path)
    assert saved_path.is_file()
    assert temp_storage.read_extracted_text(file_id) == text


def test_clause_storage_service_delegation(temp_storage: LocalStorageService):
    """Verify ClauseStorageService save_clauses and load_clauses delegate to storage service."""
    file_id = "delegation-clause-id"
    sample_text = "This agreement is governed by the laws of India."
    clauses = [
        Clause(
            clause_id="cl-1",
            title="Governing Law",
            text=sample_text,
            order=1,
            character_count=len(sample_text),
            clause_type="governing_law",
        )
    ]

    # Save clauses
    saved_path = ClauseStorageService.save_clauses(file_id, clauses)
    assert isinstance(saved_path, Path)
    assert saved_path.is_file()

    # Load clauses
    loaded_clauses = ClauseStorageService.load_clauses(file_id)
    assert len(loaded_clauses) == 1
    assert loaded_clauses[0].clause_id == "cl-1"
    assert loaded_clauses[0].clause_type == "governing_law"

    # Loading non-existent returns empty list
    assert ClauseStorageService.load_clauses("non-existent-id") == []


def test_ownership_contract_exists_delegation(temp_storage: LocalStorageService):
    """Verify contract_exists in ownership.py works seamlessly with storage service."""
    file_id = "ownership-test-id"

    assert contract_exists(file_id) is False

    temp_storage.save_extracted_text(file_id, "Contract text")
    assert contract_exists(file_id) is True

    temp_storage.delete_extracted_text(file_id)
    assert contract_exists(file_id) is False
