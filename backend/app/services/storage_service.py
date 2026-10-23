from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any


class BaseStorageService(ABC):
    """Abstract storage interface defining operations for contract uploads, extracted text, and clause caches."""

    @abstractmethod
    def save_upload(self, file_id: str, extension: str, content: bytes) -> Path | str:
        """Save raw uploaded contract file content."""
        pass

    @abstractmethod
    def read_upload(self, file_id: str, extension: str) -> bytes | None:
        """Read raw uploaded contract file content if it exists."""
        pass

    @abstractmethod
    def delete_upload(self, file_id: str, extension: str) -> bool:
        """Delete raw uploaded contract file if it exists."""
        pass

    @abstractmethod
    def upload_exists(self, file_id: str, extension: str | None = None) -> bool:
        """Check if raw uploaded file exists. If extension is None, check for any extension."""
        pass

    @abstractmethod
    def save_extracted_text(self, file_id: str, text: str) -> Path | str:
        """Save extracted text for a contract."""
        pass

    @abstractmethod
    def read_extracted_text(self, file_id: str) -> str | None:
        """Read extracted text for a contract if it exists."""
        pass

    @abstractmethod
    def delete_extracted_text(self, file_id: str) -> bool:
        """Delete extracted text for a contract if it exists."""
        pass

    @abstractmethod
    def extracted_text_exists(self, file_id: str) -> bool:
        """Check if extracted text exists for a contract."""
        pass

    @abstractmethod
    def save_clauses_json(self, file_id: str, clauses_data: dict[str, Any] | list[Any]) -> Path | str:
        """Save clause data in JSON format."""
        pass

    @abstractmethod
    def load_clauses_json(self, file_id: str) -> dict[str, Any] | None:
        """Load clause data JSON for a contract if it exists."""
        pass

    @abstractmethod
    def delete_clauses_json(self, file_id: str) -> bool:
        """Delete clause data JSON for a contract if it exists."""
        pass

    @abstractmethod
    def clauses_json_exists(self, file_id: str) -> bool:
        """Check if clause data JSON exists for a contract."""
        pass

    @abstractmethod
    def has_contract_data(self, file_id: str) -> bool:
        """Check if any data (upload, extracted text, or clause JSON) exists for a contract."""
        pass


class LocalStorageService(BaseStorageService):
    """Local filesystem implementation of the storage service."""

    def __init__(
        self,
        base_dir: Path | str = Path("storage"),
        uploads_dir: Path | str | None = None,
        extracted_dir: Path | str | None = None,
        clauses_dir: Path | str | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self._uploads_dir = Path(uploads_dir) if uploads_dir else None
        self._extracted_dir = Path(extracted_dir) if extracted_dir else None
        self._clauses_dir = Path(clauses_dir) if clauses_dir else None

    @property
    def uploads_dir(self) -> Path:
        if self._uploads_dir is not None:
            return self._uploads_dir
        try:
            from app.services.file_ingestion_service import FileIngestionService
            configured = Path(FileIngestionService.UPLOAD_DIR)
            if configured != Path(FileIngestionService.BASE_STORAGE_DIR) / "uploads":
                return configured
        except (ImportError, AttributeError):
            pass
        if self.base_dir != Path("storage"):
            return self.base_dir / "uploads"
        try:
            from app.services.file_ingestion_service import FileIngestionService
            return Path(FileIngestionService.UPLOAD_DIR)
        except (ImportError, AttributeError):
            return self.base_dir / "uploads"

    @property
    def extracted_dir(self) -> Path:
        if self._extracted_dir is not None:
            return self._extracted_dir
        try:
            from app.services.file_ingestion_service import FileIngestionService
            configured = Path(FileIngestionService.EXTRACTED_DIR)
            if configured != Path(FileIngestionService.BASE_STORAGE_DIR) / "extracted":
                return configured
        except (ImportError, AttributeError):
            pass
        if self.base_dir != Path("storage"):
            return self.base_dir / "extracted"
        try:
            from app.services.file_ingestion_service import FileIngestionService
            return Path(FileIngestionService.EXTRACTED_DIR)
        except (ImportError, AttributeError):
            return self.base_dir / "extracted"

    @property
    def clauses_dir(self) -> Path:
        if self._clauses_dir is not None:
            return self._clauses_dir
        try:
            from app.services.clause_storage_service import ClauseStorageService
            configured = Path(ClauseStorageService.CLAUSES_DIR)
            if self.base_dir != Path("storage") and configured != self.base_dir / "clauses" and configured != Path("storage/clauses"):
                return configured
        except (ImportError, AttributeError):
            pass
        if self.base_dir != Path("storage"):
            return self.base_dir / "clauses"
        try:
            from app.services.clause_storage_service import ClauseStorageService
            return Path(ClauseStorageService.CLAUSES_DIR)
        except (ImportError, AttributeError):
            return self.base_dir / "clauses"

    def validate_file_id(self, file_id: str) -> str:
        """Validate and return safe file identifier, raising ValueError on path traversal attempts."""
        if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id or "\x00" in file_id:
            raise ValueError("Invalid file identifier.")
        return file_id

    def _resolve_safe_path(self, parent_dir: Path, filename: str) -> Path:
        resolved_parent = parent_dir.resolve()
        resolved_path = (parent_dir / filename).resolve()
        if not resolved_path.is_relative_to(resolved_parent):
            raise ValueError("Invalid storage path destination.")
        return resolved_path


    # --- Raw Uploads ---

    def save_upload(self, file_id: str, extension: str, content: bytes) -> Path:
        clean_id = self.validate_file_id(file_id)
        clean_ext = extension.strip()
        if not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self._resolve_safe_path(self.uploads_dir, f"{clean_id}{clean_ext}")
        stored_path.write_bytes(content)
        return stored_path

    def read_upload(self, file_id: str, extension: str) -> bytes | None:
        try:
            clean_id = self.validate_file_id(file_id)
        except ValueError:
            return None

        clean_ext = extension.strip()
        if not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"

        try:
            stored_path = self._resolve_safe_path(self.uploads_dir, f"{clean_id}{clean_ext}")
        except ValueError:
            return None

        if not stored_path.is_file():
            return None

        try:
            return stored_path.read_bytes()
        except OSError:
            return None

    def delete_upload(self, file_id: str, extension: str) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
        except ValueError:
            return False

        clean_ext = extension.strip()
        if not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"

        try:
            stored_path = self._resolve_safe_path(self.uploads_dir, f"{clean_id}{clean_ext}")
        except ValueError:
            return False

        if not stored_path.is_file():
            return False

        try:
            stored_path.unlink()
            return True
        except OSError:
            return False

    def upload_exists(self, file_id: str, extension: str | None = None) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
        except ValueError:
            return False

        if extension:
            clean_ext = extension.strip()
            if not clean_ext.startswith("."):
                clean_ext = f".{clean_ext}"
            try:
                stored_path = self._resolve_safe_path(self.uploads_dir, f"{clean_id}{clean_ext}")
                return stored_path.is_file()
            except ValueError:
                return False

        if not self.uploads_dir.exists():
            return False

        matches = list(self.uploads_dir.glob(f"{clean_id}.*"))
        return any(p.is_file() for p in matches)

    # --- Extracted Text ---

    def save_extracted_text(self, file_id: str, text: str) -> Path:
        clean_id = self.validate_file_id(file_id)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        extracted_path = self._resolve_safe_path(self.extracted_dir, f"{clean_id}.txt")
        extracted_path.write_text(text, encoding="utf-8")
        return extracted_path

    def read_extracted_text(self, file_id: str) -> str | None:
        try:
            clean_id = self.validate_file_id(file_id)
            extracted_path = self._resolve_safe_path(self.extracted_dir, f"{clean_id}.txt")
        except ValueError:
            return None

        if not extracted_path.is_file():
            return None

        try:
            return extracted_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def delete_extracted_text(self, file_id: str) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
            extracted_path = self._resolve_safe_path(self.extracted_dir, f"{clean_id}.txt")
        except ValueError:
            return False

        if not extracted_path.is_file():
            return False

        try:
            extracted_path.unlink()
            return True
        except OSError:
            return False

    def extracted_text_exists(self, file_id: str) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
            extracted_path = self._resolve_safe_path(self.extracted_dir, f"{clean_id}.txt")
            return extracted_path.is_file()
        except ValueError:
            return False

    # --- Clause JSON ---

    def save_clauses_json(self, file_id: str, clauses_data: dict[str, Any] | list[Any]) -> Path:
        clean_id = self.validate_file_id(file_id)
        self.clauses_dir.mkdir(parents=True, exist_ok=True)
        clauses_path = self._resolve_safe_path(self.clauses_dir, f"{clean_id}.json")

        if isinstance(clauses_data, list):
            data_to_write = {
                "file_id": clean_id,
                "clause_count": len(clauses_data),
                "clauses": clauses_data,
            }
        else:
            data_to_write = clauses_data

        clauses_path.write_text(
            json.dumps(data_to_write, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return clauses_path

    def load_clauses_json(self, file_id: str) -> dict[str, Any] | None:
        try:
            clean_id = self.validate_file_id(file_id)
            clauses_path = self._resolve_safe_path(self.clauses_dir, f"{clean_id}.json")
        except ValueError:
            return None

        if not clauses_path.is_file():
            return None

        try:
            return json.loads(clauses_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def delete_clauses_json(self, file_id: str) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
            clauses_path = self._resolve_safe_path(self.clauses_dir, f"{clean_id}.json")
        except ValueError:
            return False

        if not clauses_path.is_file():
            return False

        try:
            clauses_path.unlink()
            return True
        except OSError:
            return False

    def clauses_json_exists(self, file_id: str) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
            clauses_path = self._resolve_safe_path(self.clauses_dir, f"{clean_id}.json")
            return clauses_path.is_file()
        except ValueError:
            return False

    # --- Composite Check ---

    def has_contract_data(self, file_id: str) -> bool:
        return (
            self.extracted_text_exists(file_id)
            or self.clauses_json_exists(file_id)
            or self.upload_exists(file_id)
        )


class R2StorageService(BaseStorageService):
    """Cloudflare R2 (S3-compatible) implementation of the storage service."""

    def __init__(
        self,
        bucket_name: str | None = None,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        endpoint_url: str | None = None,
        s3_client: Any = None,
        uploads_prefix: str = "uploads",
        extracted_prefix: str = "extracted",
        clauses_prefix: str = "clauses",
    ) -> None:
        self.bucket_name = bucket_name or "term-shield-storage"
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self._endpoint_url = endpoint_url
        self._client = s3_client
        self.uploads_prefix = uploads_prefix.strip("/")
        self.extracted_prefix = extracted_prefix.strip("/")
        self.clauses_prefix = clauses_prefix.strip("/")

    @property
    def endpoint_url(self) -> str:
        if self._endpoint_url:
            return self._endpoint_url
        if self.account_id:
            return f"https://{self.account_id}.r2.cloudflarestorage.com"
        return "https://r2.cloudflarestorage.com"

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as err:
                raise RuntimeError(
                    "boto3 is required for R2StorageService but is not installed."
                ) from err

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
            )
        return self._client

    # --- Key Resolution & Path Safety ---

    def validate_file_id(self, file_id: str) -> str:
        """Validate and return safe file identifier, raising ValueError on path traversal attempts."""
        if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id or "\x00" in file_id:
            raise ValueError("Invalid file identifier.")
        return file_id

    @staticmethod
    def validate_extension(extension: str) -> str:
        """Validate and return safe file extension, raising ValueError on path traversal, separators, or malformed input."""
        if not extension or not isinstance(extension, str):
            raise ValueError("Invalid file extension.")
        clean_ext = extension.strip()
        if (
            not clean_ext
            or clean_ext == "."
            or "/" in clean_ext
            or "\\" in clean_ext
            or ".." in clean_ext
            or "\x00" in clean_ext
        ):
            raise ValueError("Invalid file extension.")
        if not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"
        ext_body = clean_ext[1:]
        if (
            not ext_body
            or any(c.isspace() or not (c.isalnum() or c in ".-_") for c in ext_body)
            or ext_body.endswith(".")
        ):
            raise ValueError("Invalid file extension.")
        return clean_ext

    def get_upload_key(self, file_id: str, extension: str) -> str:
        clean_id = self.validate_file_id(file_id)
        clean_ext = self.validate_extension(extension)
        return f"{self.uploads_prefix}/{clean_id}{clean_ext}"

    def get_extracted_text_key(self, file_id: str) -> str:
        clean_id = self.validate_file_id(file_id)
        return f"{self.extracted_prefix}/{clean_id}.txt"

    def get_clauses_json_key(self, file_id: str) -> str:
        clean_id = self.validate_file_id(file_id)
        return f"{self.clauses_prefix}/{clean_id}.json"

    @staticmethod
    def _guess_content_type(extension: str) -> str:
        ext = extension.lower().lstrip(".")
        types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "txt": "text/plain; charset=utf-8",
            "json": "application/json",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "mkv": "video/x-matroska",
            "webm": "video/webm",
        }
        return types.get(ext, "application/octet-stream")

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        if hasattr(exc, "response") and isinstance(exc.response, dict):
            error_dict = exc.response.get("Error", {})
            code = str(error_dict.get("Code", ""))
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"NoSuchKey", "NotFound", "404", "NoSuchBucket"} or status_code == 404:
                return True
        err_str = str(exc).lower()
        return "nosuchkey" in err_str or "not found" in err_str or "404" in err_str

    def _object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    # --- Raw Uploads (Private by default) ---

    def save_upload(self, file_id: str, extension: str, content: bytes) -> str:
        key = self.get_upload_key(file_id, extension)
        content_type = self._guess_content_type(extension)
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return key

    def read_upload(self, file_id: str, extension: str) -> bytes | None:
        try:
            key = self.get_upload_key(file_id, extension)
        except ValueError:
            return None

        try:
            resp = self.client.get_object(Bucket=self.bucket_name, Key=key)
            body = resp.get("Body")
            if body is None:
                return None
            if hasattr(body, "read"):
                return body.read()
            if isinstance(body, (bytes, bytearray)):
                return bytes(body)
            return None
        except Exception as exc:
            if self._is_not_found_error(exc):
                return None
            raise

    def delete_upload(self, file_id: str, extension: str) -> bool:
        try:
            key = self.get_upload_key(file_id, extension)
        except ValueError:
            return False

        if not self.upload_exists(file_id, extension):
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    def upload_exists(self, file_id: str, extension: str | None = None) -> bool:
        try:
            clean_id = self.validate_file_id(file_id)
        except ValueError:
            return False

        if extension is not None:
            try:
                key = self.get_upload_key(clean_id, extension)
            except ValueError:
                return False
            return self._object_exists(key)

        prefix = f"{self.uploads_prefix}/{clean_id}."
        try:
            resp = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1,
            )
            return resp.get("KeyCount", 0) > 0 or len(resp.get("Contents", [])) > 0
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    # --- Extracted Text ---

    def save_extracted_text(self, file_id: str, text: str) -> str:
        key = self.get_extracted_text_key(file_id)
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        return key

    def read_extracted_text(self, file_id: str) -> str | None:
        try:
            key = self.get_extracted_text_key(file_id)
        except ValueError:
            return None

        try:
            resp = self.client.get_object(Bucket=self.bucket_name, Key=key)
            body = resp.get("Body")
            if body is None:
                return None
            data = body.read() if hasattr(body, "read") else bytes(body)
            return data.decode("utf-8")
        except Exception as exc:
            if self._is_not_found_error(exc):
                return None
            raise

    def delete_extracted_text(self, file_id: str) -> bool:
        try:
            key = self.get_extracted_text_key(file_id)
        except ValueError:
            return False

        if not self.extracted_text_exists(file_id):
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    def extracted_text_exists(self, file_id: str) -> bool:
        try:
            key = self.get_extracted_text_key(file_id)
            return self._object_exists(key)
        except ValueError:
            return False

    # --- Clause JSON Data ---

    def save_clauses_json(self, file_id: str, clauses_data: dict[str, Any] | list[Any]) -> str:
        key = self.get_clauses_json_key(file_id)
        payload = json.dumps(clauses_data, ensure_ascii=False, indent=2).encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=payload,
            ContentType="application/json",
        )
        return key

    def load_clauses_json(self, file_id: str) -> dict[str, Any] | list[Any] | None:
        try:
            key = self.get_clauses_json_key(file_id)
        except ValueError:
            return None

        try:
            resp = self.client.get_object(Bucket=self.bucket_name, Key=key)
            body = resp.get("Body")
            if body is None:
                return None
            data = body.read() if hasattr(body, "read") else bytes(body)
            return json.loads(data.decode("utf-8"))
        except Exception as exc:
            if self._is_not_found_error(exc):
                return None
            raise

    def delete_clauses_json(self, file_id: str) -> bool:
        try:
            key = self.get_clauses_json_key(file_id)
        except ValueError:
            return False

        if not self.clauses_json_exists(file_id):
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    def clauses_json_exists(self, file_id: str) -> bool:
        try:
            key = self.get_clauses_json_key(file_id)
            return self._object_exists(key)
        except ValueError:
            return False

    # --- Composite Check ---

    def has_contract_data(self, file_id: str) -> bool:
        return (
            self.extracted_text_exists(file_id)
            or self.clauses_json_exists(file_id)
            or self.upload_exists(file_id)
        )


class SupabaseStorageService(R2StorageService):
    """Supabase Storage (S3-compatible API) implementation of the storage service."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        region_name: str = "ap-northeast-2",
        s3_client: Any = None,
        uploads_prefix: str = "uploads",
        extracted_prefix: str = "extracted",
        clauses_prefix: str = "clauses",
    ) -> None:
        super().__init__(
            bucket_name=bucket_name or "term-shield-contracts",
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            s3_client=s3_client,
            uploads_prefix=uploads_prefix,
            extracted_prefix=extracted_prefix,
            clauses_prefix=clauses_prefix,
        )
        self.region_name = region_name

    @property
    def endpoint_url(self) -> str:
        if self._endpoint_url:
            return self._endpoint_url.rstrip("/")
        return ""

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                import boto3
                from botocore.client import Config
            except ImportError as err:
                raise RuntimeError(
                    "boto3 is required for SupabaseStorageService but is not installed."
                ) from err

            if not self.endpoint_url:
                raise ValueError("SUPABASE_S3_ENDPOINT must be configured for Supabase storage.")

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name,
                config=Config(s3={"addressing_style": "path"}),
            )
        return self._client

_default_storage_service: BaseStorageService | None = None
_cached_storage_provider: str | None = None
_is_service_overridden: bool = False


def get_storage_service() -> BaseStorageService:
    """Return the global default storage service instance, respecting configuration."""
    global _default_storage_service, _cached_storage_provider, _is_service_overridden

    # If an explicit service was set via set_storage_service(service), respect it
    if _is_service_overridden and _default_storage_service is not None:
        return _default_storage_service

    try:
        from app.core.config import get_settings
        settings = get_settings()
        current_provider = getattr(settings, "storage_provider", "local").lower()
    except Exception:
        current_provider = "local"

    # Refresh instance if not created yet or if configured provider has changed
    if _default_storage_service is None or _cached_storage_provider != current_provider:
        if current_provider == "r2":
            _default_storage_service = R2StorageService(
                bucket_name=getattr(settings, "r2_bucket_name", None),
                account_id=getattr(settings, "r2_account_id", None),
                access_key_id=getattr(settings, "r2_access_key_id", None),
                secret_access_key=getattr(settings, "r2_secret_access_key", None),
                endpoint_url=getattr(settings, "r2_endpoint_url", None),
            )
        elif current_provider == "supabase":
            _default_storage_service = SupabaseStorageService(
                endpoint_url=getattr(settings, "supabase_s3_endpoint", None),
                access_key_id=getattr(settings, "supabase_s3_access_key_id", None),
                secret_access_key=getattr(settings, "supabase_s3_secret_access_key", None),
                bucket_name=getattr(settings, "supabase_s3_bucket", "term-shield-contracts"),
                region_name=getattr(settings, "supabase_s3_region", "ap-northeast-2"),
            )
        else:
            _default_storage_service = LocalStorageService()
        _cached_storage_provider = current_provider

    return _default_storage_service


def set_storage_service(service: BaseStorageService | None) -> None:
    """Override or reset the global storage service instance (primarily used in tests)."""
    global _default_storage_service, _cached_storage_provider, _is_service_overridden
    _default_storage_service = service
    if service is None:
        _cached_storage_provider = None
        _is_service_overridden = False
    else:
        _is_service_overridden = True
