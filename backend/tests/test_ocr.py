import io

import pymupdf
from PIL import Image, ImageDraw

from app.services.ocr_service import OCRService


def _create_test_image(
    text: str,
    width: int = 1400,
    height: int = 400,
) -> bytes:
    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (50, 100),
        text,
        fill="black",
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def _create_scanned_pdf(
    pages: list[str],
) -> bytes:
    document = pymupdf.open()

    try:
        for text in pages:
            image_bytes = _create_test_image(text)

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            page = document.new_page(
                width=image.width,
                height=image.height,
            )

            page.insert_image(
                page.rect,
                stream=image_bytes,
            )

        buffer = io.BytesIO()

        document.save(buffer)

        return buffer.getvalue()

    finally:
        document.close()


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def test_extract_from_image():
    content = _create_test_image(
        "Payment shall be made within 30 days."
    )

    result = OCRService.extract_from_image(content)

    normalized = _normalize(result)

    assert "payment" in normalized
    assert "30 days" in normalized


def test_extract_jpg_image():
    image = Image.new(
        "RGB",
        (1400, 400),
        "white",
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (50, 100),
        "Cancellation charge of INR 5000 applies.",
        fill="black",
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
    )

    result = OCRService.extract_from_image(
        buffer.getvalue()
    )

    normalized = _normalize(result)

    assert "cancellation" in normalized
    assert "charge" in normalized


def test_extract_jpeg_image():
    image = Image.new(
        "RGB",
        (1400, 400),
        "white",
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (50, 100),
        "Interest shall be charged at 2 percent per month.",
        fill="black",
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=95,
    )

    result = OCRService.extract_from_image(
        buffer.getvalue()
    )

    normalized = _normalize(result)

    assert "interest" in normalized
    assert "2 percent" in normalized


def test_extract_from_image_rejects_empty_content():
    try:
        OCRService.extract_from_image(b"")

        assert False, "Expected ValueError"

    except ValueError as exc:
        assert "empty" in str(exc).lower()


def test_extract_from_pdf_rejects_empty_content():
    try:
        OCRService.extract_from_pdf(b"")

        assert False, "Expected ValueError"

    except ValueError as exc:
        assert "empty" in str(exc).lower()


def test_extract_scanned_pdf():
    content = _create_scanned_pdf(
        [
            "Payment shall be made within 30 days.",
        ]
    )

    result = OCRService.extract_from_pdf(
        content
    )

    normalized = _normalize(result)

    assert "payment" in normalized
    assert "30 days" in normalized


def test_extract_multi_page_scanned_pdf():
    content = _create_scanned_pdf(
        [
            "The Customer shall pay INR 50000.",
            "A cancellation charge of INR 5000 shall apply.",
            "The agreement shall renew for 12 months.",
        ]
    )

    result = OCRService.extract_from_pdf(
        content
    )

    normalized = _normalize(result)

    assert "customer" in normalized
    assert "50000" in normalized
    assert "cancellation" in normalized
    assert "5000" in normalized
    assert "renew" in normalized
    assert "12 months" in normalized