from app.schemas.clause import Clause
from app.services.clause_classifier_service import ClauseClassifierService
from app.services.clause_analysis_service import ClauseAnalysisService


def analyze(text: str):
    clause = Clause(
        clause_id="risk-test",
        clause_number="1",
        title=None,
        text=text,
        order=1,
        character_count=len(text),
    )

    classified = ClauseClassifierService.classify(clause)
    return ClauseAnalysisService.analyze_clause(classified)


def test_unlimited_liability_is_high_risk():
    result = analyze(
        "The Customer shall have unlimited liability for all losses."
    )

    assert result.risk_level == "HIGH"
    assert result.risk_score >= 60
    assert result.risk_reasons


def test_indemnification_creates_risk():
    result = analyze(
        "The Customer shall indemnify the Company for all losses and claims."
    )

    assert result.risk_score > 0
    assert result.risk_level in {"MEDIUM", "HIGH"}
    assert result.risk_reasons


def test_penalty_is_medium_risk():
    result = analyze(
        "A penalty of 10,000 USD shall apply for late performance."
    )

    assert result.risk_level == "MEDIUM"
    assert result.risk_score >= 20
    assert result.risk_reasons


def test_termination_creates_risk_signal():
    result = analyze(
        "Either party may terminate this agreement upon written notice."
    )

    assert result.risk_score > 0
    assert result.risk_reasons


def test_confidentiality_creates_risk_signal():
    result = analyze(
        "The receiving party shall keep all confidential information strictly confidential."
    )

    assert result.risk_score > 0
    assert result.risk_reasons


def test_ordinary_payment_clause_is_not_high_risk():
    result = analyze(
        "The Customer shall pay the invoice within 30 days."
    )

    assert result.risk_level in {"LOW", "MEDIUM"}
    assert result.risk_score < 60


def test_risk_score_never_exceeds_100():
    result = analyze(
        """
        The Customer shall indemnify the Company for all losses.
        The Customer shall have unlimited liability.
        The Customer waives all rights.
        The Company may terminate without notice.
        A penalty shall apply upon breach.
        The agreement shall be subject to arbitration and jurisdiction.
        """
    )

    assert 0 <= result.risk_score <= 100


def test_high_risk_clause_has_recommendation():
    result = analyze(
        "The Customer shall have unlimited liability for all losses."
    )

    assert result.risk_level == "HIGH"
    assert result.recommendations