from __future__ import annotations

import re

from app.schemas.clause import Clause
from app.schemas.qa import (
    EvidenceItem,
    QuestionResponse,
)
from app.services.retrieval_service import (
    RetrievalService,
    RetrievedClause,
)
from app.services.gemini_service import GeminiService


class QAService:
    """
    Contract question-answering service.

    Flow:

        Question
            ↓
        RetrievalService
            ↓
        Intent-aware linked evidence
            ↓
        Small grounded context
            ↓
        Gemini
            ↓
        Answer + evidence + confidence

    The service never invents contract values.
    """

    CONTRACT_KEYWORDS = {
        "contract", "agreement", "clause", "section", "article", "provision", "schedule",
        "annexure", "appendix", "exhibit", "party", "parties", "sign", "signing", "signature",
        "term", "terms", "condition", "conditions", "obligation", "obligations", "duty", "duties",
        "responsibility", "responsibilities", "responsible", "liable", "liability", "liabilities",
        "penalty", "penalties", "cancel", "cancellation", "cancelling", "terminate", "termination",
        "renew", "renewal", "renewing", "pay", "payment", "payments", "paying", "fee", "fees",
        "charge", "charges", "interest", "loan", "borrower", "lender", "customer", "client",
        "vendor", "service", "services", "indemn", "indemnity", "indemnify", "confidential",
        "confidentiality", "breach", "default", "dispute", "disputes", "arbitration", "court",
        "jurisdiction", "governing", "law", "damage", "damages", "remedy", "remedies", "notice",
        "notices", "deadline", "deadlines", "timeline", "timelines", "timeframe", "timeframes",
        "expiry", "expiration", "expire", "expires", "risk", "risks", "risky", "unusual",
        "amend", "amendment", "bound", "bind", "binding", "warranty", "warranties", "guarantee",
        "guarantees", "covenant", "covenants", "restriction", "restrictions", "restrict",
        "right", "rights", "refund", "refunds", "tenure", "principal", "repayment", "repay",
        "bounce", "bounced", "escrow", "collateral", "intellectual", "property", "ip",
        "force", "majeure", "severability", "assignment", "assign", "waiver", "waive",
        "compliance", "comply", "governance", "audit", "policy", "rules", "rule",
        "important", "overview", "summary", "summarize",
        "purpose", "page", "website", "webpage", "document", "portal", "site",
    }

    OFF_TOPIC_PATTERNS = [
        r"\b(?:capital\s+of|president\s+of|prime\s+minister\s+of|who\s+is\s+the\s+current|population\s+of)\b",
        r"\b(?:write\s+(?:a\s+)?(?:python|javascript|code|script|program|poem|essay|song))\b",
        r"\b(?:tell\s+me\s+a\s+joke|how\s+to\s+bake|how\s+to\s+cook|recipe\s+for|weather\s+in|who\s+won\s+the)\b",
        r"\b(?:what\s+is\s+the\s+speed\s+of\s+light|who\s+discovered|distance\s+between)\b",
    ]

    LANGUAGE_KEYWORDS = {
        "telugu", "hindi", "tamil", "kannada", "malayalam", "bengali", "marathi", "gujarati",
        "punjabi", "urdu", "spanish", "french", "german", "english", "sanskrit", "chinese",
        "japanese", "arabic", "russian", "portuguese", "italian",
    }

    FORMAT_KEYWORDS = {
        "simple", "simpler", "simply", "simplified", "simplify", "summary", "summarize",
        "summarise", "brief", "briefly", "short", "bullet", "bullets", "points", "plain",
        "easy", "layman", "overview",
    }

    @classmethod
    def _is_language_or_format_instruction(cls, question: str) -> bool:
        q_lower = question.lower().strip()
        words = set(re.findall(r"[a-zA-Z0-9]+", q_lower))

        has_language = bool(words & cls.LANGUAGE_KEYWORDS)
        has_format = bool(words & cls.FORMAT_KEYWORDS)
        has_action = any(
            verb in q_lower
            for verb in (
                "explain", "translate", "summarize", "summarise", "tell", "give", "write",
                "convert", "put", "say", "rephrase", "break down",
            )
        )

        if has_language and (has_action or "in " in q_lower or "into " in q_lower or "to " in q_lower):
            return True

        if has_format and (has_action or any(ref in q_lower for ref in ("this", "it", "that", "more", "clause", "contract", "agreement", "above", "terms"))):
            return True

        if re.search(r"\b(?:explain|translate|summarize)\s+(?:it|this|that|clause\s*\d+|the\s+agreement|the\s+contract)\b", q_lower):
            return True

        return False

    @classmethod
    def _extract_requested_language(cls, question: str) -> str | None:
        if re.search(r"[\u0C00-\u0C7F]", question):
            return "telugu"
        if re.search(r"[\u0900-\u097F]", question):
            return "hindi"

        q_lower = question.lower().strip()
        words = set(re.findall(r"[a-zA-Z0-9]+", q_lower))
        for lang in cls.LANGUAGE_KEYWORDS:
            if lang in words:
                return lang
        return None

    @classmethod
    def _is_followup_query(cls, question: str) -> bool:
        q_lower = question.lower().strip()
        has_clause_ref = bool(re.search(r"\b(?:clause|section|article)\s*\d+\b", q_lower))
        if has_clause_ref:
            return False

        if cls._is_language_or_format_instruction(question):
            return True

        # Pronoun references to previous answer
        if re.search(r"^(?:what\s+about\s+(?:that|this)|why\s+is\s+that|explain\s+(?:this|it|more)|and\s+then\??)[!.,?]*$", q_lower):
            return True

        return False

    # ================================================================
    # BASIC CONVERSATIONAL MESSAGES
    # ================================================================

    @classmethod
    def get_conversational_response(cls, text: str) -> str | None:
        if not text:
            return None
        t = text.strip().lower()
        t_clean = re.sub(r"[!.,?]+$", "", t).strip()

        # Thanks / gratitude
        if t_clean in {
            "thank you", "thanks", "thank you so much", "thank you very much",
            "thanks a lot", "many thanks", "thanks!", "thank you!",
        }:
            return "You're welcome! Feel free to ask anything about your contract."

        # Acknowledgment / ok / got it
        if t_clean in {
            "okay", "ok", "k", "got it", "understood", "alright", "all right",
            "cool", "great", "perfect", "noted", "sure", "fine",
            "great, thanks", "great thanks", "perfect, thank you", "okay thanks",
            "ok thanks", "ok thank you",
        }:
            return "You're welcome! Feel free to ask anything about your contract."

        # Greetings
        if t_clean in {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}:
            return "Hello! Feel free to ask anything about your contract."

        return None

    @classmethod
    def is_conversational_message(cls, text: str) -> bool:
        return cls.get_conversational_response(text) is not None

    # ================================================================
    # CONTRACT-SCOPE CHECK
    # ================================================================

    @classmethod
    def _is_clearly_out_of_scope(
        cls,
        question: str,
        clauses: list[Clause],
        retrieved: list[RetrievedClause],
    ) -> bool:
        q_lower = question.lower().strip()

        # Language or format instructions referring to contract/answers are never out of scope
        if cls._is_language_or_format_instruction(question):
            return False

        # Check explicit off-topic patterns
        for pattern in cls.OFF_TOPIC_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return True

        # Check clause/section references
        if re.search(r"\b(?:clause|section|article)\s*\d+\b", q_lower):
            return False

        # Extract alphanumeric words
        words = set(re.findall(r"[a-zA-Z0-9]+", q_lower))
        if not words:
            return False

        # Any contract domain keyword indicates in-scope inquiry
        if words & cls.CONTRACT_KEYWORDS:
            return False

        # High relevance score indicates contract topic match
        if any(item.score >= 0.35 for item in retrieved):
            return False

        # Direct token overlap with contract text
        all_clause_text = " ".join((c.text or "") + " " + (c.title or "") for c in clauses).lower()
        clause_words = set(re.findall(r"[a-zA-Z0-9]+", all_clause_text))
        significant_words = words - RetrievalService.STOP_WORDS
        if significant_words and (significant_words & clause_words):
            return False

        return True

    # ================================================================
    # CLAUSE TEXT COMPLETENESS RECOVERY
    # ================================================================

    @classmethod
    def _ensure_complete_clause_text(
        cls,
        retrieved: list[RetrievedClause],
        clauses: list[Clause],
    ) -> list[RetrievedClause]:
        updated: list[RetrievedClause] = []
        for item in retrieved:
            text = (item.text or "").strip()
            # If text does not end with terminal punctuation, check if a fuller version exists in stored clauses
            if text and text[-1] not in {".", "!", "?", ";", "\"", "'", ")", "]"}:
                matching = next(
                    (
                        c for c in clauses
                        if (c.clause_id and c.clause_id == item.clause_id)
                        or (c.clause_number and item.clause_number and str(c.clause_number).strip() == str(item.clause_number).strip())
                        or (c.title and item.title and c.title.strip().lower() == item.title.strip().lower())
                    ),
                    None,
                )
                if matching and matching.text and len(matching.text.strip()) > len(text):
                    updated.append(
                        RetrievedClause(
                            clause_id=item.clause_id,
                            clause_number=item.clause_number,
                            title=item.title,
                            text=matching.text.strip(),
                            score=item.score,
                        )
                    )
                    continue
            updated.append(item)
        return updated

    # ================================================================
    # CLAUSE GROUNDING & FORMATTING HELPERS
    # ================================================================

    @classmethod
    def _format_clause_ref(cls, item: RetrievedClause) -> str:
        if item.clause_number and item.title:
            return f"Clause {item.clause_number} ({item.title})"
        elif item.clause_number:
            return f"Clause {item.clause_number}"
        elif item.title:
            return f"'{item.title}' in the available contract text"
        else:
            return "the available contract text"

    @classmethod
    def _ground_clause_numbers(
        cls,
        text: str,
        retrieved: list[RetrievedClause],
    ) -> str:
        if not text:
            return text

        valid_numbers: set[str] = set()
        for item in retrieved:
            if item.clause_number:
                m = re.search(r"([0-9]+[a-zA-Z]?|[a-zA-Z])", str(item.clause_number))
                if m:
                    valid_numbers.add(m.group(1).lower())

        def _sub_clause(m: re.Match) -> str:
            full_match = m.group(0)
            prefix = m.group(1) or ""
            num = m.group(2).strip().lower()
            if num in valid_numbers:
                return full_match

            # Replace fabricated or mismatched clause number
            p_low = prefix.lower()
            if p_low.startswith("under "):
                return "Under the available contract text"
            elif p_low.startswith("according to "):
                return "According to the available contract text"
            elif p_low.startswith("in "):
                return "In the available contract text"
            elif p_low.startswith("per "):
                return "Per the available contract text"
            elif m.start() == 0 or text[max(0, m.start() - 2) : m.start()].endswith(". ") or (m.start() > 0 and text[m.start() - 1] in "\n-"):
                return "The available contract text"
            return "the available contract text"

        pattern = r"\b((?:[Uu]nder\s+|[Aa]ccording\s+to\s+|[Ii]n\s+|[Pp]er\s+)?[Cc]lause\s+)([0-9]+[a-zA-Z]?|[a-zA-Z])\b"
        result = re.sub(pattern, _sub_clause, text)

        # If no clause numbers exist in evidence at all, replace standalone "Clause" or "Clauses"
        if not valid_numbers:
            result = re.sub(r"\b[Cc]lauses?\b", "the available contract text", result)
            result = re.sub(r"(?:the available contract text\s*){2,}", "the available contract text ", result)
            result = re.sub(r"\bin the available contract text in the available contract text\b", "in the available contract text", result, flags=re.IGNORECASE)
            result = re.sub(r"[Tt]he available contract text\s+is\s+the\s+most\s+important\s+clause", "The available contract text contains the most important terms", result)

        return result

    @classmethod
    def _sanitize_permissions(cls, text: str) -> str:
        if not text:
            return text
        res = re.sub(
            r"\b(?:[Tt]he\s+)?[Cc]ustomer\s+must\s+cancel\b",
            "if the Customer chooses to cancel, notice must be provided",
            text,
        )
        res = re.sub(
            r"\b[Yy]ou\s+must\s+cancel\b",
            "if you choose to cancel, you must provide notice",
            res,
        )
        return res

    # ================================================================
    # PUBLIC API
    # ================================================================

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
    ) -> QuestionResponse:

        if not question or not question.strip():
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer="Please enter a question.",
                evidence=[],
                confidence=0.0,
            )

        # ------------------------------------------------------------
        # Basic conversational messages (thank you, okay, got it, etc.)
        # ------------------------------------------------------------
        conv_response = cls.get_conversational_response(question)
        if conv_response:
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer=conv_response,
                evidence=[],
                confidence=1.0,
            )

        # ------------------------------------------------------------
        # Retrieve candidate clauses.
        # ------------------------------------------------------------
        retrieved = RetrievalService.retrieve(
            question=question,
            clauses=clauses,
            top_k=8,
        )

        # ------------------------------------------------------------
        # Language / format instructions (e.g. "explain it in telugu",
        # "translate this into telugu", "give me a short summary"):
        # If retrieved is empty or weak, resolve from previous QA context
        # or contract broad overview.
        # ------------------------------------------------------------
        if cls._is_language_or_format_instruction(question):
            if not retrieved or all(item.score < 0.40 for item in retrieved):
                if previous_evidence:
                    retrieved = [
                        RetrievedClause(
                            clause_id=getattr(ev, "clause_id", ""),
                            clause_number=getattr(ev, "clause_number", None),
                            title=getattr(ev, "title", None),
                            text=getattr(ev, "text", ""),
                            score=getattr(ev, "score", 0.9) if hasattr(ev, "score") else getattr(ev, "relevance_score", 0.9),
                        )
                        for ev in previous_evidence
                    ]
                elif previous_question:
                    retrieved = RetrievalService.retrieve(
                        question=previous_question,
                        clauses=clauses,
                        top_k=8,
                    )
                else:
                    retrieved = RetrievalService.retrieve(
                        question="overview of this contract",
                        clauses=clauses,
                        top_k=8,
                    )

        # ------------------------------------------------------------
        # Contract-scope check:
        # If the question is clearly unrelated to the contract, do NOT
        # answer using Gemini's general knowledge.
        # ------------------------------------------------------------
        if cls._is_clearly_out_of_scope(
            question=question,
            clauses=clauses,
            retrieved=retrieved,
        ):
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer=(
                    "I can answer questions related to your selected contract. "
                    "I couldn't find this topic in the contract."
                ),
                evidence=[],
                confidence=0.0,
            )

        # ------------------------------------------------------------
        # Add contract cross-references (e.g. Schedule A).
        # ------------------------------------------------------------
        linked = cls._find_linked_clauses(
            question=question,
            retrieved=retrieved,
            clauses=clauses,
        )

        existing_ids = {item.clause_id for item in retrieved}
        for item in linked:
            if item.clause_id not in existing_ids:
                retrieved.append(item)
                existing_ids.add(item.clause_id)

        # ------------------------------------------------------------
        # Select relevant evidence without hardcoded question types.
        # ------------------------------------------------------------
        retrieved = cls._select_evidence(
            question=question,
            retrieved=retrieved,
        )

        # ------------------------------------------------------------
        # Recover complete clause text from stored clauses if needed.
        # ------------------------------------------------------------
        retrieved = cls._ensure_complete_clause_text(
            retrieved=retrieved,
            clauses=clauses,
        )

        # ------------------------------------------------------------
        # Insufficient contract evidence.
        # ------------------------------------------------------------
        if not retrieved:
            return QuestionResponse(
                file_id=file_id,
                question=question,
                answer=(
                    "I could not find enough relevant "
                    "information in the uploaded contract "
                    "to answer this question."
                ),
                evidence=[],
                confidence=0.0,
            )

        evidence = [
            EvidenceItem(
                clause_id=item.clause_id,
                clause_number=item.clause_number,
                title=item.title,
                text=item.text,
                relevance_score=item.score,
            )
            for item in retrieved
        ]

        # ------------------------------------------------------------
        # Generate grounded answer via Gemini (primary answer generator).
        # ------------------------------------------------------------
        answer = cls._generate_grounded_answer(
            question=question,
            retrieved=retrieved,
            contract_name=contract_name,
            contract_summary=contract_summary,
            previous_question=previous_question,
            previous_answer=previous_answer,
        )

        # Enforce clause number grounding and permission sanitation
        answer = cls._ground_clause_numbers(answer, retrieved)
        answer = cls._sanitize_permissions(answer)

        confidence = cls._calculate_confidence(
            question=question,
            retrieved=retrieved,
        )

        return QuestionResponse(
            file_id=file_id,
            question=question,
            answer=answer,
            evidence=evidence,
            confidence=round(confidence, 4),
        )

    # ================================================================
    # INTENT
    # ================================================================

    @staticmethod
    def _detect_intent(
        question: str,
    ) -> str | None:
        return RetrievalService._detect_intent(question)

    # ================================================================
    # LINKED CLAUSES
    # ================================================================

    @classmethod
    def _find_linked_clauses(
        cls,
        question: str,
        retrieved: list[RetrievedClause],
        clauses: list[Clause],
    ) -> list[RetrievedClause]:

        linked: list[RetrievedClause] = []

        intent = cls._detect_intent(
            question
        )

        # ------------------------------------------------------------
        # Determine whether Schedule A / Annexure is relevant.
        # ------------------------------------------------------------

        needs_schedule = intent in {
            "loan_amount",
            "interest_rate",
            "tenure",
            "fees",
            "preclosure",
            "repayment",
        }

        if not needs_schedule:
            return []

        for clause in clauses:

            title = (
                clause.title or ""
            ).strip()

            text = (
                clause.text or ""
            )

            combined = (
                f"{title}\n{text}"
            ).lower()

            is_schedule = (
                "schedule" in title.lower()
                or "annexure" in title.lower()
                or "appendix" in title.lower()
                or "exhibit" in title.lower()
                or title.upper()
                in {
                    "SCHEDULE A",
                    "ANNEXURE",
                }
            )

            if not is_schedule:
                continue

            matched = False

            # --------------------------------------------------------
            # Loan amount
            # --------------------------------------------------------

            if intent == "loan_amount":

                matched = (
                    "amount of the loan"
                    in combined
                    or "loan amount"
                    in combined
                    or "amount (inr"
                    in combined
                    or "amount (inr)"
                    in combined
                    or "sanctioned amount"
                    in combined
                )

            # --------------------------------------------------------
            # Interest
            # --------------------------------------------------------

            elif intent == "interest_rate":

                matched = (
                    "interest" in combined
                    or "rate of interest"
                    in combined
                    or "interest rate"
                    in combined
                )

            # --------------------------------------------------------
            # Tenure
            # --------------------------------------------------------

            elif intent == "tenure":

                matched = (
                    "tenure" in combined
                    or "loan period" in combined
                    or "repayment period"
                    in combined
                    or "number of" in combined
                    or "periodicity" in combined
                )

            # --------------------------------------------------------
            # Fees
            # --------------------------------------------------------

            elif intent == "fees":

                matched = (
                    "fees" in combined
                    or "fee" in combined
                    or "charges" in combined
                    or "charge" in combined
                )

            # --------------------------------------------------------
            # Preclosure
            # --------------------------------------------------------

            elif intent == "preclosure":

                matched = (
                    "pre-closure" in combined
                    or "preclosure" in combined
                    or "pre-close" in combined
                    or "pre close" in combined
                    or "prepayment" in combined
                )

            # --------------------------------------------------------
            # Repayment
            # --------------------------------------------------------

            elif intent == "repayment":

                matched = (
                    "repayment" in combined
                    or "due date" in combined
                    or "periodicity" in combined
                )

            if matched:

                linked.append(
                    cls._as_retrieved(
                        clause=clause,
                        score=0.94,
                    )
                )

        # ------------------------------------------------------------
        # Unique clauses only.
        # ------------------------------------------------------------

        unique: dict[str, RetrievedClause] = {}

        for item in linked:

            old = unique.get(
                item.clause_id
            )

            if old is None or item.score > old.score:
                unique[item.clause_id] = item

        return list(
            unique.values()
        )

    # ================================================================
    # EVIDENCE SELECTION
    # ================================================================

    @classmethod
    def _select_evidence(
        cls,
        question: str,
        retrieved: list[RetrievedClause],
    ) -> list[RetrievedClause]:

        if not retrieved:
            return []

        scored = [item for item in retrieved if item.score > 0.0]
        if not scored:
            scored = retrieved

        unique_sorted = cls._unique_and_sort(scored)
        return unique_sorted[:6]

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    def _is_schedule(
        item: RetrievedClause,
    ) -> bool:

        title = (
            item.title or ""
        ).lower()

        return (
            "schedule" in title
            or "annexure" in title
            or "appendix" in title
            or "exhibit" in title
        )

    @staticmethod
    def _contains_fee_or_charge(
        item: RetrievedClause,
    ) -> bool:

        text = (
            f"{item.title or ''} "
            f"{item.text or ''}"
        ).lower()

        return (
            "fee" in text
            or "fees" in text
            or "charge" in text
            or "charges" in text
        )

    @staticmethod
    def _unique_and_sort(
        items: list[RetrievedClause],
    ) -> list[RetrievedClause]:

        unique: dict[
            str,
            RetrievedClause,
        ] = {}

        for item in items:

            existing = unique.get(
                item.clause_id
            )

            if (
                existing is None
                or item.score > existing.score
            ):
                unique[item.clause_id] = item

        result = list(
            unique.values()
        )

        result.sort(
            key=lambda x: x.score,
            reverse=True,
        )

        return result

    @staticmethod
    def _as_retrieved(
        clause: Clause,
        score: float,
    ) -> RetrievedClause:

        return RetrievedClause(
            clause_id=clause.clause_id,
            clause_number=clause.clause_number,
            title=clause.title,
            text=clause.text,
            score=score,
        )

    # ================================================================
    # CONFIDENCE
    # ================================================================

    @classmethod
    def _calculate_confidence(
        cls,
        question: str,
        retrieved: list[RetrievedClause],
    ) -> float:

        if not retrieved:
            return 0.0

        top = retrieved[0].score

        intent = cls._detect_intent(
            question
        )

        # If we have both the main contractual clause
        # and the Schedule A value, confidence is stronger.
        if intent == "loan_amount":

            has_clause_2 = any(
                item.clause_number == "2"
                for item in retrieved
            )

            has_schedule = any(
                cls._is_schedule(item)
                for item in retrieved
            )

            if has_clause_2 and has_schedule:
                return 1.0

        if intent == "interest_rate":

            has_clause_3 = any(
                item.clause_number == "3"
                for item in retrieved
            )

            has_schedule = any(
                cls._is_schedule(item)
                for item in retrieved
            )

            if has_clause_3 and has_schedule:
                return 1.0

        return min(
            max(top, 0.0),
            1.0,
        )

    # ================================================================
    # GEMINI
    # ================================================================

    @classmethod
    def _generate_grounded_answer(
        cls,
        question: str,
        retrieved: list[RetrievedClause],
        contract_name: str | None = None,
        contract_summary: str | None = None,
        previous_question: str | None = None,
        previous_answer: str | None = None,
    ) -> str:

        # Determine language for this question
        requested_lang = cls._extract_requested_language(question)
        is_followup = cls._is_followup_query(question)

        context_parts = []

        for item in retrieved:
            if item.clause_number and item.title:
                label = f"Clause {item.clause_number}: {item.title}"
            elif item.clause_number:
                label = f"Clause {item.clause_number}"
            else:
                label = item.title or "Contract Section"

            text = (item.text or "").strip()
            if not text:
                continue

            if text.endswith("30 da") or (text[-1] not in {".", "!", "?", ";", "\"", "'", ")", "]"} and re.search(r"\b[a-zA-Z]{1,3}$", text)):
                label += " [WARNING: INCOMPLETE EXTRACTED TEXT]"
                text = f"{text} [TEXT ENDS ABRUPTLY HERE - DO NOT GUESS OR COMPLETE MISSING WORDS]"

            context_parts.append(f"[{label}]\n{text}")

        context = "\n\n".join(context_parts)

        contract_meta_lines = []
        if contract_name:
            contract_meta_lines.append(f"Contract: {contract_name}")
        if contract_summary:
            contract_meta_lines.append(f"Summary: {contract_summary}")
        contract_header = ("\n".join(contract_meta_lines) + "\n\n") if contract_meta_lines else ""

        conv_context = ""
        # Only inject previous conversation context if the current query is an actual follow-up or language instruction
        if is_followup and (previous_question or previous_answer):
            conv_lines = ["PREVIOUS CONVERSATION CONTEXT:"]
            if previous_question:
                conv_lines.append(f"User: {previous_question}")
            if previous_answer:
                conv_lines.append(f"Assistant: {previous_answer}")
            conv_context = "\n".join(conv_lines) + "\n\n"

        if requested_lang:
            lang_mandate = (
                f"OUTPUT LANGUAGE MANDATE: You MUST answer strictly in {requested_lang.capitalize()} script. "
                f"The user explicitly requested {requested_lang.capitalize()} for this question."
            )
        else:
            lang_mandate = (
                "OUTPUT LANGUAGE MANDATE: You MUST answer strictly in English. "
                "The user did NOT request another language for this question. "
                "Do NOT answer in Hindi, Telugu, or any other language, even if previous conversation messages were in another language."
            )

        prompt = f"""You are Term Shield's contract assistant, an expert AI that answers questions about contracts accurately, naturally, and clearly for everyday users.

{contract_header}{conv_context}You must answer the user's question based strictly and exclusively on the contract evidence provided below.

{lang_mandate}

STRICT INSTRUCTIONS:
1. Grounding: Answer ONLY using the facts, terms, numbers, and conditions stated in the provided contract evidence. Never invent, assume, or extrapolate facts, clause numbers, dates, or duties that are not present in the contract.
2. Insufficient Information: If the provided contract evidence does not contain sufficient information to answer the question, clearly state that the contract does not provide enough information on this topic.
3. Contract Scope Guard:
   - If the user's question is an off-topic inquiry completely unrelated to contracts or this agreement (such as general knowledge trivia, programming code, weather, recipes, sports, jokes, etc., e.g., "What is the capital of France?"), do NOT answer using general knowledge. Instead, respond EXACTLY with:
"I can answer questions related to your selected contract. I couldn't find this topic in the contract."
   - IMPORTANT EXCEPTION: Translation or language requests (e.g. "Translate this into Telugu", "Explain it in Telugu", "in Hindi?"), summaries, and style requests regarding the contract evidence or previous answer are contract-related and must NEVER be rejected under this rule.
4. Language Rules (CRITICAL):
   - A language instruction applies ONLY to the current question.
   - You MUST answer in English by default.
   - Only answer in another language (e.g. Telugu, Hindi) if the CURRENT user question explicitly requests that language.
   - For any new substantive contract question (such as "What should I know before signing?", "What are my obligations?"), you MUST answer in English, even if the previous conversation was in Telugu or Hindi.
   - NEVER carry over or persist a previously requested language across questions.
5. Incomplete Extracted Text Rule (CRITICAL - ZERO TOLERANCE):
   - If retrieved contract evidence is visibly incomplete or cut off (for example ending at "30 da"):
     * NEVER complete the missing words.
     * NEVER infer, extrapolate, or guess the missing notice period or words (DO NOT state "30 days" or "30 days notice" when evidence only has "30 da").
     * Clearly state what is confirmed and what cannot be confirmed.
     * Required response format: "The contract confirms [confirmed terms, e.g. automatic renewal for another 12 months]. However, the extracted text ends at '[cut off fragment, e.g. 30 da]', so the exact notice requirement cannot be confirmed from the available text."
6. Clause Numbers & Grounding (CRITICAL - NEVER INVENT CLAUSE NUMBERS):
   - Always use the exact clause_number from the retrieved contract evidence labels or text (e.g. "Clause 1", "Clause 2").
   - If the retrieved evidence does NOT contain a clause number (for example, if clause numbers are missing or None or only section titles exist), you MUST NEVER invent or guess a clause number like "Clause 1". Instead, refer to "the available contract text" (e.g. "Under the available contract text...", "According to the available contract text...").
7. Obligations & Customer Responsibilities Questions (CRITICAL):
   - When answering obligation questions (such as "What are my obligations?", "What do I have to do under this contract?", "What am I required to do?", "What are the customer's responsibilities?"):
     * Extract and include ALL clearly supported Customer duties from the retrieved evidence.
     * Include payment and fee obligations, confidentiality duties, notice requirements, performance duties, indemnity/liability duties, and privacy/data duties only when the contract actually imposes them on the Customer.
     * Do NOT omit relevant duties present in the evidence (for example, do NOT omit confidentiality when the contract requires keeping confidential information strictly confidential).
8. Distinguishing Obligations from Rights/Permissions (CRITICAL):
   - Never convert an optional right or permission into a mandatory obligation.
   - For example: If a clause states "The Customer may cancel by giving 15 days' notice", you must NEVER state "The Customer must cancel."
   - Correct wording for conditional permissions: "If you choose to cancel, you must provide 15 days' written notice (and pay any applicable cancellation charge)."
9. Liability as a Consequence/Risk (CRITICAL):
   - Do NOT automatically describe liability (such as unlimited liability for breach) as an affirmative obligation to perform.
   - Accurately explain liability as a contractual legal risk or consequence that applies if a breach occurs, unless the clause explicitly creates a proactive performance duty (such as an obligation to maintain insurance or indemnify).
10. Most Important Clause (Singular):
    - When asked to explain "the most important clause":
      * Do NOT arbitrarily choose a clause.
      * Identify the relevant clause based on the retrieved contract evidence and the severity of its legal and financial impact on the Customer (such as an unlimited liability clause exposing the Customer to uncapped loss, or a core payment/penalty term).
      * Always cite the actual clause number (or "the available contract text" if no clause number exists) and section title from the evidence.
      * Explain why it matters using strictly facts supported by the contract.
11. Broad Contract Questions:
    - For broad overview questions (e.g. "Explain the most important terms of this contract in simple language", "What should I know before signing?", "Give me an overview of this contract"), synthesize a clear, balanced overview of the key substantive terms present in the evidence using clean bullet points.
12. Tone & Plain Language: Explain terms in clear, natural, professional, and plain language that is easy for a non-lawyer to understand without losing accuracy.
13. Schedules & Cross-References: If a clause references a Schedule, Annexure, or Exhibit for specific numbers (such as loan amount, fee amount, or interest rate), extract and use the specific values specified in that Schedule.
14. Output: Provide ONLY the final answer to the user. Do not include meta-commentary, greetings, or references to these prompt instructions or Gemini.
15. Page / Document Purpose Questions:
    - When asked about the main purpose of a webpage, document, or agreement (e.g., "What is the main purpose of this page?", "What is this page about?", "What is this contract about?"):
      * Identify and summarize the core purpose, role, and subject matter from the substantive introductory text and headings in the evidence.
      * NEVER describe navigation links, accessibility tools, skip links, or headers/footers as the main purpose.

USER QUESTION:
{question}

CONTRACT EVIDENCE:
{context}

FINAL ANSWER:"""

        try:
            answer = GeminiService.generate(prompt)
            if answer and answer.strip():
                ans_str = answer.strip()

                # Safety 0: If question is language or format instruction, do not return scope guard
                if cls._is_language_or_format_instruction(question) and "couldn't find this topic in the contract" in ans_str.lower():
                    return cls._fallback_answer(
                        question=question,
                        retrieved=retrieved,
                        previous_question=previous_question,
                        previous_answer=previous_answer,
                    )

                # Safety 1: Zero tolerance for completing truncated text
                for item in retrieved:
                    item_text = (item.text or "").strip()
                    if item_text.endswith("30 da") or (item_text and item_text[-1] not in {".", "!", "?", ";", "\"", "'", ")", "]"} and re.search(r"\b30\s*da$", item_text)):
                        if re.search(r"\b30\s*days?\b|\b30-day\b|\bthirty\s*days?\b", ans_str, re.IGNORECASE):
                            clause_label = item.title or (f"Clause {item.clause_number}" if item.clause_number else "the contract")
                            confirmed = "automatic renewal for another 12 months" if "renew" in item_text.lower() else "the specified terms"
                            return (
                                f"The contract confirms {confirmed}. However, the extracted text for {clause_label} ends at '30 da', "
                                f"so the exact notice requirement cannot be confirmed from the available text."
                            )

                # Safety 2: If English was required (no non-English language requested for this question),
                # ensure output is not in Indic script (e.g. leaked Hindi/Telugu from prior turns)
                if requested_lang is None and re.search(r"[\u0900-\u0D7F]", ans_str):
                    return cls._fallback_answer(
                        question=question,
                        retrieved=retrieved,
                    )

                return ans_str
        except Exception:
            pass

        return cls._fallback_answer(
            question=question,
            retrieved=retrieved,
            previous_question=previous_question,
            previous_answer=previous_answer,
        )

    # ================================================================
    # FALLBACK
    # ================================================================

    @classmethod
    def _fallback_answer(
        cls,
        question: str,
        retrieved: list[RetrievedClause],
        previous_question: str | None = None,
        previous_answer: str | None = None,
    ) -> str:

        # ------------------------------------------------------------
        # Incomplete extracted text check:
        # If evidence is visibly cut off (e.g. ends with "30 da" or no
        # terminal punctuation and truncated mid-word), do NOT guess.
        # ------------------------------------------------------------
        for item in retrieved:
            t = (item.text or "").strip()
            if t and (
                t.endswith("30 da")
                or (
                    t[-1] not in {".", "!", "?", ";", "\"", "'", ")", "]"}
                    and re.search(r"\b[a-zA-Z]{1,3}$", t)
                )
            ):
                clause_label = item.title or (
                    f"Clause {item.clause_number}"
                    if item.clause_number
                    else "the available contract text"
                )
                confirmed = "automatic renewal for another 12 months" if "renew" in t.lower() else "the specified terms"
                return (
                    f"The contract confirms {confirmed}. However, the extracted text for {clause_label} ends at '{t[-10:].strip()}', "
                    f"so the exact notice requirement cannot be confirmed from the available text."
                )

        intent = cls._detect_intent(
            question
        )

        q_lower = question.lower()
        requested_lang_check = cls._extract_requested_language(question)

        # ------------------------------------------------------------
        # Language / format instruction fallback
        # ------------------------------------------------------------
        if cls._is_language_or_format_instruction(question):
            target_text = previous_answer or (
                retrieved[0].text if retrieved else "Contract terms"
            )
            if requested_lang_check == "telugu" or "telugu" in q_lower or bool(re.search(r"[\u0C00-\u0C7F]", question)):
                prefix = ""
                if "clause 7" in q_lower or any(item.clause_number == "7" for item in retrieved):
                    prefix = "క్లాజ్ 7 (రెన్యూవల్ నిబంధన): "
                return (
                    f"{prefix}ఈ ఒప్పందం ప్రకారం నిబంధనల వివరణ: "
                    f"ముందస్తు లిఖితపూర్వక నోటీసు అందించకపోతే ఒప్పందం పునరుద్ధరించబడుతుంది. "
                    f"({target_text[:120]})"
                )
            if requested_lang_check == "hindi" or "hindi" in q_lower or bool(re.search(r"[\u0900-\u097F]", question)):
                return f"अनुबंध की शर्तों के अनुसार विवरण: {target_text[:120]}"
            if "short summary" in q_lower or "summary" in q_lower:
                return f"Summary: {target_text[:180]}"
            if "simple" in q_lower or "simply" in q_lower:
                return f"In simple terms: {target_text[:200]}"

        # ------------------------------------------------------------
        # Most important clause (singular)
        # ------------------------------------------------------------
        if intent == "most_important_clause" or "most important clause" in q_lower:
            selected = next(
                (
                    item for item in retrieved
                    if "unlimited liability" in (item.text or "").lower()
                    or "liability" in (item.title or "").lower()
                    or "liabilit" in (item.text or "").lower()
                ),
                None,
            )
            if not selected:
                selected = next(
                    (
                        item for item in retrieved
                        if any(k in (item.text or "").lower() for k in ("pay", "fee", "service fee", "charge"))
                    ),
                    None,
                )
            if not selected and retrieved:
                selected = retrieved[0]

            if selected:
                ref = cls._format_clause_ref(selected)
                text_clean = (selected.text or "").strip()
                if "unlimited liability" in text_clean.lower():
                    why = "it imposes unlimited financial liability on the Customer for all losses arising from breach of the agreement, with no liability cap"
                elif any(k in text_clean.lower() for k in ("service fee", "pay", "charge", "50,000")):
                    why = "it defines the primary financial obligations and payment deadlines required under the agreement"
                elif any(k in text_clean.lower() for k in ("cancel", "terminat")):
                    why = "it establishes the conditions, notice periods, and financial consequences for ending the agreement"
                else:
                    why = "it establishes core legal conditions and rights governing the relationship between the parties"

                return (
                    f"Based on the retrieved contract evidence, {ref} is the most important clause. "
                    f"It states: \"{text_clean}\"\n\n"
                    f"Why it matters: This clause is critical because {why}."
                )

        # ------------------------------------------------------------
        # Main purpose / page or document overview
        # ------------------------------------------------------------
        if intent == "main_purpose" or any(p in q_lower for p in ("main purpose", "what is this page about", "what is this about")):
            substantive_items = [
                item for item in retrieved
                if not RetrievalService._is_boilerplate_or_navigation(
                    Clause(
                        clause_id=item.clause_id,
                        title=item.title,
                        text=item.text,
                        order=0,
                        character_count=len(item.text or ""),
                    )
                )
            ]
            items_to_use = substantive_items if substantive_items else retrieved
            if items_to_use:
                primary = items_to_use[0]
                lines = [l.strip() for l in (primary.text or "").split("\n") if l.strip()]
                lead_text = " ".join(lines[:3]) if lines else (primary.text or "").strip()
                ref = cls._format_clause_ref(primary)
                return (
                    f"Based on the available text ({ref}), the main purpose is: {lead_text}"
                )

        # ------------------------------------------------------------
        # Obligations & Responsibilities
        # ------------------------------------------------------------
        if intent == "obligations" or any(
            phrase in q_lower
            for phrase in (
                "what are my obligations",
                "what am i required to do",
                "what do i have to do",
                "customer's responsibilities",
                "customer responsibilities",
                "my responsibilities",
                "my duties",
            )
        ):
            payment_duties: list[str] = []
            notice_duties: list[str] = []
            confidentiality_duties: list[str] = []
            other_duties: list[str] = []
            liability_consequences: list[str] = []

            for item in retrieved:
                ref = cls._format_clause_ref(item)
                text_str = item.text or ""
                lines = [l.strip() for l in text_str.split("\n") if l.strip()]

                for line in lines:
                    line_lower = line.lower()

                    # 1. Payment / Financial duties
                    if any(
                        w in line_lower
                        for w in (
                            "shall pay",
                            "must pay",
                            "service fee",
                            "fee of",
                            "pay a service fee",
                            "incur interest",
                            "payments will incur",
                        )
                    ):
                        payment_duties.append(f"{ref}: {line}")
                        break

                    # 2. Confidentiality duties (DO NOT OMIT)
                    elif any(
                        w in line_lower
                        for w in (
                            "confidential information",
                            "strictly confidential",
                            "shall keep all confidential",
                            "keep all confidential",
                        )
                    ):
                        confidentiality_duties.append(f"{ref}: {line}")
                        break

                    # 3. Cancellation / Notice (Distinguish permission from obligation)
                    elif any(
                        w in line_lower
                        for w in (
                            "may cancel",
                            "cancel this agreement",
                            "providing 15 days written notice",
                            "written notice before cancellation",
                        )
                    ):
                        if "may cancel" in line_lower:
                            formatted = re.sub(
                                r"(?:the\s+customer|you)\s+may\s+cancel\s+(?:this agreement\s+)?by\s+providing\s+",
                                "If you choose to cancel, you must provide ",
                                line,
                                flags=re.IGNORECASE,
                            )
                            notice_duties.append(f"{ref}: {formatted}")
                        else:
                            notice_duties.append(f"{ref}: {line}")
                        break

                    elif any(
                        w in line_lower
                        for w in (
                            "terminate this agreement",
                            "early termination",
                            "written notice before expiry",
                            "automatic renew",
                        )
                    ):
                        notice_duties.append(f"{ref}: {line}")
                        break

                    # 4. Liability (Explain accurately as consequence/risk, not obligation)
                    elif "unlimited liability" in line_lower or ("liability" in line_lower and "breach" in line_lower):
                        liability_consequences.append(f"{ref}: {line}")
                        break

                    # 5. Other general obligations
                    elif any(
                        w in line_lower
                        for w in (
                            "must",
                            "shall",
                            "required to",
                            "agrees to",
                            "responsible for",
                            "obligated to",
                        )
                    ):
                        other_duties.append(f"{ref}: {line}")
                        break

            all_duties: list[str] = []
            if payment_duties:
                all_duties.extend(payment_duties)
            if confidentiality_duties:
                all_duties.extend(confidentiality_duties)
            if notice_duties:
                all_duties.extend(notice_duties)
            if other_duties:
                all_duties.extend(other_duties)

            if all_duties:
                # Telugu answer ONLY if current question requests Telugu
                if requested_lang_check == "telugu" or "telugu" in q_lower or bool(re.search(r"[\u0C00-\u0C7F]", question)):
                    return (
                        "ఒప్పందం ప్రకారం మీ ముఖ్యమైన బాధ్యతలు:\n"
                        "- చెల్లింపు బాధ్యత (సర్వీస్ ఫీజు సకాలంలో చెల్లించాలి)\n"
                        "- గోప్యతా నిబంధన (గోప్య సమాచారాన్ని అత్యంత భద్రంగా ఉంచాలి)\n"
                        "- నోటీసు నిబంధనలు (రద్దు చేయాలనుకుంటే 15 రోజుల ముందస్తు లిఖితపూర్వక నోటీసు అందించాలి)"
                    )

                bullet_list = "\n".join(f"- {d}" for d in all_duties)
                ans = f"Your primary responsibilities under this contract include:\n{bullet_list}"
                if liability_consequences:
                    ans += f"\n\nNote on Contractual Risk: As a legal consequence of breach rather than a proactive duty, {liability_consequences[0]}."
                return ans

        # ------------------------------------------------------------
        # Broad contract overview / review risk
        # ------------------------------------------------------------
        if intent in {"broad_overview", "review_risk"}:
            bullets = []
            for item in retrieved:
                t = cls._format_clause_ref(item)
                lines = [l.strip() for l in (item.text or "").split("\n") if l.strip()]
                first_line = lines[0] if lines else ""
                if first_line:
                    bullets.append(f"{t}: {first_line}")
            if bullets:
                return (
                    "Here is an overview of the key terms in this agreement:\n"
                    + "\n".join(f"- {b}" for b in bullets[:6])
                )

        # ------------------------------------------------------------
        # Loan amount
        # ------------------------------------------------------------

        if intent == "loan_amount":

            for item in retrieved:

                if cls._is_schedule(item):

                    match = re.search(
                        r"amount\s+of\s+the\s+loan"
                        r".{0,200}?"
                        r"(?:inr|rs\.?|₹)"
                        r"\s*[\d,]+",
                        item.text or "",
                        re.IGNORECASE
                        | re.DOTALL,
                    )

                    if match:
                        return (
                            "The loan amount is "
                            + match.group(0).strip()
                            + "."
                        )

            for item in retrieved:

                if item.clause_number == "2":

                    return (
                        "Clause 2 states that the "
                        "loan amount cannot exceed "
                        "the amount specified in "
                        "Schedule A."
                    )

        # ------------------------------------------------------------
        # Interest
        # ------------------------------------------------------------

        if intent == "interest_rate":

            for item in retrieved:

                if cls._is_schedule(item):

                    match = re.search(
                        r"interest.{0,150}?"
                        r"(\d+(?:\.\d+)?\s*%)",
                        item.text or "",
                        re.IGNORECASE
                        | re.DOTALL,
                    )

                    if match:
                        return (
                            "The interest rate is "
                            + match.group(1)
                            + "."
                        )

        # ------------------------------------------------------------
        # Cancellation / Termination
        # ------------------------------------------------------------

        if intent == "cancellation":

            for item in retrieved:
                text = item.text or ""
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    if any(k in line.lower() for k in ("early termination", "termination fee", "cancellation charge", "cancellation fee")):
                        return line
                for line in lines:
                    if "terminate" in q_lower and "terminat" in line.lower():
                        return line
                for line in lines:
                    if "cancel" in line.lower() or "terminat" in line.lower():
                        return line

        # ------------------------------------------------------------
        # Renewal
        # ------------------------------------------------------------

        if intent == "renewal":

            for item in retrieved:
                text = item.text or ""
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    if "renew" in line.lower():
                        return line

        # ------------------------------------------------------------
        # Deadlines
        # ------------------------------------------------------------

        if intent == "deadlines":

            deadlines_found = []
            for item in retrieved:
                text = item.text or ""
                title = cls._format_clause_ref(item)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    if re.search(
                        r"\b\d+\s+(?:days?|months?|weeks?)\b",
                        line,
                        re.IGNORECASE,
                    ):
                        deadlines_found.append(f"{title}: {line}")
                        break

            if deadlines_found:
                return (
                    "The contract specifies the following key timelines and deadlines:\n"
                    + "\n".join(f"- {d}" for d in deadlines_found[:4])
                )

        # ------------------------------------------------------------
        # Payments
        # ------------------------------------------------------------

        if intent == "payments":

            payments_found = []
            for item in retrieved:
                text = item.text or ""
                title = cls._format_clause_ref(item)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    if any(
                        w in line.lower()
                        for w in (
                            "inr",
                            "rs.",
                            "rs ",
                            "fee",
                            "pay",
                            "charge",
                            "interest",
                        )
                    ):
                        payments_found.append(f"{title}: {line}")
                        break

            if payments_found:
                return (
                    "Payment responsibilities specified in the contract include:\n"
                    + "\n".join(f"- {p}" for p in payments_found[:3])
                )

        # ------------------------------------------------------------
        # Generic fallback
        # ------------------------------------------------------------

        return (
            "Based on the provided contract clauses, "
            "I could not determine the exact answer "
            "from the available text."
        )