from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.clause import Clause


@dataclass
class QuestionAnalysis:
    raw_question: str
    cleaned_question: str
    coarse_intent: str  # "contract", "general", "capability", "unrelated"
    fine_intent: str    # "explanation", "summary", "simplification", "translation", "obligation", "deadline", "financial", "risk", "rights", "responsibility", "termination", "renewal", "penalty", "exact_clause", "general_contract", "unrelated", "greeting", "capability"
    clause_number: str | None
    language: str
    is_follow_up: bool
    references_previous_answer: bool
    is_conversational: bool
    target_entity: str | None = None


class QuestionAnalyzer:
    """
    Unified Question Analyzer for Ask My T&C.
    Single source of truth for intent detection, clause extraction, language resolution,
    and multi-turn follow-up parsing.
    """

    KNOWN_LANGUAGES: dict[str, str] = {
        "telugu": "Telugu",
        "hindi": "Hindi",
        "tamil": "Tamil",
        "kannada": "Kannada",
        "malayalam": "Malayalam",
        "marathi": "Marathi",
        "bengali": "Bengali",
        "bangla": "Bengali",
        "gujarati": "Gujarati",
        "punjabi": "Punjabi",
        "urdu": "Urdu",
        "english": "English",
        "spanish": "Spanish",
        "french": "French",
        "german": "German",
    }

    SCRIPT_LANGUAGE_MAP: list[tuple[str, str]] = [
        (r"[\u0C00-\u0C7F]", "Telugu"),
        (r"[\u0900-\u097F]", "Hindi"),
        (r"[\u0B80-\u0BFF]", "Tamil"),
        (r"[\u0C80-\u0CFF]", "Kannada"),
        (r"[\u0D00-\u0D7F]", "Malayalam"),
        (r"[\u0980-\u09FF]", "Bengali"),
        (r"[\u0A80-\u0AFF]", "Gujarati"),
        (r"[\u0A00-\u0A7F]", "Punjabi"),
        (r"[\u0600-\u06FF]", "Urdu"),
    ]

    GREETINGS_OR_GENERAL: set[str] = {
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
        "good evening", "how are you", "how are you?", "how r u", "who are you",
        "who are you?", "who r u", "who r u?", "who am i", "do you know me",
        "do you know me?", "do u know me", "do u know me?", "thank you",
        "thanks", "thank u", "thx", "bye", "goodbye", "see you", "see ya",
        "namaste", "namaskaram", "dhanyavadalu", "shukriya", "okay", "ok", "got it",
        "yup", "yep", "yeah", "yea", "cool", "sure", "alright", "noted",
    }

    CAPABILITY_PATTERNS: list[str] = [
        r"\b(?:what\s+can\s+(?:you|u)\s+do|what\s+do\s+you\s+do)\b",
        r"\b(?:what\s+questions?\s+should\s+i\s+ask|what\s+can\s+i\s+ask|what\s+questions?\s+can\s+i\s+ask)\b",
        r"\b(?:how\s+does\s+this\s+work|how\s+do\s+(?:you|u)\s+work|how\s+do\s+(?:you|u)\s+analyze|how\s+do\s+i\s+use)\b",
        r"\b(?:what\s+ai\s+do\s+you\s+use|do\s+you\s+use\s+machine\s+learning|do\s+you\s+use\s+ml)\b",
        r"\b(?:is\s+this\s+gemini|are\s+you\s+gemini|is\s+it\s+gemini)\b",
        r"\b(?:what\s+gemini\s+(?:are\s+you|are\s+u\s+using|version|model)|which\s+(?:version\s+of\s+)?gemini)\b",
        r"\b(?:can\s+you\s+explain\s+contracts\s+in\s+\w+|can\s+you\s+translate|do\s+you\s+support\s+other\s+languages)\b",
        r"\b(?:explain\s+what\s+term\s*shield\s+does|how\s+to\s+use\s+term\s*shield|what\s+is\s+term\s*shield)\b",
        r"(?:ఇది\s*gemini|నేను\s*నిన్ను\s*ఏమేమి\s*అడగవచ్చు|మీరు\s*ఏమి\s*చేయగలరు|ఈ\s*యాప్‌ను\s*ఎలా\s*ఉపయోగించాలి)",
    ]

    LEGAL_CONCEPT_PATTERNS: list[str] = [
        r"^(?:what\s+is\s+(?:a\s+)?contract|define\s+contract|what\s+is\s+an\s+agreement|what\s+does\s+nda\s+mean|what\s+is\s+(?:an?\s+)?nda|what\s+is\s+a\s+non[-\s]disclosure\s+agreement|what\s+does\s+sla\s+mean|what\s+is\s+(?:an?\s+)?sla|what\s+is\s+force\s+majeure|what\s+is\s+indemnity|what\s+is\s+a\s+memorandum\s+of\s+understanding|what\s+is\s+mou)\??$",
    ]

    UNRELATED_PATTERNS: list[str] = [
        r"\bcapital\s+of\b",
        r"\bweather\s+(?:today|tomorrow|in\s+\w+)\b",
        r"\bwrite\s+(?:a\s+)?(?:python|java|c\+\+|javascript|code|script|program)\b",
        r"\btell\s+me\s+a\s+joke\b",
        r"\bwho\s+won\s+(?:yesterday'?s\s+)?(?:the\s+)?(?:world\s+cup|cricket|football|match)\b",
        r"\bpresident\s+of\b",
        r"\bprime\s+minister\s+of\b",
        r"\brecipe\s+for\b",
        r"\bhow\s+to\s+bake\b",
        r"\bhow\s+to\s+cook\b",
    ]

    @classmethod
    def detect_language(
        cls,
        question: str,
        explicit_language: str | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """
        Detects language cleanly without modifying the question text.
        Priority:
        1. Explicit request in question (e.g. "in Telugu", "now in English", "explain in Hindi", "telugu lo cheppu")
        2. Unicode script detection (Telugu, Devanagari, Tamil, etc.)
        3. Parameter `explicit_language` passed from user preferences
        4. History carryover ONLY if current question does NOT specify an English question
        5. Default: "English"
        """
        q_raw = question.strip()
        q_low = q_raw.lower()

        # Check for explicit switch to English or transliterated English
        if re.search(r"\b(?:now\s+(?:in|explain\s+in)?\s*english|in\s+english|english\s+please|switch\s+to\s+english|english\s*lo|englishlo)\b", q_low):
            return "English"

        # 1. Regex checks for explicit language mention in query
        if re.search(r"\b(?:okasari\s+)?(?:telugu\s*lo|telugulo)(?:\s+(?:cheppu|cheppandi|cheppava|raayi|matladu|vivarincu|explain))?\b", q_low) or \
           re.search(r"(?:తెలుగులో\s*(?:చెప్పు|చెప్పండి|వివరించండి)|ఒకసారి\s*తెలుగులో)", q_raw):
            return "Telugu"

        if re.search(r"\b(?:hindi\s+me(?:n)?|hindi\s+mein)(?:\s+(?:batao|bolo|samjhao|likho))?\b", q_low) or \
           re.search(r"(?:हिंदी\s*में\s*(?:बताओ|बताइए|समझाइए)|सरल\s*भाषा\s*में)", q_raw):
            return "Hindi"

        for key, lang_name in cls.KNOWN_LANGUAGES.items():
            if re.search(rf"\b(?:in|into|to|explain\s+in|say\s+it\s+in|translate\s+(?:this\s+)?to|explain\s+(?:it\s+)?in)\s+{key}\b", q_low):
                return lang_name
            if re.search(rf"\b{key}\s+(?:lo|me|mein|la|te|script|language|il|dalli|thil|vich|ma)\b", q_low):
                return lang_name
            if re.search(rf"^{key}\s*(?:please|cheppu|batao|parayoo)?[!?.]*$", q_low):
                return lang_name

        # 2. Native script regex
        for pattern, lang_name in cls.SCRIPT_LANGUAGE_MAP:
            if re.search(pattern, question):
                return lang_name

        # 3. Explicit language parameter from frontend
        if explicit_language and explicit_language.strip():
            normalized = explicit_language.strip().title()
            if normalized in cls.KNOWN_LANGUAGES.values():
                return normalized

        # 4. History carryover:
        # CRITICAL SAFETY: Never let a previous turn's language leak into a new English question!
        # If current question contains English words and asks a question or mentions contract concepts,
        # it is an English question.
        has_english_words = bool(re.search(r"\b[a-zA-Z]{3,}\b", q_low))
        is_explicit_english_question = has_english_words and not re.search(r"\b(?:lo|me|mein|cheppu|batao|ga)\b", q_low)
        if not is_explicit_english_question and history:
            for item in reversed(history):
                prev_lang = item.get("language")
                if prev_lang and prev_lang in cls.KNOWN_LANGUAGES.values() and prev_lang != "English":
                    return prev_lang

        return "English"

    @classmethod
    def extract_clause_number(cls, question: str) -> str | None:
        """
        Extracts specific target clause number (e.g. '7' from 'Clause 7', 'Clause 70' -> '70').
        Avoids word-boundary ambiguity.
        Supports English and Indic keywords for clause/section.
        """
        # English: clause 7, section 7, article 7, provision 7
        m = re.search(
            r"\b(?:clause|section|article|provision|item)\s*(?:no\.?|num\.?|number\s+)?(\d+)\b",
            question,
            re.IGNORECASE,
        )
        if m:
            return str(int(m.group(1)))

        # Indic: క్లాజ్ 7 (Telugu), खंड 7 (Hindi), பிரிவு 7 (Tamil), etc.
        m_indic = re.search(
            r"(?:క్లాజ్|సెక్షన్|ఆర్టికల్|खंड|धारा|अनुच्छेद|பிரிவு|విధి)\s*(\d+)",
            question,
            re.IGNORECASE,
        )
        if m_indic:
            return str(int(m_indic.group(1)))

        return None

    @classmethod
    def is_follow_up(cls, question: str) -> bool:
        """Determines if the question refers to prior conversation context."""
        q_low = question.lower().strip()
        q_clean = re.sub(r"[!.,?]+$", "", q_low).strip()

        # If it explicitly names a new clause number, it's a new clause query, not a pure follow-up
        if re.search(r"\b(?:clause|section|article)\s*\d+\b", q_low):
            return False

        # Language instructions or translation requests
        if re.search(
            r"\b(?:in\s+telugu|in\s+hindi|in\s+tamil|in\s+kannada|in\s+malayalam|in\s+bengali|in\s+marathi|in\s+gujarati|in\s+punjabi|in\s+urdu|in\s+english|telugu\s*lo|telugulo|hindi\s*me|translate\s+this|translate\s+to|explain\s+in|okasari\s+telugu)\b",
            q_low,
        ) or re.search(r"(?:తెలుగులో\s*(?:చెప్పు|చెప్పండి|వివరించండి)|ఒకసారి\s*తెలుగులో|हिंदी\s*में)", q_low):
            return True

        # Simplification requests
        if re.search(
            r"\b(?:make\s+it\s+simple|explain\s+simply|explain\s+it\s+simply|simplify|simple\s+terms|in\s+simple\s+words|simpler|simple\s*ga|okasari\s+simple)\b",
            q_low,
        ):
            return True

        # Action / obligation follow-ups
        if re.search(r"\b(?:what\s+do\s+i\s+need\s+to\s+do|what\s+are\s+my\s+duties|what\s+must\s+i\s+do|what\s+should\s+i\s+do|what\s+is\s+my\s+obligation|what\s+are\s+my\s+obligations\s+under\s+it)\b", q_low):
            return True

        # Consequence / penalty / breach follow-ups
        if re.search(r"\b(?:what\s+happens\s+if\s+i\s+don'?t|what\s+if\s+i\s+miss\s+it|what\s+if\s+i\s+don'?t\s+do\s+it|and\s+what\s+happens\s+if|what\s+if\s+i\s+fail|what\s+if\s+i\s+breach)\b", q_low):
            return True

        # Risk / responsibility follow-ups
        if re.search(r"\b(?:what\s+is\s+the\s+risk|is\s+it\s+risky|what\s+are\s+the\s+risks|who\s+is\s+responsible|who\s+is\s+liable|who\s+pays)\b", q_low):
            return True

        # Deadline follow-ups
        if re.search(r"\b(?:what\s+about\s+the\s+deadline|when\s+is\s+the\s+deadline|what\s+is\s+the\s+timeframe|what\s+about\s+the\s+notice\s+period)\b", q_low):
            return True

        # Entity follow-ups ("what about the consultant?")
        if re.search(r"\b(?:what\s+about|how\s+about|and)\s+(?:the\s+)?(?:consultant|commission|customer|client|vendor)\b", q_low):
            return True

        # Payment follow-ups
        if re.search(r"\b(?:is\s+that\s+something\s+i\s+(?:have|need)\s+to\s+pay|what\s+happens\s+if\s+i\s+don'?t\s+pay|what\s+if\s+i\s+don'?t\s+pay)\b", q_low):
            return True

        # Pronoun & demonstrative references
        follow_up_patterns = [
            r"^(?:what\s+about|how\s+about|and\s+what\s+about|and\s+then)\s+",
            r"^and\s+(?:payment|notice|termination|penalty|penalties|liabilities|liability|deadlines|cancellation|damages|consultant|commission|customer)\??$",
            r"^(?:what\s+about\s+(?:that|this)|why\s+is\s+that|explain\s+(?:this|it|more|it\s+simply)|tell\s+me\s+more|and\s+then\??)[!.,?]*$",
            r"\b(?:under\s+it|under\s+this|under\s+that|about\s+it|in\s+it|does\s+it|can\s+it|what\s+does\s+it\s+say|what\s+does\s+it\s+mean)\b",
            r"^(?:is\s+this\s+risky|is\s+it\s+risky)\??$",
        ]
        return any(re.search(pat, q_clean) for pat in follow_up_patterns)

    @classmethod
    def is_language_or_format_instruction(cls, question: str) -> bool:
        """Determines if the question is an instruction to switch language or format of previous answer."""
        if not question or not question.strip():
            return False
        q_low = question.lower().strip()
        q_clean = re.sub(r"[!.,?]+$", "", q_low).strip()
        if re.search(
            r"\b(?:in\s+telugu|in\s+hindi|in\s+tamil|in\s+kannada|in\s+malayalam|in\s+bengali|in\s+marathi|in\s+gujarati|in\s+punjabi|in\s+urdu|in\s+english|telugu\s*lo|telugulo|hindi\s*me|translate\s+this|translate\s+to|explain\s+in|okasari\s+telugu)\b",
            q_low,
        ) or re.search(r"(?:తెలుగులో\s*(?:చెప్పు|చెప్పండి|వివరించండి)|ఒకసారి\s*తెలుగులో|हिंदी\s*में)", question):
            return True
        if re.search(
            r"\b(?:make\s+it\s+simple|explain\s+simply|explain\s+it\s+simply|simplify|simple\s+terms|in\s+simple\s+words|simpler|simple\s*ga|okasari\s+simple)\b",
            q_low,
        ):
            return True
        if q_clean in {"telugu", "telugu lo", "telugulo", "hindi", "hindi me", "hindi mein", "english", "english lo", "simple ga", "simply", "simple"}:
            return True
        return False

    @classmethod
    def classify_coarse_intent(cls, question: str, clauses: list[Clause] | None = None) -> str:
        """
        Classifies high-level intent into: 'general', 'capability', 'unrelated', 'contract'.
        """
        if not question or not question.strip():
            return "general"

        q_raw = question.strip()
        q_low = q_raw.lower()
        q_clean = re.sub(r"[!.,?]+$", "", q_low).strip()

        # 1. Greetings, acknowledgments, basic pleasantries
        if q_clean in cls.GREETINGS_OR_GENERAL or any(q_clean.startswith(g) for g in ["hi ", "hello ", "hey "]):
            return "general"

        if re.search(r"^(?:నమస్కారం|నమస్తే|హలో|ధన్యవాదాలు|థాంక్స్|వీడ్కోలు)[!.,?]*$", q_raw) or \
           re.search(r"^(?:नमस्ते|नमस्कार|हेलो|धन्यवाद|शुक्रिया|अलविदा)[!.,?]*$", q_raw):
            return "general"

        # Identity & User Privacy ("do u know me", "who am i", "who are you")
        if re.search(
            r"\b(?:do\s+(?:you|u)\s+know\s+me|who\s+am\s+i|do\s+(?:you|u)\s+remember\s+me|do\s+(?:you|u)\s+know\s+who\s+i\s+am)\b",
            q_clean,
        ) or re.search(r"(?:నన్ను\s*తెలుసా|నేను\s*ఎవరు|क्या\s*तुम\s*मुझे\s*जानते\s*हो|मैं\s*कौन\s*हूँ)", q_raw):
            return "general"

        if re.search(
            r"\b(?:who\s+(?:are|r)\s+(?:you|u)|what\s+is\s+your\s+name|who\s+made\s+you|what\s+are\s+you)\b",
            q_clean,
        ) or re.search(r"(?:నువ్వు\s*ఎవరు|మీరు\s*ఎవరు|నువ్వు\s*ఎవరివి|మీరెవరు|నువ్వెవరు|आप\s*कौन\s*हैं|तुम\s*कौन\s*हो)", q_raw):
            return "general"

        # General Legal Concept definitions (without contract/document specifier)
        has_doc_specifier = bool(
            re.search(
                r"\b(?:this\s+(?:contract|agreement|document|policy|deal|lease)|uploaded\s+contract|my\s+contract|in\s+(?:the|this)\s+(?:contract|agreement)|the\s+(?:contract|agreement))\b",
                q_low,
            )
            or re.search(r"(?:ఈ\s*(?:ఒప్పందం|కాంట్రాక్ట్)|ఒప్పందంలో|కాంట్రాక్ట్‌లో|यह\s*अनुबंध|इस\s*अनुबंध)", q_raw)
        )
        if not has_doc_specifier:
            if any(re.search(pat, q_clean) for pat in cls.LEGAL_CONCEPT_PATTERNS):
                return "general"

        # 2. Assistant capabilities
        if any(re.search(pat, q_clean, re.IGNORECASE) for pat in cls.CAPABILITY_PATTERNS):
            return "capability"

        # 3. Explicit unrelated topics
        if any(re.search(pat, q_low) for pat in cls.UNRELATED_PATTERNS):
            return "unrelated"

        # 4. If query mentions a clause number or follow-up, it is 'contract'
        if cls.extract_clause_number(question) or cls.is_follow_up(question):
            return "contract"

        # Specific contract payment and obligation patterns (e.g. "do u think i need to pay anything")
        if re.search(r"\b(?:pay|payment|obligation|terminate|termination|penalty|penalties|deadline|breach|liability)\b", q_low):
            return "contract"

        contract_terms = [
            "contract", "agreement", "clause", "section", "article", "provision",
            "obligation", "duty", "duties", "liable", "liability", "liabilities",
            "cancel", "cancellation", "terminate", "termination", "renew", "renewal",
            "pay", "payment", "fee", "fees", "charge", "interest", "penalty", "penalties",
            "breach", "default", "dispute", "confidential", "notice", "deadline",
            "risk", "sign", "signing", "customer", "consultant", "vendor", "client",
            "terms", "condition", "conditions", "refund", "reprocurement",
            "purpose", "main purpose", "page",
        ]
        if any(term in q_low for term in contract_terms):
            return "contract"

        if re.search(r"(?:చెల్లింపు|రద్దు|ముగింపు|బాధ్యత|గడువు|పెనాల్టీ|రిస్క్|నోటీసు|నిబంధన)", q_raw):
            return "contract"

        # If clauses exist and words overlap substantively with contract text, it's contract
        if clauses:
            q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", q_low))
            for c in clauses[:10]:
                c_text = (c.text or "").lower()
                c_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", c_text))
                if len(q_words & c_words) >= 2:
                    return "contract"

        # If question is generic trivia without contract cues
        if re.search(r"^(?:who\s+is|where\s+is|what\s+is\s+the\s+capital|how\s+to\s+cook|recipe)\b", q_low):
            return "unrelated"

        return "contract"

    @classmethod
    def analyze(
        cls,
        question: str,
        requested_language: str | None = None,
        history: list[dict] | None = None,
        clauses: list[Clause] | None = None,
    ) -> QuestionAnalysis:
        cleaned = question.strip()
        coarse = cls.classify_coarse_intent(cleaned, clauses)
        clause_num = cls.extract_clause_number(cleaned)
        language = cls.detect_language(cleaned, requested_language, history)
        follow_up = cls.is_follow_up(cleaned)
        references_previous = False

        # If follow-up has no clause number in current question, resolve from history
        if follow_up and not clause_num and history:
            for item in reversed(history):
                prev_q = item.get("question", "")
                prev_num = cls.extract_clause_number(prev_q)
                if prev_num:
                    clause_num = prev_num
                    references_previous = True
                    break
                # Also check evidence in previous turn
                prev_ev = item.get("evidence", []) or item.get("evidence_json")
                if prev_ev:
                    if isinstance(prev_ev, str):
                        try:
                            import json
                            prev_ev = json.loads(prev_ev)
                        except Exception:
                            prev_ev = []
                    if isinstance(prev_ev, list) and len(prev_ev) > 0:
                        ev_num = prev_ev[0].get("clause_number")
                        if ev_num and str(ev_num).strip().isdigit():
                            clause_num = str(int(ev_num))
                            references_previous = True
                            break

        # Fine intent determination based on substantive phrasing FIRST
        q_low = cleaned.lower()

        if re.search(r"\b(?:most\s+important\s+clause|most\s+critical\s+clause|key\s+clause|main\s+clause)\b", q_low):
            fine = "most_important_clause"
        elif re.search(r"\b(?:main\s+purpose|purpose\s+of\s+this|what\s+is\s+this\s+(?:page|document|site|contract)\s+about)\b", q_low):
            fine = "main_purpose"
        elif re.search(r"\b(?:what\s+do\s+i\s+need\s+to\s+do|obligat\w*|dut\w*|responsib\w*|required\s+to\s+do|have\s+to\s+do|what\s+must\s+i\s+do)\b", q_low):
            fine = "obligation"
        elif re.search(r"\b(?:what\s+happens\s+if\s+i\s+don'?t|penalt\w*|late\s+fee\w*|interest|fine\w*|consequence\w*|default\w*|breach\w*)\b", q_low):
            fine = "penalty"
        elif re.search(r"\b(?:risk\w*|red\s+flag\w*|concern\w*|before\s+signing|is\s+it\s+risky|what\s+should\s+i\s+know)\b", q_low):
            fine = "risk"
        elif re.search(r"\b(?:who\s+is\s+responsible|who\s+is\s+liable|liab\w*|indemn\w*)\b", q_low):
            fine = "responsibility"
        elif re.search(r"\b(?:pay\w*|fee\w*|cost\w*|charg\w*|reimburs\w*|invoic\w*|need\s+to\s+pay|pay\s+anything)\b", q_low):
            fine = "financial"
        elif re.search(r"\b(?:deadlin\w*|timelin\w*|timeframe\w*|due\s+date|within\s+\d+|notice\s+period|when\s+must|how\s+long)\b", q_low):
            fine = "deadline"
        elif re.search(r"\b(?:renew\w*|auto-renew\w*|extension\w*)\b", q_low):
            fine = "renewal"
        elif re.search(r"\b(?:terminat\w*|cancel\w*|end\s+the\s+contract|end\s+the\s+agreement)\b", q_low):
            fine = "termination"
        elif re.search(r"\b(?:confidenti\w*|non-disclosure|trade\s+secret\w*)\b", q_low):
            fine = "confidentiality"
        elif re.search(r"\b(?:govern\w*|jurisdiction|applicable\s+law)\b", q_low):
            fine = "governing_law"
        elif re.search(r"\b(?:make\s+it\s+simple|explain\s+simply|explain\s+it\s+simply|simplify|simple\s+terms|in\s+simple\s+words|simpler|simple\s*ga)\b", q_low):
            fine = "simplification"
        elif re.search(r"\b(?:translate|translation|in\s+telugu|in\s+hindi|in\s+tamil|in\s+kannada|in\s+malayalam|in\s+marathi|in\s+bengali|in\s+gujarati|in\s+punjabi|in\s+urdu|telugu\s*lo|hindi\s*me|now\s+in\s+english)\b", q_low) or \
             re.search(r"(?:తెలుగులో|చెప్పు)", q_low):
            fine = "translation"
        elif clause_num and not follow_up:
            fine = "explanation"
        elif follow_up:
            fine = "explanation"
        elif coarse == "unrelated":
            fine = "unrelated"
        elif coarse == "capability":
            fine = "capability"
        elif coarse == "general":
            fine = "greeting"
        else:
            fine = "general_contract"

        # If follow-up has fine intent of translation/simplification/explanation,
        # inherit the substantive intent of the previous turn if available
        if follow_up and fine in {"translation", "simplification", "explanation"} and history:
            last_item = history[-1]
            last_q = (last_item.get("question") or "").lower()
            if re.search(r"\b(?:obligat\w*|dut\w*|responsib\w*|required\s+to\s+do|have\s+to\s+do|what\s+must\s+i\s+do)\b", last_q):
                fine = "obligation"
            elif re.search(r"\b(?:pay\w*|fee\w*|cost\w*|charg\w*|invoic\w*)\b", last_q):
                fine = "financial"
            elif re.search(r"\b(?:terminat\w*|cancel\w*)\b", last_q):
                fine = "termination"
            elif re.search(r"\b(?:renew\w*|auto-renew\w*)\b", last_q):
                fine = "renewal"
            elif re.search(r"\b(?:deadlin\w*|notice\s+period)\b", last_q):
                fine = "deadline"

        # Check target entity
        target_entity = None
        if "consultant" in q_low:
            target_entity = "consultant"
        elif "commission" in q_low:
            target_entity = "commission"
        elif "customer" in q_low or "client" in q_low:
            target_entity = "customer"

        is_conv = coarse in {"general", "capability"}

        return QuestionAnalysis(
            raw_question=question,
            cleaned_question=cleaned,
            coarse_intent=coarse,
            fine_intent=fine,
            clause_number=clause_num,
            language=language,
            is_follow_up=follow_up,
            references_previous_answer=references_previous,
            is_conversational=is_conv,
            target_entity=target_entity,
        )
