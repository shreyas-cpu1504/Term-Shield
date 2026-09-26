"""Security hardening test suite for Term Shield.

Covers:
- SSRF prevention (localhost, private subnets, link-local, cloud metadata, IPv6 loopback, unspecified, userinfo)
- Safe DNS resolution checking
- Safe redirect following with intermediate SSRF validation
- Filename sanitization against path traversal (../, ..\\, absolute Windows/Unix, mixed slashes)
- Storage path confinement (uploads, extracted, clauses)
- Upload size limit consistency across all endpoints (file, audio, video, URL)
- Internal filesystem path disclosure prevention in error messages
- Authentication enforcement across all ingestion endpoints
"""

import io
from pathlib import Path
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services.file_ingestion_service import FileIngestionService
from app.services.url_ingestion_service import URLIngestionService
from app.services.video_transcription_service import VideoTranscriptionService


# ==========================================
# 1. SSRF & URL Ingestion Protection Tests
# ==========================================

@pytest.mark.anyio
@pytest.mark.parametrize(
    "url,reason",
    [
        ("http://localhost/contract.pdf", "localhost"),
        ("http://127.0.0.1/contract.pdf", "IPv4 loopback"),
        ("http://127.0.0.2:8000/doc.txt", "IPv4 loopback subnet"),
        ("http://[::1]/contract.pdf", "IPv6 loopback"),
        ("http://10.0.0.1/contract.pdf", "Private 10.0.0.0/8"),
        ("http://172.16.0.1/contract.pdf", "Private 172.16.0.0/12"),
        ("http://192.168.1.1/contract.pdf", "Private 192.168.0.0/16"),
        ("http://169.254.169.254/latest/meta-data/", "Cloud metadata / Link-local"),
        ("http://169.254.1.1/test.pdf", "Link-local subnet"),
        ("http://0.0.0.0/contract.pdf", "Unspecified IPv4"),
        ("http://[::]/contract.pdf", "Unspecified IPv6"),
    ],
)
async def test_ssrf_rejects_internal_and_private_destinations(url: str, reason: str):
    """Verify that private, loopback, link-local, and metadata destinations are blocked."""
    with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
        await URLIngestionService.download(url)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "file:///C:/Windows/win.ini",
        "ftp://example.com/contract.pdf",
        "gopher://example.com/",
        "data:text/plain;base64,SGVsbG8=",
        "javascript:alert(1)",
    ],
)
async def test_ssrf_rejects_dangerous_schemes(url: str):
    """Verify that only HTTP and HTTPS schemes are allowed."""
    with pytest.raises(ValueError, match="Only HTTP and HTTPS URLs are supported"):
        await URLIngestionService.download(url)


@pytest.mark.anyio
async def test_ssrf_rejects_credentials_in_url():
    """Verify that URLs containing embedded username/password are rejected."""
    with pytest.raises(ValueError, match="URLs containing credentials are not permitted"):
        await URLIngestionService.download("http://admin:secret@example.com/contract.pdf")


@pytest.mark.anyio
async def test_ssrf_blocks_hostname_resolving_to_private_ip():
    """Verify that a public-looking domain that resolves to a private IP is blocked."""
    fake_dns_entry = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.5", 80))]

    with patch("socket.getaddrinfo", return_value=fake_dns_entry):
        with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
            await URLIngestionService.download("http://internal-corp-service.com/contract.pdf")


@pytest.mark.anyio
async def test_ssrf_blocks_hostname_resolving_to_cloud_metadata():
    """Verify that a domain resolving to 169.254.169.254 is blocked."""
    fake_dns_entry = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("169.254.169.254", 80))]

    with patch("socket.getaddrinfo", return_value=fake_dns_entry):
        with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
            await URLIngestionService.download("http://metadata.google.internal/contract.pdf")


@pytest.mark.anyio
async def test_ssrf_allows_public_domain_and_downloads_content():
    """Verify that a legitimate public URL resolves safely and downloads content."""
    fake_dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_redirect = False
    mock_response.content = b"Contract terms content for testing."
    mock_response.url = httpx.URL("https://example.com/contract.txt")
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.raise_for_status = MagicMock()

    with patch("socket.getaddrinfo", return_value=fake_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            filename, content = await URLIngestionService.download("https://example.com/contract.txt")

    assert filename == "contract.txt"
    assert content == b"Contract terms content for testing."


@pytest.mark.anyio
async def test_ssrf_blocks_redirect_to_internal_address():
    """Verify that a redirect to an internal IP (e.g. 127.0.0.1) is blocked before request is sent."""
    def mock_dns(host, port, **kwargs):
        if host == "127.0.0.1" or host == "localhost":
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    # Initial response is a redirect to 127.0.0.1
    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.is_redirect = True
    redirect_response.headers = {"location": "http://127.0.0.1:8080/admin/secret.txt"}

    with patch("socket.getaddrinfo", side_effect=mock_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = redirect_response
            with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
                await URLIngestionService.download("http://example.com/redirect-me")


@pytest.mark.anyio
async def test_ssrf_blocks_excessive_redirects():
    """Verify that infinite redirect loops are halted."""
    fake_public_dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    loop_response = MagicMock()
    loop_response.status_code = 302
    loop_response.is_redirect = True
    loop_response.headers = {"location": "http://example.com/loop"}

    with patch("socket.getaddrinfo", return_value=fake_public_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = loop_response
            with pytest.raises(ValueError, match="Too many redirects"):
                await URLIngestionService.download("http://example.com/loop")


@pytest.mark.anyio
async def test_ssrf_rejects_cgnat_subnet():
    """Verify that Carrier-Grade NAT (100.64.0.0/10) is rejected."""
    fake_cgnat_dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("100.64.1.5", 80))]

    with patch("socket.getaddrinfo", return_value=fake_cgnat_dns):
        with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
            await URLIngestionService.download("http://cgnat-service.com/contract.pdf")


@pytest.mark.anyio
async def test_ssrf_fallback_to_ipv4_preserves_ssrf_block():
    """Verify that when dual-stack DNS fails, IPv4 fallback still enforces SSRF."""
    def mock_dns(host, port, family=0, **kwargs):
        if family == socket.AF_UNSPEC:
            raise socket.gaierror("Dual-stack resolution failure")
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.168.1.50", port))]

    with patch("socket.getaddrinfo", side_effect=mock_dns):
        with pytest.raises(ValueError, match="Access to private, loopback, or internal network addresses is prohibited"):
            await URLIngestionService.download("http://fallback-internal.com/contract.pdf")


@pytest.mark.anyio
async def test_ssrf_fallback_to_ipv4_allows_public_ip():
    """Verify that when dual-stack DNS fails, valid public IPv4 resolves and downloads safely."""
    def mock_dns(host, port, family=0, **kwargs):
        if family == socket.AF_UNSPEC:
            raise socket.gaierror("Dual-stack resolution failure")
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_redirect = False
    mock_response.content = b"%PDF-1.4 dummy pdf"
    mock_response.url = httpx.URL("https://example.com/contract.pdf")
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.raise_for_status = MagicMock()

    with patch("socket.getaddrinfo", side_effect=mock_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            filename, content = await URLIngestionService.download("https://example.com/contract.pdf")

    assert filename == "contract.pdf"
    assert content.startswith(b"%PDF")


@pytest.mark.anyio
async def test_unresolvable_host_raises_clear_error():
    """Verify that a host that cannot be resolved at all raises a clear error."""
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("Unknown host")):
        with patch("socket.gethostbyname_ex", side_effect=socket.gaierror("Unknown host")):
            with pytest.raises(ValueError, match="Failed to resolve host 'non-existent-domain.xyz'"):
                await URLIngestionService.download("https://non-existent-domain.xyz/contract.pdf")


# ==========================================
# 2. Filename Sanitization & Path Traversal
# ==========================================


@pytest.mark.parametrize(
    "input_name,expected_clean",
    [
        ("../../secret.txt", "secret.txt"),
        ("..\\..\\Windows\\System32\\cmd.exe", "cmd.exe"),
        ("C:\\Users\\Administrator\\contract.pdf", "contract.pdf"),
        ("/var/data/private/nda.docx", "nda.docx"),
        ("../..\\mixed/path\\traversal.txt", "traversal.txt"),
        ("normal_contract.pdf", "normal_contract.pdf"),
        ("contract..name..pdf", "contract..name..pdf"),
        (".hidden_file.txt", "hidden_file.txt"),
        ("..", "unnamed_contract.txt"),
        ("", "unnamed_contract.txt"),
        (None, "unnamed_contract.txt"),
    ],
)
def test_filename_sanitization_utility(input_name: str | None, expected_clean: str):
    """Verify FileIngestionService.sanitize_filename strips all path traversal components."""
    sanitized = FileIngestionService.sanitize_filename(input_name)
    assert sanitized == expected_clean
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert not sanitized.startswith("..")


def test_file_upload_sanitizes_malicious_filename(client: TestClient):
    """Verify that an upload with traversal filename stores a clean filename in DB and metadata."""
    traversal_filename = "../../evil_path_traversal.txt"
    content = b"1. Term and Termination\nThis agreement terminates in 30 days."

    response = client.post(
        "/api/v1/ingestion/file",
        files={"file": (traversal_filename, content, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "evil_path_traversal.txt"
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]

    # Verify physical file on disk is inside storage/uploads using UUID
    file_id = data["file_id"]
    stored_path = (FileIngestionService.UPLOAD_DIR / f"{file_id}.txt").resolve()
    assert stored_path.exists()
    assert stored_path.is_relative_to(FileIngestionService.UPLOAD_DIR.resolve())


def test_extracted_text_path_confinement():
    """Verify that saving extracted text never escapes storage/extracted."""
    valid_id = "test-uuid-safe-1234"
    path = FileIngestionService.save_extracted_text(valid_id, "Sample extracted content")
    assert path.exists()
    assert path.resolve().is_relative_to(FileIngestionService.EXTRACTED_DIR.resolve())

    # Traversal attempts in file_id must be rejected
    with pytest.raises(ValueError, match="Invalid file identifier"):
        FileIngestionService.save_extracted_text("../../escaped", "Dangerous content")

    with pytest.raises(ValueError, match="Invalid file identifier"):
        FileIngestionService.save_extracted_text("..\\..\\escaped", "Dangerous content")


def test_clauses_storage_path_confinement():
    """Verify that clause storage never escapes storage/clauses."""
    from app.schemas.clause import Clause
    from app.services.clause_storage_service import ClauseStorageService

    dummy_clause = Clause(
        clause_id="c1",
        clause_number="1",
        title="Title",
        text="Clause text",
        order=1,
        character_count=11,
    )

    valid_id = "test-clauses-uuid-5678"
    path = ClauseStorageService.save_clauses(valid_id, [dummy_clause])
    assert path.exists()
    assert path.resolve().is_relative_to(ClauseStorageService.CLAUSES_DIR.resolve())

    with pytest.raises(ValueError, match="Invalid file identifier"):
        ClauseStorageService.save_clauses("../../escaped", [dummy_clause])

    with pytest.raises(ValueError, match="Invalid file identifier"):
        ClauseStorageService.save_clauses("..\\..\\escaped", [dummy_clause])


def test_file_id_traversal_route_rejected(client: TestClient):
    """Verify that traversal via file_id parameter in clauses route returns 404."""
    response = client.get("/api/v1/clauses/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code in (400, 404)


# ==========================================
# 3. Upload Size Limits Enforcement
# ==========================================

def test_video_upload_size_limit_enforced(client: TestClient):
    """Verify that video ingestion rejects files exceeding configured max size."""
    small_settings = Settings(max_upload_size_mb=1)

    with patch("app.api.v1.media_ingestion.get_settings", return_value=small_settings):
        oversized = b"V" * (2 * 1024 * 1024)  # 2MB
        response = client.post(
            "/api/v1/ingestion/video",
            files={"file": ("video.mp4", oversized, "video/mp4")},
        )

    assert response.status_code == 400
    assert "File size exceeds the 1 MB limit" in response.json()["detail"]


def test_file_upload_size_limit_enforced(client: TestClient):
    """Verify that file ingestion rejects files exceeding configured max size."""
    small_settings = Settings(max_upload_size_mb=1)

    with patch("app.services.file_ingestion_service.get_settings", return_value=small_settings):
        oversized = b"F" * (2 * 1024 * 1024)  # 2MB
        response = client.post(
            "/api/v1/ingestion/file",
            files={"file": ("large.txt", oversized, "text/plain")},
        )

    assert response.status_code == 400
    assert "File size exceeds the 1 MB limit" in response.json()["detail"]


# ==========================================
# 4. Error Message Path Sanitization
# ==========================================

def test_video_error_sanitizes_internal_temp_paths(client: TestClient):
    """Verify that underlying video transcription errors do not disclose temporary disk paths."""
    def fail_with_path(path, **kwargs):
        raise RuntimeError(f"ffmpeg decode error processing {path}: invalid bitstream")

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = fail_with_path

    with patch.object(VideoTranscriptionService, "_get_model", return_value=mock_model):
        response = client.post(
            "/api/v1/ingestion/video",
            files={"file": ("leak_test.mp4", b"video_bytes", "video/mp4")},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "AppData" not in detail
    assert "Temp" not in detail
    assert "leak_test.mp4" in detail


# ==========================================
# 5. Authentication Enforcement
# ==========================================

@pytest.mark.parametrize(
    "endpoint,method,payload",
    [
        ("/api/v1/ingestion/text", "POST", {"json": {"input_type": "text", "content": "Sample"}}),
        ("/api/v1/ingestion/file", "POST", {"files": {"file": ("test.txt", b"content", "text/plain")}}),
        ("/api/v1/ingestion/url", "POST", {"json": {"url": "https://example.com/test.txt"}}),
        ("/api/v1/ingestion/audio", "POST", {"files": {"file": ("test.mp3", b"audio", "audio/mpeg")}}),
        ("/api/v1/ingestion/video", "POST", {"files": {"file": ("test.mp4", b"video", "video/mp4")}}),
    ],
)
def test_all_ingestion_endpoints_require_authentication(endpoint: str, method: str, payload: dict):
    """Verify that all ingestion endpoints reject unauthenticated calls with 401."""
    unauth_client = TestClient(app)
    if method == "POST":
        response = unauth_client.post(endpoint, **payload)
    else:
        response = unauth_client.get(endpoint)

    assert response.status_code == 401
