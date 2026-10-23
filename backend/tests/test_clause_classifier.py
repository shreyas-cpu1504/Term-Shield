from app.services.clause_classifier_service import ClauseClassifierService
from app.schemas.clause import Clause


def make_clause(text: str, title: str | None = None) -> Clause:
    return Clause(
        clause_id="test-clause",
        title=title,
        text=text,
        order=1,
        character_count=len(text),
        clause_number="1",
    )


def test_payment_clause():
    result = ClauseClassifierService.classify(
        make_clause("The Customer shall pay the invoice within 30 days.")
    )
    assert result.clause_type == "PAYMENT"


def test_termination_clause():
    result = ClauseClassifierService.classify(
        make_clause("Either party may terminate this agreement upon written notice.")
    )
    assert result.clause_type == "TERMINATION"


def test_confidentiality_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "The receiving party shall keep all confidential information strictly confidential."
        )
    )
    assert result.clause_type == "CONFIDENTIALITY"


def test_force_majeure_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "Neither party shall be liable for delays caused by force majeure."
        )
    )
    assert result.clause_type == "FORCE_MAJEURE"


def test_governing_law_clause():
    result = ClauseClassifierService.classify(
        make_clause("This agreement shall be governed by the laws of India.")
    )
    assert result.clause_type == "GOVERNING_LAW"


def test_dispute_resolution_clause():
    result = ClauseClassifierService.classify(
        make_clause("Any dispute shall be resolved by arbitration.")
    )
    assert result.clause_type == "DISPUTE_RESOLUTION"


def test_data_protection_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "The processor shall comply with data protection requirements."
        )
    )
    assert result.clause_type == "DATA_PROTECTION"


def test_intellectual_property_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "All intellectual property rights shall remain with the Company."
        )
    )
    assert result.clause_type == "INTELLECTUAL_PROPERTY"


def test_insurance_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "The Contractor shall maintain adequate insurance coverage."
        )
    )
    assert result.clause_type == "INSURANCE"


def test_warranty_clause():
    result = ClauseClassifierService.classify(
        make_clause(
            "The Seller warrants that the products conform to the specifications."
        )
    )
    assert result.clause_type == "WARRANTY"


def test_unknown_clause():
    result = ClauseClassifierService.classify(
        make_clause("The parties acknowledge receipt of this document.")
    )
    assert result.clause_type == "GENERAL"


def test_classify_many():
    clauses = [
        make_clause("The Customer shall pay the invoice."),
        make_clause("Either party may terminate this agreement."),
        make_clause("The receiving party shall keep information confidential."),
    ]

    results = ClauseClassifierService.classify_many(clauses)

    assert len(results) == 3
    assert results[0].clause_type == "PAYMENT"
    assert results[1].clause_type == "TERMINATION"
    assert results[2].clause_type == "CONFIDENTIALITY"
