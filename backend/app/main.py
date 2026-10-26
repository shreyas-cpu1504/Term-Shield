from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.file_ingestion import router as file_ingestion_router
from app.api.v1.clauses import router as clauses_router
from app.api.v1.qa import router as qa_router
from app.api.v1.media_ingestion import router as media_ingestion_router
from app.api.v1.auth import router as auth_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.tts import router as tts_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.schemas.health import HealthResponse


from app.services.ocr_service import OCRService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Eagerly discover and configure Tesseract binary and paths on startup
    OCRService.is_available()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title=settings.app_name,
    description="AI-powered multimodal contract intelligence platform",
    version=settings.app_version,
    lifespan=lifespan,
)


def resolve_cors_origins(app_settings) -> list[str]:
    """Resolve and normalize approved CORS origins without duplicates or trailing slashes.

    Includes default approved production and development origins, plus any additional
    origins configured in frontend_url or cors_origins environment variables.
    """
    approved_defaults = [
        "https://term-shield.in",
        "https://www.term-shield.in",
        "https://term-shield-ten.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    origins: list[str] = []

    def _add_origin(raw: str):
        if not raw:
            return
        cleaned = raw.strip().rstrip("/")
        # Disallow empty strings or wildcard with credentials
        if not cleaned or cleaned == "*":
            return
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            return
        if cleaned not in origins:
            origins.append(cleaned)

    for default_origin in approved_defaults:
        _add_origin(default_origin)

    # Check settings.cors_origins
    configured_cors = getattr(app_settings, "cors_origins", None)
    if configured_cors:
        if isinstance(configured_cors, str):
            for entry in configured_cors.split(","):
                _add_origin(entry)
        elif isinstance(configured_cors, (list, tuple, set)):
            for entry in configured_cors:
                _add_origin(str(entry))

    # Check settings.frontend_url
    if getattr(app_settings, "frontend_url", None):
        for entry in app_settings.frontend_url.split(","):
            _add_origin(entry)

    return origins


cors_origins = resolve_cors_origins(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
    )


app.include_router(
    ingestion_router,
    prefix=settings.api_prefix,
)

app.include_router(
    file_ingestion_router,
    prefix=settings.api_prefix,
)

app.include_router(
    clauses_router,
    prefix=settings.api_prefix,
)

app.include_router(
    qa_router,
    prefix=settings.api_prefix,
)

app.include_router(
    media_ingestion_router,
    prefix=settings.api_prefix,
)

app.include_router(
    auth_router,
    prefix=settings.api_prefix,
)

app.include_router(
    contracts_router,
    prefix=settings.api_prefix,
)

app.include_router(
    tts_router,
    prefix=settings.api_prefix,
)
