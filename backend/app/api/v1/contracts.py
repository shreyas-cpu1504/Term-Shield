from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.clause import Clause
from app.models.clause_analysis import ClauseAnalysisRecord
from app.models.contract import Contract
from app.models.qa_history import QAHistory
from app.models.user import User
from app.schemas.contract import ContractResponse
from app.services.storage_service import get_storage_service


router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


@router.get(
    "",
    response_model=list[ContractResponse],
)
async def list_contracts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContractResponse]:
    result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
        .order_by(Contract.created_at.desc())
    )

    return list(result.scalars().all())


@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()

    if not contract or contract.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    # Safely delete dependent records to maintain integrity across all DB drivers
    await db.execute(
        delete(QAHistory).where(QAHistory.contract_id == contract.id)
    )
    await db.execute(
        delete(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == contract.id)
    )
    await db.execute(
        delete(Clause).where(Clause.contract_id == contract.id)
    )
    await db.delete(contract)
    await db.commit()

    storage = get_storage_service()

    # Clean up extracted text file if present
    storage.delete_extracted_text(contract.id)
    if contract.extracted_text_path:
        try:
            path = Path(contract.extracted_text_path)
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    # Clean up disk clause cache if present
    storage.delete_clauses_json(contract.id)

    # Clean up uploaded raw file if present
    if contract.file_type:
        storage.delete_upload(contract.id, contract.file_type)


    return {
        "message": "Contract deleted successfully",
        "id": contract_id,
    }