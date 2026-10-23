import uuid
import pytest
from app.schemas.clause import Clause
from app.services.retrieval_service import RetrievedClause
from app.services.qa import QAService
from app.services.qa.analyzer import QuestionAnalyzer
from app.services.qa.integrity import EvidenceIntegrityChecker
from app.services.qa.retriever import ClauseRetriever


def get_sample_test_clauses() -> list[Clause]:
    return [
        Clause(
            clause_id="clause-1",
            clause_number="1",
            title="Services and Payment",
            text="1. Services and Payment. The Service Provider shall perform the consulting services. The Customer shall pay all invoices within 30 days of receipt. Late payments shall accrue interest at 2% per month.",
            order=1,
            character_count=210,
        ),
        Clause(
            clause_id="clause-4",
            clause_number="4",
            title="Termination",
            text="4. Termination. Either party may terminate this agreement without cause by providing 30 days prior written notice. Upon termination, Customer shall pay for all services rendered up to the date of termination.",
            order=4,
            character_count=225,
        ),
        Clause(
            clause_id="clause-6",
            clause_number="6",
            title="Liability and Indemnification",
            text="6. Liability. The Customer agrees to unlimited liability for any direct, indirect, or consequential damages resulting from breach of this agreement. Customer shall indemnify the Service Provider.",
            order=6,
            character_count=215,
        ),
        Clause(
            clause_id="clause-7",
            clause_number="7",
            title="Term and Renewal",
            text="7. Term and Renewal. This agreement shall commence on the Effective Date and remain in effect for one (1) year. It shall automatically renew for additional one-year periods unless either party provides written notice of non-renewal.",
            order=7,
            character_count=230,
        ),
        Clause(
            clause_id="clause-10",
            clause_number="10",
            title="Governing Law",
            text="10. Governing Law. This agreement shall be governed by and construed in accordance with the laws of the State of New York, without regard to conflict of law principles.",
            order=10,
            character_count=170,
        ),
        Clause(
            clause_id="clause-12",
            clause_number="12",
            title="Truncated Renewal Clause",
            text="12. Renewal Notice. This agreement shall automatically renew for another 12 months unless either party provides 30 da",
            order=12,
            character_count=115,
        ),
    ]


class TestAskMyTCRedesignCore:
    """Comprehensive test suite for Ask My T&C requirements A through V."""

    # A. Exact clause
    def test_a_exact_clause_7(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 7", clauses=clauses)
        assert res.confidence == 1.0
        assert len(res.evidence) == 1
        assert res.evidence[0].clause_number == "7"
        assert "renew" in res.answer.lower()
        assert res.language == "English"

    # B. Exact clause in Telugu
    def test_b_exact_clause_7_in_telugu(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 7 in Telugu", clauses=clauses)
        assert res.confidence == 1.0
        assert res.language == "Telugu"
        assert len(res.evidence) == 1
        assert res.evidence[0].clause_number == "7"
        # Must contain Telugu script characters
        assert any('\u0C00' <= char <= '\u0C7F' for char in res.answer)

    # C. Follow-up language: "Explain Clause 7" -> "in Telugu"
    def test_c_follow_up_language_in_telugu(self):
        clauses = get_sample_test_clauses()
        # Turn 1
        res1 = QAService.answer(file_id="c1", question="Explain Clause 7", clauses=clauses)
        assert res1.language == "English"
        # Turn 2: Follow-up
        history = [
            {"question": "Explain Clause 7", "answer": res1.answer, "evidence": [e.model_dump() for e in res1.evidence]}
        ]
        res2 = QAService.answer(file_id="c1", question="in Telugu", clauses=clauses, conversation_history=history)
        assert res2.confidence == 1.0
        assert res2.language == "Telugu"
        assert len(res2.evidence) == 1
        assert res2.evidence[0].clause_number == "7"
        assert any('\u0C00' <= char <= '\u0C7F' for char in res2.answer)

    # D. Follow-up simplification: "Explain Clause 7" -> "make it simple"
    def test_d_follow_up_simplification(self):
        clauses = get_sample_test_clauses()
        history = [
            {"question": "Explain Clause 7", "answer": "Clause 7 defines the initial one-year term and automatic renewal provisions."}
        ]
        res = QAService.answer(file_id="c1", question="make it simple", clauses=clauses, conversation_history=history)
        assert res.confidence == 1.0
        assert len(res.evidence) == 1
        assert res.evidence[0].clause_number == "7"
        assert "renew" in res.answer.lower() or "year" in res.answer.lower()

    # E. Follow-up obligation: "what do I need to do?"
    def test_e_follow_up_obligation(self):
        clauses = get_sample_test_clauses()
        history = [
            {"question": "Explain Clause 7", "answer": "Clause 7 defines term and renewal."}
        ]
        res = QAService.answer(file_id="c1", question="what do I need to do?", clauses=clauses, conversation_history=history)
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "7"
        assert "notice" in res.answer.lower() or "written" in res.answer.lower()

    # F. Follow-up consequence: "what happens if I don't do it?"
    def test_f_follow_up_consequence(self):
        clauses = get_sample_test_clauses()
        history = [
            {"question": "Explain Clause 7", "answer": "Clause 7 defines term and renewal."}
        ]
        res = QAService.answer(file_id="c1", question="what happens if I don't do it?", clauses=clauses, conversation_history=history)
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "7"
        assert "renew" in res.answer.lower() or "automatically" in res.answer.lower()

    # G. Switch language: "now explain it in English"
    def test_g_switch_language_to_english(self):
        clauses = get_sample_test_clauses()
        history = [
            {"question": "Explain Clause 7", "answer": "క్లాజ్ 7 పునరుద్ధరణ గురించి చెబుతుంది.", "language": "Telugu"}
        ]
        res = QAService.answer(file_id="c1", question="now explain it in English", clauses=clauses, conversation_history=history)
        assert res.language == "English"
        assert res.evidence[0].clause_number == "7"
        # Must not contain Telugu script
        assert not any('\u0C00' <= char <= '\u0C7F' for char in res.answer)

    # H. Another language: Hindi
    def test_h_hindi_language(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 7 in Hindi", clauses=clauses)
        assert res.language == "Hindi"
        assert res.evidence[0].clause_number == "7"
        # Must contain Devanagari script
        assert any('\u0900' <= char <= '\u097F' for char in res.answer)

    # I. Tamil
    def test_i_tamil_language(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 7 in Tamil", clauses=clauses)
        assert res.language == "Tamil"
        assert res.evidence[0].clause_number == "7"
        # Must contain Tamil script
        assert any('\u0B80' <= char <= '\u0BFF' for char in res.answer)

    # J. Exact clause not found
    def test_j_exact_clause_not_found(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 999", clauses=clauses)
        assert res.confidence == 0.0
        assert len(res.evidence) == 0
        assert "999 was not found" in res.answer

    # K. General contract question
    def test_k_general_contract_question(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="What is the termination notice period?", clauses=clauses)
        assert res.confidence > 0
        assert len(res.evidence) > 0
        assert any(e.clause_number == "4" for e in res.evidence)
        assert "30 days" in res.answer or "written notice" in res.answer.lower()

    # L. Unrelated question
    def test_l_unrelated_question(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="What is the capital of France?", clauses=clauses)
        assert res.confidence == 0.0
        assert len(res.evidence) == 0
        assert "Paris" not in res.answer
        assert "contract" in res.answer.lower()

    # M. Truncated evidence handling
    def test_m_truncated_evidence_no_extrapolation(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 12", clauses=clauses)
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "12"
        # Must explain confirmed portion (renew)
        assert "renew" in res.answer.lower()
        # Must explicitly disclose that the text ends at '30 da' and cannot be confirmed
        assert "30 da" in res.answer or "incomplete" in res.answer.lower() or "cannot be confirmed" in res.answer.lower()

    # N. Gemini failure fallback
    def test_n_gemini_failure_fallback(self, monkeypatch):
        def mock_error(prompt):
            raise RuntimeError("Simulated Gemini API 500 error")

        monkeypatch.setattr("app.services.gemini_service.GeminiService.generate", mock_error)
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="Explain Clause 4", clauses=clauses)
        assert res.confidence == 1.0
        assert len(res.evidence) == 1
        assert "Clause 4" in res.answer or "termination" in res.answer.lower()

    # O. English script leakage check
    def test_o_english_script_leakage(self):
        analysis = QuestionAnalyzer.analyze("Explain Clause 1", requested_language="English")
        evidence = [RetrievedClause(clause_id="c1", clause_number="1", title="Payment", text="Pay within 30 days.", score=1.0)]
        from app.services.qa.validator import AnswerValidator
        # Simulate an answer that accidentally had Telugu characters leaked
        leaked_answer = "Clause 1 details: \nచెల్లింపు నిబంధనలు\nThe customer must pay all invoices within 30 days."
        refined = AnswerValidator.validate_and_refine(leaked_answer, analysis, evidence)
        assert not any('\u0C00' <= char <= '\u0C7F' for char in refined)
        assert "pay" in refined.lower()

    # T. Empty question
    def test_t_empty_question(self):
        clauses = get_sample_test_clauses()
        res = QAService.answer(file_id="c1", question="   ", clauses=clauses)
        assert res.confidence == 0.0
        assert "Please enter a question" in res.answer

    # U. Long question
    def test_u_long_question(self):
        clauses = get_sample_test_clauses()
        long_q = "Could you please explain Clause 1 in detail and " + ("tell me more about payment terms and " * 10) + "explain when invoices are due?"
        res = QAService.answer(file_id="c1", question=long_q, clauses=clauses)
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "1"

    # V. Repeated questions
    def test_v_repeated_questions(self):
        clauses = get_sample_test_clauses()
        res1 = QAService.answer(file_id="c1", question="Explain Clause 7", clauses=clauses)
        res2 = QAService.answer(file_id="c1", question="Explain Clause 7", clauses=clauses)
        assert res1.confidence == 1.0 and res2.confidence == 1.0
        assert res1.evidence[0].clause_number == "7"
        assert res2.evidence[0].clause_number == "7"


class TestAskMyTCAPIAndIsolation:
    """Tests P, Q, R, S: Clear Chat, Ownership Protection, Contract Isolation, Multi-turn Flow."""

    def test_p_clear_chat_and_r_contract_isolation(self, client):
        # Create Contract A
        res_a = client.post(
            "/api/v1/ingestion/file",
            files={"file": ("contract_a.txt", b"1. Payment\nPay within 30 days.\n", "text/plain")},
        )
        assert res_a.status_code == 200
        file_id_a = res_a.json()["file_id"]

        # Create Contract B
        res_b = client.post(
            "/api/v1/ingestion/file",
            files={"file": ("contract_b.txt", b"1. License\nGrant of software license.\n", "text/plain")},
        )
        assert res_b.status_code == 200
        file_id_b = res_b.json()["file_id"]

        try:
            # Ask on Contract A
            res_qa_a = client.post(f"/api/v1/qa/{file_id_a}", json={"question": "Explain Clause 1"})
            assert res_qa_a.status_code == 200

            # Ask on Contract B
            res_qa_b = client.post(f"/api/v1/qa/{file_id_b}", json={"question": "Explain Clause 1"})
            assert res_qa_b.status_code == 200

            # Verify history exists on both
            hist_a = client.get(f"/api/v1/qa/{file_id_a}/history").json()
            hist_b = client.get(f"/api/v1/qa/{file_id_b}/history").json()
            assert len(hist_a) == 1
            assert len(hist_b) == 1

            # P. Clear chat on Contract A ONLY
            clear_res = client.delete(f"/api/v1/qa/{file_id_a}/history")
            assert clear_res.status_code == 200
            assert clear_res.json()["success"] is True
            assert clear_res.json()["cleared_records"] == 1

            # Verify Contract A history is empty
            hist_a_after = client.get(f"/api/v1/qa/{file_id_a}/history").json()
            assert len(hist_a_after) == 0

            # R. Verify Contract B history is completely untouched!
            hist_b_after = client.get(f"/api/v1/qa/{file_id_b}/history").json()
            assert len(hist_b_after) == 1

            # Verify Contract A itself was NOT deleted
            all_contracts = client.get("/api/v1/contracts").json()
            assert file_id_a in [c["id"] for c in all_contracts]

        finally:
            client.delete(f"/api/v1/contracts/{file_id_a}")
            client.delete(f"/api/v1/contracts/{file_id_b}")

    def test_q_ownership_protection(self, client):
        # Non-existent contract ID or random UUID returns 404
        fake_id = str(uuid.uuid4())
        res = client.get(f"/api/v1/qa/{fake_id}/history")
        assert res.status_code == 404

        del_res = client.delete(f"/api/v1/qa/{fake_id}/history")
        assert del_res.status_code == 404

        ask_res = client.post(f"/api/v1/qa/{fake_id}", json={"question": "Explain Clause 1"})
        assert ask_res.status_code == 404

    def test_s_multiple_conversation_turns(self, client):
        content = (
            b"Agreement Title: Terms of Service\n\n"
            b"1. Scope\nThis agreement covers the provided services.\n\n"
            b"7. Term and Renewal\nThis agreement shall remain in effect for 1 year and "
            b"automatically renews unless either party gives 30 days notice.\n\n"
        )
        upload_res = client.post(
            "/api/v1/ingestion/file",
            files={"file": ("turns_contract.txt", content, "text/plain")},
        )
        assert upload_res.status_code == 200
        file_id = upload_res.json()["file_id"]

        try:
            # Turn 1: Explain Clause 7
            t1 = client.post(f"/api/v1/qa/{file_id}", json={"question": "Explain Clause 7"})
            assert t1.status_code == 200
            assert "renew" in t1.json()["answer"].lower()

            # Turn 2: in Telugu (follow-up)
            t2 = client.post(f"/api/v1/qa/{file_id}", json={"question": "in Telugu"})
            assert t2.status_code == 200
            assert any('\u0C00' <= char <= '\u0C7F' for char in t2.json()["answer"])

            # Turn 3: make it simple (follow-up)
            t3 = client.post(f"/api/v1/qa/{file_id}", json={"question": "make it simple"})
            assert t3.status_code == 200

            # Turn 4: what do I need to do? (follow-up)
            t4 = client.post(f"/api/v1/qa/{file_id}", json={"question": "what do I need to do?"})
            assert t4.status_code == 200
            assert "notice" in t4.json()["answer"].lower() or any('\u0C00' <= char <= '\u0C7F' for char in t4.json()["answer"])

            # Verify history records all 4 turns
            hist = client.get(f"/api/v1/qa/{file_id}/history").json()
            assert len(hist) == 4
        finally:
            client.delete(f"/api/v1/contracts/{file_id}")
