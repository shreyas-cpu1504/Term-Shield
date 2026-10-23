from __future__ import annotations

import json
import logging
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.clause import Clause
from app.schemas.qa import EvidenceItem, QuestionResponse
from app.models.qa_history import QAHistory
from app.services.retrieval_service import RetrievedClause

from app.services.qa.analyzer import QuestionAnalyzer, QuestionAnalysis
from app.services.qa.retriever import ClauseRetriever
from app.services.qa.integrity import EvidenceIntegrityChecker
from app.services.qa.context import ConversationContextManager
from app.services.qa.generator import AnswerGenerator
from app.services.qa.validator import AnswerValidator

logger = logging.getLogger(__name__)


class QAService:
    """
    Unified Contract Question-Answering Service.
    Single clean pipeline:
    QuestionAnalyzer -> ClauseRetriever -> EvidenceIntegrityChecker
    -> ConversationContextManager -> ONE AnswerGenerator -> AnswerValidator.
    """

    @classmethod
    def classify_intent(cls, question: str, clauses: list[Clause] | None = None) -> str:
        """Coarse intent classification for backward compatibility with existing tests."""
        return QuestionAnalyzer.classify_coarse_intent(question, clauses)

    @classmethod
    def get_conversational_response(cls, text: str) -> str | None:
        """Quick greeting/gratitude bypass for conversational pleasantries."""
        if not text or not text.strip():
            return None
        analysis = QuestionAnalyzer.analyze(text)
        if analysis.coarse_intent == "general" and analysis.cleaned_question.lower() in QuestionAnalyzer.GREETINGS_OR_GENERAL:
            return AnswerGenerator._handle_general_conversational(analysis.cleaned_question, analysis.language)
        return None

    @classmethod
    def is_conversational_message(cls, text: str) -> bool:
        res = cls.get_conversational_response(text)
        return res is not None

    @classmethod
    def _ensure_complete_clause_text(
        cls,
        retrieved: list[RetrievedClause],
        clauses: list[Clause],
    ) -> list[RetrievedClause]:
        """Recovers full clause text for truncated retrieved items when available."""
        return EvidenceIntegrityChecker.ensure_complete_clause_text(retrieved, clauses)

    @classmethod
    def answer(
        cls,
        file_id: str,
        question: str,
        clauses: list[Clause],
        contract_name: str | None = None,
        contract_summary: str | None = None,
        previous_question: str | None = None,
        previous_answer: str | None = None,
        previous_evidence: list[RetrievedClause] | None = None,
        conversation_history: list[QAHistory] | list[dict] | None = None,
        language: str | None = None,
    ) -> QuestionResponse:
        """
        Unified Ask My T&C entry point.
        """
        if not question or not question.strip():
            return QuestionResponse(
                file_id=file_id,
                question=question or "",
                answer="Please enter a question about your contract.",
                language=language or "English",
                evidence=[],
                confidence=0.0,
            )

        # 1. Normalize conversation history
        history_list: list[dict] = []
        if conversation_history:
            for item in conversation_history:
                if isinstance(item, dict):
                    history_list.append(item)
                else:
                    history_list.append({
                        "question": getattr(item, "question", "") or "",
                        "answer": getattr(item, "answer", "") or "",
                        "language": getattr(item, "language", None),
                        "evidence_json": getattr(item, "evidence_json", None),
                    })
        elif previous_question or previous_answer:
            history_list.append({
                "question": previous_question or "",
                "answer": previous_answer or "",
                "language": language,
                "evidence_json": json.dumps([
                    {
                        "clause_id": e.clause_id,
                        "clause_number": e.clause_number,
                        "title": e.title,
                        "text": e.text,
                        "relevance_score": getattr(e, "score", 0.9),
                    }
                    for e in (previous_evidence or [])
                ]) if previous_evidence else None,
            })

        # 2. Unified Question Analysis
        analysis = QuestionAnalyzer.analyze(
            question=question,
            requested_language=language,
            history=history_list,
            clauses=clauses,
        )

        # 3. Conversational / Capability / Unrelated handling
        if analysis.coarse_intent in {"general", "capability", "unrelated"}:
            direct_ans = AnswerGenerator.generate(
                analysis=analysis,
                evidence=[],
                conversation_context="",
                contract_name=contract_name,
                contract_summary=contract_summary,
            )
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer=direct_ans,
                language=analysis.language,
                evidence=[],
                confidence=1.0 if analysis.coarse_intent != "unrelated" else 0.0,
            )

        # 4. Retrieval Layer
        retrieved: list[RetrievedClause] = []

        # If user explicitly references a clause number (or follow-up resolved to a clause number)
        if analysis.clause_number:
            retrieved = ClauseRetriever.exact_clause_retrieval(analysis.clause_number, clauses)
            if not retrieved:
                # Target clause was not found in the current contract.
                # Never use lexical retrieval to guess a different clause.
                return QuestionResponse(
                    file_id=file_id,
                    question=question,
                    answer=f"Clause {analysis.clause_number} was not found in the uploaded contract.",
                    language=analysis.language,
                    evidence=[],
                    confidence=0.0,
                )

        # If no exact clause query
        if not retrieved:
            # Check if this is a follow-up reusing prior evidence (translation, simplification, obligation, etc.)
            if analysis.is_follow_up and history_list:
                retrieved = ConversationContextManager.extract_recent_evidence(history_list)

            # If still not retrieved, perform semantic search
            if not retrieved:
                query_to_search = analysis.cleaned_question
                if analysis.is_follow_up and history_list:
                    last_q = history_list[-1].get("question", "")
                    if last_q:
                        query_to_search = f"{last_q} {query_to_search}"

                retrieved = ClauseRetriever.semantic_retrieval(
                    query=query_to_search,
                    clauses=clauses,
                    fine_intent=analysis.fine_intent,
                    top_k=8,
                )

        # 5. Integrity Check & Recovery
        retrieved = EvidenceIntegrityChecker.ensure_complete_clause_text(retrieved, clauses)

        # If no relevant evidence was found
        if not retrieved:
            clause_msg = (
                f"Clause {analysis.clause_number} was not found in the uploaded contract."
                if analysis.clause_number
                else "I could not find enough relevant information in the uploaded contract to answer this question."
            )
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer=clause_msg,
                language=analysis.language,
                evidence=[],
                confidence=0.0,
            )

        # 6. Format Conversation Context
        conv_context_str = ConversationContextManager.format_history_for_prompt(history_list)

        # 7. Unified Gemini Generation
        raw_answer = ""
        try:
            raw_answer = AnswerGenerator.generate(
                analysis=analysis,
                evidence=retrieved,
                conversation_context=conv_context_str,
                contract_name=contract_name,
                contract_summary=contract_summary,
            )
        except Exception as exc:
            logger.exception("Gemini QA generation failed: %s", exc)
            raw_answer = ""

        # 8. Answer Validation & Safe Fallback
        if not raw_answer or not raw_answer.strip():
            final_answer = AnswerValidator.evidence_fallback(analysis, retrieved)
        else:
            final_answer = AnswerValidator.validate_and_refine(raw_answer, analysis, retrieved)

        # 9. Format Evidence and Confidence
        evidence_items = [
            EvidenceItem(
                clause_id=item.clause_id,
                clause_number=item.clause_number,
                title=item.title,
                text=item.text,
                relevance_score=item.score,
            )
            for item in retrieved
        ]

        # Confidence calculation
        is_lang_or_format_followup = (
            bool(history_list)
            and (
                analysis.fine_intent in {"translation", "simplification"}
                or QuestionAnalyzer.is_language_or_format_instruction(question)
            )
        )
        if is_lang_or_format_followup:
            confidence = 1.0
        elif analysis.clause_number and retrieved:
            confidence = 1.0
        else:
            confidence = round(max((e.score for e in retrieved), default=0.5), 4)

        return QuestionResponse(
            file_id=file_id,
            question=question,
            answer=final_answer,
            language=analysis.language,
            evidence=evidence_items,
            confidence=confidence,
        )

    @classmethod
    async def clear_history(cls, db: AsyncSession, contract_id: str, user_id: str) -> int:
        """
        Clears QAHistory for the specified contract and user only.
        Does not touch contracts, clauses, or other users' history.
        """
        result = await db.execute(
            delete(QAHistory).where(
                QAHistory.contract_id == contract_id,
                QAHistory.user_id == user_id,
            )
        )
        await db.commit()
        return result.rowcount or 0
