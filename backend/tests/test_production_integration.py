"""Production readiness and end-to-end integration tests for Term Shield."""
import io
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.core.database import close_db, init_db
from app.main import app


def test_health_check_endpoint():
    """Verify that /health is public, returns 200, and contains service metadata."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_cors_preflight_handling():
    """Verify that CORS preflight requests from allowed origins succeed with proper headers."""
    client = TestClient(app)
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/api/v1/contracts", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_unauthenticated_access_rejected():
    """Verify that protected endpoints reject requests without valid credentials."""
    unauth_client = TestClient(app)

    routes_to_test = [
        ("GET", "/api/v1/contracts"),
        ("DELETE", "/api/v1/contracts/dummy-id"),
        ("GET", "/api/v1/clauses/dummy-id"),
        ("GET", "/api/v1/clauses/dummy-id/analysis"),
        ("GET", "/api/v1/clauses/dummy-id/summary"),
        ("POST", "/api/v1/qa/dummy-id"),
        ("GET", "/api/v1/qa/dummy-id/history"),
        ("POST", "/api/v1/ingestion/text"),
        ("POST", "/api/v1/ingestion/url"),
    ]

    for method, path in routes_to_test:
        if method == "GET":
            resp = unauth_client.get(path)
        elif method == "DELETE":
            resp = unauth_client.delete(path)
        else:
            resp = unauth_client.post(path, json={})

        assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"


def test_invalid_token_rejected():
    """Verify that forged or malformed tokens are rejected with 401."""
    client = TestClient(app)
    client.headers.update({"Authorization": "Bearer completely-invalid-token"})

    response = client.get("/api/v1/contracts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_database_lifecycle():
    """Verify that init_db and close_db execute cleanly without error."""
    await init_db()
    await close_db()


def test_full_contract_lifecycle_and_cascade(client: TestClient):
    """
    Verify complete flow:
    1. Upload file contract
    2. List contracts in library
    3. Segment clauses
    4. Analyze clauses
    5. Read persisted clauses & summary
    6. Ask question (QA)
    7. Retrieve persistent QA history
    8. Delete contract
    9. Verify cascade deletion of all dependent records and disk artifacts
    """
    contract_text = (
        "CONFIDENTIALITY AND SERVICES AGREEMENT\n\n"
        "1. Services and Payment.\n"
        "The Consultant shall provide architectural consulting services. "
        "The Client shall pay a total fixed fee of $75,000 upon final milestone delivery.\n\n"
        "2. Termination.\n"
        "Either party may terminate this Agreement by providing 30 days written notice to the other party.\n\n"
        "3. Limitation of Liability.\n"
        "In no event shall either party be liable for any punitive, special, or indirect damages.\n"
    )

    # 1. Ingest file
    file_bytes = contract_text.encode("utf-8")
    files = {"file": ("consulting_agreement.txt", io.BytesIO(file_bytes), "text/plain")}

    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 200, resp.text
    file_id = resp.json()["file_id"]
    assert file_id

    # 2. List contracts
    list_resp = client.get("/api/v1/contracts")
    assert list_resp.status_code == 200
    contracts = list_resp.json()
    assert any(c["id"] == file_id for c in contracts)

    # 3. Get / Segment clauses
    seg_resp = client.get(f"/api/v1/clauses/{file_id}")
    assert seg_resp.status_code == 200
    clauses_data = seg_resp.json()
    assert clauses_data["clause_count"] >= 3

    # 4. Analyze clauses & overall risk
    analysis_resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    assert analysis_data["analysis_count"] >= 3

    # 5. Read persisted summary and relationships
    summary_resp = client.get(f"/api/v1/clauses/{file_id}/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert "overall_risk" in summary_data
    assert "risk_summary" in summary_data
    assert summary_data["total_clauses"] >= 3

    rel_resp = client.get(f"/api/v1/clauses/{file_id}/relationships")
    assert rel_resp.status_code == 200

    # 6. Ask question
    qa_resp = client.post(
        f"/api/v1/qa/{file_id}",
        json={"question": "What is the fee or payment amount?"},
    )
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert qa_data["answer"]

    # 7. Retrieve persistent QA history
    history_resp = client.get(f"/api/v1/qa/{file_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["question"] == "What is the fee or payment amount?"

    # Check that disk artifacts exist before deletion
    extracted_path = Path("storage/extracted") / f"{file_id}.txt"
    assert extracted_path.is_file()

    # 8. Delete contract
    del_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert del_resp.status_code == 200

    # 9. Verify cascade deletion
    list_after = client.get("/api/v1/contracts")
    assert all(c["id"] != file_id for c in list_after.json())

    # QA history and clauses should return 404
    assert client.get(f"/api/v1/qa/{file_id}/history").status_code == 404
    assert client.get(f"/api/v1/clauses/{file_id}").status_code == 404

    # Disk extracted file should be removed
    assert not extracted_path.exists()


def test_user_isolation_across_endpoints(client: TestClient, other_client: TestClient):
    """Verify that User 2 cannot view, segment, query, or delete User 1's contract."""
    contract_text = "Standard nondisclosure agreement for user isolation testing."
    files = {"file": ("secret_contract.txt", io.BytesIO(contract_text.encode("utf-8")), "text/plain")}

    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    # User 2 listing should NOT include file_id
    other_list = other_client.get("/api/v1/contracts")
    assert all(c["id"] != file_id for c in other_list.json())

    # User 2 get clauses should return 404
    assert other_client.get(f"/api/v1/clauses/{file_id}").status_code == 404

    # User 2 analyze should return 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/analysis").status_code == 404

    # User 2 relationships should return 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/relationships").status_code == 404

    # User 2 summary should return 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/summary").status_code == 404

    # User 2 QA should return 404
    assert other_client.post(f"/api/v1/qa/{file_id}", json={"question": "Test?"}).status_code == 404

    # User 2 QA history should return 404
    assert other_client.get(f"/api/v1/qa/{file_id}/history").status_code == 404

    # User 2 delete should return 404
    assert other_client.delete(f"/api/v1/contracts/{file_id}").status_code == 404

    # User 1 can still access and delete cleanly
    assert client.delete(f"/api/v1/contracts/{file_id}").status_code == 200


def test_audio_ingestion_integration_with_mock(client: TestClient):
    """Verify audio ingestion pipeline end-to-end with mocked Whisper transcription."""
    mock_transcript = "This is a recorded oral contract agreeing to provide marketing services for $500 per month."

    with patch("app.services.audio_transcription_service.AudioTranscriptionService.transcribe", return_value=mock_transcript):
        fake_audio = io.BytesIO(b"fake-audio-bytes-header-data")
        files = {"file": ("oral_contract.mp3", fake_audio, "audio/mpeg")}

        resp = client.post("/api/v1/ingestion/audio", files=files)
        assert resp.status_code == 200
        data = resp.json()
        file_id = data["file_id"]
        assert file_id
        assert data["transcript"] == mock_transcript

        # Verify contract appears in contracts list
        contracts_resp = client.get("/api/v1/contracts")
        assert any(c["id"] == file_id for c in contracts_resp.json())

        # Cleanup
        del_resp = client.delete(f"/api/v1/contracts/{file_id}")
        assert del_resp.status_code == 200


def test_url_ingestion_integration_with_mock(client: TestClient):
    """Verify URL ingestion flow end-to-end with mocked download."""
    from app.services.url_ingestion_service import URLIngestionService

    mock_content = b"Service Agreement. Term begins on signing. Payment is $10,000 net 30."

    with patch.object(URLIngestionService, "download", return_value=("remote_agreement.txt", mock_content)):
        resp = client.post(
            "/api/v1/ingestion/url",
            json={"url": "https://example.com/remote_agreement.txt"},
        )
        assert resp.status_code == 200
        data = resp.json()
        file_id = data["file_id"]
        assert file_id
        assert data["filename"] == "remote_agreement.txt"

        # Verify contract listed
        contracts_resp = client.get("/api/v1/contracts")
        assert any(c["id"] == file_id for c in contracts_resp.json())

        # Cleanup
        del_resp = client.delete(f"/api/v1/contracts/{file_id}")
        assert del_resp.status_code == 200


def test_direct_text_ingestion(client: TestClient):
    """Verify POST /api/v1/ingestion/text handles raw text input."""
    resp = client.post(
        "/api/v1/ingestion/text",
        json={"input_type": "text", "content": "Here is raw contract text for analysis."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_count"] > 0
    assert data["message"] == "Text received successfully."


def test_unsupported_file_extension_rejected(client: TestClient):
    """Verify that uploading files with dangerous/unsupported extensions is rejected."""
    files = {"file": ("malicious.exe", io.BytesIO(b"MZ executable content"), "application/x-msdownload")}
    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 400


def test_contract_deletion_cleans_storage_uploads(client: TestClient):
    """Verify that deleting a contract removes the raw file in storage/uploads if present."""
    fake_txt = b"Test contract content to verify storage/uploads cleanup upon deletion."
    files = {"file": ("cleanup_test.txt", io.BytesIO(fake_txt), "text/plain")}

    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    raw_upload = Path("storage/uploads") / f"{file_id}.txt"
    assert raw_upload.is_file(), "Raw upload file should exist before deletion"

    del_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert del_resp.status_code == 200

    assert not raw_upload.exists(), "Raw upload file in storage/uploads should be removed after deletion"


def test_cors_multiple_origins_support():
    """Verify that multiple origins separated by commas in frontend_url are loaded into CORS headers."""
    from app.main import app
    from app.core.config import get_settings

    settings = get_settings()
    # Test that CORS middleware is registered and default origins exist
    for middleware in app.user_middleware:
        if "CORSMiddleware" in str(middleware.cls):
            allow_origins = middleware.kwargs.get("allow_origins", [])
            assert "http://localhost:5173" in allow_origins
            assert "http://127.0.0.1:5173" in allow_origins


def test_reports_and_analysis_contract_integrity(client: TestClient):
    """Verify that analysis, summary, and relationships return all fields needed by frontend Reports & Risk Analysis."""
    fake_txt = (
        b"1. Definitions and Term.\n"
        b"This Agreement starts on Effective Date and lasts 2 years.\n\n"
        b"2. Limitation of Liability.\n"
        b"Vendor liability shall be unlimited for all indirect and consequential damages.\n\n"
        b"3. Termination.\n"
        b"Either party may terminate immediately with written notice.\n"
    )
    files = {"file": ("reports_contract.txt", io.BytesIO(fake_txt), "text/plain")}
    resp = client.post("/api/v1/ingestion/file", files=files)
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    # 1. Fetch analysis
    analysis_resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    assert "analyses" in analysis_data
    assert len(analysis_data["analyses"]) > 0
    first_analysis = analysis_data["analyses"][0]
    assert "clause_id" in first_analysis
    assert "risk_level" in first_analysis
    assert "risk_score" in first_analysis
    assert "meaning" in first_analysis

    # 2. Fetch summary
    summary_resp = client.get(f"/api/v1/clauses/{file_id}/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert "overall_risk" in summary_data
    assert "overall_risk_score" in summary_data
    assert "risk_summary" in summary_data
    assert "total_clauses" in summary_data

    # 3. Fetch relationships
    rel_resp = client.get(f"/api/v1/clauses/{file_id}/relationships")
    assert rel_resp.status_code == 200
    rel_data = rel_resp.json()
    assert "relationships" in rel_data
    assert "relationship_count" in rel_data


