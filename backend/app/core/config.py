from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Contract Simplifier API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    max_upload_size_mb: int = 25

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"

    database_url: str = "sqlite+aiosqlite:///storage/term_shield.db"

    # Authentication
    jwt_secret_key: str | None = None
    access_token_expire_minutes: int = 60

    # Email verification / password reset
    frontend_url: str = "http://localhost:5173"
    resend_api_key: str | None = None
    email_from: str = "Term Shield <onboarding@resend.dev>"
    password_reset_token_expire_minutes: int = 30

    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    # Storage Provider (defaults to local filesystem)
    storage_provider: str = "local"
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_endpoint_url: str | None = None


    model_config = SettingsConfigDict(
        env_file=(_BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
