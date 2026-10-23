from io import BytesIO

import pymupdf
import pytesseract
from PIL import Image


class OCRService:
    """OCR service for images and scanned PDF pages."""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Clean common OCR encoding artifacts while preserving
        the actual contract text.
        """

        if not text:
            return ""

        replacements = {
            "Â°": "•",
            "Â¢": "•",
            "Â·": "•",
            "â€¢": "•",
            "â€“": "–",
            "â€”": "—",
            "â€™": "’",
            "â€œ": "“",
            "â€": "”",
            "â€˜": "‘",
            "Â": "",
            "°": "•",
            "¢": "•",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Normalize excessive whitespace without destroying
        # paragraph structure.
        lines = []

        for line in text.splitlines():
            line = line.strip()

            if line:
                lines.append(line)
            elif lines and lines[-1] != "":
                lines.append("")

        return "\n".join(lines).strip()

    @classmethod
    def extract_from_image(cls, content: bytes) -> str:
        if not content:
            raise ValueError("Image content is empty.")

        try:
            image = Image.open(BytesIO(content))

            text = pytesseract.image_to_string(
                image
            )

        except Exception as exc:
            raise ValueError(
                f"Failed to perform OCR on image: {exc}"
            ) from exc

        return cls._normalize_text(text)

    @classmethod
    def extract_from_pdf(cls, content: bytes) -> str:
        if not content:
            raise ValueError("PDF content is empty.")

        try:
            document = pymupdf.open(
                stream=content,
                filetype="pdf",
            )

            pages = []

            try:
                for page in document:
                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False,
                    )

                    image = Image.frombytes(
                        "RGB",
                        [pixmap.width, pixmap.height],
                        pixmap.samples,
                    )

                    text = pytesseract.image_to_string(
                        image
                    )

                    text = cls._normalize_text(text)

                    if text:
                        pages.append(text)

            finally:
                document.close()

        except Exception as exc:
            raise ValueError(
                f"Failed to perform OCR on PDF: {exc}"
            ) from exc

        return "\n\n".join(pages).strip()