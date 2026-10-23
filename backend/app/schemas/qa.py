from datetime import datetime

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=5000,
        description="Question about the uploaded contract.",
    )
    language: str | None = Field(
        default=None,
        description="Explicit preferred language for response (e.g. English, Telugu, Hindi).",
    )


class EvidenceItem(BaseModel):
    clause_id: str
    clause_number: str | None = None
    title: str | None = None
    text: str
    relevance_score: float


class QuestionResponse(BaseModel):
    file_id: str
    question: str
    answer: str
    language: str = "English"
    evidence: list[EvidenceItem] = Field(
        default_factory=list
    )
    confidence: float = 0.0


class QAHistoryItemResponse(BaseModel):
    id: str
    contract_id: str
    question: str
    answer: str
    language: str | None = "English"
    confidence: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class ClearChatResponse(BaseModel):
    success: bool
    cleared_records: int
    message: str