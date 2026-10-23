import io

import pymupdf
from PIL import Image, ImageDraw

from app.services.text_extraction_service import TextExtractionService


def _create_test_image(text: str) -> bytes:
    image = Image.new("RGB", (1000, 250), "white")
    draw = ImageDraw.Draw(image)

    draw.text(
        (40, 80),
        text,
        fill="black",
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()


def _create_scanned_pdf(text: str) -> bytes:
    image_bytes = _create_test_image(text)

    image = Image.open(io.BytesIO(image_bytes))

    buffer = io.BytesIO()

    document = pymupdf.open()
    page = document.new_page(
        width=image.width,
        height=image.height,
    )

    page.insert_image(
        page.rect,
        stream=image_bytes,
    )

    document.save(buffer)
    document.close()

    return buffer.getvalue()


def test_extract_image_uses_ocr():
    content = _create_test_image(
        "Payment shall be made within 30 days."
    )

    result = TextExtractionService.extract(
        filename="contract.png",
        content=content,
    )

    normalized = " ".join(result.split()).lower()

    assert "payment" in normalized
    assert "30 days" in normalized


def test_extract_pdf_with_text_uses_normal_pdf_extraction():
    document = pymupdf.open()

    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Payment shall be made within 30 days.",
    )

    buffer = io.BytesIO()
    document.save(buffer)
    document.close()

    result = TextExtractionService.extract(
        filename="contract.pdf",
        content=buffer.getvalue(),
    )

    normalized = " ".join(result.split()).lower()

    assert "payment" in normalized
    assert "30 days" in normalized


def test_extract_scanned_pdf_uses_ocr():
    content = _create_scanned_pdf(
        "Payment shall be made within 30 days."
    )

    result = TextExtractionService.extract(
        filename="scanned-contract.pdf",
        content=content,
    )

    normalized = " ".join(result.split()).lower()

    assert "payment" in normalized
    assert "30 days" in normalized