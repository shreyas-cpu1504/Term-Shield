from __future__ import annotations

import re
from dataclasses import dataclass
from app.schemas.clause import Clause
from app.services.retrieval_service import RetrievedClause


@dataclass
class ClauseIntegrityResult:
    is_truncated: bool
    confirmed_portion: str
    truncated_fragment: str | None
    warning_message: str | None


class EvidenceIntegrityChecker:
    """
    Centralized Evidence Text-Integrity Check.
    Detects truncated / cut-off text generally without hardcoding specific contract strings.
    Supports English, Telugu, Hindi, Tamil, and other languages.
    """

    # Terminal punctuation marks across Latin and Indic scripts (including danda । and double danda ॥)
    TERMINAL_PUNCTUATION = {".", "!", "?", ";", "\"", "'", ")", "]", "}", "।", "॥"}

    @classmethod
    def check_clause_text(cls, text: str) -> ClauseIntegrityResult:
        """
        Analyzes clause text for general truncation indicators.
        Does not hardcode specific case-by-case phrases.
        """
        clean = (text or "").strip()
        if not clean:
            return ClauseIntegrityResult(
                is_truncated=False,
                confirmed_portion="",
                truncated_fragment=None,
                warning_message=None,
            )

        last_char = clean[-1]
        is_truncated = False
        truncated_fragment = None

        # 1. Check if the text ends without terminal punctuation
        if last_char not in cls.TERMINAL_PUNCTUATION:
            # Trailing partial word, cut-off letters, or abrupt number/word ending
            m_tail = re.search(r"(\b[^\s.,!?;:\"')\]}।॥]{1,8})$", clean)
            if m_tail:
                truncated_fragment = m_tail.group(1)
                is_truncated = True

        # 2. Check for explicit ellipsis or truncation markers
        if clean.endswith("...") or clean.endswith("[...]") or "[truncated]" in clean.lower() or "[cut off]" in clean.lower():
            is_truncated = True
            if not truncated_fragment:
                truncated_fragment = clean[-10:]

        if is_truncated:
            # Confirmed portion is everything up to the last sentence ending, or preceding the cut-off fragment
            last_period = max(clean.rfind("."), clean.rfind(";"), clean.rfind("।"))
            if last_period > 0:
                confirmed = clean[:last_period + 1].strip()
            else:
                # If single sentence was cut off, confirmed portion is text up to the cut-off fragment
                if truncated_fragment and clean.endswith(truncated_fragment):
                    confirmed = clean[:-len(truncated_fragment)].strip()
                else:
                    confirmed = clean

            warning = (
                f"The available extracted text is incomplete and ends abruptly at '{truncated_fragment}'. "
                f"Do not guess or infer missing terms or requirements."
            )
            return ClauseIntegrityResult(
                is_truncated=True,
                confirmed_portion=confirmed,
                truncated_fragment=truncated_fragment,
                warning_message=warning,
            )

        return ClauseIntegrityResult(
            is_truncated=False,
            confirmed_portion=clean,
            truncated_fragment=None,
            warning_message=None,
        )

    @classmethod
    def ensure_complete_clause_text(
        cls,
        retrieved: list[RetrievedClause],
        stored_clauses: list[Clause],
    ) -> list[RetrievedClause]:
        """
        If a retrieved clause appears truncated, attempts to find the fuller version from stored clauses.
        """
        recovered_list: list[RetrievedClause] = []

        for item in retrieved:
            text = (item.text or "").strip()
            integrity = cls.check_clause_text(text)

            if integrity.is_truncated:
                matching = next(
                    (
                        c for c in stored_clauses
                        if (c.clause_id and c.clause_id == item.clause_id)
                        or (
                            c.clause_number is not None
                            and item.clause_number is not None
                            and str(c.clause_number).strip() == str(item.clause_number).strip()
                        )
                        or (
                            c.title and item.title and c.title.strip().lower() == item.title.strip().lower()
                        )
                    ),
                    None,
                )
                if matching and matching.text and len(matching.text.strip()) > len(text):
                    recovered_list.append(
                        RetrievedClause(
                            clause_id=item.clause_id,
                            clause_number=item.clause_number,
                            title=item.title,
                            text=matching.text.strip(),
                            score=item.score,
                        )
                    )
                    continue

            recovered_list.append(item)

        return recovered_list
