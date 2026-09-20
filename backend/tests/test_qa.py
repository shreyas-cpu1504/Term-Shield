import re
from pathlib import Path

from app.schemas.clause import Clause
from app.services.file_ingestion_service import FileIngestionService
from app.services.qa_service import QAService


def test_contract_qa_endpoint(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n\n"
        b"3. Confidentiality\n"
        b"The receiving party shall keep all confidential information "
        b"strictly confidential.\n"
    )

    upload_response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "qa_test_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        response = client.post(
            f"/api/v1/qa/{file_id}",
            json={
                "question": "When must the customer pay the invoice?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["file_id"] == file_id
        assert data["question"] == (
            "When must the customer pay the invoice?"
        )

        assert data["answer"]
        assert data["evidence"]
        assert data["confidence"] > 0

        evidence = data["evidence"][0]

        assert evidence["clause_number"] == "1"
        assert "30 days" in evidence["text"]
        assert evidence["relevance_score"] > 0

    finally:
        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(
                    f"{file_id}.*"
                ):
                    path.unlink()

        clauses_path = (
            Path("storage/clauses")
            / f"{file_id}.json"
        )

        if clauses_path.exists():
            clauses_path.unlink()


def test_contract_qa_termination_question(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n"
    )

    upload_response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "termination_qa_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        response = client.post(
            f"/api/v1/qa/{file_id}",
            json={
                "question": "How can the agreement be terminated?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["answer"]
        assert data["evidence"]

        evidence = data["evidence"][0]

        assert evidence["clause_number"] == "2"
        assert "terminate" in evidence["text"].lower()

    finally:
        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(
                    f"{file_id}.*"
                ):
                    path.unlink()

        clauses_path = (
            Path("storage/clauses")
            / f"{file_id}.json"
        )

        if clauses_path.exists():
            clauses_path.unlink()


def test_contract_qa_unknown_file_returns_404(client):
    response = client.post(
        "/api/v1/qa/does-not-exist",
        json={
            "question": "What is the payment deadline?"
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Extracted document not found."
    )


def test_contract_qa_rejects_empty_question(client):
    response = client.post(
        "/api/v1/qa/some-file",
        json={
            "question": ""
        },
    )

    assert response.status_code == 422


def sample_test_clauses() -> list[Clause]:
    return [
        Clause(
            clause_id="clause-1",
            clause_number="1",
            title="Payment",
            text=(
                "The Customer shall pay a service fee of INR 50,000 within 30 days of receiving the invoice.\n"
                "A late payment shall incur interest at 2 percent per month."
            ),
            order=1,
            character_count=151,
            clause_type="PAYMENT",
        ),
        Clause(
            clause_id="clause-2",
            clause_number="2",
            title="Cancellation",
            text=(
                "The Customer may cancel this agreement by providing 15 days written notice.\n"
                "A cancellation charge of INR 5,000 shall apply if the Customer cancels before the minimum service period.\n"
                "Payments already made are non-refundable after cancellation."
            ),
            order=2,
            character_count=242,
            clause_type="NOTICES",
        ),
        Clause(
            clause_id="clause-3",
            clause_number="3",
            title="Termination",
            text=(
                "Either party may terminate this agreement for material breach by providing 30 days written notice.\n"
                "Early termination by the Customer shall result in a termination fee of INR 10,000."
            ),
            order=3,
            character_count=181,
            clause_type="TERMINATION",
        ),
        Clause(
            clause_id="clause-4",
            clause_number="4",
            title="Confidentiality",
            text="The receiving party shall keep all confidential information strictly confidential.",
            order=4,
            character_count=82,
            clause_type="CONFIDENTIALITY",
        ),
        Clause(
            clause_id="clause-5",
            clause_number="5",
            title="Privacy",
            text=(
                "The Customer personal information may be collected and processed for providing the services.\n"
                "The service provider may share necessary information with third-party service providers.\n"
                "Personal information shall be retained for the duration required to provide the services."
            ),
            order=5,
            character_count=271,
            clause_type="DATA_PROTECTION",
        ),
        Clause(
            clause_id="clause-6",
            clause_number="6",
            title="Liability",
            text="The Customer shall have unlimited liability for all losses arising from breach of this agreement.",
            order=6,
            character_count=97,
            clause_type="LIABILITY",
        ),
        Clause(
            clause_id="clause-7",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 days written notice before expiry.",
            order=7,
            character_count=129,
            clause_type="RENEWAL",
        ),
    ]


def test_qa_broad_obligations_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What are my biggest obligations?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    evidence_clause_numbers = {ev.clause_number for ev in response.evidence}
    assert any(num in evidence_clause_numbers for num in {"1", "4", "6"})
    assert "could not find enough relevant information" not in response.answer.lower()
    assert len(response.answer.strip()) > 0


def test_qa_cancellation_charge_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What is the cancellation charge?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    assert any(ev.clause_number == "2" for ev in response.evidence)
    assert "5,000" in response.answer or "5000" in response.answer


def test_qa_renewal_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="When does the agreement renew?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    assert any(ev.clause_number == "7" for ev in response.evidence)
    assert "12 months" in response.answer or "renew" in response.answer.lower()


def test_qa_unsupported_question_insufficient_information():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What is the pet policy for the office premises?",
        clauses=clauses,
    )

    assert response.confidence == 0.0
    assert response.evidence == []
    assert "could not find enough relevant information" in response.answer.lower()


def test_qa_normal_contract_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Can the other party terminate this agreement?",
        clauses=clauses,
        contract_name="master_service_agreement.pdf",
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    clause_nums = {ev.clause_number for ev in response.evidence}
    assert any(num in clause_nums for num in {"2", "3"})
    assert len(response.answer.strip()) > 0
    assert "could not find" not in response.answer.lower()


def test_qa_explanation_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Explain clause 7 in simple language.",
        clauses=clauses,
        contract_name="service_agreement.pdf",
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    assert any(ev.clause_number == "7" for ev in response.evidence)
    assert len(response.answer.strip()) > 0
    assert "renew" in response.answer.lower() or "12 months" in response.answer or "30 days" in response.answer


def test_qa_multiple_clauses_question():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What are the financial terms regarding payments and cancellation charges?",
        clauses=clauses,
        contract_name="service_agreement.pdf",
    )

    assert response.confidence > 0
    assert len(response.evidence) >= 2
    clause_nums = {ev.clause_number for ev in response.evidence}
    assert "1" in clause_nums
    assert any(num in clause_nums for num in {"2", "3"})
    assert len(response.answer.strip()) > 0


def test_qa_off_topic_scope_check():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What is the capital of France?",
        clauses=clauses,
    )

    assert response.confidence == 0.0
    assert response.evidence == []
    assert response.answer == (
        "I can answer questions related to your selected contract. "
        "I couldn't find this topic in the contract."
    )


def test_qa_gemini_failure_fallback(monkeypatch):
    def mock_generate_failure(prompt):
        raise RuntimeError("Gemini service unavailable")

    monkeypatch.setattr("app.services.gemini_service.GeminiService.generate", mock_generate_failure)

    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What is the cancellation charge?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) > 0
    assert "5,000" in response.answer or "5000" in response.answer


def test_qa_insufficient_contract_evidence():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What are the rules regarding pets in the office in this contract?",
        clauses=clauses,
    )

    assert response.confidence == 0.0
    assert response.evidence == []
    assert "could not find enough relevant information" in response.answer.lower()


# ====================================================================
# QA IMPROVEMENTS TESTS
# ====================================================================

def test_qa_explain_it_in_telugu_followup():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Explain it in Telugu",
        clauses=clauses,
        previous_question="When does the agreement renew?",
        previous_answer="The agreement automatically renews for another 12 months unless either party provides 30 days written notice before expiry.",
    )

    # Must NOT be rejected as out-of-scope
    assert "I couldn't find this topic in the contract" not in response.answer
    assert response.confidence > 0
    assert len(response.evidence) > 0
    assert len(response.answer.strip()) > 0


def test_qa_explain_clause_7_in_telugu():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Explain Clause 7 in Telugu.",
        clauses=clauses,
    )

    assert "I couldn't find this topic in the contract" not in response.answer
    assert response.confidence > 0
    assert any(ev.clause_number == "7" for ev in response.evidence)
    assert len(response.answer.strip()) > 0


def test_qa_translate_this_into_telugu():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Translate this into Telugu.",
        clauses=clauses,
        previous_question="What is the cancellation charge?",
        previous_answer="The cancellation charge is INR 5,000 if the Customer cancels before the minimum service period.",
    )

    assert "I couldn't find this topic in the contract" not in response.answer
    assert response.confidence > 0
    assert len(response.answer.strip()) > 0


def test_qa_explain_most_important_terms_simple_language():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Explain the most important terms of this contract in simple language.",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) >= 3
    assert "could not find enough relevant information" not in response.answer.lower()
    # Evidence must contain balanced substantive clauses (e.g. payment, termination, renewal, liability)
    clause_types = {ev.clause_type for ev in response.evidence if hasattr(ev, "clause_type")}
    clause_numbers = {ev.clause_number for ev in response.evidence}
    assert any(num in clause_numbers for num in {"1", "2", "3", "4", "6", "7"})
    assert len(response.answer.strip()) > 0


def test_qa_what_should_i_know_before_signing():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What should I know before signing?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) >= 3
    assert "could not find enough relevant information" not in response.answer.lower()
    assert len(response.answer.strip()) > 0


def test_qa_broad_contract_summary_overview():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="Give me an overview of this contract.",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert len(response.evidence) >= 3
    assert "could not find enough relevant information" not in response.answer.lower()
    assert len(response.answer.strip()) > 0


def test_qa_incomplete_extracted_text_not_guessed():
    incomplete_clauses = [
        Clause(
            clause_id="clause-inc",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 da",
            order=1,
            character_count=98,
            clause_type="RENEWAL",
        )
    ]
    response = QAService.answer(
        file_id="test-file",
        question="When does the agreement renew?",
        clauses=incomplete_clauses,
    )

    assert response.confidence > 0
    answer_lower = response.answer.lower()
    # Must NOT guess/complete the missing text into "30 days" or "30-day"
    assert "30 days" not in answer_lower
    assert "30-day" not in answer_lower
    assert "thirty days" not in answer_lower
    # Must state that the extracted clause is incomplete or cannot be confirmed
    assert (
        "cannot be confirmed" in answer_lower
        or "incomplete" in answer_lower
        or "cut off" in answer_lower
    )
    assert "30 da" in answer_lower or "ends" in answer_lower


def test_qa_truncated_30_da_never_completed_to_30_days():
    """Verify that when Clause 7 ends with '30 da', neither '30 days' nor a 30-day notice period is inferred."""
    incomplete_clauses = [
        Clause(
            clause_id="clause-7",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 da",
            order=1,
            character_count=98,
            clause_type="RENEWAL",
        )
    ]
    response = QAService.answer(
        file_id="test-file",
        question="When does the agreement renew?",
        clauses=incomplete_clauses,
    )

    assert response.confidence > 0
    answer_lower = response.answer.lower()
    # Must NOT transform '30 da' into '30 days'
    assert "30 days" not in answer_lower
    assert "30-day" not in answer_lower
    # Must state what is confirmed and what cannot be confirmed
    assert "12 months" in answer_lower or "renew" in answer_lower
    assert "cannot be confirmed" in answer_lower or "incomplete" in answer_lower


def test_qa_incomplete_excerpt_recovers_complete_stored_clause():
    from app.services.retrieval_service import RetrievedClause

    stored_clauses = [
        Clause(
            clause_id="clause-7",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 days written notice before expiry.",
            order=7,
            character_count=129,
            clause_type="RENEWAL",
        )
    ]
    truncated_retrieved = [
        RetrievedClause(
            clause_id="clause-7",
            clause_number="7",
            title="Renewal",
            text="This agreement shall automatically renew for another 12 months unless either party provides 30 da",
            score=0.95,
        )
    ]

    recovered = QAService._ensure_complete_clause_text(truncated_retrieved, stored_clauses)
    assert recovered[0].text == stored_clauses[0].text
    assert "30 days written notice" in recovered[0].text


def test_qa_language_instruction_does_not_leak_into_new_questions():
    """
    Regression test:
    Q1: What are my obligations? -> English
    Q2: in hindi? / Explain it in Telugu -> Telugu/Hindi
    Q3: What should I know before signing this contract? -> English (NOT Hindi/Telugu)
    """
    import re
    clauses = sample_test_clauses()

    # Turn 1: Substantive question
    r1 = QAService.answer(
        file_id="test-file",
        question="What are my obligations?",
        clauses=clauses,
    )
    assert not re.search(r"[\u0900-\u0D7F]", r1.answer)

    # Turn 2: Follow-up requesting Telugu
    r2 = QAService.answer(
        file_id="test-file",
        question="Explain it in Telugu",
        clauses=clauses,
        previous_question="What are my obligations?",
        previous_answer=r1.answer,
    )
    assert r2.confidence > 0
    assert "I couldn't find this topic in the contract" not in r2.answer

    # Turn 3: New substantive question - MUST default back to English!
    r3 = QAService.answer(
        file_id="test-file",
        question="What should I know before signing this contract?",
        clauses=clauses,
        previous_question="Explain it in Telugu",
        previous_answer=r2.answer,
    )
    assert r3.confidence > 0
    # Must NOT contain Indic / Telugu / Devanagari characters
    assert not re.search(r"[\u0900-\u0D7F]", r3.answer)
    assert "contract" in r3.answer.lower() or "terms" in r3.answer.lower() or "agreement" in r3.answer.lower() or "important" in r3.answer.lower() or "overview" in r3.answer.lower()


def test_qa_explain_clause_in_hindi_then_terminate_early_in_english():
    """
    Regression test:
    Q1: Explain Clause 7 in Hindi. -> Hindi answer
    Q2: What happens if I terminate early? -> English answer
    """
    import re
    clauses = sample_test_clauses()

    # Q1: Hindi
    r1 = QAService.answer(
        file_id="test-file",
        question="Explain Clause 7 in Hindi.",
        clauses=clauses,
    )
    assert r1.confidence > 0

    # Q2: English substantive question with previous Hindi QA passed in
    r2 = QAService.answer(
        file_id="test-file",
        question="What happens if I terminate early?",
        clauses=clauses,
        previous_question="Explain Clause 7 in Hindi.",
        previous_answer=r1.answer,
    )
    assert r2.confidence > 0
    # Must be in English, NOT in Hindi / Devanagari script!
    assert not re.search(r"[\u0900-\u097F]", r2.answer)
    assert any(w in r2.answer.lower() for w in ("terminate", "termination", "cancel", "cancellation", "fee", "notice", "clause"))


def test_qa_conversational_messages_handled_locally():
    """Basic conversational messages must be handled locally and return friendly response."""
    clauses = sample_test_clauses()
    for phrase in ["thank you", "thanks", "thanks!", "okay", "got it", "ok"]:
        response = QAService.answer(
            file_id="test-file",
            question=phrase,
            clauses=clauses,
        )
        assert response.confidence == 1.0
        assert response.evidence == []
        assert "welcome" in response.answer.lower() or "feel free" in response.answer.lower()
        # Must NOT be rejected as out of scope
        assert "I couldn't find this topic in the contract" not in response.answer


def test_qa_conversational_endpoint_does_not_store_history(client):
    """Conversational messages must not be stored in QAHistory."""
    content = (
        b"1. Payment\nThe Customer shall pay within 30 days.\n\n"
        b"2. Termination\nEither party may terminate.\n"
    )
    upload_res = client.post(
        "/api/v1/ingestion/file",
        files={"file": ("conv_test.txt", content, "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        # Ask conversational message
        res = client.post(
            f"/api/v1/qa/{file_id}",
            json={"question": "thank you"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "welcome" in data["answer"].lower() or "feel free" in data["answer"].lower()
        assert data["evidence"] == []

        # Check history - must NOT contain "thank you"
        history_res = client.get(f"/api/v1/qa/{file_id}/history")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 0

        # Ask another conversational message: "got it"
        res2 = client.post(
            f"/api/v1/qa/{file_id}",
            json={"question": "got it"},
        )
        assert res2.status_code == 200
        assert "welcome" in res2.json()["answer"].lower() or "feel free" in res2.json()["answer"].lower()

        # Check history again - still 0
        history_res2 = client.get(f"/api/v1/qa/{file_id}/history")
        assert len(history_res2.json()) == 0

    finally:
        from app.services.file_ingestion_service import FileIngestionService
        from pathlib import Path
        for d in (FileIngestionService.UPLOAD_DIR, FileIngestionService.EXTRACTED_DIR):
            if d.exists():
                for p in d.glob(f"{file_id}.*"):
                    p.unlink()
        cp = Path("storage/clauses") / f"{file_id}.json"
        if cp.exists():
            cp.unlink()


def test_qa_off_topic_french_capital_still_rejected():
    clauses = sample_test_clauses()
    response = QAService.answer(
        file_id="test-file",
        question="What is the capital of France?",
        clauses=clauses,
    )

    assert response.confidence == 0.0
    assert response.evidence == []
    assert response.answer == (
        "I can answer questions related to your selected contract. "
        "I couldn't find this topic in the contract."
    )


def test_qa_handles_clause_with_none_title():
    """
    Regression test:
    Ensure QAService.answer() does not crash when clauses have title=None,
    such as OCR or image-extracted clauses.
    """
    clauses = [
        Clause(
            clause_id="ocr_c1",
            clause_number="1",
            title=None,
            text="The Customer shall pay a fee of INR 25,000 within 30 days of receiving the invoice.",
            order=1,
            character_count=87,
            clause_type="PAYMENT",
        ),
        Clause(
            clause_id="ocr_c2",
            clause_number="2",
            title=None,
            text="The agreement may be terminated by either party with 30 days prior written notice.",
            order=2,
            character_count=84,
            clause_type=None,
        ),
    ]

    response = QAService.answer(
        file_id="ocr-file",
        question="What are the main risks and overview of this contract?",
        clauses=clauses,
    )

    assert response is not None
    assert response.answer
    assert response.confidence >= 0.0


def test_qa_obligations_with_none_metadata_clause():
    """
    Regression test:
    Verify 'What are my obligations?' returns a clause as evidence even when
    title=None and clause_type=None, recognizing operative language in actual
    clause text ('must pay', 'must provide written notice') and not returning
    'insufficient information'.
    """
    clause = Clause(
        clause_id="ocr_obl_test",
        clause_number="1",
        title=None,
        clause_type=None,
        text="The Customer must pay INR 50,000 within 30 days and must provide 15 days written notice before cancellation.",
        order=1,
        character_count=110,
    )

    response = QAService.answer(
        file_id="ocr-file-obl",
        question="What are my obligations?",
        clauses=[clause],
    )

    assert response is not None
    assert any(e.clause_id == "ocr_obl_test" for e in response.evidence)
    # Ensure it does NOT return insufficient information
    assert "could not find enough relevant information" not in response.answer.lower()
    assert "insufficient information" not in response.answer.lower()
    assert response.confidence > 0.0
    # Also verify key obligations are present in the response
    assert "50,000" in response.answer or "pay" in response.answer.lower()


def test_clause_number_must_come_from_evidence():
    """
    Regression test:
    NEVER invent a clause number.
    If the evidence does not contain a clause number, say 'the available contract text'.
    """
    # Case A: Clause with clause_number=None
    ocr_clause = Clause(
        clause_id="c_ocr_no_num",
        clause_number=None,
        title=None,
        text="The Customer must pay INR 20,000 service fee within 15 days of invoice.",
        order=1,
        character_count=75,
    )
    res_no_num = QAService.answer(
        file_id="ocr-test",
        question="What are my obligations?",
        clauses=[ocr_clause],
    )
    assert res_no_num is not None
    # Must NOT invent Clause 1, Clause 2, etc.
    assert not re.search(r"\bClause\s+\d+\b", res_no_num.answer)
    assert "the available contract text" in res_no_num.answer.lower()

    # Case B: Evidence has Clause 4 only
    clause_4 = Clause(
        clause_id="c4_only",
        clause_number="4",
        title="Confidentiality",
        text="The receiving party shall keep all confidential information strictly confidential.",
        order=1,
        character_count=82,
        clause_type="CONFIDENTIALITY",
    )
    res_c4 = QAService.answer(
        file_id="c4-test",
        question="What am I required to do?",
        clauses=[clause_4],
    )
    assert res_c4 is not None
    # Must use actual clause number 4, not invent 1 or 2
    assert "clause 4" in res_c4.answer.lower()
    assert "clause 1" not in res_c4.answer.lower()
    assert "clause 2" not in res_c4.answer.lower()


def test_permission_not_incorrectly_converted_into_obligation():
    """
    Regression test:
    Distinguish obligations from rights/permissions.
    'The Customer may cancel by giving 15 days notice' must NOT become:
    'The Customer must cancel.'
    """
    cancel_clause = Clause(
        clause_id="c_cancel",
        clause_number="2",
        title="Cancellation",
        text=(
            "The Customer may cancel this agreement by providing 15 days written notice. "
            "A cancellation charge of INR 5,000 shall apply if the Customer cancels before the minimum service period."
        ),
        order=1,
        character_count=180,
        clause_type="NOTICES",
    )
    res = QAService.answer(
        file_id="cancel-test",
        question="What are my obligations?",
        clauses=[cancel_clause],
    )
    assert res is not None
    ans_lower = res.answer.lower()
    # Must NOT say "Customer must cancel" or "You must cancel"
    assert "customer must cancel" not in ans_lower
    assert "you must cancel" not in ans_lower
    # Must correctly present it as conditional/permission
    assert "if you choose to cancel" in ans_lower or "may cancel" in ans_lower or "15 days" in ans_lower


def test_obligations_includes_all_supported_duties():
    """
    Regression test:
    'What are my obligations?' includes all clearly supported Customer duties:
    payment, confidentiality, notice requirements, etc.
    """
    clauses = sample_test_clauses()
    res = QAService.answer(
        file_id="obl-test",
        question="What are my obligations?",
        clauses=clauses,
    )
    assert res is not None
    ans_lower = res.answer.lower()
    # Must include payment
    assert "50,000" in ans_lower or "pay" in ans_lower
    # Must include confidentiality
    assert "confidential" in ans_lower
    # Must include notice requirements
    assert "notice" in ans_lower


def test_what_am_i_required_to_do_does_not_omit_confidentiality():
    """
    Regression test:
    'What am I required to do?' does not omit confidentiality when applicable.
    """
    clauses = sample_test_clauses()
    res = QAService.answer(
        file_id="req-test",
        question="What am I required to do?",
        clauses=clauses,
    )
    assert res is not None
    ans_lower = res.answer.lower()
    assert "confidential" in ans_lower


def test_most_important_clause_uses_actual_retrieved_clause_number():
    """
    Regression test:
    'Explain the most important clause' identifies the relevant clause based on
    retrieved evidence and uses actual retrieved clause number/title.
    """
    clauses = sample_test_clauses()
    res = QAService.answer(
        file_id="most-imp-test",
        question="Explain the most important clause",
        clauses=clauses,
    )
    assert res is not None
    ans_lower = res.answer.lower()
    # Identifies Clause 6 (Liability) as the most critical due to unlimited liability
    assert "clause 6" in ans_lower
    assert "liability" in ans_lower or "unlimited" in ans_lower
    # Does not invent a non-existent clause number like Clause 12
    assert "clause 12" not in ans_lower

    # When clause numbers are missing, uses "the available contract text" and never invents numbers
    ocr_clauses = [
        Clause(
            clause_id="ocr_liab",
            clause_number=None,
            title="Liability",
            text="The Customer shall have unlimited liability for all losses arising from breach of this agreement.",
            order=1,
            character_count=100,
            clause_type="LIABILITY",
        )
    ]
    res_ocr = QAService.answer(
        file_id="most-imp-ocr",
        question="Explain the most important clause",
        clauses=ocr_clauses,
    )
    assert not re.search(r"\bClause\s+\d+\b", res_ocr.answer)
    assert "the available contract text" in res_ocr.answer.lower() or "liability" in res_ocr.answer.lower()


def test_telugu_only_when_current_question_requests_telugu():
    """
    Regression test:
    - Default answer language = English.
    - If CURRENT question explicitly asks Telugu, answer in Telugu.
    - Do not let a previous Telugu/Hindi question affect later English questions.
    """
    clauses = sample_test_clauses()

    # Turn 1: Explicitly requests Telugu
    r1 = QAService.answer(
        file_id="telugu-flow",
        question="Explain the important terms in Telugu.",
        clauses=clauses,
    )
    assert r1 is not None
    assert bool(re.search(r"[\u0C00-\u0C7F]", r1.answer))

    # Turn 2: Later English question (must NOT be in Telugu, must NOT leak previous Telugu)
    r2 = QAService.answer(
        file_id="telugu-flow",
        question="What are my obligations?",
        clauses=clauses,
        previous_question="Explain the important terms in Telugu.",
        previous_answer=r1.answer,
    )
    assert r2 is not None
    # Must be in English, NO Telugu script
    assert not re.search(r"[\u0C00-\u0C7F]", r2.answer)
    r2_lower = r2.answer.lower()
    assert "obligations" in r2_lower or "responsibilities" in r2_lower or "pay" in r2_lower

    # Turn 3: Explicitly asks Telugu again
    r3 = QAService.answer(
        file_id="telugu-flow",
        question="What are my obligations in Telugu?",
        clauses=clauses,
    )
    assert r3 is not None
    assert bool(re.search(r"[\u0C00-\u0C7F]", r3.answer))


def test_qa_main_purpose_does_not_select_skip_to_main_content():
    """
    Regression test:
    Verify that when testing a webpage such as https://sam.gov/contracting:
    - 'What is the main purpose of this page?' retrieves the page introduction,
      NOT 'Skip to main content'.
    - The answer explains the actual substantive purpose rather than navigation text.
    """
    clauses = [
        Clause(
            clause_id="clause-1",
            title=None,
            text="Skip to main content",
            order=1,
            character_count=20,
        ),
        Clause(
            clause_id="clause-2",
            title="Contracting on SAM.gov",
            text="SAM.gov is the official U.S. government website for people who make, receive, and manage federal awards. It allows contractors to search for federal procurement opportunities, register their business entity, and manage contract compliance.",
            order=2,
            character_count=248,
        ),
        Clause(
            clause_id="clause-3",
            title=None,
            text="Menu | Search | Data Services | Help Desk",
            order=3,
            character_count=42,
        ),
        Clause(
            clause_id="clause-4",
            title=None,
            text="© 2024 General Services Administration. All rights reserved. Privacy Policy | Terms of Service",
            order=4,
            character_count=96,
        ),
    ]

    response = QAService.answer(
        file_id="sam_gov_webpage",
        question="What is the main purpose of this page?",
        clauses=clauses,
    )

    assert response.confidence > 0
    assert response.evidence
    # Evidence must be the substantive introduction, not "Skip to main content"
    assert response.evidence[0].clause_id == "clause-2"
    assert "Skip to main content" not in response.answer
    ans_lower = response.answer.lower()
    assert "official" in ans_lower or "federal awards" in ans_lower or "contracting" in ans_lower or "procurement" in ans_lower