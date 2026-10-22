import io
import json
import pytest
from botocore.exceptions import ClientError

from app.services.storage_service import (
    BaseStorageService,
    LocalStorageService,
    R2StorageService,
    get_storage_service,
    set_storage_service,
)
from app.core.config import get_settings


class MockS3Client:
    """In-memory mock of the boto3 S3 client for testing R2 operations without cloud credentials or network."""

    def __init__(self):
        self.objects: dict[str, dict] = {}
        self.put_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str | None = None, **kwargs):
        self.put_calls.append({
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            **kwargs,
        })
        self.objects[Key] = {
            "Body": Body if isinstance(Body, bytes) else bytes(Body),
            "ContentType": ContentType,
            "Metadata": kwargs,
        }
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_object(self, Bucket: str, Key: str):
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "GetObject",
            )
        data = self.objects[Key]["Body"]
        return {
            "Body": io.BytesIO(data),
            "ContentType": self.objects[Key].get("ContentType"),
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

    def head_object(self, Bucket: str, Key: str):
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadObject",
            )
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def delete_object(self, Bucket: str, Key: str):
        self.delete_calls.append({"Bucket": Bucket, "Key": Key})
        self.objects.pop(Key, None)
        return {"ResponseMetadata": {"HTTPStatusCode": 204}}

    def list_objects_v2(self, Bucket: str, Prefix: str = "", MaxKeys: int = 1000):
        matched = [k for k in self.objects.keys() if k.startswith(Prefix)]
        return {
            "KeyCount": len(matched),
            "Contents": [{"Key": k} for k in matched],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }


@pytest.fixture
def mock_s3():
    return MockS3Client()


@pytest.fixture
def r2_service(mock_s3: MockS3Client):
    return R2StorageService(
        bucket_name="test-term-shield-bucket",
        account_id="fake-account-id",
        access_key_id="fake-key",
        secret_access_key="fake-secret",
        s3_client=mock_s3,
    )


# --- 1. Interface & Configuration Compliance ---

def test_r2_interface_compliance(r2_service: R2StorageService):
    """Verify that R2StorageService inherits from BaseStorageService."""
    assert isinstance(r2_service, BaseStorageService)


def test_default_storage_provider_is_local():
    """Verify that default storage provider remains LocalStorageService."""
    set_storage_service(None)  # Reset cached instance
    settings = get_settings()
    assert settings.storage_provider == "local"
    service = get_storage_service()
    assert isinstance(service, LocalStorageService)


def test_storage_provider_r2_switch(monkeypatch):
    """Verify that setting STORAGE_PROVIDER=r2 returns R2StorageService."""
    set_storage_service(None)
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_provider", "r2")
    monkeypatch.setattr(settings, "r2_bucket_name", "test-bucket")
    service = get_storage_service()
    assert isinstance(service, R2StorageService)
    set_storage_service(None)


# --- 2. Raw Uploads Lifecycle ---

def test_r2_upload_lifecycle(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify saving, checking, reading, and deleting raw upload files in R2."""
    file_id = "test-r2-contract"
    content = b"PDF dummy content for Cloudflare R2 test"

    assert not r2_service.upload_exists(file_id)
    assert not r2_service.upload_exists(file_id, ".pdf")
    assert r2_service.read_upload(file_id, ".pdf") is None

    # Save
    saved_key = r2_service.save_upload(file_id, ".pdf", content)
    assert saved_key == f"uploads/{file_id}.pdf"
    assert saved_key in mock_s3.objects

    # Check existence
    assert r2_service.upload_exists(file_id)
    assert r2_service.upload_exists(file_id, ".pdf")
    assert r2_service.upload_exists(file_id, "pdf")
    assert not r2_service.upload_exists(file_id, ".docx")

    # Read
    read_data = r2_service.read_upload(file_id, ".pdf")
    assert read_data == content
    assert r2_service.read_upload(file_id, "pdf") == content

    # Delete
    deleted = r2_service.delete_upload(file_id, ".pdf")
    assert deleted is True
    assert not r2_service.upload_exists(file_id)
    assert r2_service.read_upload(file_id, ".pdf") is None

    # Deleting missing object returns False
    assert r2_service.delete_upload(file_id, ".pdf") is False


def test_r2_private_by_default(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify R2 storage adapter does not set public-read ACL or expose files publicly."""
    r2_service.save_upload("safe-id", ".pdf", b"Confidential Legal NDA")
    assert len(mock_s3.put_calls) == 1
    call = mock_s3.put_calls[0]
    # Verify no public ACL was sent
    assert "ACL" not in call or call["ACL"] != "public-read"
    assert call["Bucket"] == "test-term-shield-bucket"


# --- 3. Extracted Text Lifecycle ---

def test_r2_extracted_text_lifecycle(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify saving, checking, reading, and deleting extracted contract text."""
    file_id = "extracted-contract-001"
    sample_text = "Clause 1: Confidentiality obligation.\nClause 2: Governing Law."

    assert not r2_service.extracted_text_exists(file_id)
    assert r2_service.read_extracted_text(file_id) is None

    # Save
    key = r2_service.save_extracted_text(file_id, sample_text)
    assert key == f"extracted/{file_id}.txt"
    assert r2_service.extracted_text_exists(file_id)

    # Read
    loaded = r2_service.read_extracted_text(file_id)
    assert loaded == sample_text

    # Delete
    assert r2_service.delete_extracted_text(file_id) is True
    assert not r2_service.extracted_text_exists(file_id)
    assert r2_service.read_extracted_text(file_id) is None
    assert r2_service.delete_extracted_text(file_id) is False


# --- 4. Clause JSON Data Lifecycle ---

def test_r2_clauses_json_lifecycle(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify saving, reading, checking, and deleting clause analysis JSON caches."""
    file_id = "clause-cache-001"
    clause_data = [
        {"clause_id": "c1", "clause_number": "1", "title": "Payment Terms", "text": "Net 30 days."},
        {"clause_id": "c2", "clause_number": "2", "title": "Liability", "text": "Capped at fees paid."},
    ]

    assert not r2_service.clauses_json_exists(file_id)
    assert r2_service.load_clauses_json(file_id) is None

    # Save
    key = r2_service.save_clauses_json(file_id, clause_data)
    assert key == f"clauses/{file_id}.json"
    assert r2_service.clauses_json_exists(file_id)

    # Read
    loaded = r2_service.load_clauses_json(file_id)
    assert loaded == clause_data

    # Delete
    assert r2_service.delete_clauses_json(file_id) is True
    assert not r2_service.clauses_json_exists(file_id)
    assert r2_service.load_clauses_json(file_id) is None
    assert r2_service.delete_clauses_json(file_id) is False


# --- 5. Composite Check & Missing Handling ---

def test_r2_has_contract_data(r2_service: R2StorageService):
    """Verify composite check returns True if any asset exists, False if none."""
    file_id = "contract-composite-test"
    assert r2_service.has_contract_data(file_id) is False

    r2_service.save_extracted_text(file_id, "Sample extracted text")
    assert r2_service.has_contract_data(file_id) is True

    r2_service.delete_extracted_text(file_id)
    assert r2_service.has_contract_data(file_id) is False

    r2_service.save_upload(file_id, ".pdf", b"data")
    assert r2_service.has_contract_data(file_id) is True


# --- 6. Path Traversal & Security Protection ---

@pytest.mark.parametrize("malicious_id", [
    "../../secret",
    "..\\..\\Windows\\win.ini",
    "/etc/passwd",
    "C:\\Users\\admin\\file",
    "contract/subfolder",
    "file\x00traversal",
    "",
])
def test_r2_path_traversal_rejection(r2_service: R2StorageService, malicious_id: str):
    """Verify that malicious identifiers attempting path/key traversal are rejected."""
    with pytest.raises(ValueError, match="Invalid file identifier."):
        r2_service.save_upload(malicious_id, ".pdf", b"malicious")

    with pytest.raises(ValueError, match="Invalid file identifier."):
        r2_service.save_extracted_text(malicious_id, "malicious")

    with pytest.raises(ValueError, match="Invalid file identifier."):
        r2_service.save_clauses_json(malicious_id, {})

    # Read and delete safely return None / False without crashing
    assert r2_service.read_upload(malicious_id, ".pdf") is None
    assert r2_service.delete_upload(malicious_id, ".pdf") is False
    assert r2_service.upload_exists(malicious_id, ".pdf") is False
    assert r2_service.read_extracted_text(malicious_id) is None
    assert r2_service.delete_extracted_text(malicious_id) is False
    assert r2_service.extracted_text_exists(malicious_id) is False
    assert r2_service.load_clauses_json(malicious_id) is None
    assert r2_service.delete_clauses_json(malicious_id) is False
    assert r2_service.clauses_json_exists(malicious_id) is False


# --- 7. Content Type Deduction ---

def test_r2_content_type_deduction(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify content type is properly deduced for contracts and media."""
    r2_service.save_upload("c-pdf", ".pdf", b"pdf")
    assert mock_s3.objects["uploads/c-pdf.pdf"]["ContentType"] == "application/pdf"

    r2_service.save_upload("c-docx", ".docx", b"docx")
    assert "wordprocessingml" in mock_s3.objects["uploads/c-docx.docx"]["ContentType"]

    r2_service.save_upload("c-mp3", ".mp3", b"audio")
    assert mock_s3.objects["uploads/c-mp3.mp3"]["ContentType"] == "audio/mpeg"

    r2_service.save_upload("c-mp4", ".mp4", b"video")
    assert mock_s3.objects["uploads/c-mp4.mp4"]["ContentType"] == "video/mp4"


# --- 8. Non-404 Client Errors Propagated ---

def test_r2_server_error_propagation(r2_service: R2StorageService, mock_s3: MockS3Client):
    """Verify that unexpected S3 500 errors are propagated and not silently masked as missing files."""
    def broken_get_object(*args, **kwargs):
        raise ClientError(
            {"Error": {"Code": "InternalError", "Message": "Cloudflare R2 service internal error."}},
            "GetObject",
        )
    mock_s3.get_object = broken_get_object

    with pytest.raises(ClientError):
        r2_service.read_upload("test-file", ".pdf")


# --- 9. Dynamic Provider Switching & Cache Invalidation ---

def test_storage_provider_dynamic_switch_without_manual_reset(monkeypatch):
    """Verify get_storage_service() automatically detects provider changes without manual reset."""
    set_storage_service(None)
    settings = get_settings()

    # Default is local
    monkeypatch.setattr(settings, "storage_provider", "local")
    s1 = get_storage_service()
    assert isinstance(s1, LocalStorageService)

    # Change settings dynamically to r2 - should switch automatically without set_storage_service(None)
    monkeypatch.setattr(settings, "storage_provider", "r2")
    monkeypatch.setattr(settings, "r2_bucket_name", "dynamic-r2-bucket")
    s2 = get_storage_service()
    assert isinstance(s2, R2StorageService)
    assert s2.bucket_name == "dynamic-r2-bucket"

    # Switch back to local dynamically
    monkeypatch.setattr(settings, "storage_provider", "local")
    s3 = get_storage_service()
    assert isinstance(s3, LocalStorageService)

    set_storage_service(None)


def test_set_storage_service_none_and_override():
    """Verify set_storage_service accepts None and explicit overrides properly."""
    set_storage_service(None)
    default_service = get_storage_service()
    assert isinstance(default_service, LocalStorageService)

    # Inject explicit mock / override
    custom_override = LocalStorageService(base_dir="custom_temp")
    set_storage_service(custom_override)
    assert get_storage_service() is custom_override

    # Reset with None
    set_storage_service(None)
    reloaded = get_storage_service()
    assert reloaded is not custom_override
    assert isinstance(reloaded, LocalStorageService)


# --- 10. Extension Validation & Hardening ---

@pytest.mark.parametrize("valid_ext,expected_clean", [
    (".pdf", ".pdf"),
    ("pdf", ".pdf"),
    (".PDF", ".PDF"),
    ("PDF", ".PDF"),
    (".docx", ".docx"),
    ("docx", ".docx"),
    (".tar.gz", ".tar.gz"),
    ("tar.gz", ".tar.gz"),
    (".mp3", ".mp3"),
    (".webm", ".webm"),
])
def test_r2_valid_extensions(r2_service: R2StorageService, valid_ext: str, expected_clean: str):
    """Verify that legitimate extensions are accepted and normalized."""
    key = r2_service.get_upload_key("doc-123", valid_ext)
    assert key == f"uploads/doc-123{expected_clean}"

    # Also verify save and exists
    saved = r2_service.save_upload("doc-123", valid_ext, b"data")
    assert saved == key
    assert r2_service.upload_exists("doc-123", valid_ext) is True
    assert r2_service.read_upload("doc-123", valid_ext) == b"data"
    assert r2_service.delete_upload("doc-123", valid_ext) is True


@pytest.mark.parametrize("invalid_ext", [
    "../../hack",
    "..\\windows\\win.ini",
    "/hack",
    "\\hack",
    "pdf\x00.exe",
    "..",
    ".",
    "",
    "   ",
    "pdf evil",
    ".pdf.",
    "pdf/subfolder",
])
def test_r2_invalid_extensions_rejection(r2_service: R2StorageService, invalid_ext: str):
    """Verify that malicious, traversal, or malformed extensions are rejected."""
    # get_upload_key and save_upload must raise ValueError
    with pytest.raises(ValueError, match="Invalid file extension."):
        r2_service.get_upload_key("doc-123", invalid_ext)

    with pytest.raises(ValueError, match="Invalid file extension."):
        r2_service.save_upload("doc-123", invalid_ext, b"malicious")

    # Read, delete, and exists safely return None or False without unhandled exceptions
    assert r2_service.read_upload("doc-123", invalid_ext) is None
    assert r2_service.delete_upload("doc-123", invalid_ext) is False
    assert r2_service.upload_exists("doc-123", invalid_ext) is False
