import uuid
import pytest
from app.schemas.clause import Clause
from app.services.qa import QAService
from app.services.qa.analyzer import QuestionAnalyzer
from app.services.qa.integrity import EvidenceIntegrityChecker
from app.services.qa.retriever import ClauseRetriever


def sample_contract_clauses() -> list[Clause]:
    return [
        Clause(
            clause_id="clause-1",
            clause_number="1",
            title="Services and Payment",
            text="1. Services and Payment. The Service Provider shall perform the services described in Exhibit A. The Customer shall pay all invoices within 30 days of receipt. Late payments shall accrue interest at 2% per month.",
            order=1,
            character_count=200,
        ),
        Clause(
            clause_id="clause-4",
            clause_number="4",
            title="Termination",
            text="4. Termination. Either party may terminate this agreement without cause by providing 30 days prior written notice. If Customer terminates for convenience, Customer shall pay for all services rendered up to the date of termination.",
            order=4,
            character_count=210,
        ),
        Clause(
            clause_id="clause-6",
            clause_number="6",
            title="Liability and Indemnification",
            text="6. Liability. The Customer agrees to unlimited liability for any direct, indirect, or consequential damages resulting from breach of this agreement. Customer shall indemnify and hold harmless the Service Provider against all claims.",
            order=6,
            character_count=230,
        ),
        Clause(
            clause_id="clause-7",
            clause_number="7",
            title="Term and Renewal",
            text="7. Term and Renewal. This agreement shall commence on the Effective Date and remain in effect for one (1) year. It shall automatically renew for additional one-year periods unless either party provides written notice of non-renewal.",
            order=7,
            character_count=220,
        ),
        Clause(
            clause_id="clause-10",
            clause_number="10",
            title="Governing Law",
            text="10. Governing Law. This agreement shall be governed by and construed in accordance with the laws of the State of New York, without regard to conflict of law principles.",
            order=10,
            character_count=160,
        ),
        Clause(
            clause_id="clause-12",
            clause_number="12",
            title="Truncated Notice Clause",
            text="12. Renewal Notice. This agreement shall automatically renew for another 12 months unless either party provides 30 da",
            order=12,
            character_count=115,
        ),
    ]


class TestUnifiedAnalyzer:
    def test_exact_clause_extraction(self):
        clauses = sample_contract_clauses()
        for q, expected in [
            ("What is Clause 7?", "7"),
            ("Explain clause 4 in Telugu", "4"),
            ("Tell me about Section 10", "10"),
            ("Clause 1 details please", "1"),
            ("What does clause 70 say?", "70"),
        ]:
            analysis = QuestionAnalyzer.analyze(q, clauses=clauses)
            assert analysis.clause_number == expected, f"Failed on {q}"

    def test_multilingual_detection(self):
        for q, expected in [
            ("Explain Clause 7 in Telugu", "Telugu"),
            ("Explain Clause 7 in Hindi", "Hindi"),
            ("Explain Clause 7 in Tamil", "Tamil"),
            ("Explain Clause 7 in Kannada", "Kannada"),
            ("Explain Clause 7 in Malayalam", "Malayalam"),
            ("Explain Clause 7 in Marathi", "Marathi"),
            ("Explain Clause 7 in Bengali", "Bengali"),
            ("క్లాజ్ 7 వివరించండి", "Telugu"),
            ("खंड 7 समझाओ", "Hindi"),
            ("Explain Clause 7", "English"),
        ]:
            analysis = QuestionAnalyzer.analyze(q)
            assert analysis.language == expected, f"Failed language for {q}: got {analysis.language}"

    def test_follow_up_pronoun_resolution(self):
        clauses = sample_contract_clauses()
        history = [
            {"question": "Explain Clause 7", "answer": "Clause 7 governs renewal."},
        ]
        analysis = QuestionAnalyzer.analyze("Explain it simply", history=history, clauses=clauses)
        assert analysis.is_follow_up is True
        assert analysis.clause_number == "7"

        analysis2 = QuestionAnalyzer.analyze("In Telugu", history=history, clauses=clauses)
        assert analysis2.language == "Telugu"
        assert analysis2.clause_number == "7"

        analysis3 = QuestionAnalyzer.analyze("What do I need to do?", history=history, clauses=clauses)
        assert analysis3.clause_number == "7"


class TestClauseRetriever:
    def test_exact_clause_no_7_vs_70_confusion(self):
        clauses = sample_contract_clauses()
        # Looking for 7
        res7 = ClauseRetriever.exact_clause_retrieval("7", clauses)
        assert len(res7) == 1
        assert res7[0].clause_number == "7"
        assert res7[0].title == "Term and Renewal"

        # Looking for 70 (does not exist in contract)
        res70 = ClauseRetriever.exact_clause_retrieval("70", clauses)
        assert len(res70) == 0

    def test_exact_clause_retrieval_all(self):
        clauses = sample_contract_clauses()
        for num in ["1", "4", "6", "7", "10"]:
            res = ClauseRetriever.exact_clause_retrieval(num, clauses)
            assert len(res) == 1
            assert res[0].clause_number == num

    def test_exact_clause_999_not_found(self):
        clauses = sample_contract_clauses()
        res = ClauseRetriever.exact_clause_retrieval("999", clauses)
        assert len(res) == 0


class TestEvidenceIntegrity:
    def test_truncated_text_detection(self):
        text = "This agreement shall automatically renew for another 12 months unless either party provides 30 da"
        res = EvidenceIntegrityChecker.check_clause_text(text)
        assert res.is_truncated is True
        assert res.truncated_fragment == "da"

    def test_complete_text_no_false_positive(self):
        text = "The Customer shall pay all invoices within 30 days of receipt."
        res = EvidenceIntegrityChecker.check_clause_text(text)
        assert res.is_truncated is False


class TestQAServiceEndToEnd:
    def test_exact_clause_1(self):
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="Explain Clause 1",
            clauses=clauses,
        )
        assert res.confidence == 1.0
        assert len(res.evidence) == 1
        assert res.evidence[0].clause_number == "1"
        assert "30 days" in res.answer or "invoice" in res.answer.lower()

    def test_exact_clause_4(self):
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="What is Clause 4?",
            clauses=clauses,
        )
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "4"
        assert "termination" in res.answer.lower()

    def test_exact_clause_7(self):
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="Explain Clause 7",
            clauses=clauses,
        )
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "7"
        assert "renew" in res.answer.lower()

    def test_exact_clause_10(self):
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="What does Clause 10 say?",
            clauses=clauses,
        )
        assert res.confidence == 1.0
        assert res.evidence[0].clause_number == "10"
        assert "new york" in res.answer.lower() or "governing law" in res.answer.lower()

    def test_exact_clause_999_not_found(self):
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="Explain Clause 999",
            clauses=clauses,
        )
        assert res.confidence == 0.0
        assert "not found" in res.answer.lower()

    def test_truncated_clause_no_hallucination(self):
        """Zero-tolerance test: text ending in '30 da' must NOT claim '30 days'."""
        clauses = sample_contract_clauses()
        res = QAService.answer(
            file_id="test-file",
            question="Explain Clause 12",
            clauses=clauses,
        )
        # Answer must state incomplete/cannot determine, and must NOT assert 30 days
        ans_low = res.answer.lower()
        assert "incomplete" in ans_low or "cut off" in ans_low or "cannot be" in ans_low or "30 da" in ans_low

    def test_unrelated_questions(self):
        clauses = sample_contract_clauses()
        for q in ["What is the capital of France?", "Weather today"]:
            res = QAService.answer(
                file_id="test-file",
                question=q,
                clauses=clauses,
            )
            assert res.confidence == 0.0
            assert "contract" in res.answer.lower()

    def test_contract_thematic_queries(self):
        clauses = sample_contract_clauses()
        # Obligations
        res_ob = QAService.answer(file_id="test-file", question="What are my obligations?", clauses=clauses)
        assert len(res_ob.evidence) > 0
        assert "pay" in res_ob.answer.lower() or "obligation" in res_ob.answer.lower()

        # Cancellation
        res_can = QAService.answer(file_id="test-file", question="Can I cancel?", clauses=clauses)
        assert len(res_can.evidence) > 0
        assert "terminate" in res_can.answer.lower() or "notice" in res_can.answer.lower()

        # Major Risk
        res_risk = QAService.answer(file_id="test-file", question="What is the major risk?", clauses=clauses)
        assert len(res_risk.evidence) > 0
        assert "liability" in res_risk.answer.lower() or "risk" in res_risk.answer.lower()


class TestQAEndpointAndClearChatAPI:
    def test_endpoint_qa_and_clear_chat(self, client):
        content = (
            b"1. Payment Terms\n"
            b"The Customer shall pay all invoices within 30 days.\n\n"
            b"2. Early Termination\n"
            b"Either party may terminate this agreement upon 15 days notice.\n"
        )

        upload_res = client.post(
            "/api/v1/ingestion/file",
            files={"file": ("unified_qa_test.txt", content, "text/plain")},
        )
        assert upload_res.status_code == 200
        file_id = upload_res.json()["file_id"]

        try:
            # 1. Ask initial question
            res1 = client.post(
                f"/api/v1/qa/{file_id}",
                json={"question": "What are my payment obligations?"},
            )
            assert res1.status_code == 200
            assert res1.json()["answer"]

            # 2. Ask follow-up with explicit language
            res2 = client.post(
                f"/api/v1/qa/{file_id}",
                json={"question": "Can I terminate?", "language": "English"},
            )
            assert res2.status_code == 200
            assert res2.json()["answer"]

            # 3. Check history contains 2 records
            hist_res = client.get(f"/api/v1/qa/{file_id}/history")
            assert hist_res.status_code == 200
            records = hist_res.json()
            assert len(records) == 2

            # 4. Clear chat history
            clear_res = client.delete(f"/api/v1/qa/{file_id}/history")
            assert clear_res.status_code == 200
            clear_data = clear_res.json()
            assert clear_data["success"] is True
            assert clear_data["cleared_records"] == 2

            # 5. Verify history is now empty
            hist_res_after = client.get(f"/api/v1/qa/{file_id}/history")
            assert hist_res_after.status_code == 200
            assert len(hist_res_after.json()) == 0

            # 6. Verify contract itself still exists
            contracts_res = client.get("/api/v1/contracts")
            assert contracts_res.status_code == 200
            assert file_id in [c["id"] for c in contracts_res.json()]

        finally:
            # Clean up contract
            client.delete(f"/api/v1/contracts/{file_id}")
