from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import ContractResponse


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