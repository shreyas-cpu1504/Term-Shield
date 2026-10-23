from fastapi import APIRouter

from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.file_ingestion import router as file_ingestion_router
from app.api.v1.clauses import router as clauses_router

router = APIRouter()

router.include_router(ingestion_router)
router.include_router(file_ingestion_router)
router.include_router(clauses_router)
