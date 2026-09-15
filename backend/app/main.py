from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.file_ingestion import router as file_ingestion_router
from app.api.v1.clauses import router as clauses_router
from app.api.v1.qa import router as qa_router
from app.api.v1.media_ingestion import router as media_ingestion_router
from app.api.v1.auth import router as auth_router
from app.core.config import get_settings
from app.core.database import init_db
from app.schemas.health import HealthResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-powered multimodal contract intelligence platform",
    version=settings.app_version,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
