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
    QAHistoryItemResponse,
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

    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted document not found.",
        )
    # Handle basic conversational acknowledgments locally without cluttering QA history
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

    # Fetch most recent QA exchange for conversational context (e.g. language/format follow-up instructions)
    history_res = await db.execute(
        select(QAHistory)
        .where(
            QAHistory.contract_id == file_id,
            QAHistory.user_id == current_user.id,
        )
        .order_by(QAHistory.created_at.desc())
        .limit(1)
    )
    last_qa = history_res.scalars().first()

    previous_question = last_qa.question if last_qa else None
    previous_answer = last_qa.answer if last_qa else None
    previous_evidence = None
    if last_qa and last_qa.evidence_json:
        try:
            ev_list = json.loads(last_qa.evidence_json)
            from app.services.retrieval_service import RetrievedClause
            previous_evidence = [
                RetrievedClause(
                    clause_id=e.get("clause_id", ""),
                    clause_number=e.get("clause_number"),
                    title=e.get("title"),
                    text=e.get("text", ""),
                    score=e.get("relevance_score", 0.9),
                )
                for e in ev_list
            ]
        except Exception:
            previous_evidence = None

    response = QAService.answer(
        file_id=file_id,
        question=request.question,
        clauses=clauses,
        contract_name=contract.filename,
        contract_summary=contract.summary_json,
        previous_question=previous_question,
        previous_answer=previous_answer,
        previous_evidence=previous_evidence,
    )

    qa_record = QAHistory(
        id=str(uuid.uuid4()),
        contract_id=file_id,
        user_id=current_user.id,
        question=request.question,
        answer=response.answer,
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