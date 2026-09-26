import ipaddress
from pathlib import Path
import re
import socket
import time
from urllib.parse import unquote_plus, urljoin, urlparse

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
    def _resolve_host_ips(cls, hostname: str, port: int) -> list[str]:
        """
        Safely resolve hostname to all IP addresses (IPv4 and IPv6).
        Includes transient retry and IPv4 fallback if dual-stack/IPv6 resolution fails.
        """
        addr_info = []
        last_exc: Exception | None = None

        # 1. Try standard dual-stack getaddrinfo with stream socket type (retry once for transient DNS timeout)
        for attempt in range(2):
            try:
                addr_info = socket.getaddrinfo(
                    hostname,
                    port,
                    family=socket.AF_UNSPEC,
                    type=socket.SOCK_STREAM,
                )
                if addr_info:
                    break
            except socket.gaierror as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(0.2)

        # 2. If dual-stack resolution failed (common on networks where IPv6 AAAA query fails/times out),
        # fall back to IPv4 resolution
        if not addr_info:
            try:
                addr_info = socket.getaddrinfo(
                    hostname,
                    port,
                    family=socket.AF_INET,
                    type=socket.SOCK_STREAM,
                )
            except socket.gaierror as exc:
                last_exc = exc

        ip_list: list[str] = []
        if addr_info:
            for entry in addr_info:
                sockaddr = entry[4]
                ip_list.append(sockaddr[0])
        else:
            # 3. Final resolver fallback via gethostbyname_ex (IPv4 only)
            try:
                _, _, host_ips = socket.gethostbyname_ex(hostname)
                ip_list.extend(host_ips)
            except socket.gaierror as exc:
                last_exc = exc

        if not ip_list:
            raise ValueError(f"Failed to resolve host '{hostname}'.") from last_exc

        return ip_list

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

        port = parsed.port or (443 if scheme == "https" else 80)
        ip_list = cls._resolve_host_ips(hostname, port)

        # Check each resolved IP against prohibited ranges
        cgnat_net = ipaddress.ip_network("100.64.0.0/10")
        for ip_str in ip_list:
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
                or ip in cgnat_net
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
                timeout=httpx.Timeout(45.0, connect=15.0, read=35.0),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    ),
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",
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

        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Failed to download URL: HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            host = parsed.hostname or url
            raise ValueError(
                f"Could not connect to host '{host}'. The server may be unreachable."
            ) from exc
        except httpx.ReadTimeout as exc:
            host = parsed.hostname or url
            raise ValueError(
                f"Timed out while reading response from '{host}'."
            ) from exc
        except httpx.RequestError as exc:
            err_msg = str(exc) or type(exc).__name__
            raise ValueError(
                f"Failed to download URL: {err_msg}"
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

        content_disposition = (
            response.headers.get("content-disposition", "")
            if response
            else ""
        )
        content_type = (
            response.headers.get("content-type", "")
            if response
            else ""
        )
        final_url = str(response.url if response else current_url)

        extension = cls._detect_extension(
            url=final_url,
            content_type=content_type,
            content=content,
            content_disposition=content_disposition,
        )

        if not extension:
            raise ValueError(
                "Unable to determine the content type of the URL."
            )

        filename = cls._build_filename(
            url=final_url,
            extension=extension,
            content_disposition=content_disposition,
        )

        return filename, content

    @staticmethod
    def _extract_filename_from_disposition(disposition: str) -> str:
        """Extract filename from Content-Disposition header if present."""
        if not disposition:
            return ""

        # RFC 5987 format: filename*=UTF-8''encoded_name
        match_star = re.search(
            r"filename\*\s*=\s*(?:UTF-8''|utf-8'')([^;\r\n]+)",
            disposition,
            re.IGNORECASE,
        )
        if match_star:
            return unquote_plus(match_star.group(1).strip().strip('"\''))

        # Standard format: filename="name" or filename=name
        match = re.search(
            r'filename\s*=\s*(?:"([^"]+)"|([^\s;]+))',
            disposition,
            re.IGNORECASE,
        )
        if match:
            fn = match.group(1) or match.group(2)
            return unquote_plus(fn.strip().strip('"\''))

        return ""

    @classmethod
    def _detect_extension(
        cls,
        url: str,
        content_type: str = "",
        content: bytes | None = None,
        content_disposition: str = "",
    ) -> str:
        """
        Detect file extension using multiple signals:
        1. Magic bytes in content (%PDF, PK\x03\x04 for docx)
        2. Content-Disposition filename
        3. URL path extension
        4. Content-Type header
        5. Content text/HTML inspection fallback
        """
        # 1. Magic bytes inspection
        if content:
            if content.startswith(b"%PDF"):
                return ".pdf"
            if content.startswith(b"PK\x03\x04"):
                if (
                    "wordprocessingml" in (content_type or "").lower()
                    or "docx" in (content_disposition or "").lower()
                    or "docx" in url.lower()
                    or b"word/" in content[:2000]
                ):
                    return ".docx"
            if content.startswith(b"\x89PNG\r\n\x1a\n"):
                return ".png"
            if content.startswith(b"\xff\xd8\xff"):
                return ".jpg"

        # 2. Content-Disposition filename
        if content_disposition:
            cd_filename = cls._extract_filename_from_disposition(content_disposition)
            if cd_filename:
                cd_ext = Path(cd_filename).suffix.lower()
                if cd_ext in cls.ALLOWED_EXTENSIONS:
                    return cd_ext

        # 3. URL path extension
        parsed = urlparse(url)
        unquoted_path = unquote_plus(parsed.path)
        path_ext = Path(unquoted_path).suffix.lower()
        if path_ext in cls.ALLOWED_EXTENSIONS:
            return path_ext

        # 4. Content-Type mapping
        content_type_clean = (
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
            "application/x-pdf": ".pdf",
            "application/acrobat": ".pdf",
            "applications/vnd.pdf": ".pdf",
            "text/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/docx": ".docx",
            "application/msword": ".docx",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
        }

        detected = content_type_map.get(content_type_clean)
        if detected:
            return detected

        # 5. Content inspection fallback
        if content:
            sample = content[:1024].lower()
            if (
                b"<!doctype html" in sample
                or b"<html" in sample
                or b"<head" in sample
                or b"<body" in sample
            ):
                return ".html"
            try:
                content[:1024].decode("utf-8")
                return ".txt"
            except UnicodeDecodeError:
                pass

        # If the URL has no recognizable extension and the server
        # does not provide a known content type, treat it as a webpage.
        if not path_ext:
            return ".html"

        return ""

    @classmethod
    def _build_filename(
        cls,
        url: str,
        extension: str,
        content_disposition: str = "",
    ) -> str:
        # 1. Prefer filename from Content-Disposition header
        if content_disposition:
            cd_filename = cls._extract_filename_from_disposition(content_disposition)
            if cd_filename:
                cd_name = Path(cd_filename).name
                cd_ext = Path(cd_name).suffix.lower()
                if cd_ext in cls.ALLOWED_EXTENSIONS:
                    return cd_name
                return f"{Path(cd_name).stem}{extension}"

        # 2. Extract from URL path if it has a recognized extension
        parsed = urlparse(url)
        unquoted_path = unquote_plus(parsed.path)
        filename = Path(unquoted_path).name

        if filename:
            existing_extension = Path(filename).suffix.lower()
            if existing_extension in cls.ALLOWED_EXTENSIONS:
                return filename

        # 3. Fallback defaults
        if extension == ".html":
            return "webpage_contract.html"

        return f"downloaded_contract{extension}"

