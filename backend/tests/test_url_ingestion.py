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