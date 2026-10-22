from __future__ import annotations

import re
from app.schemas.clause import Clause
from app.services.retrieval_service import RetrievedClause


class ClauseRetriever:
    """
    Unified Clause Retriever for Ask My T&C.
    Handles exact clause number lookup without lexical confusion (e.g. 7 vs 70),
    as well as multilingual semantic retrieval with cross-reference resolution.
    """

    INTENT_KEYWORDS: dict[str, set[str]] = {
        "payments": {
            "pay", "payment", "payments", "fee", "fees", "invoice", "invoices",
            "invoicing", "cost", "costs", "charge", "charges", "interest", "rate",
            "due", "amount", "monetary", "reimburse", "reimbursement", "price",
            "compensation", "remuneration", "sum", "currency", "inr", "usd", "dollar",
            "చెల్లింపు", "ఖర్చు", "ఫీజు", "ఇన్వాయిస్", "డబ్బులు", "भुगतान", "शुल्क",
        },
        "financial": {
            "pay", "payment", "payments", "fee", "fees", "invoice", "invoices",
            "invoicing", "cost", "costs", "charge", "charges", "interest", "rate",
            "due", "amount", "reimburse", "price", "compensation",
            "చెల్లింపు", "ఖర్చు", "ఫీజు", "भुगतान",
        },
        "obligations": {
            "obligation", "obligations", "shall", "must", "duty", "duties",
            "responsibility", "responsibilities", "required", "require", "agrees",
            "undertakes", "covenant", "covenants", "perform", "performance",
            "బాధ్యత", "చేయాల్సింది", "కర్తవ్యం", "दायित्व", "कर्तव्य",
        },
        "obligation": {
            "obligation", "obligations", "shall", "must", "duty", "duties",
            "responsibility", "responsibilities", "required", "require", "agrees",
            "undertakes", "covenant", "covenants", "perform", "performance",
            "బాధ్యత", "చేయాల్సింది", "కర్తవ్యం", "दायित्व", "कर्तव्य",
        },
        "deadlines": {
            "deadline", "deadlines", "timeline", "timelines", "within", "days",
            "months", "period", "notice", "schedule", "calendar", "effective",
            "commencement", "expiry", "expiration", "due", "time",
            "గడువు", "సమయం", "రోజులు", "నోటీసు", "समयसीमा", "अवधि", "नोटिस",
        },
        "deadline": {
            "deadline", "deadlines", "timeline", "timelines", "within", "days",
            "months", "period", "notice", "schedule", "calendar", "effective",
            "commencement", "expiry", "expiration", "due", "time",
            "గడువు", "సమయం", "రోజులు", "నోటీసు", "समयसीमा", "अवधि", "नोटिस",
        },
        "renewal": {
            "renew", "renewal", "renewing", "automatic", "automatically", "extend",
            "extension", "subsequent", "term", "continuation",
            "పునరుద్ధరణ", "పొడిగింపు", "ఆటోమేటిక్", "नवीनीकरण", "विस्तार",
        },
        "termination": {
            "terminate", "termination", "terminating", "cancel", "cancellation",
            "cancelling", "notice", "written notice", "default", "breach", "cure",
            "convenience", "cause", "end", "discontinue", "revoke",
            "రద్దు", "ముగింపు", "రద్దుచేయడం", "समाप्ति", "रद्द",
        },
        "liability": {
            "liable", "liability", "liabilities", "indemn", "indemnity", "indemnify",
            "hold harmless", "damage", "damages", "loss", "losses", "unlimited",
            "consequential", "limitation", "cap", "reprocurement",
            "బాధ్యత", "నష్టపరిహారం", "హాని", "उत्तरदायित्व", "क्षतिपूर्ति",
        },
        "responsibility": {
            "liable", "liability", "responsible", "responsibility", "indemnify",
            "hold harmless", "duty", "duties", "shall", "must",
            "ఎవరు బాధ్యులు", "బాధ్యత", "जिम्मेदार", "उत्तरदायी",
        },
        "penalties": {
            "penalty", "penalties", "late fee", "late charges", "interest", "delay",
            "liquidated damages", "forfeiture", "fine", "fines",
            "జరిమానా", "పెనాల్టీ", "నష్టం", "जुर्माना", "दंड",
        },
        "penalty": {
            "penalty", "penalties", "late fee", "late charges", "interest", "delay",
            "liquidated damages", "forfeiture", "fine", "fines",
            "జరిమానా", "పెనాల్టీ", "నష్టం", "जुर्माना", "दंड",
        },
        "risks": {
            "unlimited liability", "liability", "indemn", "indemnity", "penalty",
            "damages", "breach", "default", "reprocurement", "termination",
            "consequential damages", "non-compete", "exclusive", "dispute",
            "రిస్క్", "ప్రమాదం", "నష్టం", "जोखिम", "खतरा",
        },
        "risk": {
            "unlimited liability", "liability", "indemn", "indemnity", "penalty",
            "damages", "breach", "default", "reprocurement", "termination",
            "consequential damages", "non-compete", "exclusive", "dispute",
            "రిస్క్", "ప్రమాదం", "నష్టం", "जोखिम", "खतरा",
        },
    }

    BOILERPLATE_PATTERNS: list[str] = [
        r"^table\s+of\s+contents",
        r"^skip\s+to\s+(?:main\s+)?content",
        r"^(?:header|footer|navigation|menu)\b",
        r"^page\s+\d+\s+of\s+\d+",
        r"^all\s+rights\s+reserved",
    ]

    STOP_WORDS: set[str] = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "to", "of", "in", "on", "at", "for", "and", "or", "with", "this", "that",
        "what", "when", "where", "who", "which", "how", "does", "do", "did",
        "can", "could", "would", "should", "will", "shall", "may", "might", "must",
        "upon", "agreement", "contract", "within", "from", "by", "as", "it", "its",
        "their", "them", "they", "he", "she", "his", "her", "my", "your", "our",
        "me", "you", "i", "there", "here", "about", "into", "after", "before",
    }

    @classmethod
    def is_boilerplate(cls, clause: Clause) -> bool:
        t = (clause.title or "").strip().lower()
        txt = (clause.text or "").strip().lower()
        for pat in cls.BOILERPLATE_PATTERNS:
            if re.search(pat, t) or (len(txt) < 80 and re.search(pat, txt)):
                return True
        return False

    @classmethod
    def exact_clause_retrieval(
        cls,
        target_number: str,
        clauses: list[Clause],
    ) -> list[RetrievedClause]:
        """
        High-precision exact clause matching.
        Ensures Clause 7 does NOT match Clause 70.
        Searches ONLY the current contract clauses provided.
        """
        try:
            target_int = int(str(target_number).strip())
        except (ValueError, TypeError):
            return []

        candidates: list[tuple[int, int, Clause]] = []

        for c in clauses:
            # 1. Check clause_number property
            num_str = getattr(c, "clause_number", None)
            c_num = None
            if num_str is not None:
                m_num = re.search(r"\b\d+\b", str(num_str).strip())
                if m_num:
                    c_num = int(m_num.group(0))

            # 2. Check text prefix (e.g. '7. LICENSES' or 'Clause 7:')
            t = (getattr(c, "text", "") or "").strip()
            m_t = re.match(r"^(?:clause|section|article|provision|item)?\s*(\d+)[.:\s]", t, re.IGNORECASE)
            text_num = int(m_t.group(1)) if m_t else None

            # 3. Check title prefix (e.g. '7. LICENSES')
            title = (getattr(c, "title", "") or "").strip()
            m_title = re.match(r"^(?:clause|section|article|provision|item)?\s*(\d+)[.:\s]", title, re.IGNORECASE)
            title_num = int(m_title.group(1)) if m_title else None

            # 4. Check clause_id (e.g. 'clause-7')
            cid = (getattr(c, "clause_id", "") or "").strip()
            m_cid = re.search(r"(?:clause|c)[-_](\d+)\b", cid, re.IGNORECASE)
            cid_num = int(m_cid.group(1)) if m_cid else None

            order_num = getattr(c, "order", None)
            order_int = int(order_num) if order_num is not None and str(order_num).isdigit() else None

            # Strict priority assignment (lowest score = highest priority match)
            if c_num == target_int and text_num == target_int:
                candidates.append((0, c.order or 0, c))
            elif text_num == target_int:
                candidates.append((1, c.order or 0, c))
            elif title_num == target_int:
                candidates.append((2, c.order or 0, c))
            elif c_num == target_int and cid_num == target_int:
                candidates.append((3, c.order or 0, c))
            elif c_num == target_int:
                candidates.append((4, c.order or 0, c))
            elif cid_num == target_int:
                candidates.append((5, c.order or 0, c))
            elif order_int == target_int:
                candidates.append((6, c.order or 0, c))

        if not candidates:
            return []

        # Sort by priority, then sequential order
        candidates.sort(key=lambda x: (x[0], x[1]))
        best_clause = candidates[0][2]

        return [
            RetrievedClause(
                clause_id=best_clause.clause_id,
                clause_number=str(target_int),
                title=best_clause.title or f"Clause {target_int}",
                text=best_clause.text or "",
                score=1.0,
            )
        ]

    @classmethod
    def semantic_retrieval(
        cls,
        query: str,
        clauses: list[Clause],
        fine_intent: str,
        top_k: int = 8,
    ) -> list[RetrievedClause]:
        """
        Retrieves top relevant clauses for topic and general queries.
        Includes schedule/cross-reference resolution.
        """
        if not query or not clauses:
            return []

        # Extract search tokens excluding stopwords
        all_tokens = [w.lower() for w in re.findall(r"\b[\w]{2,}\b", query)]
        q_tokens = {w for w in all_tokens if w not in cls.STOP_WORDS}
        # Roots (prefix 4+ chars) for flexible matching
        q_stems = {w[:5] for w in q_tokens if len(w) >= 4}

        intent_keywords = cls.INTENT_KEYWORDS.get(fine_intent, set())

        scored_clauses: list[tuple[float, Clause]] = []

        for c in clauses:
            if cls.is_boilerplate(c):
                continue

            text = f"{c.title or ''} {c.text or ''}".lower()
            if not text.strip():
                continue

            c_tokens = set(re.findall(r"\b[\w]{2,}\b", text))
            if not c_tokens:
                continue

            c_stems = {w[:5] for w in c_tokens if len(w) >= 4}
            score = 0.0

            # Title tokens
            title_text = (c.title or "").lower()
            title_tokens = set(re.findall(r"\b[\w]{2,}\b", title_text))

            # 1. Query token exact overlap in full text
            overlap = q_tokens & c_tokens
            if overlap:
                score += len(overlap) * 3.0

            # 1b. Query token overlap in TITLE (strong precision signal)
            title_overlap = q_tokens & title_tokens
            if title_overlap:
                score += len(title_overlap) * 12.0

            # 2. Query stem overlap (e.g. terminated -> terminate)
            stem_overlap = q_stems & c_stems
            if stem_overlap:
                score += len(stem_overlap) * 2.0

            # 3. Intent keyword boost
            intent_overlap = intent_keywords & c_tokens
            if intent_overlap:
                score += len(intent_overlap) * 2.5

            is_payment_q = bool(re.search(r"\b(?:pay\w*|fee\w*|invoic\w*|cost\w*|charg\w*)\b", query.lower()))
            is_term_q = bool(re.search(r"\b(?:terminat\w*|cancel\w*)\b", query.lower()))
            is_renew_q = bool(re.search(r"\b(?:renew\w*|auto-renew\w*)\b", query.lower()))
            is_breach_q = bool(re.search(r"\b(?:breach|default|violate|violation)\b", query.lower()))
            is_purpose_q = fine_intent in {"main_purpose", "purpose"} or bool(re.search(r"\b(?:main\s+purpose|purpose\s+of\s+this\s+page)\b", query.lower()))
            is_most_imp_q = fine_intent in {"most_important_clause"} or bool(re.search(r"\bmost\s+important\b", query.lower()))

            if is_breach_q or fine_intent in {"breach"}:
                if any(w in title_text for w in ["breach", "liability", "default", "remed"]):
                    score += 30.0
                if "breach" in text:
                    score += 25.0
                if "liability" in text:
                    score += 15.0


            if is_purpose_q:
                # The substantive page/contract intro is usually the first non-boilerplate clause
                if (c.order in {1, 2} or getattr(c, "clause_id", "") in {"clause-1", "clause-2"}) and not cls.is_boilerplate(c):
                    score += 35.0
                if any(w in text for w in ["official", "procurement", "purpose", "allows", "federal awards", "contracting", "compliance"]):
                    score += 20.0

            if is_most_imp_q:
                if "unlimited liability" in text or ("unlimited" in text and "liability" in text):
                    score += 55.0
                elif "liability" in text or "indemn" in text:
                    score += 35.0
                elif any(w in text for w in ["termination", "breach", "default", "penalty"]):
                    score += 20.0

            if "consultant" in query.lower() and "consultant" in text:
                score += 15.0

            if is_payment_q or fine_intent in {"payments", "financial", "payment"}:
                if any(w in title_text for w in ["pay", "fee", "invoice", "cost", "charge", "price"]):
                    score += 25.0
                elif any(w in text for w in ["pay", "fee", "invoice"]):
                    score += 12.0
                if re.search(r"\b(?:inr|\$|rs\.?|usd)\s*[\d,]+|\b[\d,]+\s*(?:dollars|rupees)\b", text):
                    score += 8.0
                if any(w in text for w in ["reprocurement", "consultant shall be responsible"]):
                    score += 10.0

            if is_term_q or fine_intent in {"termination", "terminate"}:
                if any(w in title_text for w in ["terminat", "cancel"]):
                    score += 25.0
                elif any(w in text for w in ["terminat", "cancel"]):
                    score += 12.0
                if "written notice" in text or "notice" in text:
                    score += 5.0
                if "120 days" in text and "consultant" in text:
                    score += 10.0

            if is_renew_q or fine_intent in {"renewal"}:
                if any(w in title_text for w in ["renew", "term"]):
                    score += 25.0
                elif "renew" in text:
                    score += 12.0

            if fine_intent in {"risks", "risk"}:
                if "unlimited liability" in text or "uncapped" in text:
                    score += 25.0
                elif "indemn" in text or "hold harmless" in text:
                    score += 15.0
                elif "reprocurement" in text or "default" in text:
                    score += 10.0
            elif fine_intent in {"penalties", "penalty"}:
                if "penalty" in text or "interest" in text or "late" in text or "damages" in text:
                    score += 12.0
            elif fine_intent in {"confidentiality"}:
                if "confidential" in text or "non-disclosure" in text or "proprietary" in text:
                    score += 15.0
            elif fine_intent in {"governing_law"}:
                if "governing law" in text or "laws of" in text or "jurisdiction" in text:
                    score += 15.0
            elif fine_intent in {"deadlines", "deadline"}:
                if "within" in text or "days" in text or "months" in text or "deadline" in text:
                    score += 8.0
            elif fine_intent in {"obligations", "obligation"}:
                if "shall" in text or "must" in text or "agrees to" in text or "required" in text:
                    score += 8.0
                if "confidential" in text:
                    score += 5.0

            # 5. Schedule boost if query asks about details or schedules
            if "schedule" in (c.title or "").lower() or "schedule" in text[:60]:
                if fine_intent in {"payments", "financial", "deadlines", "deadline", "obligations", "obligation"}:
                    score += 4.0

            if score > 0:
                scored_clauses.append((score, c))

        # 6. Fallback for contract-wide overview, summary, and advisory queries (e.g. "What should I know before signing?")
        is_broad_query = fine_intent in {"summary", "simplification", "main_purpose", "purpose"} or bool(
            re.search(
                r"\b(?:important\s+terms|key\s+terms|overview|summary|summarize|what\s+does\s+this\s+contract\s+say|explain\s+this\s+contract|explain\s+this\s+agreement|before\s+signing|what\s+should\s+i\s+know|main\s+purpose)\b",
                query.lower(),
            )
        )
        if len(scored_clauses) < 3 and clauses and is_broad_query:
            existing_cids = {
                str(getattr(c, "clause_id", None) or getattr(c, "id", None) or getattr(c, "order", ""))
                for _, c in scored_clauses
            }
            for c in clauses[:top_k]:
                cid_str = str(getattr(c, "clause_id", None) or getattr(c, "id", None) or getattr(c, "order", ""))
                if cid_str not in existing_cids and not cls.is_boilerplate(c):
                    scored_clauses.append((3.0, c))
                    existing_cids.add(cid_str)
                if len(scored_clauses) >= 3:
                    break

        # Sort by score descending
        scored_clauses.sort(key=lambda x: x[0], reverse=True)

        # Select top candidates
        top_items = scored_clauses[:top_k]

        # 5. Cross-reference linking: check if top items reference schedules or other clauses
        existing_ids = {
            str(getattr(c, "clause_id", None) or getattr(c, "id", None) or getattr(c, "order", ""))
            for _, c in top_items
        }
        linked_to_add: list[Clause] = []

        for _, item in top_items[:4]:
            t = (item.text or "")
            refs = re.findall(r"\b(?:Schedule|Exhibit|Annexure)\s+([A-Z0-9]+)\b", t, re.IGNORECASE)
            for ref in refs:
                for c in clauses:
                    c_id = str(getattr(c, "clause_id", None) or getattr(c, "id", None) or getattr(c, "order", ""))
                    if c_id not in existing_ids:
                        c_title = (c.title or "").lower()
                        c_text_start = (c.text or "")[:100].lower()
                        ref_lower = ref.lower()
                        if f"schedule {ref_lower}" in c_title or f"schedule {ref_lower}" in c_text_start:
                            linked_to_add.append(c)
                            existing_ids.add(c_id)

        results: list[RetrievedClause] = []
        for score, c in top_items:
            results.append(
                RetrievedClause(
                    clause_id=str(getattr(c, "clause_id", None) or getattr(c, "id", None) or c.clause_number or ""),
                    clause_number=c.clause_number,
                    title=c.title,
                    text=c.text or "",
                    score=round(min(score / 20.0, 1.0), 4),
                )
            )

        for c in linked_to_add:
            results.append(
                RetrievedClause(
                    clause_id=str(getattr(c, "clause_id", None) or getattr(c, "id", None) or c.clause_number or ""),
                    clause_number=c.clause_number,
                    title=c.title,
                    text=c.text or "",
                    score=0.85,
                )
            )

        return results
