from app.schemas.clause import Clause
from app.services.clause_classifier_service import ClauseClassifierService
from app.services.clause_analysis_service import ClauseAnalysisService


def make_clause(text: str, title: str | None = None) -> Clause:
    return Clause(
        clause_id="analysis-test",
        clause_number="1",
        title=title,
        text=text,
        order=1,
        character_count=len(text),
    )


def analyze(text: str, title: str | None = None):
    clause = make_clause(text, title)
    classified = ClauseClassifierService.classify(clause)
    return ClauseAnalysisService.analyze_clause(classified)


def test_payment_analysis():
    result = analyze(
        "The Customer shall pay 10,000 USD within 30 days."
    )

    assert result.clause_type == "PAYMENT"
    assert "Customer" in result.parties
    assert result.obligations
    assert "30 days" in result.deadlines
    assert "USD" in result.currencies


def test_termination_analysis():
    result = analyze(
        "Either party may terminate this agreement upon written notice."
    )

    assert result.clause_type == "TERMINATION"
    assert result.rights or result.permissions
    assert result.notice_terms or result.triggers


def test_confidentiality_analysis():
    result = analyze(
        "The receiving party shall keep all confidential information strictly confidential."
    )

    assert result.clause_type == "CONFIDENTIALITY"
    assert result.confidentiality_terms
    assert result.obligations


def test_governing_law_analysis():
    result = analyze(
        "This agreement shall be governed by the laws of India."
    )

    assert result.clause_type == "GOVERNING_LAW"
    assert result.governing_law


def test_arbitration_analysis():
    result = analyze(
        "Any dispute shall be resolved by arbitration."
    )

    assert result.clause_type == "DISPUTE_RESOLUTION"
    assert result.arbitration
    assert result.dispute_terms


def test_data_protection_analysis():
    result = analyze(
        "The processor shall comply with data protection requirements."
    )

    assert result.clause_type == "DATA_PROTECTION"
    assert result.data_terms


def test_intellectual_property_analysis():
    result = analyze(
        "All intellectual property rights shall remain with the Company."
    )

    assert result.clause_type == "INTELLECTUAL_PROPERTY"
    assert result.intellectual_property_terms


def test_risk_analysis():
    result = analyze(
        "The Customer shall indemnify the Company for all losses."
    )

    assert result.risk_level in {"MEDIUM", "HIGH"}
    assert result.risk_score > 0
    assert result.risk_reasons


def test_analysis_has_meaning():
    result = analyze(
        "The Customer shall pay the invoice within 30 days."
    )

    assert result.meaning
    assert isinstance(result.meaning, str)
    assert result.user_impact
    assert result.recommendations


def test_analysis_batch():
    clauses = [
        make_clause(
            "The Customer shall pay the invoice."
        ),
        make_clause(
            "Either party may terminate this agreement."
        ),
        make_clause(
            "The receiving party shall keep information confidential."
        ),
    ]

    classified = ClauseClassifierService.classify_many(clauses)
    results = ClauseAnalysisService.analyze_clauses(classified)

    assert len(results) == 3
    assert results[0].clause_type == "PAYMENT"
    assert results[1].clause_type == "TERMINATION"
    assert results[2].clause_type == "CONFIDENTIALITY"


# ============================================================
# Financial term tests
# ============================================================

def test_fee_extraction():
    result = analyze(
        "The Customer shall pay a service fee of INR 50,000 within 30 days."
    )

    assert result.fees
    assert any(
        "service fee" in item.lower()
        for item in result.fees
    )


def test_cancellation_charge_extraction():
    result = analyze(
        "A cancellation charge of INR 5,000 shall apply if the Customer cancels."
    )

    assert result.fees
    assert any(
        "cancellation charge" in item.lower()
        for item in result.fees
    )


def test_penalty_extraction():
    result = analyze(
        "A penalty of INR 10,000 shall apply for late performance."
    )

    assert result.penalties
    assert any(
        "penalty" in item.lower()
        for item in result.penalties
    )


def test_interest_extraction():
    result = analyze(
        "A late payment shall incur interest at 2 percent per month."
    )

    assert result.interest_terms
    assert any(
        "interest" in item.lower()
        for item in result.interest_terms
    )


def test_tax_extraction():
    result = analyze(
        "The Customer shall pay GST at 18 percent on the service fee."
    )

    assert result.taxes
    assert any(
        "gst" in item.lower()
        for item in result.taxes
    )


def test_multiple_financial_terms():
    result = analyze(
        """
        The Customer shall pay INR 50,000 as a service fee.
        A cancellation charge of INR 5,000 shall apply.
        A penalty of INR 10,000 shall apply for late performance.
        Late payment shall incur interest at 2 percent per month.
        GST at 18 percent shall apply.
        """
    )

    assert result.monetary_terms
    assert result.fees
    assert result.penalties
    assert result.interest_terms
    assert result.taxes
    assert result.currencies
    assert result.percentages


def test_why_important_across_clause_types():
    # 1. Termination clause
    term_res = analyze("Either party may terminate this agreement by giving 30 days written notice.")
    assert term_res.why_important
    assert any("terminate" in item.lower() for item in term_res.why_important)

    # 2. Payment clause
    pay_res = analyze("The Customer shall pay 10,000 USD within 30 days. Late payment incurs 1.5% interest.")
    assert pay_res.why_important
    assert any("payment" in item.lower() or "financial" in item.lower() for item in pay_res.why_important)

    # 3. Privacy clause
    priv_res = analyze("The processor shall protect personal data and notify the customer of breaches.")
    assert priv_res.why_important
    assert any("data" in item.lower() or "privacy" in item.lower() for item in priv_res.why_important)

    # 4. Liability clause
    liab_res = analyze("The Company's aggregate liability shall not exceed the fees paid. Consequential damages are excluded.")
    assert liab_res.why_important
    assert any("liability" in item.lower() or "risk" in item.lower() for item in liab_res.why_important)


def test_potential_concerns_detection():
    # 1. Missing Exhibit/reference
    exhibit_res = analyze("The Contractor shall deliver the deliverables as specified in Exhibit A: Scope of Services.")
    assert exhibit_res.potential_concerns
    assert any("exhibit a" in c.lower() for c in exhibit_res.potential_concerns)
    assert any("verify exhibit a" in c.lower() for c in exhibit_res.potential_concerns)

    # 2. Blank or missing value
    blank_res = analyze("The Customer shall pay __________ to Provider on or before the due date.")
    assert blank_res.potential_concerns
    assert any("value appears to be missing" in c.lower() for c in blank_res.potential_concerns)

    # 3. Ambiguous wording ("reasonable efforts")
    ambig_res = analyze("The Contractor shall use reasonable efforts to complete the integration.")
    assert ambig_res.potential_concerns
    assert any('"reasonable efforts"' in c.lower() for c in ambig_res.potential_concerns)

    # 4. Truncated clause
    trunc_res = analyze("Either party may terminate this agreement immediately if...")
    assert trunc_res.potential_concerns
    assert any("truncated or incomplete" in c.lower() for c in trunc_res.potential_concerns)

    # 5. Complete clause with no concern
    clean_res = analyze("Either party may terminate the agreement by giving 30 days' written notice to the other party via email.")
    assert clean_res.potential_concerns == ["No specific ambiguity or missing information was identified in the available clause text."]

    # 6. Ensure no fabricated concerns or alarmist words like 'illegal' or 'dangerous'
    for c in clean_res.potential_concerns:
        assert "illegal" not in c.lower()
        assert "dangerous" not in c.lower()
        assert "unfair" not in c.lower()
