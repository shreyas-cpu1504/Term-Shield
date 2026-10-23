from pydantic import BaseModel, Field


class RiskSummary(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class ContractSummary(BaseModel):
    file_id: str

    total_clauses: int

    risk_summary: RiskSummary

    overall_risk: str

    overall_risk_score: int = 0

    priority_clauses: list[str] = Field(
        default_factory=list
    )

    deadlines: list[str] = Field(
        default_factory=list
    )

    monetary_terms: list[str] = Field(
        default_factory=list
    )

    key_obligations: list[str] = Field(
        default_factory=list
    )

    key_rights: list[str] = Field(
        default_factory=list
    )

    summary_points: list[str] = Field(
        default_factory=list
    )


class ContractSummaryResponse(BaseModel):
    file_id: str
    summary: ContractSummary
