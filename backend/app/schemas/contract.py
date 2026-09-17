from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    size_bytes: int
    character_count: int
    status: str
    overall_risk: str
    overall_risk_score: int
    created_at: datetime
    updated_at: datetime