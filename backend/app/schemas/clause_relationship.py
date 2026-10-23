from typing import Any

from pydantic import BaseModel, Field


class ClauseRelationship(BaseModel):
    source_clause_id: str
    target_clause_id: str | None = None
    relationship_type: str
    evidence: str
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ClauseRelationshipResponse(BaseModel):
    file_id: str
    relationship_count: int
    relationships: list[ClauseRelationship]
