import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.ownership import require_owned_contract
from app.models.qa_history import QAHistory
from app.models.user import User
from app.schemas.qa import (
    ClearChatResponse,
    QAHistoryItemResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.services.qa import QAService
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
    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted document not found.",
        )

    # 1. Handle fast conversational greetings/gratitude locally without saving to DB
    conv_response = QAService.get_conversational_response(request.question)
    if conv_response:
        return QuestionResponse(
            file_id=file_id,
            question=request.question,
            answer=conv_response,
            evidence=[],
            confidence=1.0,
        )

    clauses = await _load_clauses(file_id, db)

    # 2. Fetch recent conversation history (last 10 turns) for multi-turn context
    history_res = await db.execute(
        select(QAHistory)
        .where(
            QAHistory.contract_id == file_id,
            QAHistory.user_id == current_user.id,
        )
        .order_by(QAHistory.created_at.desc())
        .limit(10)
    )
    # Reverse to chronological order (oldest -> newest)
    recent_history = list(reversed(history_res.scalars().all()))

    # 3. Call unified QA Service
    response = QAService.answer(
        file_id=file_id,
        question=request.question,
        clauses=clauses,
        contract_name=contract.filename,
        contract_summary=contract.summary_json,
        conversation_history=recent_history,
        language=request.language,
    )

    # 4. Save exchange to QAHistory
    qa_record = QAHistory(
        id=str(uuid.uuid4()),
        contract_id=file_id,
        user_id=current_user.id,
        question=request.question,
        answer=response.answer,
        language=response.language,
        evidence_json=(
            json.dumps([e.model_dump() for e in response.evidence])
            if response.evidence
            else None
        ),
        confidence=response.confidence,
    )
    db.add(qa_record)
    await db.commit()

    return response


@router.get(
    "/{file_id}/history",
    response_model=list[QAHistoryItemResponse],
)
async def get_qa_history(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QAHistoryItemResponse]:
    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted document not found.",
        )

    result = await db.execute(
        select(QAHistory)
        .where(
            QAHistory.contract_id == file_id,
            QAHistory.user_id == current_user.id,
        )
        .order_by(QAHistory.created_at.asc())
    )

    records = result.scalars().all()
    return list(records)


@router.delete(
    "/{file_id}/history",
    response_model=ClearChatResponse,
)
async def clear_qa_history(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClearChatResponse:
    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted document not found.",
        )

    cleared_count = await QAService.clear_history(db, file_id, current_user.id)
    return ClearChatResponse(
        success=True,
        cleared_records=cleared_count,
        message="Conversation history cleared successfully.",
    )