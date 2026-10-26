import gc
import logging
import os
import shutil
from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR service for images and scanned PDF pages.
    Optimized for low-memory environments (such as Render 512MB limits)
    with automatic system Tesseract discovery and graceful degradation.
    """

    MAX_IMAGE_DIMENSION: int = 2000
    MAX_PDF_OCR_PAGES: int = 30
    _configured_cmd: str | None = None
    _is_configured: bool = False

    @classmethod
    def _configure_tesseract(cls) -> bool:
        """
        Locate and configure the Tesseract executable and language data.
        Supports standard system PATH, Render .apt vendor directories,
        custom environment settings, and standard OS installation paths.
        """
        if cls._is_configured and cls._configured_cmd:
            return True

        settings = get_settings()

        # 1. Explicit setting or environment variable
        configured_path = settings.tesseract_cmd or os.environ.get("TESSERACT_CMD")
        if configured_path and Path(configured_path).is_file():
            cls._apply_tesseract_cmd(str(configured_path))
            cls._configure_tessdata(settings.tessdata_prefix, Path(configured_path))
            cls._is_configured = True
            return True

        # 2. Check system PATH
        path_binary = shutil.which("tesseract")
        if path_binary:
            cls._apply_tesseract_cmd(path_binary)
            cls._configure_tessdata(settings.tessdata_prefix, Path(path_binary))
            cls._is_configured = True
            return True

        # 3. Known Linux & Render deployment paths (.apt, /usr/bin, etc.)
        candidate_paths = [
            Path("/usr/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
            Path("/opt/render/project/src/.apt/usr/bin/tesseract"),
            Path("/opt/render/project/src/backend/.apt/usr/bin/tesseract"),
            Path.cwd() / ".apt" / "usr" / "bin" / "tesseract",
            Path(__file__).resolve().parents[2] / ".apt" / "usr" / "bin" / "tesseract",
            Path(__file__).resolve().parents[3] / ".apt" / "usr" / "bin" / "tesseract",
            # Standard Windows locations for local development
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate_paths.append(
                Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
            )

        for candidate in candidate_paths:
            if candidate.is_file():
                cls._apply_tesseract_cmd(str(candidate))
                cls._configure_tessdata(settings.tessdata_prefix, candidate)
                cls._is_configured = True
                return True

        return False

    @classmethod
    def _apply_tesseract_cmd(cls, cmd_path: str) -> None:
        cls._configured_cmd = cmd_path
        pytesseract.pytesseract.tesseract_cmd = cmd_path
        logger.info("Configured Tesseract binary at: %s", cmd_path)

    @classmethod
    def _configure_tessdata(
        cls,
        custom_prefix: str | None = None,
        binary_path: Path | None = None,
    ) -> None:
        """Ensure TESSDATA_PREFIX and library search paths are configured."""
        if custom_prefix and Path(custom_prefix).is_dir():
            os.environ["TESSDATA_PREFIX"] = str(custom_prefix)
            return

        if "TESSDATA_PREFIX" in os.environ and Path(os.environ["TESSDATA_PREFIX"]).is_dir():
            return

        # If binary is inside a .apt directory on Render, add library paths and tessdata
        if binary_path and ".apt" in binary_path.parts:
            apt_idx = binary_path.parts.index(".apt")
            apt_root = Path(*binary_path.parts[: apt_idx + 1])

            bin_dir = apt_root / "usr" / "bin"
            if bin_dir.is_dir():
                current_path = os.environ.get("PATH", "")
                if str(bin_dir) not in current_path:
                    os.environ["PATH"] = f"{bin_dir}:{current_path}"

            lib_dirs = [
                apt_root / "usr" / "lib" / "x86_64-linux-gnu",
                apt_root / "usr" / "lib",
                apt_root / "lib" / "x86_64-linux-gnu",
                apt_root / "lib",
            ]
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            for lib_dir in lib_dirs:
                if lib_dir.is_dir() and str(lib_dir) not in current_ld:
                    current_ld = (
                        f"{lib_dir}:{current_ld}" if current_ld else str(lib_dir)
                    )
            if current_ld:
                os.environ["LD_LIBRARY_PATH"] = current_ld

            for td_candidate in [
                apt_root / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata",
                apt_root / "usr" / "share" / "tesseract-ocr" / "4.00" / "tessdata",
                apt_root / "usr" / "share" / "tessdata",
            ]:
                if td_candidate.is_dir():
                    os.environ["TESSDATA_PREFIX"] = str(td_candidate)
                    return

    @classmethod
    def is_available(cls) -> bool:
        """Check if Tesseract binary is available and functional."""
        if not cls._configure_tesseract():
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception as exc:
            logger.warning("Tesseract availability check failed: %s", exc)
            return False

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
            "â€ ": "”",
            "â€˜": "‘",
            "Â": "",
            "°": "•",
            "¢": "•",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Normalize excessive whitespace without destroying paragraph structure.
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
            elif lines and lines[-1] != "":
                lines.append("")

        return "\n".join(lines).strip()

    @classmethod
    def _prepare_image_for_ocr(cls, image: Image.Image) -> Image.Image:
        """
        Optimize image for OCR accuracy and bounded memory usage:
        1. Downsample oversized images so max dimension <= MAX_IMAGE_DIMENSION.
        2. Convert to grayscale (1 channel) to cut PIL memory usage by 66% while
           preserving or improving OCR accuracy.
        """
        width, height = image.size
        max_dim = max(width, height)

        if max_dim > cls.MAX_IMAGE_DIMENSION:
            scale = cls.MAX_IMAGE_DIMENSION / float(max_dim)
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            image = image.resize((new_width, new_height), resample=resample_filter)

        if image.mode != "L":
            image = image.convert("L")

        return image

    @classmethod
    def extract_from_image(cls, content: bytes) -> str:
        """
        Extract text from an image with bounded memory and robust error handling.
        """
        if not content:
            raise ValueError("Image content is empty.")

        if not cls._configure_tesseract():
            raise ValueError(
                "Tesseract is not installed or it's not in your PATH. "
                "Please configure the tesseract-ocr system dependency in production."
            )

        try:
            raw_image = Image.open(BytesIO(content))
        except (UnidentifiedImageError, Exception) as exc:
            raise ValueError(
                f"Uploaded image is corrupted or in an unsupported format: {exc}"
            ) from exc

        try:
            processed_image = cls._prepare_image_for_ocr(raw_image)
            text = pytesseract.image_to_string(processed_image)
        except pytesseract.pytesseract.TesseractNotFoundError as exc:
            raise ValueError(
                "Tesseract is not installed or it's not in your PATH. "
                "Please configure the tesseract-ocr system dependency in production."
            ) from exc
        except Exception as exc:
            raise ValueError(
                f"Failed to perform OCR on image: {exc}"
            ) from exc
        finally:
            try:
                raw_image.close()
            except Exception:
                pass

        return cls._normalize_text(text)

    @classmethod
    def extract_from_pdf(cls, content: bytes) -> str:
        """
        Extract text from scanned PDF pages using PyMuPDF and Tesseract.
        Renders directly to grayscale and caps resolution/page counts to stay
        strictly within 512 MB memory constraints.
        """
        if not content:
            raise ValueError("PDF content is empty.")

        if not cls._configure_tesseract():
            raise ValueError(
                "Tesseract is not installed or it's not in your PATH. "
                "Please configure the tesseract-ocr system dependency in production."
            )

        try:
            document = pymupdf.open(
                stream=content,
                filetype="pdf",
            )
        except Exception as exc:
            raise ValueError(
                f"Failed to open PDF document for OCR: {exc}"
            ) from exc

        pages = []
        try:
            total_pages = len(document)
            # Process up to MAX_PDF_OCR_PAGES to stay strictly within 512MB RAM
            pages_to_process = min(total_pages, cls.MAX_PDF_OCR_PAGES)

            for page_index in range(pages_to_process):
                page = document[page_index]
                rect = page.rect
                max_dim = max(rect.width, rect.height)

                # Dynamically choose zoom to keep rendered page <= 2000px
                zoom = min(2.0, 2000.0 / max(max_dim, 1.0))
                zoom = max(1.0, zoom)
                matrix = pymupdf.Matrix(zoom, zoom)

                # Render directly to grayscale to cut memory consumption by 66%
                pixmap = page.get_pixmap(
                    matrix=matrix,
                    alpha=False,
                    colorspace=pymupdf.csGRAY,
                )

                try:
                    image = Image.frombytes(
                        "L",
                        [pixmap.width, pixmap.height],
                        pixmap.samples,
                    )
                finally:
                    # Immediately release PyMuPDF C memory
                    del pixmap

                try:
                    page_text = pytesseract.image_to_string(image)
                except pytesseract.pytesseract.TesseractNotFoundError as exc:
                    raise ValueError(
                        "Tesseract is not installed or it's not in your PATH. "
                        "Please configure the tesseract-ocr system dependency in production."
                    ) from exc
                finally:
                    try:
                        image.close()
                    except Exception:
                        pass
                    del image

                normalized = cls._normalize_text(page_text)
                if normalized:
                    pages.append(normalized)

            if total_pages > cls.MAX_PDF_OCR_PAGES:
                logger.warning(
                    "PDF has %d pages; OCR was capped at %d pages to prevent memory exhaustion.",
                    total_pages,
                    cls.MAX_PDF_OCR_PAGES,
                )

        except pytesseract.pytesseract.TesseractNotFoundError as exc:
            raise ValueError(
                "Tesseract is not installed or it's not in your PATH. "
                "Please configure the tesseract-ocr system dependency in production."
            ) from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"Failed to perform OCR on PDF: {exc}"
            ) from exc
        finally:
            document.close()
            gc.collect()

        return "\n\n".join(pages).strip()