import re
from dataclasses import dataclass

from app.schemas.clause import Clause


@dataclass(frozen=True)
class RetrievedClause:
    clause_id: str
    clause_number: str | None
    title: str | None
    text: str
    score: float


class RetrievalService:

    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were",
        "be", "been", "being", "to", "of", "in", "on",
        "at", "for", "and", "or", "with", "this", "that",
        "what", "when", "where", "who", "which", "how",
        "does", "do", "did", "can", "could", "would",
        "should", "will", "shall", "may", "might", "must",
        "upon", "agreement", "contract", "within", "from",
        "by", "as", "it", "its", "their", "them", "they",
        "he", "she", "his", "her", "my", "your", "our",
        "me", "you", "i", "there", "here", "about", "into",
        "after", "before", "during", "than", "then", "if",
        "customer", "party", "parties", "person", "people",
        "provider", "service", "services", "information",
        "happens", "happen", "long", "have",
        "get", "give",
        "page", "website", "webpage", "document", "portal", "site",
    }

    BOILERPLATE_PATTERNS = [
        # Skip links
        r"\bskip\s+to\s+(?:main\s+)?(?:content|navigation|search|menu|footer)\b",
        # Navigation / Menus
        r"^\s*(?:main\s+)?menu\s*$",
        r"^\s*toggle\s+navigation\s*$",
        r"^\s*site\s+navigation\s*$",
        r"^\s*navigation\s*$",
        r"^\s*nav(?:igation)?\s+menu\s*$",
        # Accessibility boilerplate
        r"^\s*accessibility\s+(?:statement|assistance|notice|options|support|tools|help)\b",
        r"^\s*for\s+accessibility\s+(?:support|assistance)\b",
        r"^\s*screen\s+reader\b",
        # Footer / Copyright
        r"^\s*(?:copyright\s+©?|©)\s*\d{4}",
        r"^\s*all\s+rights\s+reserved\.?\s*$",
        r"^\s*back\s+to\s+top\s*$",
        # Cookie banners
        r"\b(?:we\s+use\s+cookies|this\s+(?:website|site)\s+uses\s+cookies|accept\s+(?:all\s+)?cookies|cookie\s+preferences|manage\s+cookies)\b",
    ]

    @classmethod
    def _is_navigation_or_boilerplate_query(cls, question: str) -> bool:
        q = question.lower()
        return bool(
            re.search(
                r"\b(?:navigation|navigate|menu|skip|accessibility|screen\s+reader|cookie|cookies|footer|header|copyright|breadcrumb|breadcrumbs|privacy|disclaimer|sitemap)\b",
                q,
            )
        )

    @classmethod
    def _is_boilerplate_or_navigation(cls, clause: Clause) -> bool:
        title = (clause.title or "").strip().lower()
        text = (clause.text or "").strip().lower()

        # Check skip links (always boilerplate)
        if re.search(r"\bskip\s+to\s+(?:main\s+)?(?:content|navigation|search|menu|footer)\b", text):
            return True

        # Check explicit patterns in text or title
        for pattern in cls.BOILERPLATE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE) or (title and re.search(pattern, title, re.IGNORECASE)):
                if clause.clause_number and len(text) > 200 and not re.search(r"\bskip\s+to\b", text):
                    continue
                return True

        # Short link sequences: e.g. "Home / Services / Contracting" or "Home | Opportunities | Data Bank | Help"
        if len(text) < 160:
            if re.search(r"^(?:home|menu|navigation)\b", text) and any(sep in text for sep in ("/", "|", ">", "•", "·", "»")):
                return True
            if re.search(r"^(?:privacy\s+policy|terms\s+of\s+(?:use|service)|contact\s+us|site\s+map)\s*[|/•·»]\s*", text):
                return True

        return False

    @classmethod
    def _is_substantive(cls, clause: Clause) -> bool:
        text = (clause.text or "").strip()
        if not text or len(text) < 20:
            return False
        return not cls._is_boilerplate_or_navigation(clause)

    IRREGULAR_WORDS = {
        "paid": "pay",
        "pays": "pay",
        "paying": "pay",
        "fees": "fee",
        "charges": "charge",
        "charged": "charge",
        "charging": "charge",
        "payments": "payment",
        "terminated": "terminate",
        "terminates": "terminate",
        "terminating": "terminate",
        "cancelled": "cancel",
        "canceled": "cancel",
        "cancels": "cancel",
        "cancelling": "cancel",
        "renewed": "renew",
        "renews": "renew",
        "renewing": "renew",
        "received": "receive",
        "receives": "receive",
        "receiving": "receive",
        "provided": "provide",
        "provides": "provide",
        "providing": "provide",
        "shared": "share",
        "shares": "share",
        "sharing": "share",
        "losses": "loss",
        "days": "day",
        "months": "month",
        "years": "year",
        "notices": "notice",
        "parties": "party",
        "services": "service",
        "invoices": "invoice",
        "percentages": "percentage",
        "bounced": "bounce",
        "bounces": "bounce",
        "bouncing": "bounce",
        "defaulted": "default",
        "defaults": "default",
        "defaulting": "default",
        "repaid": "repay",
        "repays": "repay",
        "repaying": "repay",
        "recalled": "recall",
        "recalls": "recall",
        "recalling": "recall",
        "failed": "fail",
        "fails": "fail",
        "failing": "fail",
        "preclosed": "preclose",
        "preclosing": "preclose",
        "obligations": "obligation",
        "obligated": "obligation",
        "responsibilities": "responsibility",
        "responsible": "responsibility",
        "duties": "duty",
        "requirements": "requirement",
        "required": "require",
        "requires": "require",
        "deadlines": "deadline",
        "timelines": "timeline",
        "timeframes": "timeframe",
        "liabilities": "liability",
        "liable": "liability",
        "penalties": "penalty",
    }

    # ============================================================
    # MAIN
    # ============================================================

    @classmethod
    def retrieve(
        cls,
        question: str,
        clauses: list[Clause],
        top_k: int = 5,
    ) -> list[RetrievedClause]:

        if not question or not question.strip():
            return []

        question = question.strip()
        intent = cls._detect_intent(question)
        question_tokens = cls._tokenize(question)

        if not question_tokens and not intent:
            return []

        # Identify substantive clauses and their sequential order
        substantive_clauses = [
            c for c in clauses
            if cls._is_substantive(c)
        ]
        substantive_order = {
            c.clause_id: idx
            for idx, c in enumerate(substantive_clauses)
        }

        results = []

        for clause in clauses:

            text = (
                f"{clause.title or ''} "
                f"{clause.text or ''}"
            )

            clause_tokens = cls._tokenize(text)

            if not clause_tokens:
                continue

            overlap = (
                question_tokens
                & clause_tokens
            )

            score = cls._calculate_score(
                question=question,
                question_tokens=question_tokens,
                clause_tokens=clause_tokens,
                overlap=overlap,
                clause=clause,
                intent=intent,
                substantive_rank=substantive_order.get(clause.clause_id),
            )

            if score <= 0:
                continue

            results.append(
                RetrievedClause(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    title=clause.title,
                    text=clause.text,
                    score=round(score, 4),
                )
            )

        results.sort(
            key=lambda item: (
                item.score,
                cls._clause_number_sort_key(
                    item.clause_number
                ),
            ),
            reverse=True,
        )

        if intent in {"broad_overview", "review_risk"}:
            category_buckets: dict[str, list[RetrievedClause]] = {
                "payment": [],
                "termination": [],
                "renewal": [],
                "liability": [],
                "confidentiality": [],
                "penalties_disputes": [],
                "other": [],
            }
            for item in results:
                matching = next((c for c in clauses if c.clause_id == item.clause_id), None)
                c_type = (
                    getattr(matching, "clause_type", None)
                    or getattr(matching, "type", None)
                    or ""
                ).upper() if matching else ""
                c_title = (matching.title or "").lower() if matching else ""
                c_category = (getattr(matching, "category", None) or "").lower() if matching else ""

                if (
                    c_type in {"PAYMENT", "FEES"}
                    or c_category in {"payment", "fees"}
                    or "payment" in c_title
                    or "fee" in c_title
                ):
                    category_buckets["payment"].append(item)
                elif (
                    c_type in {"TERMINATION", "CANCELLATION", "NOTICES"}
                    or c_category in {"termination", "cancellation", "notices"}
                    or "terminat" in c_title
                    or "cancel" in c_title
                ):
                    category_buckets["termination"].append(item)
                elif (
                    c_type in {"RENEWAL", "TERM"}
                    or c_category in {"renewal", "term"}
                    or "renew" in c_title
                ):
                    category_buckets["renewal"].append(item)
                elif (
                    c_type in {"LIABILITY", "INDEMNITY"}
                    or c_category in {"liability", "indemnity"}
                    or "liabilit" in c_title
                    or "indemn" in c_title
                    or "damages" in c_title
                ):
                    category_buckets["liability"].append(item)
                elif (
                    c_type in {"CONFIDENTIALITY", "DATA_PROTECTION", "PRIVACY"}
                    or c_category in {"confidentiality", "data_protection", "privacy"}
                    or "confident" in c_title
                ):
                    category_buckets["confidentiality"].append(item)
                elif (
                    c_type in {"PENALTY", "DISPUTE"}
                    or c_category in {"penalty", "dispute"}
                    or "penalty" in c_title
                    or "dispute" in c_title
                ):
                    category_buckets["penalties_disputes"].append(item)
                else:
                    category_buckets["other"].append(item)

            balanced: list[RetrievedClause] = []
            used_ids: set[str] = set()

            # First pass: pick top representative from each distinct category
            for cat in ["payment", "termination", "renewal", "liability", "confidentiality", "penalties_disputes", "other"]:
                for item in category_buckets[cat]:
                    if item.clause_id not in used_ids:
                        balanced.append(item)
                        used_ids.add(item.clause_id)
                        break

            # Second pass: fill remaining up to top_k
            for item in results:
                if len(balanced) >= top_k:
                    break
                if item.clause_id not in used_ids:
                    balanced.append(item)
                    used_ids.add(item.clause_id)

            return balanced[:top_k]

        return results[:top_k]

    # ============================================================
    # INTENT
    # ============================================================

    @staticmethod
    def _detect_intent(question: str) -> str | None:

        q = question.lower()

        # Cancellation and termination
        if (
            "cancellation charge" in q
            or "cancellation fee" in q
            or "cancel this agreement" in q
            or "cancel the agreement" in q
            or "cancel the contract" in q
            or "cancellation" in q
            or "can i cancel" in q
            or "how to cancel" in q
            or "terminate" in q
            or "termination" in q
            or "end the agreement" in q
            or "end this contract" in q
        ):
            return "cancellation"

        # Most important clause (singular)
        if (
            re.search(r"\bmost\s+important\s+clause\b", q)
            or re.search(r"\bmost\s+critical\s+clause\b", q)
            or re.search(r"\bmost\s+significant\s+clause\b", q)
            or re.search(r"\bwhich\s+clause\s+is\s+(?:the\s+)?most\s+important\b", q)
            or re.search(r"\bwhat\s+is\s+the\s+most\s+important\s+clause\b", q)
            or re.search(r"\bexplain\s+(?:the\s+)?most\s+important\s+clause\b", q)
        ):
            return "most_important_clause"

        # Main purpose / page or document overview
        if (
            re.search(r"\b(?:main\s+)?purpose\b", q)
            or re.search(r"\bwhat\s+is\s+(?:this\s+)?(?:page|website|site|document|portal)\s+about\b", q)
            or re.search(r"\bwhat\s+is\s+this\s+about\b", q)
            or re.search(r"\bwhat\s+does\s+this\s+(?:page|website|site|document|portal)\s+(?:do|cover|provide|say)\b", q)
            or re.search(r"\b(?:overview|summary)\s+of\s+(?:this\s+)?(?:page|website|site|portal)\b", q)
            or re.search(r"\b(?:page|website|site|portal)\s+(?:overview|summary)\b", q)
            or re.search(r"\bexplain\s+(?:the\s+)?(?:purpose|overview)\s+of\s+(?:this\s+)?(?:page|website|site|document|contract|agreement|portal)\b", q)
            or re.search(r"\bexplain\s+what\s+this\s+(?:page|website|site|document|contract|agreement|portal)\s+is\s+about\b", q)
            or re.search(r"\babout\s+this\s+(?:page|website|site|portal)\b", q)
            or re.search(r"(?:ఉద్దేశం|సారాంశం)", q)
        ):
            return "main_purpose"

        # Broad contract overview and important terms
        if (
            "important terms" in q
            or "important parts" in q
            or "important clauses" in q
            or "key terms" in q
            or "key provisions" in q
            or "main terms" in q
            or "main points" in q
            or "overview of this contract" in q
            or "overview of this agreement" in q
            or "overview of the contract" in q
            or "overview of the agreement" in q
            or "give me an overview" in q
            or "contract overview" in q
            or "summarize the important" in q
            or "summarize this contract" in q
            or "summarize this agreement" in q
            or "summarize the contract" in q
            or "summarize the agreement" in q
            or "what should i know before signing" in q
            or "what should i know" in q
            or "what should i pay attention to" in q
            or "what to pay attention to" in q
            or "main risks" in q
            or "what are the risks" in q
            or "explain this contract" in q
            or "most important" in q
            or "review before signing" in q
            or "before signing" in q
            or "should i review" in q
            or "unusual" in q
            or "risky" in q
            or "most risk" in q
            or "carry the most risk" in q
            or "carries the most risk" in q
            or "high risk" in q
            or "risk signals" in q
            or "look out for" in q
            or "watch out for" in q
        ):
            return "broad_overview"

        # Renewal
        if (
            "when does the agreement renew" in q
            or "when does the contract renew" in q
            or "automatic renewal" in q
            or "auto renew" in q
            or "renewal" in q
            or "renew" in q
        ):
            return "renewal"

        # Broad obligations and responsibilities
        if (
            "obligation" in q
            or "obligations" in q
            or "responsibility" in q
            or "responsibilities" in q
            or "responsible for" in q
            or "what do i have to do" in q
            or "what do i need to do" in q
            or "what must i do" in q
            or "what am i required to do" in q
            or "what am i obligated to do" in q
            or "what am i supposed to do" in q
            or "what responsibilities do i have" in q
            or "what are my responsibilities" in q
            or "what must i pay or provide" in q
            or "what must i pay" in q
            or "what must i provide" in q
            or "what do i have to pay or provide" in q
            or "my duties" in q
            or "my responsibilities" in q
            or "main duties" in q
            or "biggest obligations" in q
            or "customer duties" in q
            or "customer obligations" in q
            or "customer responsibilities" in q
            or "customer's responsibilities" in q
            or "customer's obligations" in q
            or "what are my liabilities" in q
            or "what am i liable for" in q
            or "what is the customer responsible for" in q
            or "what is the customer required to do" in q
            or "what does the customer have to do" in q
            or "what must the customer do" in q
        ):
            return "obligations"

        # Deadlines and notice periods
        if (
            "deadline" in q
            or "deadlines" in q
            or "timeline" in q
            or "timelines" in q
            or "timeframe" in q
            or "timeframes" in q
            or "time limit" in q
            or "time limits" in q
            or "notice period" in q
            or "notice periods" in q
            or "how many days" in q
            or "by when" in q
        ):
            return "deadlines"

        # Payments and financial obligations
        if (
            "what payments" in q
            or "payment obligation" in q
            or "payment obligations" in q
            or "financial obligation" in q
            or "financial obligations" in q
            or "financial liability" in q
            or "financial liabilities" in q
            or "how much do i pay" in q
            or "how much will i pay" in q
            or "what do i have to pay" in q
            or "need to pay" in q
            or "have to pay" in q
            or "pay anything" in q
            or "pay any" in q
            or "pay something" in q
            or "pay money" in q
            or "do i pay" in q
            or "do u pay" in q
            or "do you pay" in q
            or "do i owe" in q
            or "do u owe" in q
            or "do you owe" in q
            or "owe anything" in q
            or "service fee" in q
            or "payment terms" in q
            or "penalties" in q
            or "penalty" in q
            or "reprocurement" in q
            or "reimbursement" in q
            or "damages" in q
        ):
            return "payments"

        # Loan-specific intents (preserve existing behaviors)
        if (
            "loan amount" in q
            or "amount of loan" in q
            or "amount of the loan" in q
            or "principal amount" in q
            or "how much is the loan" in q
            or "how much loan" in q
        ):
            return "loan_amount"

        if (
            "interest rate" in q
            or "rate of interest" in q
        ):
            return "interest_rate"

        if (
            "loan tenure" in q
            or "tenure of loan" in q
            or "tenure of the loan" in q
            or "loan period" in q
            or "repayment period" in q
            or "how long is the loan" in q
        ):
            return "tenure"

        if (
            "fees" in q
            or "fee" in q
            or "charges" in q
            or "charge" in q
        ):
            return "fees"

        if (
            "pre-close" in q
            or "preclose" in q
            or "pre closure" in q
            or "preclosure" in q
            or "prepayment" in q
        ):
            return "preclosure"

        if (
            "bounce" in q
            or "bounced" in q
            or "payment bounce" in q
        ):
            return "bounce"

        if (
            "fail to repay" in q
            or "failure to repay" in q
            or "default" in q
            or "overdue" in q
        ):
            return "default"

        if (
            "repay" in q
            or "repayment" in q
        ):
            return "repayment"

        return None

    # ============================================================
    # SCHEDULE DETECTION
    # ============================================================

    @staticmethod
    def _is_schedule(clause: Clause) -> bool:

        title = (
            clause.title or ""
        ).strip().lower()

        if title.startswith("schedule"):
            return True

        if title.startswith("annexure"):
            return True

        if title.startswith("appendix"):
            return True

        if title.startswith("exhibit"):
            return True

        return False

    # ============================================================
    # SCHEDULE FIELD MATCH
    # ============================================================

    @staticmethod
    def _schedule_contains(
        clause: Clause,
        intent: str,
    ) -> bool:

        text = (
            f"{clause.title or ''} "
            f"{clause.text or ''}"
        ).lower()

        if intent == "loan_amount":
            return bool(
                re.search(
                    r"amount\s+of\s+the\s+loan",
                    text,
                )
                or re.search(
                    r"loan\s+amount",
                    text,
                )
                or re.search(
                    r"amount\s*\(\s*inr",
                    text,
                )
                or re.search(
                    r"sanctioned\s+amount",
                    text,
                )
            )

        if intent == "interest_rate":
            return (
                "interest" in text
                or "rate of interest" in text
                or "interest rate" in text
            )

        if intent == "tenure":
            return (
                "tenure" in text
                or "loan period" in text
                or "repayment period" in text
                or "periodicity" in text
                or "number of" in text
            )

        if intent == "fees":
            return (
                "fees" in text
                or "fee" in text
                or "charges" in text
                or "charge" in text
            )

        return False

    # ============================================================
    # SCORE
    # ============================================================

    @classmethod
    def _calculate_score(
        cls,
        question: str,
        question_tokens: set[str],
        clause_tokens: set[str],
        overlap: set[str],
        clause: Clause,
        intent: str | None,
        substantive_rank: int | None = None,
    ) -> float:

        # Down-rank boilerplate / navigation text unless the question explicitly asks about navigation / boilerplate
        is_boilerplate = cls._is_boilerplate_or_navigation(clause)
        is_nav_query = cls._is_navigation_or_boilerplate_query(question)

        if is_boilerplate and not is_nav_query:
            if intent or not overlap:
                return 0.0
            return min((len(overlap) / max(len(question_tokens), 1)) * 0.05, 0.02)

        text = (
            f"{clause.title or ''} "
            f"{clause.text or ''}"
        ).lower()

        is_schedule = cls._is_schedule(
            clause
        )

        clause_match = re.search(
            r"\b(?:clause|section|article)\s*([0-9]+[a-zA-Z]?)\b",
            question,
            re.IGNORECASE,
        )
        if clause_match:
            target_num = clause_match.group(1).lower().strip()
            actual_num = (clause.clause_number or "").lower().strip()
            title_text = (clause.title or "").lower()
            if (
                actual_num == target_num
                or f"clause {target_num}" in title_text
                or f"section {target_num}" in title_text
            ):
                return 0.98

        # ========================================================
        # INTENT QUESTIONS
        # ========================================================

        if intent:

            # ----------------------------------------------------
            # LOAN AMOUNT
            # ----------------------------------------------------

            if intent == "loan_amount":

                if is_schedule:
                    if cls._schedule_contains(
                        clause,
                        intent,
                    ):
                        # Schedule is important evidence,
                        # but Clause 2 should remain the primary
                        # contractual reference.
                        return 0.92

                    return 0.05

                if clause.clause_number == "2":
                    return 0.98

                if (
                    "loan amount" in text
                    or "amount of the loan" in text
                    or "amount set out" in text
                ):
                    return 0.70

                if (
                    "loan" in text
                    and "amount" in text
                ):
                    return 0.55

                if overlap:
                    return 0.25

                return 0.0

            # ----------------------------------------------------
            # INTEREST RATE
            # ----------------------------------------------------

            if intent == "interest_rate":

                if is_schedule:
                    if cls._schedule_contains(
                        clause,
                        intent,
                    ):
                        return 0.92

                    return 0.05

                if clause.clause_number == "3":
                    return 0.98

                if (
                    "interest rate" in text
                    or "rate of interest" in text
                ):
                    return 0.70

                if "interest" in text:
                    return 0.40

                return 0.0

            # ----------------------------------------------------
            # TENURE
            # ----------------------------------------------------

            if intent == "tenure":

                if is_schedule:
                    if cls._schedule_contains(
                        clause,
                        intent,
                    ):
                        return 0.92

                    return 0.05

                if clause.clause_number == "3":
                    return 0.80

                if "tenure" in text:
                    return 0.65

                if "loan period" in text:
                    return 0.60

                if "repayment period" in text:
                    return 0.60

                if overlap:
                    return 0.20

                return 0.0

            # ----------------------------------------------------
            # FEES
            # ----------------------------------------------------

            if intent == "fees":

                if is_schedule:
                    if cls._schedule_contains(
                        clause,
                        intent,
                    ):
                        return 0.92

                    return 0.05

                if (
                    "fees / charges" in text
                    or "fees/charges" in text
                ):
                    return 0.90

                if (
                    "fee" in text
                    or "charge" in text
                ):
                    return 0.50

                if overlap:
                    return 0.20

                return 0.0

            # ----------------------------------------------------
            # PRE-CLOSURE
            # ----------------------------------------------------

            if intent == "preclosure":

                if (
                    "pre-close" in text
                    or "pre -close" in text
                    or "preclosure" in text
                    or "prepayment" in text
                ):
                    return 0.95

                if is_schedule:
                    return 0.85

                if clause.clause_number == "3":
                    return 0.65

                if overlap:
                    return 0.20

                return 0.0

            # ----------------------------------------------------
            # PAYMENT BOUNCE
            # ----------------------------------------------------

            if intent == "bounce":

                if clause.clause_number == "3":

                    if (
                        "bounce" in text
                        or "bounced" in text
                        or "insufficient funds"
                        in text
                    ):
                        return 0.98

                if (
                    "bounce" in text
                    or "bounced" in text
                    or "insufficient funds"
                    in text
                ):
                    return 0.70

                if is_schedule:
                    return 0.40

                return 0.0

            # ----------------------------------------------------
            # DEFAULT
            # ----------------------------------------------------

            if intent == "default":

                score = 0.0

                if "default" in text:
                    score += 0.35

                if "failure" in text:
                    score += 0.20

                if "recall" in text:
                    score += 0.20

                if "recover" in text:
                    score += 0.15

                if "overdue" in text:
                    score += 0.20

                if "repayment" in text:
                    score += 0.10

                if clause.clause_number == "5":
                    score += 0.15

                if clause.clause_number == "16":
                    score += 0.20

                return min(
                    score,
                    0.95,
                )

            # ----------------------------------------------------
            # REPAYMENT
            # ----------------------------------------------------

            if intent == "repayment":

                if clause.clause_number == "3":
                    score = 0.75

                    if "due dates" in text:
                        score += 0.15

                    if "repayment" in text:
                        score += 0.10

                    return min(
                        score,
                        0.95,
                    )

                if is_schedule:
                    return 0.85

                if "repayment" in text:
                    return 0.45

                if "due date" in text:
                    return 0.50

                return 0.0

            # ----------------------------------------------------
            # CANCELLATION
            # ----------------------------------------------------

            if intent == "cancellation":

                if "cancellation charge" in text or "cancellation fee" in text:
                    return 0.98

                if any(k in text for k in ("cancel", "cancellation", "terminat")):
                    if any(
                        w in text
                        for w in (
                            "inr",
                            "rs",
                            "fee",
                            "charge",
                            "notice",
                            "days",
                            "refund",
                            "default",
                            "breach",
                            "other party",
                            "either party",
                            "immediate",
                        )
                    ):
                        return 0.92
                    return 0.85

                if overlap:
                    return 0.40

                return 0.0

            # ----------------------------------------------------
            # MOST IMPORTANT CLAUSE (SINGULAR)
            # ----------------------------------------------------

            if intent == "most_important_clause":

                score = 0.0
                c_type = (
                    getattr(clause, "clause_type", None)
                    or getattr(clause, "type", None)
                    or ""
                ).upper()
                c_category = (getattr(clause, "category", None) or "").lower()
                title_lower = (clause.title or "").lower()
                text_lower = (clause.text or "").lower()

                # Unlimited liability or severe liability is top priority
                if "unlimited liability" in text_lower or "unlimited liability" in title_lower:
                    return 0.98

                if (
                    c_type in {"LIABILITY", "INDEMNITY"}
                    or c_category in {"liability", "indemnity"}
                    or "liabilit" in title_lower
                    or "indemn" in title_lower
                    or "liability" in text_lower
                ):
                    score += 0.85
                elif (
                    c_type in {"PAYMENT", "TERMINATION", "PENALTY"}
                    or c_category in {"payment", "termination", "penalty"}
                    or any(k in title_lower for k in ("payment", "fee", "charge", "terminat", "penalty", "cancellation"))
                ):
                    score += 0.70
                elif any(k in text_lower for k in ("pay", "fee", "charge", "terminat", "cancel", "renew")):
                    score += 0.50

                if re.search(r"\b(?:unlimited|liquidated damages|forfeit|material breach|sole discretion|lock-in)\b", text_lower):
                    score += 0.15

                if overlap:
                    score += 0.10

                if score >= 0.30:
                    return min(score, 0.96)

                return 0.40 if len(text_lower.strip()) > 30 else 0.0

            # ----------------------------------------------------
            # MAIN PURPOSE / WHAT IS THIS ABOUT / PAGE OVERVIEW
            # ----------------------------------------------------

            if intent == "main_purpose":

                score = 0.0
                title_lower = (clause.title or "").lower()
                text_lower = (clause.text or "").lower()

                # Explicit purpose / overview / introduction keywords
                if any(
                    k in title_lower or k in text_lower
                    for k in (
                        "purpose",
                        "objective",
                        "scope",
                        "about",
                        "overview",
                        "introduction",
                        "background",
                        "preamble",
                        "recitals",
                        "description",
                    )
                ):
                    score = max(score, 0.96)

                # Definitional introductory phrasing (e.g. "SAM.gov is the official...", "This portal provides...")
                if re.search(
                    r"\b(?:is\s+the\s+official|is\s+a\s+(?:website|portal|system|platform)|is\s+designed\s+to|provides\s+(?:users|access|information)|this\s+(?:page|website|site|portal)\s+(?:provides|helps|allows|is)|purpose\s+of\s+this|governs\s+the|entered\s+into\s+by\s+and\s+between)\b",
                    text_lower,
                ):
                    score = max(score, 0.94)

                # Prioritize early substantive introductory sections
                if substantive_rank is not None:
                    if substantive_rank == 0:
                        score = max(score, 0.92)
                    elif substantive_rank == 1:
                        score = max(score, 0.88)
                    elif substantive_rank == 2:
                        score = max(score, 0.84)
                    elif substantive_rank < 6:
                        score = max(score, 0.75 - substantive_rank * 0.03)

                # Title bonus
                if clause.title and not cls._is_boilerplate_or_navigation(clause):
                    score += 0.05

                # Overlap bonus
                if overlap:
                    score += min(0.10, len(overlap) * 0.04)

                if score >= 0.30:
                    return min(round(score, 4), 0.98)

                return 0.50 if len(text_lower.strip()) >= 50 else 0.0

            # ----------------------------------------------------
            # BROAD OVERVIEW / REVIEW BEFORE SIGNING / RISKS
            # ----------------------------------------------------

            if intent in {"broad_overview", "review_risk"}:

                score = 0.0
                c_type = (
                    getattr(clause, "clause_type", None)
                    or getattr(clause, "type", None)
                    or ""
                ).upper()
                c_category = (getattr(clause, "category", None) or "").lower()
                if (
                    c_type in {
                        "PAYMENT",
                        "TERMINATION",
                        "RENEWAL",
                        "LIABILITY",
                        "INDEMNITY",
                        "PENALTY",
                        "RESTRICTION",
                        "DISPUTE",
                        "COMPLIANCE",
                    }
                    or c_category in {
                        "payment",
                        "termination",
                        "renewal",
                        "liability",
                        "indemnity",
                        "penalty",
                        "restriction",
                        "dispute",
                        "compliance",
                    }
                ):
                    score += 0.60
                elif (
                    c_type in {"CONFIDENTIALITY", "DATA_PROTECTION", "NOTICES", "WARRANTY"}
                    or c_category in {"confidentiality", "data_protection", "notices", "warranty"}
                ):
                    score += 0.50

                title_lower = (clause.title or "").lower()
                if any(
                    k in title_lower
                    for k in (
                        "payment",
                        "fee",
                        "charge",
                        "liability",
                        "indemn",
                        "penalty",
                        "cancellation",
                        "terminat",
                        "renew",
                        "lock-in",
                        "exclusive",
                        "damages",
                        "remed",
                        "risk",
                        "confident",
                        "dispute",
                        "obligat",
                        "responsib",
                        "term",
                        "notice",
                    )
                ):
                    score += 0.25

                if re.search(
                    r"\b(?:unlimited\s+liability|indemnify|hold\s+harmless|penalty|liquidated\s+damages|sole\s+discretion|lock-in|non-compete|forfeit|automatically\s+renew|material\s+breach)\b",
                    text,
                ):
                    score += 0.30
                elif re.search(
                    r"\b(?:liable|liability|terminate|termination|breach|default|shall\s+pay|charge|fees|penalty|renew|notice|confidential)\b",
                    text,
                ):
                    score += 0.15

                if overlap:
                    score += 0.15

                if is_schedule:
                    score += 0.20

                if score >= 0.30:
                    return min(score, 0.96)

                return 0.50 if len(text.strip()) > 30 else 0.0

            # ----------------------------------------------------
            # RENEWAL
            # ----------------------------------------------------

            if intent == "renewal":

                if (
                    "automatically renew" in text
                    or "automatic renewal" in text
                ):
                    return 0.98

                if "renew" in text or "renewal" in text:
                    if any(
                        w in text
                        for w in (
                            "month",
                            "months",
                            "year",
                            "years",
                            "notice",
                            "expiry",
                            "period",
                        )
                    ):
                        return 0.92
                    return 0.85

                if overlap:
                    return 0.40

                return 0.0

            # ----------------------------------------------------
            # OBLIGATIONS & RESPONSIBILITIES
            # ----------------------------------------------------

            if intent == "obligations":

                score = 0.0
                c_type = (
                    getattr(clause, "clause_type", None)
                    or getattr(clause, "type", None)
                    or ""
                ).upper()
                c_category = (getattr(clause, "category", None) or "").lower()

                # Metadata bonus (if classified)
                if (
                    c_type in {
                        "PAYMENT",
                        "LIABILITY",
                        "CONFIDENTIALITY",
                        "INDEMNITY",
                        "COMPLIANCE",
                        "RESTRICTION",
                    }
                    or c_category in {
                        "payment",
                        "liability",
                        "confidentiality",
                        "indemnity",
                        "compliance",
                        "restriction",
                    }
                ):
                    score += 0.35
                elif (
                    c_type in {
                        "TERMINATION",
                        "NOTICES",
                        "DATA_PROTECTION",
                        "DISPUTE",
                    }
                    or c_category in {
                        "termination",
                        "notices",
                        "data_protection",
                        "dispute",
                    }
                ):
                    score += 0.25

                title_lower = (clause.title or "").lower()
                if any(
                    k in title_lower
                    for k in (
                        "payment",
                        "liability",
                        "confidential",
                        "indemn",
                        "obligat",
                        "duties",
                        "responsib",
                        "fee",
                        "charge",
                    )
                ):
                    score += 0.20
                elif any(
                    k in title_lower
                    for k in (
                        "terminat",
                        "cancel",
                        "notice",
                        "privac",
                        "data",
                    )
                ):
                    score += 0.15

                # Operative contractual language in clause text
                # 1. Explicit party-linked obligations and compulsion
                if (
                    re.search(
                        r"\b(?:customer|client|borrower|user|party|parties|you)\s+(?:must|shall|agrees?\s+to|agreed\s+to|undertakes?\s+to|is\s+required\s+to|are\s+required\s+to|has\s+to|have\s+to|will\s+pay|will\s+incur|will\s+be\s+liable|will\s+provide|is\s+responsible\s+for|are\s+responsible\s+for|responsible\s+for|obligated\s+to|can\s+(?:with\s+)?cancel|may\s+(?:with\s+)?cancel)\b",
                        text,
                    )
                    or re.search(
                        r"\brequires?\s+(?:the\s+)?(?:customer|client|borrower|user|party|you)\s+to\b",
                        text,
                    )
                ):
                    score += 0.45
                elif re.search(
                    r"\b(?:must\s+pay|shall\s+pay|will\s+pay|must\s+provide|shall\s+provide|will\s+provide|must\s+give|shall\s+give|must\s+notify|shall\s+notify|must\s+maintain|shall\s+maintain|must\s+keep|shall\s+keep|unlimited\s+liability|strictly\s+confidential|shall\s+indemnify|must\s+indemnify|hold\s+harmless|late\s+payments?\s+will\s+incur)\b",
                    text,
                ):
                    score += 0.40
                elif re.search(
                    r"\b(?:must|shall)\s+(?:pay|provide|give|deliver|notify|maintain|keep|submit|inform|reimburse|indemnify|ensure|comply|refrain|cease)\b",
                    text,
                ):
                    score += 0.35
                elif re.search(
                    r"\b(?:must|shall|is\s+required\s+to|are\s+required\s+to|required\s+to|agrees?\s+to|agreed\s+to|undertakes?\s+to|obligated\s+to|responsible\s+for|has\s+to|have\s+to|will\s+pay|will\s+incur|will\s+be\s+liable)\b",
                    text,
                ):
                    score += 0.20

                # 2. Notice and cancellation duties
                if re.search(
                    r"\b(?:(?:written|prior|return)?\s*notice|may\s+cancel\s+by|cancel\s+with\s+\d+\s+days|early\s+cancellation|cancellation\s+charge|cancellation\s+fee|must\s+provide\s+notice|must\s+give\s+notice|giving\s+notice|give\s+notice)\b",
                    text,
                ):
                    score += 0.25

                # 3. Payment, financial duties or charges
                if re.search(
                    r"\b(?:pay|payment|payments|fee|fees|charge|charges|interest|penalty|penalties|rupees|inr|rs\.?|rs\s|₹)\b",
                    text,
                ):
                    score += 0.20

                # 4. Confidentiality, liability, indemnity, restrictions
                if re.search(
                    r"\b(?:confidential|confidentiality|liable|liability|indemnify|indemnity|restricted|restriction|prohibited|comply|compliance)\b",
                    text,
                ):
                    score += 0.15

                # 5. Relevant party mentioned (Customer / client / borrower / user)
                if re.search(r"\b(?:customer|client|borrower|user|you|your|receiving\s+party)\b", text):
                    score += 0.10

                if overlap:
                    score += 0.15

                if score >= 0.25:
                    return min(round(score, 4), 0.96)

                return 0.0

            # ----------------------------------------------------
            # DEADLINES & TIMELINES
            # ----------------------------------------------------

            if intent == "deadlines":

                has_timeframe = bool(
                    re.search(
                        r"\b\d+\s+(?:days?|months?|weeks?|years?|hours?|business\s+days?)\b",
                        text,
                    )
                )
                has_notice = "notice" in text
                has_due = any(
                    k in text
                    for k in (
                        "within",
                        "prior to",
                        "before expiry",
                        "due date",
                        "deadline",
                        "timeline",
                    )
                )

                if has_timeframe and (has_notice or has_due):
                    return 0.94
                elif has_timeframe:
                    return 0.80
                elif has_notice or has_due:
                    return 0.60
                elif overlap:
                    return 0.30

                return 0.0

            # ----------------------------------------------------
            # PAYMENTS
            # ----------------------------------------------------

            if intent == "payments":

                score = 0.0
                c_type = (
                    getattr(clause, "clause_type", None)
                    or getattr(clause, "type", None)
                    or ""
                ).upper()
                c_category = (getattr(clause, "category", None) or "").lower()
                c_title = (clause.title or "").lower()
                if (
                    c_type in {"PAYMENT", "PENALTY", "INDEMNITY", "LIABILITY", "TERMINATION", "DEFAULT"}
                    or c_category in {"payment", "penalty", "indemnity", "liability", "termination", "default"}
                    or any(
                        k in c_title
                        for k in (
                            "payment",
                            "penalty",
                            "fee",
                            "cost",
                            "charge",
                            "damages",
                            "reimbursement",
                            "reprocurement",
                            "indemn",
                            "default",
                            "compensation",
                            "liability",
                        )
                    )
                ):
                    score += 0.50

                if any(
                    w in text
                    for w in (
                        "inr",
                        "rs.",
                        "rs ",
                        "₹",
                        "fee",
                        "charge",
                        "pay",
                        "interest",
                        "penalt",
                        "late fee",
                        "liquidated damages",
                        "reprocurement",
                        "reimbursement",
                        "damages",
                        "indemn",
                        "cost",
                        "costs",
                        "expense",
                        "expenses",
                        "default",
                        "liab",
                    )
                ):
                    score += 0.40

                if overlap:
                    score += 0.15

                if score >= 0.30:
                    return min(score, 0.96)

                return 0.0

        # ========================================================
        # GENERAL QUESTION
        # ========================================================

        if not overlap:
            return 0.0

        score = (
            len(overlap)
            / max(len(question_tokens), 1)
        ) * 0.60

        if clause.title:

            title_tokens = cls._tokenize(
                clause.title
            )

            title_overlap = (
                question_tokens
                & title_tokens
            )

            score += min(
                0.20,
                len(title_overlap) * 0.10,
            )

        # Schedule should not automatically dominate
        # normal clauses in general questions.
        if is_schedule:
            score *= 0.80

        # Down-rank boilerplate / navigation text for non-navigation queries
        if score > 0 and is_boilerplate and not is_nav_query:
            score = min(score * 0.05, 0.02)

        return min(
            score,
            0.90,
        )

    # ============================================================
    # TOKENIZE
    # ============================================================

    @classmethod
    def _tokenize(
        cls,
        text: str,
    ) -> set[str]:

        if not text:
            return set()

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        tokens = set()

        for word in words:

            if word in cls.STOP_WORDS:
                continue

            if len(word) <= 1:
                continue

            normalized = cls._normalize_word(
                word
            )

            if not normalized:
                continue

            if normalized in cls.STOP_WORDS:
                continue

            tokens.add(normalized)

        return tokens

    # ============================================================
    # NORMALIZE WORD
    # ============================================================

    @classmethod
    def _normalize_word(
        cls,
        word: str,
    ) -> str:

        word = word.lower().strip()

        if not word:
            return word

        if word in cls.IRREGULAR_WORDS:
            return cls.IRREGULAR_WORDS[word]

        if (
            word.endswith("ies")
            and len(word) > 4
        ):
            return word[:-3] + "y"

        if (
            word.endswith("ing")
            and len(word) > 5
        ):

            base = word[:-3]

            if base.endswith("at"):
                return base + "e"

            if base.endswith("v"):
                return base + "e"

            return base

        if (
            word.endswith("ed")
            and len(word) > 4
        ):

            base = word[:-2]

            if base.endswith("at"):
                return base + "e"

            if base.endswith("iv"):
                return base + "e"

            if base.endswith("in"):
                return base + "e"

            return base

        if (
            word.endswith("es")
            and len(word) > 4
        ):
            return word[:-2]

        if (
            word.endswith("s")
            and len(word) > 3
        ):
            return word[:-1]

        return word

    # ============================================================
    # SORTING
    # ============================================================

    @staticmethod
    def _clause_number_sort_key(
        clause_number: str | None,
    ):

        if not clause_number:
            return ()

        try:
            return tuple(
                int(part)
                for part in clause_number.split(".")
            )
        except ValueError:
            return (0,)