from app.schemas.clause import Clause
from app.services.retrieval_service import RetrievalService


def make_clause(
    clause_id: str,
    number: str,
    text: str,
) -> Clause:
    return Clause(
        clause_id=clause_id,
        clause_number=number,
        title=None,
        text=text,
        order=int(number),
        character_count=len(text),
    )


def test_retrieves_payment_clause():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay the invoice within 30 days.",
        ),
        make_clause(
            "c2",
            "2",
            "Either party may terminate the agreement.",
        ),
    ]

    results = RetrievalService.retrieve(
        "When must the customer pay the invoice?",
        clauses,
    )

    assert results
    assert results[0].clause_id == "c1"


def test_retrieves_termination_clause():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay the invoice within 30 days.",
        ),
        make_clause(
            "c2",
            "2",
            "Either party may terminate the agreement upon written notice.",
        ),
    ]

    results = RetrievalService.retrieve(
        "How can the agreement be terminated?",
        clauses,
    )

    assert results
    assert results[0].clause_id == "c2"


def test_empty_question_returns_no_results():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay the invoice.",
        ),
    ]

    results = RetrievalService.retrieve(
        "",
        clauses,
    )

    assert results == []


def test_no_relevant_clause_returns_empty():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay the invoice.",
        ),
    ]

    results = RetrievalService.retrieve(
        "What is the intellectual property ownership?",
        clauses,
    )

    assert results == []


def test_unrelated_address_question_returns_no_results():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay INR 50,000 within 30 days.",
        ),
        make_clause(
            "c2",
            "2",
            "The Customer shall have unlimited liability for losses.",
        ),
    ]

    results = RetrievalService.retrieve(
        "What is the customer's address?",
        clauses,
    )

    assert results == []


def test_retrieves_broad_obligations():
    clauses = [
        Clause(
            clause_id="c1",
            clause_number="1",
            title="Payment",
            text="The Customer shall pay a service fee of INR 50,000 within 30 days of receiving the invoice.",
            order=1,
            character_count=98,
            clause_type="PAYMENT",
        ),
        Clause(
            clause_id="c2",
            clause_number="2",
            title="Cancellation",
            text="The Customer may cancel this agreement by providing 15 days written notice. A cancellation charge of INR 5,000 shall apply.",
            order=2,
            character_count=125,
            clause_type="NOTICES",
        ),
        Clause(
            clause_id="c4",
            clause_number="4",
            title="Confidentiality",
            text="The receiving party shall keep all confidential information strictly confidential.",
            order=4,
            character_count=82,
            clause_type="CONFIDENTIALITY",
        ),
        Clause(
            clause_id="c6",
            clause_number="6",
            title="Liability",
            text="The Customer shall have unlimited liability for all losses arising from breach of this agreement.",
            order=6,
            character_count=97,
            clause_type="LIABILITY",
        ),
    ]

    results = RetrievalService.retrieve(
        "What are my biggest obligations?",
        clauses,
    )

    assert len(results) > 0
    clause_ids = [r.clause_id for r in results]
    # Payment and Liability should be among top retrieved
    assert "c1" in clause_ids
    assert "c6" in clause_ids


def test_retrieves_cancellation_charge():
    clauses = [
        Clause(
            clause_id="c1",
            clause_number="1",
            title="Payment",
            text="The Customer shall pay a service fee of INR 50,000 within 30 days of receiving the invoice.",
            order=1,
            character_count=98,
            clause_type="PAYMENT",
        ),
        Clause(
            clause_id="c2",
            clause_number="2",
            title="Cancellation",
            text="A cancellation charge of INR 5,000 shall apply if the Customer cancels before the minimum service period.",
            order=2,
            character_count=110,
            clause_type="NOTICES",
        ),
    ]

    results = RetrievalService.retrieve(
        "What is the cancellation charge?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "c2"


def test_retrieves_renewal():
    clauses = [
        Clause(
            clause_id="c1",
            clause_number="1",
            title="Payment",
            text="The Customer shall pay a service fee of INR 50,000 within 30 days.",
            order=1,
            character_count=70,
            clause_type="PAYMENT",
        ),
        Clause(
            clause_id="c7",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 days written notice before expiry.",
            order=7,
            character_count=129,
            clause_type="RENEWAL",
        ),
    ]

    results = RetrievalService.retrieve(
        "When does the agreement renew?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "c7"


def test_unsupported_question_returns_empty_retrieval():
    clauses = [
        Clause(
            clause_id="c1",
            clause_number="1",
            title="Payment",
            text="The Customer shall pay a service fee of INR 50,000 within 30 days.",
            order=1,
            character_count=70,
            clause_type="PAYMENT",
        ),
    ]

    results = RetrievalService.retrieve(
        "What is the pet policy for the office building?",
        clauses,
    )

    assert results == []


def test_retrieval_handles_none_clause_title_and_type():
    """
    Regression test:
    Verify that RetrievalService.retrieve() does not crash with AttributeError
    when clauses have title=None, clause_type=None, or both, especially for
    broad overview, risk reviews, and general questions.
    """
    clauses = [
        Clause(
            clause_id="c1",
            clause_number="1",
            title=None,
            text="The Customer shall pay a fee of INR 50,000 within 30 days of receiving the invoice.",
            order=1,
            character_count=90,
            clause_type=None,
        ),
        Clause(
            clause_id="c2",
            clause_number="2",
            title=None,
            text="Either party may terminate this agreement upon 15 days written notice with unlimited liability for breach.",
            order=2,
            character_count=108,
            clause_type="LIABILITY",
        ),
    ]

    # Broad overview triggers the category bucketing logic in retrieve()
    results_overview = RetrievalService.retrieve(
        "What are the main risks before signing this contract?",
        clauses,
    )
    assert isinstance(results_overview, list)
    assert len(results_overview) > 0

    # Specific question
    results_payment = RetrievalService.retrieve(
        "When must the customer pay?",
        clauses,
    )
    assert isinstance(results_payment, list)
    assert len(results_payment) > 0
    assert results_payment[0].clause_id == "c1"


def test_retrieval_obligations_from_actual_clause_text_with_none_metadata():
    """
    Regression test:
    Verify that for obligations questions, RetrievalService.retrieve()
    identifies customer responsibilities directly from actual clause text
    (such as 'Customer must pay...', 'must provide... notice')
    even when title=None, clause_type=None, and metadata has no obligations.
    """
    clause = Clause(
        clause_id="ocr_obl_1",
        title=None,
        clause_type=None,
        text="The Customer must pay INR 50,000 within 30 days and must provide 15 days written notice before cancellation.",
        order=1,
        character_count=110,
    )

    examples = [
        "What are my obligations?",
        "What are my biggest obligations?",
        "What do I have to do under this contract?",
        "What am I required to do?",
        "What responsibilities do I have?",
        "What must I pay or provide?",
        "What are the customer's responsibilities?",
    ]

    for question in examples:
        results = RetrievalService.retrieve(question, [clause])
        assert len(results) > 0, f"Failed to retrieve for question: {question}"
        assert results[0].clause_id == "ocr_obl_1"
        assert results[0].score >= 0.50


def test_main_purpose_does_not_select_skip_to_main_content():
    """
    Regression test:
    Verify that 'What is the main purpose of this page?' prioritizes the substantive
    page title and introductory description, and does NOT select 'Skip to main content'.
    """
    clauses = [
        Clause(
            clause_id="skip_1",
            title=None,
            text="Skip to main content",
            order=1,
            character_count=20,
        ),
        Clause(
            clause_id="sam_intro",
            title="Contracting on SAM.gov",
            text="SAM.gov is the official U.S. government website for people who make, receive, and manage federal awards. It provides access to contracting opportunities, entity registration, and procurement records.",
            order=2,
            character_count=228,
        ),
        Clause(
            clause_id="nav_links",
            title=None,
            text="Home | Opportunities | Data Bank | Help",
            order=3,
            character_count=39,
        ),
        Clause(
            clause_id="footer_copy",
            title=None,
            text="© 2024 General Services Administration. All rights reserved.",
            order=4,
            character_count=60,
        ),
    ]

    results = RetrievalService.retrieve(
        "What is the main purpose of this page?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "sam_intro"
    # Ensure "skip_1" is not ranked at top
    clause_ids = [r.clause_id for r in results]
    if "skip_1" in clause_ids:
        skip_item = next(r for r in results if r.clause_id == "skip_1")
        assert results[0].score > skip_item.score


def test_substantive_introductory_content_outranks_navigation():
    """
    Regression test:
    Verify that substantive introductory content outranks navigation and menu items
    for general overview and 'about' queries.
    """
    clauses = [
        Clause(
            clause_id="menu_bar",
            title="Main Navigation",
            text="Menu: Home | About Contracting | Opportunities | Wage Determinations | Help Desk",
            order=1,
            character_count=83,
        ),
        Clause(
            clause_id="page_summary",
            title="About Contracting",
            text="This portal facilitates federal procurement by allowing contractors to register, search active solicitations, and submit bids for federal agency projects.",
            order=2,
            character_count=167,
        ),
        Clause(
            clause_id="access_notice",
            title=None,
            text="Accessibility Statement. For accessibility support or screen reader assistance, visit our help section.",
            order=3,
            character_count=104,
        ),
    ]

    results = RetrievalService.retrieve(
        "What is this page about?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "page_summary"
    top_score = results[0].score
    menu_item = next((r for r in results if r.clause_id == "menu_bar"), None)
    if menu_item:
        assert top_score > menu_item.score


def test_navigation_text_available_when_asked_about_navigation():
    """
    Regression test:
    Verify that navigation text is still retrievable when the user specifically asks
    about navigation, menu, or site links.
    """
    clauses = [
        Clause(
            clause_id="skip_1",
            title=None,
            text="Skip to main content",
            order=1,
            character_count=20,
        ),
        Clause(
            clause_id="nav_bar",
            title="Navigation Menu",
            text="Main Menu: Home | Contract Opportunities | Entity Registration | Wage Determinations | Help",
            order=2,
            character_count=95,
        ),
        Clause(
            clause_id="intro_sec",
            title="Welcome to Contracting",
            text="Learn how federal contracts are awarded and managed across government agencies.",
            order=3,
            character_count=83,
        ),
    ]

    results = RetrievalService.retrieve(
        "What options are in the navigation menu?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "nav_bar"
    assert results[0].score >= 0.50


def test_skip_to_main_content_available_when_asked_about_skip_link():
    """
    Regression test:
    Verify that 'Skip to main content' is available when specifically asked about.
    """
    clauses = [
        Clause(
            clause_id="skip_1",
            title=None,
            text="Skip to main content",
            order=1,
            character_count=20,
        ),
        Clause(
            clause_id="intro_sec",
            title="Welcome to Contracting",
            text="Learn how federal contracts are awarded and managed across government agencies.",
            order=2,
            character_count=83,
        ),
    ]

    results = RetrievalService.retrieve(
        "Is there a skip to main content link on this page?",
        clauses,
    )

    assert len(results) > 0
    assert results[0].clause_id == "skip_1"
