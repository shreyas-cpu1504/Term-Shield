"""Tests for Supabase S3-compatible storage provider."""

import io
import json
import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.services.storage_service import (
    BaseStorageService,
    LocalStorageService,
    SupabaseStorageService,
    get_storage_service,
    set_storage_service,
)


class MockS3Client:
    """In-memory mock of the boto3 S3 client for testing Supabase operations without network calls."""

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

    def list_objects_v2(self, Bucket: str, Prefix: str = "", MaxKeys: int = 1000, **kwargs):
        matching = [
            {"Key": k, "Size": len(v["Body"])}
            for k, v in self.objects.items()
            if k.startswith(Prefix)
        ]
        return {
            "KeyCount": len(matching),
            "Contents": matching,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }


@pytest.fixture
def mock_s3():
    return MockS3Client()


@pytest.fixture
def supabase_service(mock_s3):
    return SupabaseStorageService(
        endpoint_url="https://testproject.storage.supabase.co/storage/v1/s3",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        bucket_name="term-shield-contracts",
        region_name="ap-northeast-2",
        s3_client=mock_s3,
    )


# --- 1. Interface & Factory Tests ---

def test_supabase_interface_compliance(supabase_service):
    assert isinstance(supabase_service, BaseStorageService)
    assert supabase_service.bucket_name == "term-shield-contracts"
    assert supabase_service.region_name == "ap-northeast-2"


def test_supabase_provider_switch(monkeypatch):
    orig_service = get_storage_service()
    try:
        monkeypatch.setenv("STORAGE_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_S3_ENDPOINT", "https://xyz.storage.supabase.co/storage/v1/s3")
        monkeypatch.setenv("SUPABASE_S3_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("SUPABASE_S3_SECRET_ACCESS_KEY", "sec123")
        monkeypatch.setenv("SUPABASE_S3_BUCKET", "term-shield-contracts")

        get_settings.cache_clear()
        set_storage_service(None)

        svc = get_storage_service()
        assert isinstance(svc, SupabaseStorageService)
        assert svc.bucket_name == "term-shield-contracts"
        assert svc.region_name == "ap-northeast-2"
    finally:
        set_storage_service(orig_service)
        get_settings.cache_clear()


def test_supabase_configuration_error_missing_endpoint():
    svc = SupabaseStorageService(
        endpoint_url=None,
        access_key_id="test",
        secret_access_key="test",
    )
    with pytest.raises(ValueError, match="SUPABASE_S3_ENDPOINT must be configured"):
        _ = svc.client


# --- 2. Upload Lifecycle & Private-By-Default Tests ---

def test_supabase_upload_lifecycle(supabase_service, mock_s3):
    file_id = "test-doc-001"
    content = b"%PDF-1.4 sample contract text"

    # Save
    saved_key = supabase_service.save_upload(file_id, ".pdf", content)
    assert saved_key == "uploads/test-doc-001.pdf"
    assert "uploads/test-doc-001.pdf" in mock_s3.objects

    # Private by default check: ensure no ACL='public-read' was passed
    last_put = mock_s3.put_calls[-1]
    assert "ACL" not in last_put or last_put.get("ACL") != "public-read"

    # Check existence
    assert supabase_service.upload_exists(file_id, ".pdf")
    assert supabase_service.upload_exists(file_id)

    # Read
    read_data = supabase_service.read_upload(file_id, ".pdf")
    assert read_data == content

    # Delete
    deleted = supabase_service.delete_upload(file_id, ".pdf")
    assert deleted is True
    assert not supabase_service.upload_exists(file_id, ".pdf")
    assert supabase_service.read_upload(file_id, ".pdf") is None


def test_supabase_private_by_default(supabase_service, mock_s3):
    file_id = "private-contract-002"
    content = b"Confidential Non-Disclosure Agreement"

    supabase_service.save_upload(file_id, ".txt", content)
    assert len(mock_s3.put_calls) == 1
    call = mock_s3.put_calls[0]
    # S3 put_object should never include public-read ACL
    assert call.get("ACL") is None
    assert call["Bucket"] == "term-shield-contracts"


# --- 3. Extracted Text Lifecycle Tests ---

def test_supabase_extracted_text_lifecycle(supabase_service, mock_s3):
    file_id = "extracted-doc-003"
    text_content = "1. Definitions\n'Customer Data' means electronic data."

    saved_key = supabase_service.save_extracted_text(file_id, text_content)
    assert saved_key == "extracted/extracted-doc-003.txt"
    assert supabase_service.extracted_text_exists(file_id)

    read_text = supabase_service.read_extracted_text(file_id)
    assert read_text == text_content

    deleted = supabase_service.delete_extracted_text(file_id)
    assert deleted is True
    assert not supabase_service.extracted_text_exists(file_id)
    assert supabase_service.read_extracted_text(file_id) is None


# --- 4. Clause JSON Lifecycle Tests ---

def test_supabase_clauses_json_lifecycle(supabase_service, mock_s3):
    file_id = "clauses-doc-004"
    clauses = [
        {"clause_number": "1", "text": "Payment within 30 days."},
        {"clause_number": "2", "text": "Termination for breach."},
    ]

    saved_key = supabase_service.save_clauses_json(file_id, clauses)
    assert saved_key == "clauses/clauses-doc-004.json"
    assert supabase_service.clauses_json_exists(file_id)

    loaded = supabase_service.load_clauses_json(file_id)
    assert loaded == clauses

    deleted = supabase_service.delete_clauses_json(file_id)
    assert deleted is True
    assert not supabase_service.clauses_json_exists(file_id)
    assert supabase_service.load_clauses_json(file_id) is None


# --- 5. Security & Path Traversal Tests ---

@pytest.mark.parametrize("malicious_id", [
    "../../etc/passwd",
    "..\\..\\windows\\win.ini",
    "sub/folder",
    "null\x00byte",
    "",
])
def test_supabase_path_traversal_rejection(supabase_service, malicious_id):
    with pytest.raises(ValueError):
        supabase_service.save_upload(malicious_id, ".pdf", b"data")

    with pytest.raises(ValueError):
        supabase_service.save_extracted_text(malicious_id, "data")

    with pytest.raises(ValueError):
        supabase_service.save_clauses_json(malicious_id, {})

    # Safe inspection methods should return False or None instead of crashing
    assert supabase_service.read_upload(malicious_id, ".pdf") is None
    assert supabase_service.upload_exists(malicious_id, ".pdf") is False
    assert supabase_service.read_extracted_text(malicious_id) is None
    assert supabase_service.extracted_text_exists(malicious_id) is False


# --- 6. Composite Data Check ---

def test_supabase_has_contract_data(supabase_service):
    file_id = "composite-test-005"
    assert not supabase_service.has_contract_data(file_id)

    supabase_service.save_upload(file_id, ".pdf", b"pdf data")
    assert supabase_service.has_contract_data(file_id)

    supabase_service.delete_upload(file_id, ".pdf")
    assert not supabase_service.has_contract_data(file_id)

    supabase_service.save_extracted_text(file_id, "some extracted text")
    assert supabase_service.has_contract_data(file_id)
