from app.schemas.clause_analysis import ClauseAnalysis
from app.services.contract_summary_service import ContractSummaryService


def make_analysis(
    clause_id: str,
    clause_number: str,
    risk_level: str,
    risk_score: int,
    clause_type: str = "GENERAL",
    deadlines: list[str] | None = None,
    monetary_terms: list[str] | None = None,
    obligations: list[str] | None = None,
    rights: list[str] | None = None,
):
    return ClauseAnalysis(
        clause_id=clause_id,
        clause_number=clause_number,
        clause_type=clause_type,
        risk_level=risk_level,
        risk_score=risk_score,
        deadlines=deadlines or [],
        monetary_terms=monetary_terms or [],
        obligations=obligations or [],
        rights=rights or [],
    )


def test_empty_contract_summary():
    result = ContractSummaryService.generate(
        file_id="file-1",
        analyses=[],
    )

    assert result.file_id == "file-1"
    assert result.total_clauses == 0
    assert result.overall_risk == "LOW"
    assert result.overall_risk_score == 0
    assert result.priority_clauses == []


def test_high_risk_contract_summary():
    analyses = [
        make_analysis(
            "c1",
            "1.1",
            "HIGH",
            80,
            clause_type="LIABILITY",
        ),
        make_analysis(
            "c2",
            "2.1",
            "LOW",
            10,
        ),
    ]

    result = ContractSummaryService.generate(
        file_id="file-2",
        analyses=analyses,
    )

    assert result.total_clauses == 2
    assert result.overall_risk == "HIGH"
    assert result.overall_risk_score > 0
    assert "1.1" in result.priority_clauses


def test_medium_risk_contract_summary():
    analyses = [
        make_analysis("c1", "1.1", "MEDIUM", 30),
        make_analysis("c2", "2.1", "LOW", 5),
    ]

    result = ContractSummaryService.generate(
        file_id="file-3",
        analyses=analyses,
    )

    assert result.overall_risk == "MEDIUM"
    assert "1.1" in result.priority_clauses


def test_priority_clauses_include_high_and_medium():
    analyses = [
        make_analysis("c1", "1.1", "HIGH", 70),
        make_analysis("c2", "2.1", "MEDIUM", 30),
        make_analysis("c3", "3.1", "LOW", 5),
    ]

    result = ContractSummaryService.generate(
        file_id="file-4",
        analyses=analyses,
    )

    assert result.priority_clauses == ["1.1", "2.1"]


def test_summary_collects_deadlines_money_obligations_and_rights():
    analyses = [
        make_analysis(
            "c1",
            "1.1",
            "MEDIUM",
            30,
            deadlines=["30 days"],
            monetary_terms=["10,000 USD"],
            obligations=["Customer shall pay"],
            rights=["Customer may terminate"],
        ),
        make_analysis(
            "c2",
            "2.1",
            "LOW",
            5,
            deadlines=["60 days"],
            monetary_terms=["5,000 USD"],
            obligations=["Company shall deliver"],
            rights=["Company may inspect"],
        ),
    ]

    result = ContractSummaryService.generate(
        file_id="file-5",
        analyses=analyses,
    )

    assert result.deadlines == ["30 days", "60 days"]
    assert result.monetary_terms == ["10,000 USD", "5,000 USD"]
    assert result.key_obligations == [
        "Customer shall pay",
        "Company shall deliver",
    ]
    assert result.key_rights == [
        "Customer may terminate",
        "Company may inspect",
    ]


def test_overall_risk_score_is_capped_at_100():
    analyses = [
        make_analysis("c1", "1.1", "HIGH", 100),
        make_analysis("c2", "2.1", "HIGH", 100),
        make_analysis("c3", "3.1", "HIGH", 100),
    ]

    result = ContractSummaryService.generate(
        file_id="file-6",
        analyses=analyses,
    )

    assert result.overall_risk_score == 100


def test_summary_points_are_generated():
    analyses = [
        make_analysis(
            "c1",
            "1.1",
            "HIGH",
            80,
            clause_type="LIABILITY",
        )
    ]

    result = ContractSummaryService.generate(
        file_id="file-7",
        analyses=analyses,
    )

    assert result.summary_points
    assert any("high risk" in point.lower() for point in result.summary_points)