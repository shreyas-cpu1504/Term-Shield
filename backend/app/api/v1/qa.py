from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.ownership import require_owned_contract
from app.models.user import User
from app.schemas.qa import (
    QuestionRequest,
    QuestionResponse,
)
from app.services.qa_service import QAService

from app.api.v1.clauses import _load_clauses


router = APIRouter(
    prefix="/qa",
    tags=["Contract Q&A"],
)


@router.post(
    "/{file_id}",
    response_model=QuestionResponse,
)
async def ask_question(
    file_id: str,
    request: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:

    await require_owned_contract(db, current_user, file_id)

    clauses = _load_clauses(file_id)

    return QAService.answer(
        file_id=file_id,
        question=request.question,
        clauses=clauses,
    )