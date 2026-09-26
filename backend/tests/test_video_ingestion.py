"""Tests for video ingestion pipeline and authentication verification.

Covers:
- Unauthenticated requests are rejected with 401 ("Authentication required")
- Authenticated requests with valid Bearer token succeed and create contract under current_user.id
- Invalid / expired tokens are rejected with 401
- All supported video formats (.mp4, .mov, .avi, .mkv, .webm)
- Double-extension video handling (e.g. contract_test.mp4.mp4)
- Empty video file rejection
- Missing filename rejection
- Unsupported video file extension rejection
- User isolation: contracts created by User A cannot be accessed by User B
- Downstream clause analysis integration on transcribed video
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import app
from app.services.video_transcription_service import VideoTranscriptionService
from app.services.file_ingestion_service import FileIngestionService
from datetime import timedelta


SAMPLE_VIDEO_TRANSCRIPT = (
    "1. Service Agreement Terms\n"
    "This service agreement requires the customer to pay 50,000 rupees within 30 days of receiving the invoice.\n\n"
    "2. Interest on Late Payments\n"
    "Late payment will incur 2% interest per month.\n\n"
    "3. Cancellation Notice\n"
    "The customer may cancel the agreement with 15 days return notice."
)


@pytest.fixture()
def mock_whisper_video():
    """Mock Whisper model returning a valid contract transcript for video."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": SAMPLE_VIDEO_TRANSCRIPT}
    with patch.object(VideoTranscriptionService, "_get_model", return_value=mock_model):
        yield mock_model


def test_unauthenticated_video_upload_rejected():
    """Regression test: Unauthenticated requests to /api/v1/ingestion/video are rejected with 401."""
    unauth_client = TestClient(app)
    response = unauth_client.post(
        "/api/v1/ingestion/video",
        files={"file": ("contract_test.mp4", b"dummy video bytes", "video/mp4")},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_expired_token_video_upload_rejected():
    """Regression test: Expired token to /api/v1/ingestion/video is rejected with 401."""
    expired_token = create_access_token(
        subject="expired-user-id",
        expires_delta=timedelta(seconds=-60),
    )
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {expired_token}"

    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("contract_test.mp4", b"dummy video bytes", "video/mp4")},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_authenticated_video_upload_success(client: TestClient, mock_whisper_video):
    """Regression test: Authenticated user can successfully upload and ingest a video."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("contract_test.mp4", b"dummy video bytes", "video/mp4")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Video received, transcribed, and added to the contract pipeline successfully."
    assert data["media_type"] == "video"
    assert data["filename"] == "contract_test.mp4"
    assert "file_id" in data
    assert data["transcript"] == SAMPLE_VIDEO_TRANSCRIPT
    assert data["character_count"] == len(SAMPLE_VIDEO_TRANSCRIPT)


def test_authenticated_video_double_extension_success(client: TestClient, mock_whisper_video):
    """Verify that double extension files like 'contract_test.mp4.mp4' are processed successfully."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("contract_test.mp4.mp4", b"dummy video bytes", "video/mp4")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["filename"] == "contract_test.mp4.mp4"
    assert "file_id" in data


@pytest.mark.parametrize(
    "filename,content_type",
    [
        ("sample_contract.mp4", "video/mp4"),
        ("sample_contract.mov", "video/quicktime"),
        ("sample_contract.avi", "video/x-msvideo"),
        ("sample_contract.mkv", "video/x-matroska"),
        ("sample_contract.webm", "video/webm"),
    ],
)
def test_all_supported_video_formats(client: TestClient, mock_whisper_video, filename: str, content_type: str):
    """Verify all supported video formats are accepted when authenticated."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": (filename, b"video_data_bytes", content_type)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["media_type"] == "video"


def test_video_empty_file_rejected(client: TestClient):
    """Verify empty video file upload is rejected with 400."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_video_missing_filename_rejected(client: TestClient):
    """Verify missing filename is rejected with 400 or 422."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("", b"dummy", "video/mp4")},
    )
    assert response.status_code in (400, 422)


def test_video_unsupported_format_rejected(client: TestClient):
    """Verify unsupported video format is rejected with 400."""
    response = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("test.flv", b"dummy", "video/x-flv")},
    )
    assert response.status_code == 400
    assert "unsupported video file type" in response.json()["detail"].lower()


def test_video_contract_user_isolation(client: TestClient, mock_whisper_video):
    """Verify that video contract belongs exclusively to the uploading user."""
    # User A uploads video
    upload_res = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("private_video.mp4", b"dummy bytes", "video/mp4")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    # User A can access analysis
    analysis_res_a = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_res_a.status_code == 200

    # User B registers and attempts to access User A's video contract
    reg_b = TestClient(app).post(
        "/api/v1/auth/register",
        json={
            "full_name": "User B",
            "email": f"user-b-{uuid.uuid4()}@example.com",
            "password": "password456",
        },
    )
    token_b = reg_b.json()["access_token"]
    client_b = TestClient(app)
    client_b.headers["Authorization"] = f"Bearer {token_b}"

    analysis_res_b = client_b.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_res_b.status_code == 404


def test_video_contract_downstream_analysis_pipeline(client: TestClient, mock_whisper_video):
    """Verify complete end-to-end pipeline: video upload -> clauses -> analysis -> summary."""
    upload_res = client.post(
        "/api/v1/ingestion/video",
        files={"file": ("contract_test.mp4.mp4", b"video_bytes", "video/mp4")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    # Clause segmentation
    clauses_res = client.get(f"/api/v1/clauses/{file_id}")
    assert clauses_res.status_code == 200
    clauses_data = clauses_res.json()
    assert clauses_data["clause_count"] >= 3

    # Clause analysis
    analysis_res = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_res.status_code == 200
    analyses = analysis_res.json()["analyses"]
    assert len(analyses) >= 3

    # Contract summary
    summary_res = client.get(f"/api/v1/clauses/{file_id}/summary")
    assert summary_res.status_code == 200
    assert "risk_summary" in summary_res.json()
