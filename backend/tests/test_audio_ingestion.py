"""Tests for audio ingestion and transcription pipeline hardening.

Covers:
- Valid audio formats (.mp3, .wav, .m4a, .aac, .ogg, .flac)
- Empty audio file rejection
- Missing/invalid filename rejection
- Unsupported audio extensions
- Malformed/corrupt audio failure handling
- Empty transcript (no readable speech) handling
- File size limit enforcement
- Missing Whisper / model dependency handling
- Path sanitization in error messages (no temp path leak)
- Temporary audio file cleanup on success and failure
- Contract persistence and user ownership/isolation
- Downstream clause segmentation and analysis integration
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services.audio_transcription_service import AudioTranscriptionService
from app.services.file_ingestion_service import FileIngestionService


SAMPLE_TRANSCRIPT = (
    "1. Confidentiality Agreement\n"
    "The recipient shall keep all proprietary information confidential for three years.\n\n"
    "2. Governing Law\n"
    "This agreement shall be governed by and construed in accordance with the laws of California.\n\n"
    "3. Payment Terms\n"
    "Customer shall pay 10,000 USD within 30 days of receiving the invoice."
)


@pytest.fixture()
def mock_whisper():
    """Mock Whisper model returning a valid contract transcript."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": SAMPLE_TRANSCRIPT}
    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        yield mock_model


@pytest.mark.parametrize(
    "filename,content_type",
    [
        ("sample_contract.mp3", "audio/mpeg"),
        ("sample_contract.wav", "audio/wav"),
        ("sample_contract.m4a", "audio/mp4"),
        ("sample_contract.aac", "audio/aac"),
        ("sample_contract.ogg", "audio/ogg"),
        ("sample_contract.flac", "audio/flac"),
    ],
)
def test_audio_ingestion_all_supported_formats(
    client: TestClient, mock_whisper, filename: str, content_type: str
):
    """Verify that all supported audio extensions are accepted and ingested."""
    dummy_audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00fake_audio_payload"
    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": (filename, dummy_audio_bytes, content_type)},
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["media_type"] == "audio"
    assert data["filename"] == filename
    assert data["size_bytes"] == len(dummy_audio_bytes)
    assert data["character_count"] == len(SAMPLE_TRANSCRIPT)
    assert data["transcript"] == SAMPLE_TRANSCRIPT
    assert data["file_id"]
    assert data["media_id"]

    # Verify extracted text is stored on disk
    extracted_path = FileIngestionService.EXTRACTED_DIR / f"{data['file_id']}.txt"
    assert extracted_path.exists()
    assert extracted_path.read_text(encoding="utf-8") == SAMPLE_TRANSCRIPT


def test_audio_ingestion_empty_file_rejected(client: TestClient):
    """Verify that an empty audio file is rejected with 400."""
    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": ("empty.mp3", b"", "audio/mpeg")},
    )

    assert response.status_code == 400
    assert "Uploaded audio file is empty" in response.json()["detail"]


def test_audio_ingestion_missing_filename_rejected(client: TestClient):
    """Verify that missing filename is rejected with 400 or 422."""
    # API level validation
    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": ("", b"some_audio_bytes", "audio/mpeg")},
    )
    assert response.status_code in (400, 422)

    # Service level validation
    with pytest.raises(ValueError, match="Filename is required"):
        AudioTranscriptionService.transcribe("", b"audio_content")


@pytest.mark.parametrize(
    "filename",
    [
        "contract.txt",
        "contract.pdf",
        "contract.docx",
        "contract.exe",
        "contract.mp4",
        "contract.zip",
        "contract",
    ],
)
def test_audio_ingestion_unsupported_extensions_rejected(
    client: TestClient, filename: str
):
    """Verify that non-audio extensions are rejected with 400."""
    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": (filename, b"not_an_audio_payload", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported audio file type" in response.json()["detail"]


def test_audio_ingestion_unauthenticated_rejected():
    """Verify that unauthenticated audio upload returns 401."""
    unauth_client = TestClient(app)
    response = unauth_client.post(
        "/api/v1/ingestion/audio",
        files={"file": ("sample.mp3", b"dummy_content", "audio/mpeg")},
    )

    assert response.status_code == 401


def test_audio_ingestion_corrupt_or_failing_transcription(client: TestClient):
    """Verify that a transcription engine error returns 400 without crashing."""
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("Failed to decode audio stream")

    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        response = client.post(
            "/api/v1/ingestion/audio",
            files={"file": ("corrupt.mp3", b"corrupted_bytes", "audio/mpeg")},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Failed to transcribe audio" in detail
    assert "Failed to decode audio stream" in detail


def test_audio_ingestion_no_speech_detected(client: TestClient):
    """Verify that audio with no discernible speech is handled cleanly."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "   "}

    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        response = client.post(
            "/api/v1/ingestion/audio",
            files={"file": ("silence.wav", b"silent_wave_bytes", "audio/wav")},
        )

    assert response.status_code == 400
    assert "No readable speech could be transcribed" in response.json()["detail"]


def test_audio_ingestion_file_size_exceeds_limit(client: TestClient):
    """Verify that audio exceeding max_upload_size_mb is rejected."""
    small_settings = Settings(max_upload_size_mb=1)

    with patch("app.api.v1.media_ingestion.get_settings", return_value=small_settings):
        oversized_bytes = b"X" * (2 * 1024 * 1024)  # 2MB
        response = client.post(
            "/api/v1/ingestion/audio",
            files={"file": ("large.mp3", oversized_bytes, "audio/mpeg")},
        )

    assert response.status_code == 400
    assert "File size exceeds the 1 MB limit" in response.json()["detail"]


def test_audio_ingestion_whisper_dependency_failure(client: TestClient):
    """Verify that failure to load Whisper/dependencies returns a clear 400 error."""
    with patch.object(
        AudioTranscriptionService,
        "_get_model",
        side_effect=RuntimeError("Whisper library or weights unavailable"),
    ):
        response = client.post(
            "/api/v1/ingestion/audio",
            files={"file": ("sample.mp3", b"sample_bytes", "audio/mpeg")},
        )

    assert response.status_code == 400
    assert "Failed to transcribe audio" in response.json()["detail"]


def test_audio_ingestion_path_sanitization_in_error_detail(client: TestClient):
    """Verify that internal filesystem paths are sanitized and replaced with filename in error messages."""
    def fail_with_path(path, **kwargs):
        raise RuntimeError(f"ffmpeg failed processing {path}: invalid header")

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = fail_with_path

    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        response = client.post(
            "/api/v1/ingestion/audio",
            files={"file": ("leak_test.mp3", b"test_bytes", "audio/mpeg")},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "AppData" not in detail
    assert "Temp" not in detail
    assert "leak_test.mp3" in detail


def test_audio_temporary_file_cleanup_on_success():
    """Verify that temporary audio file on disk is removed after successful transcription."""
    created_temp_path = None
    mock_model = MagicMock()

    def record_and_transcribe(path, **kwargs):
        nonlocal created_temp_path
        created_temp_path = Path(path)
        assert created_temp_path.exists(), "Temp file should exist during transcription"
        return {"text": "Contract transcript"}

    mock_model.transcribe.side_effect = record_and_transcribe

    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        result = AudioTranscriptionService.transcribe("test.mp3", b"sample_audio_content")

    assert result == "Contract transcript"
    assert created_temp_path is not None
    assert not created_temp_path.exists(), "Temp file must be deleted after transcription completes"


def test_audio_temporary_file_cleanup_on_failure():
    """Verify that temporary audio file on disk is removed even if transcription fails."""
    created_temp_path = None
    mock_model = MagicMock()

    def fail_transcribe(path, **kwargs):
        nonlocal created_temp_path
        created_temp_path = Path(path)
        assert created_temp_path.exists(), "Temp file should exist before failure"
        raise RuntimeError("Whisper transcription crash")

    mock_model.transcribe.side_effect = fail_transcribe

    with patch.object(AudioTranscriptionService, "_get_model", return_value=mock_model):
        with pytest.raises(ValueError, match="Failed to transcribe audio"):
            AudioTranscriptionService.transcribe("test.mp3", b"sample_audio_content")

    assert created_temp_path is not None
    assert not created_temp_path.exists(), "Temp file must be cleaned up on failure"


def test_audio_ingestion_persists_contract_and_enforces_ownership(
    client: TestClient, mock_whisper
):
    """Verify that ingested audio creates a Contract record isolated to the user."""
    from tests.conftest import _register_and_get_client

    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": ("ownership_sample.mp3", b"audio_bytes", "audio/mpeg")},
    )
    assert response.status_code == 200
    file_id = response.json()["file_id"]

    # Verify present in client's contract library
    list_resp = client.get("/api/v1/contracts")
    assert list_resp.status_code == 200
    user_contracts = list_resp.json()
    contract_entry = next((c for c in user_contracts if c["id"] == file_id), None)
    assert contract_entry is not None
    assert contract_entry["filename"] == "ownership_sample.mp3"
    assert contract_entry["file_type"] == "mp3"

    # Verify other authenticated user cannot delete or access this contract
    other_client = _register_and_get_client()
    other_list = other_client.get("/api/v1/contracts")
    assert not any(c["id"] == file_id for c in other_list.json())

    other_del = other_client.delete(f"/api/v1/contracts/{file_id}")
    assert other_del.status_code == 404


def test_audio_ingestion_downstream_clause_analysis(
    client: TestClient, mock_whisper
):
    """Verify that extracted audio contract text flows directly into downstream clause analysis."""
    response = client.post(
        "/api/v1/ingestion/audio",
        files={"file": ("contract_audio.mp3", b"audio_bytes", "audio/mpeg")},
    )
    assert response.status_code == 200
    file_id = response.json()["file_id"]

    # Call downstream clause segmentation endpoint
    clauses_resp = client.get(f"/api/v1/clauses/{file_id}")
    assert clauses_resp.status_code == 200, clauses_resp.text
    clauses_data = clauses_resp.json()
    assert clauses_data["clause_count"] > 0

    # Call downstream clause analysis endpoint
    analysis_resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert analysis_resp.status_code == 200, analysis_resp.text
    data = analysis_resp.json()

    assert data["file_id"] == file_id
    assert data["analysis_count"] > 0
    analyses = data["analyses"]
    types = {a["clause_type"] for a in analyses}

    # Verify downstream analysis recognized clauses from transcript
    assert "CONFIDENTIALITY" in types or "GOVERNING_LAW" in types or "PAYMENT" in types
