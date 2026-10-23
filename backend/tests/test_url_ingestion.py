import io

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app


def _create_pdf() -> bytes:
    document = pymupdf.open()

    try:
        page = document.new_page()

        page.insert_text(
            (72, 72),
            "SERVICE AGREEMENT\n"
            "The Customer shall pay INR 50,000 within 30 days.",
        )

        buffer = io.BytesIO()
        document.save(buffer)

        return buffer.getvalue()

    finally:
        document.close()


def test_url_request_requires_valid_url(client):
    response = client.post(
        "/api/v1/ingestion/url",
        json={
            "url": "not-a-url",
        },
    )

    assert response.status_code == 422


def test_url_request_requires_url(client):
    response = client.post(
        "/api/v1/ingestion/url",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_url_service_rejects_empty_url():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    with pytest.raises(
        ValueError,
        match="URL is required",
    ):
        await URLIngestionService.download("")


@pytest.mark.anyio
async def test_url_service_rejects_non_http_url():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    with pytest.raises(
        ValueError,
        match="Only HTTP and HTTPS",
    ):
        await URLIngestionService.download(
            "ftp://example.com/contract.pdf"
        )


@pytest.mark.anyio
async def test_url_service_rejects_invalid_url():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    with pytest.raises(
        ValueError,
        match="Invalid URL",
    ):
        await URLIngestionService.download(
            "https://"
        )


def test_pdf_extension_detection():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    result = URLIngestionService._detect_extension(
        "https://example.com/contract.pdf",
        "",
    )

    assert result == ".pdf"


def test_content_type_pdf_detection():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    result = URLIngestionService._detect_extension(
        "https://example.com/download",
        "application/pdf",
    )

    assert result == ".pdf"


def test_content_type_docx_detection():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    result = URLIngestionService._detect_extension(
        "https://example.com/download",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert result == ".docx"


def test_content_type_image_detection():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    result = URLIngestionService._detect_extension(
        "https://example.com/download",
        "image/jpeg",
    )

    assert result == ".jpg"


def test_filename_generation():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    filename = URLIngestionService._build_filename(
        "https://example.com/contracts/service.pdf",
        ".pdf",
    )

    assert filename == "service.pdf"


def test_filename_generation_without_filename():
    from app.services.url_ingestion_service import (
        URLIngestionService,
    )

    filename = URLIngestionService._build_filename(
        "https://example.com/download",
        ".pdf",
    )

    assert filename == "downloaded_contract.pdf"


def test_magic_bytes_pdf_detection():
    from app.services.url_ingestion_service import URLIngestionService

    result = URLIngestionService._detect_extension(
        url="https://example.com/download?id=12345",
        content_type="application/octet-stream",
        content=b"%PDF-1.7\n1 0 obj\n<<>>\nendobj",
    )

    assert result == ".pdf"


def test_magic_bytes_docx_detection():
    from app.services.url_ingestion_service import URLIngestionService

    result = URLIngestionService._detect_extension(
        url="https://example.com/stream?file=agreement",
        content_type="application/octet-stream",
        content=b"PK\x03\x04" + b"x" * 50 + b"word/document.xml" + b"x" * 100,
    )

    assert result == ".docx"


def test_content_disposition_filename_and_extension():
    from app.services.url_ingestion_service import URLIngestionService

    ext = URLIngestionService._detect_extension(
        url="https://example.com/get-file",
        content_type="application/octet-stream",
        content_disposition='attachment; filename="Vendor_SLA_2026.pdf"',
    )
    assert ext == ".pdf"

    filename = URLIngestionService._build_filename(
        url="https://example.com/get-file",
        extension=ext,
        content_disposition='attachment; filename="Vendor_SLA_2026.pdf"',
    )
    assert filename == "Vendor_SLA_2026.pdf"


def test_content_disposition_encoded_filename():
    from app.services.url_ingestion_service import URLIngestionService

    filename = URLIngestionService._build_filename(
        url="https://example.com/api/export",
        extension=".pdf",
        content_disposition="attachment; filename*=UTF-8''SERVICE%20AGREEMENT%20FINAL.pdf",
    )
    assert filename == "SERVICE AGREEMENT FINAL.pdf"


def test_url_unquoting_filename_generation():
    from app.services.url_ingestion_service import URLIngestionService

    filename = URLIngestionService._build_filename(
        url="https://example.com/documents/SERVICE+LEVEL+AGREEMENT2026.pdf",
        extension=".pdf",
    )
    assert filename == "SERVICE LEVEL AGREEMENT2026.pdf"


@pytest.mark.anyio
async def test_direct_pdf_url_passes_through_pdf_extraction_pipeline():
    from unittest.mock import AsyncMock, MagicMock, patch
    import socket
    import httpx
    from app.services.url_ingestion_service import URLIngestionService
    from app.services.text_extraction_service import TextExtractionService

    pdf_bytes = _create_pdf()
    fake_dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_redirect = False
    mock_response.content = pdf_bytes
    mock_response.url = httpx.URL("https://example.com/SERVICE+LEVEL+AGREEMENT.pdf")
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'inline; filename="SERVICE LEVEL AGREEMENT.pdf"',
    }
    mock_response.raise_for_status = MagicMock()

    with patch("socket.getaddrinfo", return_value=fake_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            filename, content = await URLIngestionService.download(
                "https://example.com/SERVICE+LEVEL+AGREEMENT.pdf"
            )

    assert filename.endswith(".pdf")
    assert content.startswith(b"%PDF")

    # Pass through existing TextExtractionService pipeline
    extracted_text = TextExtractionService.extract(filename, content)
    assert "SERVICE AGREEMENT" in extracted_text
    assert "INR 50,000" in extracted_text


@pytest.mark.anyio
async def test_direct_webpage_html_url_passes_through_html_extraction_pipeline():
    from unittest.mock import AsyncMock, MagicMock, patch
    import socket
    import httpx
    from app.services.url_ingestion_service import URLIngestionService
    from app.services.text_extraction_service import TextExtractionService

    html_bytes = (
        b"<!DOCTYPE html><html><head><title>Terms</title></head>"
        b"<body><h1>Website Terms of Service</h1><p>Users must comply with all terms.</p></body></html>"
    )
    fake_dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_redirect = False
    mock_response.content = html_bytes
    mock_response.url = httpx.URL("https://example.com/legal/terms")
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.raise_for_status = MagicMock()

    with patch("socket.getaddrinfo", return_value=fake_dns):
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            filename, content = await URLIngestionService.download(
                "https://example.com/legal/terms"
            )

    assert filename.endswith(".html")
    extracted_text = TextExtractionService.extract(filename, content)
    assert "Website Terms of Service" in extracted_text
    assert "Users must comply with all terms." in extracted_text