from pydantic import BaseModel, Field


class ClauseAnalysis(BaseModel):
    clause_id: str
    clause_number: str | None = None
    clause_type: str | None = None

    # Core understanding
    title: str | None = None
    meaning: str | None = None
    key_points: list[str] = Field(default_factory=list)

    # Entities and legal actors
    entities: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    authorities: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)

    # Legal / semantic relationships
    obligations: list[str] = Field(default_factory=list)
    rights: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    prohibitions: list[str] = Field(default_factory=list)
    duties: list[str] = Field(default_factory=list)

    # Logical structure
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)

    # Time
    dates: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    durations: list[str] = Field(default_factory=list)

    # Money / quantitative information
    monetary_terms: list[str] = Field(default_factory=list)
    currencies: list[str] = Field(default_factory=list)
    percentages: list[str] = Field(default_factory=list)
    quantities: list[str] = Field(default_factory=list)
    fees: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)
    taxes: list[str] = Field(default_factory=list)

    # Legal references
    laws: list[str] = Field(default_factory=list)
    regulations: list[str] = Field(default_factory=list)
    statutes: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    articles: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    case_references: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)

    # Plain-language legal-reference understanding
    legal_reference_explanations: list[str] = Field(default_factory=list)

    # Document-specific information
    notices: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    orders: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    definitions: list[str] = Field(default_factory=list)

    # Domain signals
    employment_terms: list[str] = Field(default_factory=list)
    financial_terms: list[str] = Field(default_factory=list)
    loan_terms: list[str] = Field(default_factory=list)
    property_terms: list[str] = Field(default_factory=list)
    intellectual_property_terms: list[str] = Field(default_factory=list)
    privacy_terms: list[str] = Field(default_factory=list)
    dispute_resolution_terms: list[str] = Field(default_factory=list)
    confidentiality_terms: list[str] = Field(default_factory=list)

    # Risk / review
    risk_level: str = "LOW"
    risk_score: int = 0
    risk_reasons: list[str] = Field(default_factory=list)
    user_impact: str | None = None
    why_important: list[str] = Field(default_factory=list)
    potential_concerns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Analysis metadata
    detected_features: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ClauseAnalysisResponse(BaseModel):
    file_id: str
    analysis_count: int
    analyses: list[ClauseAnalysis]