import ipaddress
from pathlib import Path
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import get_settings


class URLIngestionService:
    """Download contract files or webpages from HTTP/HTTPS URLs with SSRF protection."""

    ALLOWED_EXTENSIONS = {
        ".txt",
        ".pdf",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
        ".html",
    }

    MAX_REDIRECTS = 5

    @classmethod
    def _validate_url_ssrf(cls, url: str) -> None:
        """Validate URL against SSRF by checking scheme, host, and resolved IP addresses."""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS URLs are supported.")

        if not parsed.netloc:
            raise ValueError("Invalid URL.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: missing host.")

        # Reject credentials in URL
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not permitted.")

        # Resolve hostname to all TCP IP addresses
        port = parsed.port or (443 if scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(
                hostname,
                port,
                proto=socket.IPPROTO_TCP,
            )
        except socket.gaierror as exc:
            raise ValueError(f"Failed to resolve host '{hostname}'.") from exc

        if not addr_info:
            raise ValueError(f"Could not resolve host '{hostname}'.")

        # Check each resolved IP
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Invalid resolved IP address: {ip_str}")

            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_unspecified
                or ip.is_multicast
                or ip.is_reserved
                or ip_str == "169.254.169.254"
            ):
                raise ValueError(
                    "Access to private, loopback, or internal network addresses is prohibited."
                )

    @classmethod
    async def download(
        cls,
        url: str,
    ) -> tuple[str, bytes]:

        url = url.strip()

        if not url:
            raise ValueError("URL is required.")

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "Only HTTP and HTTPS URLs are supported."
            )

        if not parsed.netloc:
            raise ValueError("Invalid URL.")

        current_url = url
        response = None
        content = None

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=30.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "Chrome/120.0 Safari/537.36"
                    )
                },
            ) as client:
                for redirect_idx in range(cls.MAX_REDIRECTS + 1):
                    cls._validate_url_ssrf(current_url)

                    response = await client.get(current_url)

                    if response.is_redirect:
                        if redirect_idx >= cls.MAX_REDIRECTS:
                            raise ValueError("Too many redirects.")

                        location = response.headers.get("location")
                        if not location:
                            raise ValueError(
                                "Redirect response missing Location header."
                            )

                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content = response.content
                    break

        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                raise ValueError(
                    f"Failed to download URL: HTTP {exc.response.status_code}."
                ) from exc
            raise ValueError(
                f"Failed to download URL: {exc}"
            ) from exc

        if not content:
            raise ValueError(
                "The URL returned an empty response."
            )

        settings = get_settings()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024

        if len(content) > max_bytes:
            raise ValueError(
                f"Downloaded content exceeds the {settings.max_upload_size_mb} MB limit."
            )

        extension = cls._detect_extension(
            url=str(response.url if response else current_url),
            content_type=response.headers.get(
                "content-type",
                "",
            ) if response else "",
        )

        if not extension:
            raise ValueError(
                "Unable to determine the content type of the URL."
            )

        filename = cls._build_filename(
            url=str(response.url if response else current_url),
            extension=extension,
        )

        return filename, content

    @classmethod
    def _detect_extension(
        cls,
        url: str,
        content_type: str,
    ) -> str:

        parsed = urlparse(url)

        extension = Path(
            parsed.path
        ).suffix.lower()

        if extension in cls.ALLOWED_EXTENSIONS:
            return extension

        content_type = (
            content_type
            .split(";")[0]
            .strip()
            .lower()
        )

        content_type_map = {
            "text/plain": ".txt",
            "text/html": ".html",
            "application/xhtml+xml": ".html",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "image/png": ".png",
            "image/jpeg": ".jpg",
        }

        detected = content_type_map.get(
            content_type,
        )

        if detected:
            return detected

        # If the URL has no recognizable extension and the server
        # does not provide a known content type, treat it as a webpage.
        if not extension:
            return ".html"

        return ""

    @staticmethod
    def _build_filename(
        url: str,
        extension: str,
    ) -> str:

        parsed = urlparse(url)

        filename = Path(
            parsed.path
        ).name

        if filename:
            existing_extension = Path(
                filename
            ).suffix.lower()

            if existing_extension in URLIngestionService.ALLOWED_EXTENSIONS:
                return filename

        if extension == ".html":
            return "webpage_contract.html"

        return f"downloaded_contract{extension}"
