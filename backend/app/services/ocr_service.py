import gc
import logging
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

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
    _last_error: str | None = None

    @classmethod
    def _find_apt_roots(cls) -> list[Path]:
        """Discover possible .apt vendor directories across cwd and module trees."""
        candidates = [
            Path.cwd() / ".apt",
            Path.cwd() / "backend" / ".apt",
            Path(__file__).resolve().parents[2] / ".apt",
            Path(__file__).resolve().parents[3] / ".apt",
            Path("/opt/render/project/src/.apt"),
            Path("/opt/render/project/src/backend/.apt"),
        ]
        found = []
        for candidate in candidates:
            if candidate.is_dir() and candidate not in found:
                found.append(candidate)
        return found

    @classmethod
    def _configure_environment_paths(cls) -> None:
        """
        Proactively inject local .apt binary and library paths into PATH,
        LD_LIBRARY_PATH, and TESSDATA_PREFIX before probing Tesseract.
        """
        for apt_root in cls._find_apt_roots():
            # 1. Update PATH with .apt/usr/bin
            bin_dir = apt_root / "usr" / "bin"
            if bin_dir.is_dir():
                current_path = os.environ.get("PATH", "")
                if str(bin_dir) not in current_path:
                    os.environ["PATH"] = f"{bin_dir}:{current_path}"

            # 2. Update LD_LIBRARY_PATH with all vendor library locations
            lib_dirs = [
                apt_root / "usr" / "lib" / "x86_64-linux-gnu",
                apt_root / "usr" / "lib",
                apt_root / "lib" / "x86_64-linux-gnu",
                apt_root / "lib",
            ]
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            for lib_dir in lib_dirs:
                if lib_dir.is_dir() and str(lib_dir) not in current_ld:
                    current_ld = f"{lib_dir}:{current_ld}" if current_ld else str(lib_dir)
            if current_ld:
                os.environ["LD_LIBRARY_PATH"] = current_ld

            # 3. Discover tessdata directory containing eng.traineddata
            for td_candidate in [
                apt_root / "usr" / "share" / "tesseract-ocr" / "4.00" / "tessdata",
                apt_root / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata",
                apt_root / "usr" / "share" / "tessdata",
            ]:
                if td_candidate.is_dir() and (td_candidate / "eng.traineddata").is_file():
                    os.environ["TESSDATA_PREFIX"] = str(td_candidate)
                    break

    @classmethod
    def _configure_tesseract(cls) -> bool:
        """
        Locate and configure the Tesseract executable and language data.
        Validates executable functionality via version check.
        """
        if cls._is_configured and cls._configured_cmd:
            return True

        # Pre-seed environment paths from any .apt directory
        cls._configure_environment_paths()

        settings = get_settings()

        # Build candidate binary paths to probe
        candidate_paths: list[Path] = []

        # 1. Explicit setting or environment variable
        configured_path = settings.tesseract_cmd or os.environ.get("TESSERACT_CMD")
        if configured_path:
            candidate_paths.append(Path(configured_path))

        # 2. Local vendor binaries from .apt
        for apt_root in cls._find_apt_roots():
            candidate_paths.append(apt_root / "usr" / "bin" / "tesseract")

        # 3. System PATH binary
        path_binary = shutil.which("tesseract")
        if path_binary:
            candidate_paths.append(Path(path_binary))

        # 4. Standard Linux & Render deployment paths
        candidate_paths.extend([
            Path("/usr/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
            # Common Windows locations for local development
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ])

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate_paths.append(
                Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
            )

        for candidate in candidate_paths:
            if candidate.is_file():
                try:
                    pytesseract.pytesseract.tesseract_cmd = str(candidate)
                    ver = pytesseract.get_tesseract_version()
                    cls._configured_cmd = str(candidate)
                    cls._is_configured = True
                    cls._last_error = None
                    logger.info("Configured functional Tesseract binary at: %s (v%s)", candidate, ver)
                    return True
                except Exception as exc:
                    cls._last_error = f"Candidate {candidate} failed validation: {exc}"
                    logger.debug(cls._last_error)

        cls._is_configured = False
        return False

    @classmethod
    def get_diagnostics(cls) -> dict[str, Any]:
        """
        Collect startup diagnostics for Tesseract and environment.
        Never logs or exposes any secrets or sensitive credentials.
        """
        cls._configure_environment_paths()
        cls._configure_tesseract()

        cmd = cls._configured_cmd or pytesseract.pytesseract.tesseract_cmd
        which_path = shutil.which("tesseract")

        binary_path = Path(cmd) if cmd else None
        binary_exists = binary_path.is_file() if binary_path else False
        binary_executable = (
            os.access(binary_path, os.X_OK) if binary_path and binary_exists else False
        )

        tessdata_prefix = os.environ.get("TESSDATA_PREFIX")
        installed_languages: list[str] = []
        eng_traineddata_found = False

        ver_str = None
        error_msg = cls._last_error
        is_avail = False

        if binary_exists:
            try:
                ver_str = str(pytesseract.get_tesseract_version())
                is_avail = True
                error_msg = None
            except Exception as exc:
                error_msg = str(exc)
                is_avail = False

            if is_avail:
                try:
                    installed_languages = pytesseract.get_languages()
                    eng_traineddata_found = "eng" in installed_languages
                except Exception:
                    pass

        # Check filesystem fallback for eng.traineddata
        if not eng_traineddata_found:
            tessdata_candidates = []
            if tessdata_prefix:
                tessdata_candidates.append(Path(tessdata_prefix))
            tessdata_candidates.extend([
                Path("/usr/share/tesseract-ocr/5/tessdata"),
                Path("/usr/share/tesseract-ocr/4.00/tessdata"),
                Path("/usr/share/tessdata"),
                Path("/usr/local/share/tessdata"),
                Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
                Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
            ])
            for td in tessdata_candidates:
                if td.is_dir() and (td / "eng.traineddata").is_file():
                    eng_traineddata_found = True
                    if not tessdata_prefix:
                        tessdata_prefix = str(td)
                    break

        return {
            "configured_cmd": cmd,
            "shutil_which": which_path,
            "binary_exists": binary_exists,
            "binary_executable": binary_executable,
            "tessdata_prefix": tessdata_prefix,
            "eng_traineddata_found": eng_traineddata_found,
            "installed_languages": installed_languages,
            "tesseract_version": ver_str,
            "is_available": is_avail,
            "error": error_msg,
        }

    @classmethod
    def log_startup_diagnostics(cls) -> None:
        """Log safe, non-sensitive Tesseract diagnostics during server boot."""
        diag = cls.get_diagnostics()
        logger.info("=== [OCR Startup Diagnostics] ===")
        logger.info("Tesseract binary: %s (exists=%s, executable=%s)", diag["configured_cmd"], diag["binary_exists"], diag["binary_executable"])
        logger.info("shutil.which('tesseract'): %s", diag["shutil_which"])
        logger.info("TESSDATA_PREFIX: %s (eng.traineddata=%s)", diag["tessdata_prefix"], diag["eng_traineddata_found"])
        logger.info("Installed Languages: %s", diag["installed_languages"])
        logger.info("tesseract --version: %s", diag["tesseract_version"])
        logger.info("OCR Engine Status: %s", "READY" if diag["is_available"] else f"UNAVAILABLE ({diag['error']})")
        logger.info("=================================")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Tesseract binary is available and functional."""
        diag = cls.get_diagnostics()
        return diag["is_available"]



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