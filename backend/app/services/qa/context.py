from __future__ import annotations

import json
from typing import Any
from app.models.qa_history import QAHistory
from app.services.retrieval_service import RetrievedClause


class ConversationContextManager:
    """
    Manages multi-turn conversation memory for Ask My T&C.
    Maintains a rolling window of recent turns (up to 10 turns / 20 messages)
    to enable natural ChatGPT-like follow-ups.
    """

    @classmethod
    def format_history_for_prompt(
        cls,
        history_records: list[QAHistory] | list[dict],
        max_turns: int = 10,
    ) -> str:
        """
        Formats recent QA exchanges into a compact conversation context block for Gemini.
        """
        if not history_records:
            return ""

        recent = history_records[-max_turns:]
        lines: list[str] = ["PREVIOUS CONVERSATION CONTEXT:"]

        for rec in recent:
            if isinstance(rec, dict):
                q = (rec.get("question", "") or "").strip()
                a = (rec.get("answer", "") or "").strip()
            else:
                q = (getattr(rec, "question", "") or "").strip()
                a = (getattr(rec, "answer", "") or "").strip()

            if q:
                lines.append(f"User: {q}")
            if a:
                # Keep up to 600 characters of previous answers to preserve token budget
                if len(a) > 600:
                    a = a[:600] + "... [truncated]"
                lines.append(f"Assistant: {a}")

        if len(lines) <= 1:
            return ""

        return "\n".join(lines) + "\n\n"

    @classmethod
    def extract_recent_evidence(
        cls,
        history_records: list[QAHistory] | list[dict],
    ) -> list[RetrievedClause]:
        """
        Extracts evidence items from the most recent turn.
        Useful when the user asks a language or simplification follow-up
        ('in Telugu', 'explain simply') that refers to the previous answer's evidence.
        """
        if not history_records:
            return []

        for rec in reversed(history_records):
            ev_json = None
            if isinstance(rec, dict):
                ev_json = rec.get("evidence_json") or rec.get("evidence")
            else:
                ev_json = getattr(rec, "evidence_json", None)

            if not ev_json:
                continue

            try:
                items = json.loads(ev_json) if isinstance(ev_json, str) else ev_json
                if not isinstance(items, list) or len(items) == 0:
                    continue

                results: list[RetrievedClause] = []
                for it in items:
                    if isinstance(it, dict):
                        results.append(
                            RetrievedClause(
                                clause_id=it.get("clause_id", ""),
                                clause_number=it.get("clause_number"),
                                title=it.get("title"),
                                text=it.get("text", ""),
                                score=float(it.get("relevance_score", it.get("score", 0.9))),
                            )
                        )
                if results:
                    return results
            except Exception:
                continue

        return []
