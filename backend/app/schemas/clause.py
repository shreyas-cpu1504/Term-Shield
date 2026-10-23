from pydantic import BaseModel


class Clause(BaseModel):
    clause_id: str
    title: str | None = None
    text: str
    order: int
    character_count: int
    clause_number: str | None = None
    parent_clause: str | None = None
    clause_type: str | None = None


class ClauseSegmentationResponse(BaseModel):
    file_id: str
    clause_count: int
    clauses: list[Clause]
