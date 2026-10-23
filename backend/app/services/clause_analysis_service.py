from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.clause_classifier_service import ClauseClassifierService


@dataclass
class ClauseAnalysis:
    clause_id: str
    clause_number: Optional[str] = None
    clause_type: Optional[str] = None
    title: Optional[str] = None
    meaning: Optional[str] = None

    # ------------------------------------------------------------------
    # Entities / participants
    # ------------------------------------------------------------------
    parties: list[str] = field(default_factory=list)
    persons: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    authorities: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Legal effects / actions
    # ------------------------------------------------------------------
    obligations: list[str] = field(default_factory=list)
    duties: list[str] = field(default_factory=list)
    rights: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    prohibitions: list[str] = field(default_factory=list)
    powers: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Logic / conditions
    # ------------------------------------------------------------------
    conditions: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    deadlines: list[str] = field(default_factory=list)
    durations: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Financial
    # ------------------------------------------------------------------
    monetary_terms: list[str] = field(default_factory=list)
    percentages: list[str] = field(default_factory=list)
    quantities: list[str] = field(default_factory=list)
    currencies: list[str] = field(default_factory=list)
    fees: list[str] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)
    taxes: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Legal / regulatory
    # ------------------------------------------------------------------
    laws: list[str] = field(default_factory=list)
    regulations: list[str] = field(default_factory=list)
    statutes: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    articles: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    case_references: list[str] = field(default_factory=list)
    legal_references: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Subject matter
    # ------------------------------------------------------------------
    assets: list[str] = field(default_factory=list)
    property_terms: list[str] = field(default_factory=list)
    goods: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    information: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Disputes / enforcement
    # ------------------------------------------------------------------
    dispute_terms: list[str] = field(default_factory=list)
    jurisdiction: list[str] = field(default_factory=list)
    governing_law: list[str] = field(default_factory=list)
    arbitration: list[str] = field(default_factory=list)
    remedies: list[str] = field(default_factory=list)
    enforcement: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Privacy / data / confidentiality
    # ------------------------------------------------------------------
    privacy_terms: list[str] = field(default_factory=list)
    confidentiality_terms: list[str] = field(default_factory=list)
    data_terms: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Employment
    # ------------------------------------------------------------------
    employment_terms: list[str] = field(default_factory=list)
    compensation_terms: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    leave_terms: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Loans / credit
    # ------------------------------------------------------------------
    loan_terms: list[str] = field(default_factory=list)
    interest_terms: list[str] = field(default_factory=list)
    repayment_terms: list[str] = field(default_factory=list)
    collateral: list[str] = field(default_factory=list)
    default_terms: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Intellectual property / restrictions
    # ------------------------------------------------------------------
    intellectual_property_terms: list[str] = field(default_factory=list)
    restriction_terms: list[str] = field(default_factory=list)
    non_compete_terms: list[str] = field(default_factory=list)
    exclusivity_terms: list[str] = field(default_factory=list)
    waiver_terms: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Notices / procedural material
    # ------------------------------------------------------------------
    notice_terms: list[str] = field(default_factory=list)
    procedural_terms: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------
    risk_level: str = "LOW"
    risk_score: int = 0
    risk_reasons: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # User-facing interpretation
    # ------------------------------------------------------------------
    user_impact: Optional[str] = None
    why_important: list[str] = field(default_factory=list)
    potential_concerns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ClauseAnalysisService:
    """
    Universal deterministic clause analyzer.

    IMPORTANT:
    This service does NOT assume that the input is a commercial contract.

    It can analyze individual provisions from:
        - contracts
        - employment letters
        - offer letters
        - loan documents
        - leases
        - government notices
        - policies
        - regulations
        - legal notices
        - court-related documents
        - agreements
        - terms and conditions
        - compliance documents
        - other legal / administrative documents

    This is the deterministic foundation.

    Later layers can add:
        - NER
        - embeddings
        - LLM analysis
        - RAG
        - legal knowledge retrieval
        - document-level reasoning

    without changing the basic analysis model.
    """

    # ================================================================
    # Core patterns
    # ================================================================

    PARTY_WORDS = [
        "client", "customer", "company", "employer", "employee",
        "borrower", "lender", "tenant", "landlord", "licensor",
        "licensee", "contractor", "consultant", "supplier", "vendor",
        "buyer", "seller", "applicant", "respondent", "petitioner",
        "plaintiff", "defendant", "authority", "government",
        "department", "agency", "regulator", "provider", "recipient",
        "issuer", "holder", "owner", "operator", "individual",
        "party", "parties", "subscriber", "member", "beneficiary",
        "guarantor", "agent", "principal"
    ]

    OBLIGATION_PATTERNS = [
        r"\bshall\b",
        r"\bmust\b",
        r"\bis required to\b",
        r"\bare required to\b",
        r"\bagrees to\b",
        r"\bundertakes to\b",
        r"\bis responsible for\b",
        r"\bare responsible for\b",
        r"\bhas a duty to\b",
        r"\bduty to\b",
        r"\bwill provide\b",
        r"\bwill pay\b",
        r"\bwill submit\b",
        r"\bwill comply\b",
    ]

    RIGHT_PATTERNS = [
        r"\bhas the right to\b",
        r"\bhave the right to\b",
        r"\bis entitled to\b",
        r"\bare entitled to\b",
        r"\bis permitted to\b",
        r"\bare permitted to\b",
        r"\bhas authority to\b",
        r"\bhave authority to\b",
    ]

    PROHIBITION_PATTERNS = [
        r"\bshall not\b",
        r"\bmust not\b",
        r"\bmay not\b",
        r"\bcannot\b",
        r"\bcan not\b",
        r"\bprohibited\b",
        r"\bforbidden\b",
        r"\bnot permitted\b",
        r"\bwithout permission\b",
        r"\bwithout authorization\b",
        r"\bwithout authorisation\b",
    ]

    CONDITION_PATTERNS = [
        r"\bif\b",
        r"\bunless\b",
        r"\bprovided that\b",
        r"\bsubject to\b",
        r"\bon the condition that\b",
        r"\bwhere\b",
        r"\bwhen\b",
        r"\bin the event that\b",
        r"\bin the event of\b",
    ]

    TRIGGER_PATTERNS = [
        r"\bupon\b",
        r"\bwhen\b",
        r"\bif\b",
        r"\bafter\b",
        r"\bbefore\b",
        r"\bon receipt of\b",
        r"\bon occurrence of\b",
        r"\bin the event of\b",
        r"\bfollowing\b",
        r"\bfrom the date of\b",
    ]

    EXCEPTION_PATTERNS = [
        r"\bexcept\b",
        r"\bexcept where\b",
        r"\bunless\b",
        r"\bnotwithstanding\b",
        r"\bprovided that\b",
        r"\bsubject to\b",
        r"\bother than\b",
        r"\bexcluding\b",
    ]

    DATE_PATTERNS = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"(?:\s+\d{4})?\b",
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,\s*|\s+)\d{4}\b",
    ]

    DURATION_PATTERN = (
        r"\b\d+(?:\.\d+)?\s+"
        r"(?:second|seconds|minute|minutes|hour|hours|"
        r"day|days|week|weeks|month|months|year|years)\b"
    )

    MONEY_PATTERN = (
        r"(?:(?:INR|USD|EUR|GBP|JPY|AUD|CAD)\s*"
        r"(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?"
        r"|(?:Rs\.?|\$)\s*"
        r"(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?"
        r"|\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*"
        r"(?:rupees|dollars|euros|pounds|yen)\b)"
    )

    PERCENT_PATTERN = (
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|percentage)"
)

    LEGAL_REFERENCE_PATTERNS = {
        # Specific references:
        #   Section 10
        #   Section 10(1)
        #   Section 10 of the Indian Contract Act, 1872
        "sections": [
            r"(?i)\b(?:section|sec\.?)\s+[A-Za-z0-9().-]+"
            r"(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z0-9,&'(). -]{2,100})?"
        ],

        #   Article 21
        #   Article 21 of the Constitution of India
        "articles": [
            r"(?i)\b(?:article|art\.?)\s+[A-Za-z0-9().-]+"
            r"(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z0-9,&'(). -]{2,100})?"
        ],

        #   Rule 5
        #   Rule 5 of the relevant rules
        "rules": [
            r"(?i)\b(?:rule|rules)\s+[A-Za-z0-9().-]+"
            r"(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z0-9,&'(). -]{2,100})?"
        ],

        #   Regulation 12
        "regulations": [
            r"(?i)\b(?:regulation|regulations)\s+[A-Za-z0-9().-]+"
            r"(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z0-9,&'(). -]{2,100})?"
        ],

        # Explicit statute references:
        #   Statute 15
        "statutes": [
            r"(?i)\b(?:statute|statutes)\s+[A-Za-z0-9().-]+"
            r"(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z0-9,&'(). -]{2,100})?"
        ],

        # Named laws / Acts only.
        #
        # Examples:
        #   Indian Contract Act, 1872
        #   Companies Act, 2013
        #   Information Technology Act, 2000
        #
        # This pattern is intentionally case-sensitive so generic
        # phrases such as "the law" are not detected.
        "laws": [
            r"\b(?:[A-Z][A-Za-z]+\s+){1,8}"
            r"(?:Act|Acts|Law|Laws)"
            r"(?:,\s*\d{4})?"
        ],
    }

    # Analysis
    # ================================================================

    @classmethod
    def analyze_clause(cls, clause) -> ClauseAnalysis:
        clause = ClauseClassifierService.classify(clause)
        text = cls._clean(getattr(clause, "text", "") or "")

        result = ClauseAnalysis(
    clause_id=getattr(clause, "clause_id", "") or "",
    clause_number=getattr(clause, "clause_number", None),
    clause_type=getattr(clause, "clause_type", None),
    title=getattr(clause, "title", None),
)

        if not text:
            result.meaning = "No substantive text was available for analysis."
            result.user_impact = (
                "No substantive content was available for deterministic analysis."
            )
            return result

        # Entities
        result.parties = cls._extract_parties(text)
        result.organizations = cls._extract_organizations(text)
        result.authorities = cls._extract_authorities(text)

        # Legal effects
        obligation_exclusions = [
            *cls.PROHIBITION_PATTERNS,

            # Legal-effect statements containing "shall" are not
            # contractual obligations of a party.
            r"\bshall\s+be\s+governed\s+by\b",
            r"\bgoverned\s+by\b",
            r"\bshall\s+have\s+.*\bjurisdiction\b",
            r"\bexclusive\s+jurisdiction\b",
            r"\bjurisdiction\b",
            r"\bshall\s+be\s+resolved\s+by\b",
            r"\bresolved\s+by\s+arbitration\b",
            r"\barbitration\b",
            
            # Payment-method instructions should remain under
            # financial/payment analysis rather than obligations.
            r"\bpayments?\s+shall\s+be\s+made\s+to\b",
            r"\bpayments?\s+must\s+be\s+made\s+to\b",
            r"\bpayment\s+shall\s+be\s+made\s+in\s+the\s+following\s+manner\b",
            r"\bpayment\s+must\s+be\s+made\s+in\s+the\s+following\s+manner\b",
        ]

        result.obligations = cls._extract_by_patterns(
            text,
            cls.OBLIGATION_PATTERNS,
            exclude_patterns=obligation_exclusions,
        )
        result.duties = list(result.obligations)

        result.rights = cls._extract_by_patterns(
            text, cls.RIGHT_PATTERNS
        )

        result.permissions = cls._extract_by_patterns(
            text,
            [
                r"\bmay\s+(?!result\b|cause\b|lead\b|constitute\b)",
                r"\bis permitted to\b",
                r"\bare permitted to\b",
                r"\bhas permission to\b",
                r"\bhave permission to\b",
                r"\bis authorized to\b",
                r"\bare authorized to\b",
                r"\bis authorised to\b",
                r"\bare authorised to\b",
                r"\bhas authority to\b",
                r"\bhave authority to\b",
            ],
        )

        result.prohibitions = cls._extract_by_patterns(
            text, cls.PROHIBITION_PATTERNS
        )

        # Conditions
        result.conditions = cls._extract_by_patterns(
            text, cls.CONDITION_PATTERNS
        )

        result.exceptions = cls._extract_by_patterns(
            text, cls.EXCEPTION_PATTERNS
        )

        result.triggers = cls._extract_by_patterns(
            text, cls.TRIGGER_PATTERNS
        )

        result.consequences = cls._keyword_sentences(
            text,
            [
                "consequence",
                "consequences",
                "result",
                "resulting",
                "penalty",
                "remedy",
                "remedies",
                "liable",
                "liability",
                "default",
                "termination",
                "damages",
                "sanction",
                "fine",
            ],
        )

        # Time
        result.durations = cls._regex_extract(
            text, cls.DURATION_PATTERN
        )
        result.deadlines = list(result.durations)
        result.dates = cls._extract_dates(text)

        # Financial
        result.monetary_terms = cls._extract_money(text)

        result.percentages = [
            match.group(0).strip()
            for match in re.finditer(
                cls.PERCENT_PATTERN,
                text,
                re.IGNORECASE,
            )
        ]

        result.currencies = cls._extract_currencies(text)

        result.fees = cls._keyword_sentences(
            text,
            [
                "fee",
                "fees",
                "charge",
                "charges",
                "commission",
                "payment amount",
                "payment of",
                "total payment",
                "total fee",
            ],
        )
        result.penalties = cls._keyword_sentences(
            text,
            ["penalty", "penalties", "fine", "fines"],
        )

        result.taxes = cls._keyword_sentences(
            text,
            ["tax", "taxes", "gst", "vat", "withholding", "duty"],
        )

        result.quantities = cls._extract_quantities(text)

        # Legal / regulatory
        result.sections = cls._extract_legal(
            text, "sections"
        )
        result.articles = cls._extract_legal(
            text, "articles"
        )
        result.rules = cls._extract_legal(
            text, "rules"
        )
        result.regulations = cls._extract_legal(
            text, "regulations"
        )
        result.statutes = cls._extract_legal(
            text, "statutes"
        )
        result.laws = cls._extract_legal(
            text, "laws"
        )

        result.case_references = cls._keyword_sentences(
            text,
            [
                "judgment",
        "judgement",
        "tribunal",
        "precedent",
        "petition",
        "appeal",
        "court decision",
        "court order",
        "tribunal decision",
        "tribunal order",
    ],
)
        result.legal_references = cls._unique(
            result.laws
            + result.regulations
            + result.statutes
            + result.sections
            + result.articles
            + result.rules
            + result.case_references
        )

        # Subject matter
        result.assets = cls._keyword_sentences(
            text,
            [
                "asset",
                "assets",
                "property",
                "equipment",
                "vehicle",
                "land",
                "building",
                "shares",
                "securities",
                "inventory",
            ],
        )

        result.property_terms = cls._keyword_sentences(
            text,
            [
                "real estate",
                "premises",
                "lease",
                "tenant",
                "landlord",
                "ownership",
                "title to",
                "property rights",
                "property ownership",
                "immovable property",
                "movable property",
            ],
        )

        result.goods = cls._keyword_sentences(
            text,
            [
                "goods",
                "product",
                "products",
                "merchandise",
                "materials",
                "inventory",
            ],
        )

        result.services = cls._keyword_sentences(
            text,
            [
                "service",
                "services",
                "software",
                "support",
                "maintenance",
                "consulting",
                "development",
            ],
        )

        result.information = cls._keyword_sentences(
            text,
            [
                "information",
                "data",
                "records",
                "personal information",
                "personal data",
                "confidential information",
            ],
        )

        result.documents = cls._keyword_sentences(
            text,
            [
                "document",
                "documents",
                "certificate",
                "notice",
                "report",
                "application",
                "form",
                "statement",
                "invoice",
            ],
        )

        # Dispute / enforcement
        result.dispute_terms = cls._keyword_sentences(
        text,
    [
        "dispute",
        "disputes",
        "litigation",
        "court proceedings",
        "legal proceedings",
        "settled by arbitration",
        "resolved by arbitration",
    ],
)

        result.jurisdiction = cls._extract_jurisdiction(text)

        result.governing_law = cls._keyword_sentences(
            text,
            [
                "governing law",
                "governed by",
                "applicable law",
            ],
        )

        result.arbitration = cls._keyword_sentences(
            text,
            [
                "arbitration",
                "arbitrator",
                "arbitral",
            ],
        )

        # ------------------------------------------------------------
        # Legal-effect classification cleanup
        # ------------------------------------------------------------
        # Pattern-based extraction intentionally starts broad. Refine
        # classifications here where common legal phrases such as
        # "shall be governed by" or "shall be subject to" describe
        # legal applicability rather than a party's actual duty.

        non_obligation_phrases = (
            "shall be governed by",
            "shall be subject to",
            "shall be construed",
            "shall be interpreted",
            "shall apply",
            "shall form part of",
            "must be governed by",
            "must be subject to",
            "must be construed",
            "must be interpreted",
        )

        result.obligations = [
            sentence
            for sentence in result.obligations
            if not any(
                phrase in sentence.casefold()
                for phrase in non_obligation_phrases
            )
        ]

        result.duties = list(result.obligations)

        # "Subject to" is often extracted as a generic condition, but
        # dispute-resolution and governing-law statements should remain
        # in their more specific legal categories.
        non_condition_phrases = (
            "shall be subject to",
            "must be subject to",
            "subject to the applicable law",
            "subject to applicable law",
            "subject to the laws of",
            "subject to the jurisdiction",
        )

        result.conditions = [
            sentence
            for sentence in result.conditions
            if not any(
                phrase in sentence.casefold()
                for phrase in non_condition_phrases
            )
        ]

        result.remedies = cls._keyword_sentences(
            text,
            [
                "remedy",
                "remedies",
                "damages",
                "injunction",
                "relief",
                "compensation",
                "restitution",
            ],
        )

        result.enforcement = cls._keyword_sentences(
            text,
            [
                "enforce",
                "enforcement",
                "enforceable",
                "execution",
                "execute",
                "compliance",
            ],
        )

        # Privacy / confidentiality
        result.privacy_terms = cls._keyword_sentences(
            text,
            [
                "privacy",
                "personal data",
                "personal information",
                "privacy policy",
                "data protection",
                "data privacy",
            ],
        )

        result.confidentiality_terms = cls._keyword_sentences(
            text,
            [
                "confidential",
                "confidentiality",
                "non-disclosure",
                "nda",
                "secret",
                "trade secret",
            ],
        )

        result.data_terms = cls._keyword_sentences(
            text,
            [
                "data",
                "processing",
                "processor",
                "controller",
                "consent",
                "collect",
                "collection",
                "storage",
                "sharing",
                "disclosure",
                "retention",
            ],
        )

        # Employment
        result.employment_terms = cls._keyword_sentences(
            text,
            [
                "employee",
                "employer",
                "employment",
                "job",
                "salary",
                "wages",
                "probation",
                "notice period",
                "working hours",
                "job duties",
                "termination of employment",
                "promotion",
                "disciplinary",
            ],
        )

        result.compensation_terms = cls._keyword_sentences(
            text,
            [
                "salary",
                "wages",
                "compensation",
                "bonus",
                "commission",
                "remuneration",
                "stipend",
                "payroll",
                "gross pay",
                "net pay",
                "base pay",
                "base salary",
                "annual salary",
                "monthly salary",
                "hourly wage",
            ],
        )

        result.benefits = cls._keyword_sentences(
            text,
            [
                "benefit",
                "benefits",
                "insurance",
                "provident fund",
                "pension",
                "allowance",
                "medical",
            ],
        )

        result.leave_terms = cls._keyword_sentences(
            text,
            [
                "leave",
                "vacation",
                "holiday",
                "sick leave",
                "maternity",
                "paternity",
                "absence",
            ],
        )

        # Loans / credit
        result.loan_terms = cls._keyword_sentences(
            text,
            [
                "loan",
                "borrower",
                "lender",
                "principal",
                "credit",
                "facility",
                "financing",
                "disbursement",
            ],
        )

        result.interest_terms = cls._keyword_sentences(
            text,
            [
                "interest rate",
                "interest",
                "annual percentage rate",
                "apr",
                "rate of interest",
            ],
        )

        result.repayment_terms = cls._keyword_sentences(
            text,
            [
                "repayment",
                "repay",
                "installment",
                "instalment",
                "emi",
                "amortization",
                "amortisation",
                "maturity",
            ],
        )

        result.collateral = cls._keyword_sentences(
            text,
            [
                "collateral",
                "security",
                "secured",
                "mortgage",
                "pledge",
                "lien",
                "guarantee",
                "guarantor",
            ],
        )

        result.default_terms = cls._keyword_sentences(
            text,
            [
                "default",
                "event of default",
                "failure to pay",
                "non-payment",
                "nonpayment",
                "overdue",
            ],
        )

        # IP / restrictions
        result.intellectual_property_terms = cls._keyword_sentences(
            text,
            [
                "intellectual property",
                "copyright",
                "patent",
                "trademark",
                "trade mark",
                "license",
                "licence",
                "invention",
                "royalty",
                "proprietary",
                "know-how",
            ],
        )

        result.restriction_terms = cls._keyword_sentences(
            text,
            [
                "restriction",
                "restrict",
                "restricted",
                "prohibit",
                "prohibited",
                "limitation",
                "limit",
            ],
        )

        result.non_compete_terms = cls._keyword_sentences(
            text,
            [
                "non-compete",
                "non compete",
                "noncompetition",
                "not compete",
            ],
        )

        result.exclusivity_terms = cls._keyword_sentences(
            text,
            [
                "exclusive",
                "exclusivity",
                "sole",
                "exclusive dealing",
            ],
        )

        result.waiver_terms = cls._keyword_sentences(
            text,
            [
                "waive",
                "waiver",
                "waived",
            ],
        )

        # Notices / procedure
        result.notice_terms = cls._keyword_sentences(
            text,
            [
                "notice",
                "written notice",
                "notification",
                "notify",
                "notified",
                "service of notice",
            ],
        )

        result.procedural_terms = cls._keyword_sentences(
            text,
            [
                "procedure",
                "procedures",
                "process",
                "application",
                "hearing",
                "appeal",
                "review",
                "submission",
                "filing",
            ],
        )

        # Risk
        (
            result.risk_level,
            result.risk_score,
            result.risk_reasons,
        ) = cls._calculate_risk(result, text)

        # Interpretation
        result.meaning = cls._generate_meaning(result, text)

        result.legal_reference_explanations = (
            cls._generate_legal_reference_explanations(result)
        )

        result.user_impact = cls._generate_user_impact(result)
        result.why_important = cls._generate_why_important(result, text)
        result.potential_concerns = cls._generate_potential_concerns(result, text)
        result.recommendations = cls._generate_recommendations(result)

        return result

    # ================================================================
    # Text helpers
    # ================================================================

    @staticmethod
    def _clean(text: str) -> str:
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        result = []
        seen = set()

        for value in values:
            clean = str(value).strip()

            if not clean:
                continue

            key = clean.casefold()

            if key not in seen:
                seen.add(key)
                result.append(clean)

        return result

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        """
        Split contract text into substantive sentences.

        Contract documents frequently contain line breaks in the middle
        of a sentence because of PDF/DOCX formatting. Therefore, a
        newline alone must not automatically create a new sentence.

        Sentence boundaries are primarily determined by terminal
        punctuation. Newlines are treated as whitespace unless the
        surrounding text clearly indicates a new paragraph/heading.
        """

        normalized = re.sub(
            r"[ \t]*\n[ \t]*",
            " ",
            text,
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        parts = re.split(
            r"(?<=[.!?;])\s+",
            normalized,
        )

        return [
            part.strip()
            for part in parts
            if part.strip()
        ]

    @staticmethod
    def _is_heading(sentence: str) -> bool:
        """
        Return True when a sentence is likely to be a clause heading
        rather than substantive contractual text.
        """

        value = sentence.strip()

        if not value:
            return True

        # Numbered headings such as "1. PAYMENT"
        if re.match(
            r"^\d+(?:\.\d+)*\.?\s+[A-Z][A-Z\s_-]{2,}$",
            value,
        ):
            return True

        # Plain uppercase headings such as "CONFIDENTIALITY"
        if (
            len(value) <= 80
            and value.upper() == value
            and re.search(r"[A-Z]", value)
            and not re.search(r"[.!?]", value)
        ):
            return True

        return False


    @classmethod
    def _keyword_sentences(
        cls,
        text: str,
        keywords: list[str],
    ) -> list[str]:
        found = []

        for sentence in cls._sentences(text):
            if cls._is_heading(sentence):
                continue

            lower = sentence.lower()

            for keyword in keywords:
                keyword_lower = keyword.lower().strip()

                if not keyword_lower:
                    continue

                # Multi-word phrases can safely use substring matching.
                if " " in keyword_lower:
                    matched = keyword_lower in lower
                else:
                    # Single words require word boundaries so that
                    # "pay" does not match "repayment", etc.
                    pattern = (
                        r"(?<!\w)"
                        + re.escape(keyword_lower)
                        + r"(?!\w)"
                    )
                    matched = re.search(pattern, lower) is not None

                if matched:
                    found.append(sentence)
                    break

        return cls._unique(found)

    @classmethod
    def _extract_by_patterns(
        cls,
        text: str,
        patterns: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> list[str]:
        """
        Extract complete sentences matching at least one pattern.

        Optional exclude_patterns allow a legal effect to take precedence
        over a broader pattern. For example, "shall not" matches the broad
        obligation pattern "shall", but the sentence should be classified
        as a prohibition rather than an obligation.
        """
        found = []

        exclude_patterns = exclude_patterns or []

        for sentence in cls._sentences(text):
            excluded = False

            for pattern in exclude_patterns:
                try:
                    if re.search(
                        pattern,
                        sentence,
                        re.IGNORECASE,
                    ):
                        excluded = True
                        break
                except re.error:
                    continue

            if excluded:
                continue

            for pattern in patterns:
                try:
                    if re.search(
                        pattern,
                        sentence,
                        re.IGNORECASE,
                    ):
                        if sentence.strip().endswith(":"):
                            continue

                        found.append(sentence.strip())
                        break

                except re.error:
                    continue

        lines = [
            line.strip()
            for line in text.replace(
                "\r\n",
                "\n",
            ).replace(
                "\r",
                "\n",
            ).split("\n")
        ]

        for index, line in enumerate(lines):

            if not line:
                continue

            if not line.endswith(":"):
                continue

            heading_matches_pattern = False

            for pattern in patterns:
                try:
                    if re.search(
                        pattern,
                        line,
                        re.IGNORECASE,
                    ):
                        heading_matches_pattern = True
                        break

                except re.error:
                    continue

            if not heading_matches_pattern:
                continue

            for next_line in lines[index + 1:]:

                if not next_line:
                    break

                bullet_match = re.match(
                    r"^(?:[-*•]|\(?[a-zA-Z0-9]+\)|\d+[.)])\s+(.+)$",
                    next_line,
                )

                if not bullet_match:
                    break

                bullet_text = bullet_match.group(1).strip()

                if bullet_text:
                    found.append(bullet_text)

        return cls._unique(found)

    @classmethod
    def _regex_extract(
        cls,
        text: str,
        pattern: str,
    ) -> list[str]:
        try:
            return cls._unique(
                [
                    match.group(0).strip()
                    for match in re.finditer(
                        pattern,
                        text,
                        re.IGNORECASE,
                    )
                ]
            )
        except re.error:
            return []

    # ================================================================
    # Entity extraction
    # ================================================================

    @classmethod
    def _extract_parties(cls, text: str) -> list[str]:
        found = []

        for word in cls.PARTY_WORDS:
            if re.search(
                rf"\b{re.escape(word)}\b",
                text,
                re.IGNORECASE,
            ):
                found.append(word.title())

        return cls._unique(found)

    @classmethod
    def _extract_organizations(cls, text: str) -> list[str]:
        """
        Extract named organizations using legal-entity suffixes.

        Examples:
            ABC Solutions Pvt. Ltd.
            Tata Consultancy Services Limited
            Microsoft Corporation
            HDFC Bank
        """

        if not text:
            return []

        patterns = [
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Pvt\.?\s+Ltd\.?\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Private\s+Limited\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Public\s+Limited\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Limited\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Ltd\.?\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Corporation\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Corp\.?\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Inc\.?\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}(?:LLC|LLP|PLC)\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Bank\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}University\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Institute\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Foundation\b",
            r"\b(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}Authority\b",
        ]

        found = []

        for pattern in patterns:
            try:
                matches = re.finditer(
                    pattern,
                    text,
                )
            except re.error:
                continue

            for match in matches:
                value = match.group(0).strip()
                value = re.sub(r"\s+", " ", value)
                value = value.rstrip(".,;:")

                if not value:
                    continue

                lower_value = value.casefold()

                # Reject generic contractual phrases.
                if lower_value in {
                    "the company",
                    "the bank",
                    "the authority",
                    "the institute",
                    "the university",
                    "the foundation",
                }:
                    continue

                # Reject candidates containing obvious sentence fragments.
                blocked_phrases = [
                    "made by and between",
                    "payments shall",
                    "payment shall",
                    "shall be made",
                    "account specified",
                    "this agreement",
                    "the client",
                    "the company",
                ]

                if any(
                    phrase in lower_value
                    for phrase in blocked_phrases
                ):
                    continue

                found.append(value)

        return cls._unique(found)


    @classmethod
    def _extract_authorities(cls, text: str) -> list[str]:
        """
        Extract sentences referring to genuine governmental,
        regulatory, judicial, or public authorities.
        """

        if not text:
            return []

        found = cls._keyword_sentences(
            text,
            [
                "government",
                "ministry",
                "department",
                "authority",
                "agency",
                "regulator",
                "regulatory authority",
                "commission",
                "court",
                "courts",
                "tribunal",
                "municipality",
                "local authority",
                "police",
                "central bank",
                "tax authority",
            ],
        )

        filtered = []

        for sentence in found:
            lower_sentence = sentence.casefold()

            # Commercial banking references are not authorities.
            if (
                "bank account" in lower_sentence
                or "bank details" in lower_sentence
                or "bank transfer" in lower_sentence
                or "bank payment" in lower_sentence
                or "account specified" in lower_sentence
            ):
                continue

            filtered.append(sentence)

        return cls._unique(filtered)

    # ================================================================
    # Time / money
    # ================================================================

    @classmethod
    def _extract_dates(cls, text: str) -> list[str]:
        found = []

        for pattern in cls.DATE_PATTERNS:
            found.extend(
                cls._regex_extract(text, pattern)
            )

        return cls._unique(found)

    @classmethod
    def _extract_money(cls, text: str) -> list[str]:
        """
        Extract monetary values such as:

            INR 75,000
            USD 1,500
            Rs. 75,000
            $1,500
            75,000 rupees
        """

        return cls._regex_extract(
            text,
            cls.MONEY_PATTERN,
        )

    @classmethod
    def _extract_currencies(cls, text: str) -> list[str]:
        """
        Extract currency identifiers and currency names.
        """

        patterns = [
            r"\bINR\b",
            r"\bUSD\b",
            r"\bEUR\b",
            r"\bGBP\b",
            r"\bJPY\b",
            r"\bAUD\b",
            r"\bCAD\b",
            r"\u20b9",
            r"\$",
            r"\u20ac",
            r"\u00a3",
            r"\u00a5",
            r"\brupees?\b",
            r"\bdollars?\b",
            r"\beuros?\b",
            r"\bpounds?\b",
            r"\byen\b",
        ]

        found = []

        for pattern in patterns:
            found.extend(
                cls._regex_extract(text, pattern)
            )

        return cls._unique(found)

    @classmethod
    def _extract_quantities(cls, text: str) -> list[str]:
        patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:g|grams?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:km|kilometers?|kilometres?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:m|meters?|metres?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:litres?|liters?|L)\b",
            r"\b\d+(?:\.\d+)?\s*(?:units?|items?|shares?)\b",
        ]

        found = []

        for pattern in patterns:
            found.extend(
                cls._regex_extract(text, pattern)
            )

        return cls._unique(found)
    
    @classmethod
    def _extract_quantities(cls, text: str) -> list[str]:
        patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:g|grams?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:km|kilometers?|kilometres?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:m|meters?|metres?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:litres?|liters?|L)\b",
            r"\b\d+(?:\.\d+)?\s*(?:units?|items?|shares?)\b",
        ]

        found = []

        for pattern in patterns:
            found.extend(
                cls._regex_extract(text, pattern)
            )

        return cls._unique(found)

    # ================================================================
    # Legal references
    # ================================================================

    @classmethod
    def _extract_legal(
        cls,
        text: str,
        category: str,
    ) -> list[str]:
        """
        Extract legal references.

        Legal-reference patterns are handled separately from the generic
        regex extractor because some patterns intentionally use
        capitalization to distinguish named legal instruments from
        generic phrases such as "the law" or "applicable law".
        """

        found = []

        for pattern in cls.LEGAL_REFERENCE_PATTERNS.get(
            category,
            [],
        ):
            try:
                matches = re.finditer(
                    pattern,
                    text,
                )

                for match in matches:
                    value = match.group(0).strip()

                    if value:
                        found.append(value)

            except re.error:
                continue

        return cls._unique(found)

    @classmethod
    def _extract_jurisdiction(cls, text: str) -> list[str]:
        """
        Extract likely jurisdiction or venue locations.

        Jurisdiction references are detected only when a location is
        explicitly connected to courts, jurisdiction, or venue.
        """

        patterns = [
            # "courts of Hyderabad shall have exclusive jurisdiction"
            r"\bcourts?\s+of\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will)\b|[.,;]|$)",

            # "courts in Hyderabad shall ..."
            r"\bcourts?\s+in\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will)\b|[.,;]|$)",

            # "jurisdiction of Hyderabad"
            r"\bjurisdiction\s+of\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will|be)\b|[.,;]|$)",

            # "jurisdiction in Hyderabad"
            r"\bjurisdiction\s+in\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will|be)\b|[.,;]|$)",

            # "within the jurisdiction of Hyderabad"
            r"\bwithin\s+the\s+jurisdiction\s+of\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will|be)\b|[.,;]|$)",

            # "venue in Hyderabad"
            r"\bvenue\s+in\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will|be)\b|[.,;]|$)",

            # "venue of Hyderabad"
            r"\bvenue\s+of\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*?)(?=\s+(?:shall|must|may|has|have|is|are|will|be)\b|[.,;]|$)",
        ]

        found = []

        for pattern in patterns:
            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE,
            )

            for value in matches:
                value = value.strip(" .,:;")

                if not value:
                    continue

                if value.casefold() in {
                    "the",
                    "the courts",
                    "the parties",
                    "the law",
                    "the applicable law",
                }:
                    continue

                found.append(value)

        return cls._unique(found)


    # ================================================================
    # Legal-reference explanations
    # ================================================================

    @classmethod
    def _generate_legal_reference_explanations(
        cls,
        result: ClauseAnalysis,
    ) -> list[str]:
        """
        Generate safe, general-language explanations for detected
        legal references.

        This explains the type and general purpose of a reference.
        It does not invent the exact meaning of an unknown law,
        section, regulation, or case.

        A later legal-knowledge/RAG layer can provide authoritative,
        source-backed explanations for specific references.
        """

        explanations = []

        if result.laws:
            for reference in result.laws:
                explanations.append(
                    f"{reference}: This is a reference to a law. "
                    "The clause is relying on that law or its requirements."
                )

        if result.statutes:
            for reference in result.statutes:
                explanations.append(
                    f"{reference}: This is a reference to a statute, "
                    "meaning a law formally enacted by a legislative authority."
                )

        if result.regulations:
            for reference in result.regulations:
                explanations.append(
                    f"{reference}: This is a reference to a regulation. "
                    "Regulations generally provide detailed rules or requirements "
                    "made under legal authority."
                )

        if result.sections:
            for reference in result.sections:
                explanations.append(
                    f"{reference}: This identifies a particular section "
                    "of a law or other legal document. "
                    "The exact rule should be checked in the referenced section."
                )

        if result.articles:
            for reference in result.articles:
                explanations.append(
                    f"{reference}: This identifies a particular article "
                    "within a legal document, statute, regulation, treaty, "
                    "or similar legal instrument."
                )

        if result.rules:
            for reference in result.rules:
                explanations.append(
                    f"{reference}: This is a reference to a legal or "
                    "procedural rule that may establish a requirement or process."
                )

        if result.case_references:
            for reference in result.case_references:
                explanations.append(
                    f"{reference}: This appears to refer to a court case, "
                    "judgment, or judicial proceeding. "
                    "The referenced decision should be checked to understand "
                    "its exact relevance."
                )

        return cls._unique(explanations)


    # ================================================================
    # Meaning
    # ================================================================

    @classmethod
    def _generate_meaning(
        cls,
        result: ClauseAnalysis,
        text: str,
    ) -> str:
        """
        Generate a concise deterministic plain-language interpretation.

        The current analysis layer is intentionally rule-based.
        A later AI/LLM layer can provide richer contextual explanations.
        """

        parts = []

        # ------------------------------------------------------------
        # Local helpers
        # ------------------------------------------------------------

        def clean_fragment(value: str) -> str:
            value = " ".join(
                str(value).replace("\n", " ").split()
            )

            value = value.strip(" ;,:")

            # Avoid duplicated terminal punctuation when a fragment
            # already ends with a sentence terminator.
            value = value.rstrip(".")

            return value

        def unique_fragments(values) -> list[str]:
            cleaned = []

            for value in values:
                value = clean_fragment(value)

                if not value:
                    continue

                if value not in cleaned:
                    cleaned.append(value)

            return cleaned

        def sentence_without_overlap(
            values,
            excluded,
        ) -> list[str]:
            result_values = []

            excluded_text = {
                clean_fragment(value).casefold()
                for value in excluded
            }

            for value in values:
                cleaned = clean_fragment(value)

                if not cleaned:
                    continue

                if cleaned.casefold() in excluded_text:
                    continue

                result_values.append(cleaned)

            return result_values

        # ------------------------------------------------------------
        # Obligations / duties
        # ------------------------------------------------------------

        raw_obligation_sentences = unique_fragments(
            result.obligations
        )

        # Some contractual sentences contain words such as "shall" or
        # "must" but describe legal applicability rather than an actual
        # duty. Do not present those as obligations in plain-language
        # meaning.
        obligation_exclusions = (
            "shall be governed by",
            "shall be subject to",
            "shall be construed",
            "shall be interpreted",
            "shall apply",
            "shall form part of",
            "must be governed by",
            "must be subject to",
            "must be construed",
            "must be interpreted",
        )

        obligation_sentences = []

        for sentence in raw_obligation_sentences:
            lower_sentence = sentence.casefold()

            if any(
                phrase in lower_sentence
                for phrase in obligation_exclusions
            ):
                continue

            obligation_sentences.append(sentence)

        if obligation_sentences:
            if len(obligation_sentences) == 1:
                parts.append(
                    "It requires: "
                    + obligation_sentences[0]
                )
            else:
                parts.append(
                    "It creates these requirements: "
                    + "; ".join(obligation_sentences)
                    + "."
                )

        # ------------------------------------------------------------
        # Rights / permissions
        # ------------------------------------------------------------

        right_sentences = unique_fragments(
            result.rights + result.permissions
        )

        if right_sentences:
            if len(right_sentences) == 1:
                parts.append(
                    "It gives a right or permission to: "
                    + right_sentences[0]
                )
            else:
                parts.append(
                    "It provides these rights or permissions: "
                    + "; ".join(right_sentences)
                    + "."
                )

        # ------------------------------------------------------------
        # Prohibitions
        # ------------------------------------------------------------

        prohibition_sentences = unique_fragments(
            result.prohibitions
        )

        if prohibition_sentences:
            if len(prohibition_sentences) == 1:
                parts.append(
                    "It restricts: "
                    + prohibition_sentences[0]
                )
            else:
                parts.append(
                    "It contains these restrictions: "
                    + "; ".join(prohibition_sentences)
                    + "."
                )

        # ------------------------------------------------------------
        # Conditions
        # ------------------------------------------------------------

        # Governing-law statements and dispute applicability can also
        # contain words such as "subject to". They should not be presented
        # as generic conditions.
        governing_law_sentences = unique_fragments(
            result.governing_law
        )

        dispute_sentences = unique_fragments(
            result.dispute_terms
        )

        condition_sentences = sentence_without_overlap(
            result.conditions,
            obligation_sentences
            + governing_law_sentences
            + dispute_sentences,
        )

        if condition_sentences:
            parts.append(
                "It applies under these conditions: "
                + "; ".join(condition_sentences)
                + "."
            )

        # ------------------------------------------------------------
        # Governing law
        # ------------------------------------------------------------

        if governing_law_sentences:
            if len(governing_law_sentences) == 1:
                parts.append(
                    "It specifies the governing law: "
                    + governing_law_sentences[0]
                    + "."
                )
            else:
                parts.append(
                    "It specifies the following governing-law provisions: "
                    + "; ".join(governing_law_sentences)
                    + "."
                )

        # ------------------------------------------------------------
        # Triggers
        # ------------------------------------------------------------

        trigger_sentences = sentence_without_overlap(
            result.triggers,
            obligation_sentences + condition_sentences,
        )

        if trigger_sentences:
            parts.append(
                "It is triggered by: "
                + "; ".join(trigger_sentences)
                + "."
            )

        # ------------------------------------------------------------
        # Consequences
        # ------------------------------------------------------------

        consequence_sentences = unique_fragments(
            result.consequences
        )

        if consequence_sentences:
            parts.append(
                "It specifies these consequences: "
                + "; ".join(consequence_sentences)
                + "."
            )

        # ------------------------------------------------------------
        # Financial terms
        # ------------------------------------------------------------

        monetary_terms = unique_fragments(
            result.monetary_terms
        )

        if monetary_terms and not obligation_sentences:
            parts.append(
                "It contains monetary terms such as: "
                + ", ".join(monetary_terms)
                + "."
            )

        # ------------------------------------------------------------
        # Timing
        # ------------------------------------------------------------

        timing = unique_fragments(
            result.dates
            + result.deadlines
            + result.durations
        )

        if timing and not obligation_sentences:
            parts.append(
                "The relevant timing includes: "
                + ", ".join(timing)
                + "."
            )

        # ------------------------------------------------------------
        # Disputes / jurisdiction
        # ------------------------------------------------------------

        if result.dispute_terms:
            parts.append(
                "It addresses dispute resolution or enforcement."
            )

        if result.jurisdiction:
            parts.append(
                "It specifies or affects the applicable jurisdiction."
            )

        if result.arbitration:
            parts.append(
                "It contains an arbitration-related provision."
            )

        # ------------------------------------------------------------
        # Privacy / data
        # ------------------------------------------------------------

        if result.data_terms or result.privacy_terms:
            parts.append(
                "It addresses data, privacy, or information-handling matters."
            )

        # ------------------------------------------------------------
        # Employment
        # ------------------------------------------------------------

        if result.employment_terms:
            parts.append(
                "It concerns employment-related terms."
            )

        # ------------------------------------------------------------
        # Loans
        # ------------------------------------------------------------

        if result.loan_terms:
            parts.append(
                "It concerns loan, credit, financing, or repayment terms."
            )

        # ------------------------------------------------------------
        # Property
        # ------------------------------------------------------------

        if result.property_terms:
            parts.append(
                "It concerns property, ownership, possession, or related terms."
            )

        # ------------------------------------------------------------
        # Intellectual property
        # ------------------------------------------------------------

        if result.intellectual_property_terms:
            parts.append(
                "It concerns intellectual-property rights or restrictions."
            )

        # ------------------------------------------------------------
        # Confidentiality
        # ------------------------------------------------------------

        if result.confidentiality_terms:
            parts.append(
                "It creates confidentiality or non-disclosure requirements."
            )

        # ------------------------------------------------------------
        # Legal references
        # ------------------------------------------------------------

        legal_references = unique_fragments(
            result.legal_references
        )

        if legal_references:
            if len(legal_references) == 1:
                parts.append(
                    "It refers to "
                    + legal_references[0]
                    + "."
                )
            else:
                parts.append(
                    "It refers to these legal instruments or provisions: "
                    + "; ".join(legal_references)
                    + "."
                )

        # ------------------------------------------------------------
        # Fallback
        # ------------------------------------------------------------

        if not parts:
            cleaned_text = clean_fragment(text)

            if cleaned_text:
                return (
                    "This provision generally states: "
                    + cleaned_text
                )

            return (
                "This provision defines the relationship or general "
                "terms between the parties."
            )

        return " ".join(parts)


    # Risk
    # ================================================================

    @classmethod
    def _calculate_risk(
        cls,
        result: ClauseAnalysis,
        text: str,
    ) -> tuple[str, int, list[str]]:
        lower = text.lower()

        score = 0
        reasons = []

        # ============================================================
        # HIGH-RISK INDICATORS
        # ============================================================

        high_rules = [
            (
                "unlimited liability",
                60,
                "The provision may create potentially unlimited liability."
            ),
            (
                "indemnify",
                35,
                "The provision may require one party to cover losses or claims."
            ),
            (
                "indemnification",
                35,
                "The provision may require one party to cover losses or claims."
            ),
            (
                "personal guarantee",
                45,
                "The provision may create personal financial responsibility."
            ),
            (
                "personal guarantor",
                45,
                "The provision may create personal financial responsibility."
            ),
            (
                "collateral",
                35,
                "The provision involves security or collateral."
            ),
            (
                "security interest",
                35,
                "The provision may create rights over assets or security."
            ),
            (
                "acceleration",
                35,
                "The provision may make outstanding amounts immediately payable."
            ),
            (
                "without notice",
                25,
                "The provision may permit action without prior notice."
            ),
            (
                "irrevocable",
                30,
                "The provision describes an action or authority as irrevocable."
            ),
            (
                "non-compete",
                30,
                "The provision may impose a significant restriction on activities."
            ),
            (
                "non compete",
                30,
                "The provision may impose a significant restriction on activities."
            ),
        ]

        # ============================================================
        # MEDIUM-RISK INDICATORS
        # ============================================================

        medium_rules = [
            (
                "penalty",
                20,
                "The provision contains a penalty or financial consequence."
            ),
            (
                "late fee",
                15,
                "Late action may result in an additional financial charge."
            ),
            (
                "default",
                20,
                "The provision contains default-related consequences."
            ),
            (
                "breach",
                20,
                "The provision contains breach-related consequences."
            ),
            (
                "termination",
                10,
                "The provision contains termination-related rights or conditions."
            ),
            (
                "terminate",
                10,
                "The provision contains termination-related rights or conditions."
            ),
            (
                "confidential",
                5,
                "The provision creates confidentiality responsibilities."
            ),
            (
                "jurisdiction",
                5,
                "The provision affects where legal proceedings may occur."
            ),
            (
                "arbitration",
                10,
                "The provision requires or refers to arbitration."
            ),
            (
                "guarantee",
                15,
                "The provision may create a guarantee obligation."
            ),
            (
                "interest rate",
                10,
                "The provision contains an interest-rate term."
            ),
        ]

        for phrase, weight, reason in high_rules:
            if phrase in lower:
                score += weight
                reasons.append(reason)

        for phrase, weight, reason in medium_rules:
            if phrase in lower:
                score += weight
                reasons.append(reason)

        # ============================================================
        # FINANCIAL OBLIGATION
        # ============================================================

        if result.monetary_terms:
            score += 10
            reasons.append(
                "The provision contains a financial obligation or monetary amount."
            )

        # ============================================================
        # PAYMENT + DEADLINE
        # ============================================================

        payment_words = [
            "payment",
            "pay",
            "payable",
            "invoice",
            "fee",
            "amount",
            "repayment",
        ]

        has_payment_language = any(
            word in lower
            for word in payment_words
        )

        if result.monetary_terms and has_payment_language:
            score += 10
            reasons.append(
                "The provision creates a financial payment obligation."
            )

        if result.monetary_terms and result.deadlines:
            score += 10
            reasons.append(
                "The provision combines a financial obligation with a deadline."
            )

        # ============================================================
        # FEES
        # ============================================================

        if result.fees:
            score += 10
            reasons.append(
                "The provision contains fees or charges that may create financial impact."
            )

        # ============================================================
        # PENALTIES
        # ============================================================

        if result.penalties:
            score += 20
            reasons.append(
                "The provision contains penalties or additional financial consequences."
            )

        # ============================================================
        # LOAN / BANKING TERMS
        # ============================================================

        loan_terms = [
            "loan",
            "borrower",
            "lender",
            "principal",
            "interest",
            "interest rate",
            "emi",
            "installment",
            "instalment",
            "repayment",
            "credit facility",
            "loan amount",
        ]

        matched_loan_terms = [
            term
            for term in loan_terms
            if term in lower
        ]

        if matched_loan_terms:
            score += 10
            reasons.append(
                "The provision contains loan or credit-related financial terms."
            )

        # ============================================================
        # DEFAULT / CONSEQUENCES
        # ============================================================

        if result.consequences:
            score += 10
            reasons.append(
                "The provision specifies consequences that may affect a party."
            )

        # ============================================================
        # RESTRICTIONS
        # ============================================================

        if result.prohibitions:
            score += 5
            reasons.append(
                "The provision contains restrictions or prohibitions."
            )

        if len(result.prohibitions) >= 2:
            score += 10
            reasons.append(
                "The provision contains multiple restrictions or prohibitions."
            )

        # ============================================================
        # LIABILITY LIMITATION
        # ============================================================

        liability_terms = [
            "not be liable",
            "shall not be liable",
            "limitation of liability",
            "exclude liability",
            "indirect damages",
            "consequential damages",
        ]

        if any(term in lower for term in liability_terms):
            score += 20
            reasons.append(
                "The provision limits or excludes liability for certain losses."
            )

        # ============================================================
        # LEGAL / DISPUTE TERMS
        # ============================================================

        if result.legal_references and result.consequences:
            score += 5
            reasons.append(
                "The provision combines legal references with stated consequences."
            )

        if result.dispute_terms:
            score += 10
            reasons.append(
                "The provision contains dispute or enforcement-related terms."
            )

        if result.jurisdiction:
            score += 5
            reasons.append(
                "The provision specifies jurisdiction or applicable legal authority."
            )

        # ============================================================
        # CAP SCORE
        # ============================================================

        score = min(score, 100)

        reasons = cls._unique(reasons)

        # ============================================================
        # RISK LEVEL
        # ============================================================

        if score >= 60:
            level = "HIGH"
        elif score >= 20:
            level = "MEDIUM"
        else:
            level = "LOW"

        if not reasons:
            reasons = [
                "No major risk indicator was detected by the current deterministic rules."
            ]

        return level, score, reasons

    # ================================================================
    # Impact
    # ================================================================

    @staticmethod
    def _generate_user_impact(
        result: ClauseAnalysis,
    ) -> str:
        categories = []

        mapping = [
            (result.obligations, "obligations or duties"),
            (result.rights, "rights or permissions"),
            (result.prohibitions, "restrictions"),
            (result.conditions, "conditions"),
            (result.dates + result.deadlines, "timing"),
            (result.monetary_terms, "financial terms"),
            (result.legal_references, "legal or regulatory references"),
            (result.case_references, "judicial references"),
            (result.data_terms, "data or privacy matters"),
            (result.employment_terms, "employment matters"),
            (result.loan_terms, "loan or credit matters"),
            (result.property_terms, "property matters"),
            (result.dispute_terms, "dispute or enforcement matters"),
            (result.intellectual_property_terms, "intellectual property matters"),
        ]

        for values, label in mapping:
            if values:
                categories.append(label)

        categories = ClauseAnalysisService._unique(categories)

        if not categories:
            return (
                "No specific impact category was confidently "
                "identified by the current deterministic analysis."
            )

        return (
            "This provision contains "
            + ", ".join(categories)
            + " that may affect the relevant reader or parties."
        )

    # ================================================================
    # Recommendations
    # ================================================================

    @classmethod
    def _generate_recommendations(
        cls,
        result: ClauseAnalysis,
    ) -> list[str]:
        recommendations = []

        if result.obligations:
            recommendations.append(
                "Identify who is responsible for each obligation or duty."
            )

        if result.rights or result.permissions:
            recommendations.append(
                "Identify who receives each right, permission, or authority."
            )

        if result.prohibitions:
            recommendations.append(
                "Review the scope of each restriction and any exceptions."
            )

        if result.conditions or result.triggers:
            recommendations.append(
                "Identify the events or conditions that activate the provision."
            )

        if result.dates or result.deadlines or result.durations:
            recommendations.append(
                "Verify all dates, deadlines, notice periods, and durations."
            )

        if result.monetary_terms:
            recommendations.append(
                "Verify amounts, rates, fees, payment terms, and calculation methods."
            )

        if result.penalties:
            recommendations.append(
                "Check when penalties or financial consequences become applicable."
            )

        if result.legal_references:
            recommendations.append(
                "Verify the cited law, regulation, section, rule, or legal reference."
            )

        if result.case_references:
            recommendations.append(
                "Verify the referenced case, judgment, court decision, or proceeding."
            )

        if result.data_terms or result.privacy_terms:
            recommendations.append(
                "Check what data is collected, used, shared, stored, and retained."
            )

        if result.confidentiality_terms:
            recommendations.append(
                "Check what information is protected, permitted disclosures, and duration."
            )

        if result.loan_terms:
            recommendations.append(
                "Review principal, interest, repayment, default, security, and related conditions."
            )

        if result.employment_terms:
            recommendations.append(
                "Review duties, compensation, benefits, leave, notice, and employment conditions."
            )

        if result.property_terms:
            recommendations.append(
                "Review ownership, possession, property description, rent, and related conditions."
            )

        if result.intellectual_property_terms:
            recommendations.append(
                "Review ownership, licensing, permitted use, and restrictions on intellectual property."
            )

        if result.dispute_terms or result.jurisdiction:
            recommendations.append(
                "Review dispute procedures, jurisdiction, venue, and available remedies."
            )

        if result.risk_level in {"MEDIUM", "HIGH"}:
            recommendations.append(
                "Review this provision together with related provisions elsewhere in the document."
            )

        if not recommendations:
            recommendations.append(
                "Review this provision together with the surrounding document for context."
            )

        return cls._unique(recommendations)

    @classmethod
    def _generate_why_important(
        cls,
        result: ClauseAnalysis,
        text: str,
    ) -> list[str]:
        points = []
        clause_type = (result.clause_type or "").upper()
        lower_text = text.lower()

        if clause_type == "TERMINATION":
            points.append("This defines how the agreement can be terminated.")
            if result.deadlines or result.notice_terms:
                notice_str = result.deadlines[0] if result.deadlines else "A specified notice period"
                points.append(f"{notice_str} applies to ordinary termination.")
            elif re.search(r"\bimmediate(?:ly)?|without prior notice\b", lower_text):
                points.append("Allows immediate contract termination under breach conditions.")
        elif clause_type == "PAYMENT":
            points.append("Establishes binding financial commitments, billing frequency, and payment schedules.")
            if result.deadlines:
                points.append(f"Requires payments to be settled within {result.deadlines[0]}.")
            if result.penalties or result.fees or re.search(r"\blate\s+fee|interest\b", lower_text):
                points.append("Delayed payments may incur interest charges, late fees, or service suspension.")
        elif clause_type in {"DATA_PROTECTION", "PRIVACY"}:
            points.append("Governs how personal, customer, or confidential data is collected, handled, and safeguarded.")
            if re.search(r"\bthird\s*part|subprocessor\b", lower_text):
                points.append("Regulates sharing and transmission of protected data to third-party providers.")
        elif clause_type in {"LIABILITY", "INDEMNITY"}:
            points.append("Allocates legal risk and defines monetary recovery limits between the parties.")
            if re.search(r"\bindemnif|hold harmless\b", lower_text):
                points.append("Requires one party to defend and financially protect the other against third-party claims.")
            if re.search(r"\bconsequential|indirect|incidental\b", lower_text):
                points.append("Excludes liability for indirect, punitive, or consequential losses.")
        elif clause_type == "CONFIDENTIALITY":
            points.append("Restricts disclosure of proprietary business information and trade secrets.")
            if re.search(r"\bsurvive\b", lower_text):
                points.append("Confidentiality duties survive the termination of this agreement.")
        elif clause_type in {"RENEWAL", "DURATION"}:
            points.append("Controls how the agreement is extended and may auto-renew unless cancelled.")

        if result.risk_reasons:
            for r in result.risk_reasons:
                if r and r not in points:
                    points.append(r)

        if not points:
            if len(text.strip()) < 25:
                points.append("Specific operational impacts cannot be determined from the available text.")
            else:
                title = result.title or "Contract clause"
                points.append(f"Defines binding operational requirements and legal duties for {title.lower()}.")

        return cls._unique(points)[:4]

    @classmethod
    def _generate_potential_concerns(
        cls,
        result: ClauseAnalysis,
        text: str,
    ) -> list[str]:
        concerns = []
        raw = (text or "").strip()
        if not raw:
            return ["No substantive clause text was available to evaluate potential concerns."]

        # 1. Blank or missing values (e.g. __________, [_____], [insert ...], [TBD], $___)
        blank_pattern = r"(?:_{2,}|\[\s*_{2,}\s*\]|\[\s*\]|\[\s*(?:insert|insert\s+here|tbd|to\s+be\s+determined|date|amount|name|party)\b[^\]]*\]|\$__+)"
        if re.search(blank_pattern, raw, re.IGNORECASE):
            concerns.append("A value appears to be missing from the available text. Verify the complete original document.")

        # 2. Incomplete sentences or truncated text
        is_truncated = (
            bool(re.search(r"(?:\.{3,}|…)\s*$", raw))
            or bool(re.search(r"[,;:\-\–]\s*$", raw))
            or bool(re.search(r"\b(?:if|unless|provided\s+that|subject\s+to|and|or|with\s+respect\s+to|such\s+as)\s*$", raw, re.IGNORECASE))
        )
        if is_truncated:
            concerns.append("The clause appears to be truncated or incomplete at the end. Check the complete source contract.")

        # 3. References to missing exhibits, schedules, annexures, appendices
        exhibit_match = re.search(
            r"\b(Exhibit\s+[A-Z0-9]+(?:\s*:\s*[^,.;]+)?|Schedule\s+[A-Z0-9]+|Annexure\s+[A-Z0-9]+|Appendix\s+[A-Z0-9]+|Attachment\s+[A-Z0-9]+|Addendum\s+[A-Z0-9]+|Order\s+Form|Statement\s+of\s+Work|\bSOW\b)",
            raw,
            re.IGNORECASE,
        )
        if exhibit_match:
            doc_ref = exhibit_match.group(1).strip()
            if re.search(r"Exhibit\s+A(?:\s*:\s*Scope\s+of\s+Services)?", doc_ref, re.IGNORECASE):
                concerns.append("The clause depends on Exhibit A for the scope of services, but the referenced content is not present in the available contract text.")
                concerns.append("Verify Exhibit A before accepting the agreement.")
            else:
                concerns.append(f"The clause refers to {doc_ref}, which is not detailed in the available text. Verify the referenced document before accepting.")

        # Reference to other internal sections: "subject to Section X", "as defined in Section Y"
        section_ref_match = re.search(
            r"\b(?:subject\s+to|as\s+(?:set\s+forth|defined|described)\s+in)\s+(Section\s+[0-9A-Za-z.-]+|Article\s+[0-9A-Za-z.-]+|Clause\s+[0-9A-Za-z.-]+)",
            raw,
            re.IGNORECASE,
        )
        if section_ref_match:
            concerns.append(f"The clause is {section_ref_match.group(0).lower()}. Verify {section_ref_match.group(1)} to understand how it modifies or limits this provision.")

        # 4. Undefined / ambiguous wording
        if re.search(r"\breasonable\s+efforts\b", raw, re.IGNORECASE):
            concerns.append('The term "reasonable efforts" is not specifically defined in the available text. Check whether the agreement defines this standard elsewhere.')
        elif re.search(r"\bbest\s+efforts\b", raw, re.IGNORECASE):
            concerns.append('The term "best efforts" establishes a heightened standard that is not specifically defined in the available text. Clarify the expected scope.')
        elif re.search(r"\bcommercially\s+reasonable(?:\s+efforts)?\b", raw, re.IGNORECASE):
            concerns.append('The standard "commercially reasonable" is subjective and not explicitly quantified in this clause. Check whether benchmark criteria exist.')

        if re.search(r"\b(?:at\s+its\s+sole\s+discretion|in\s+its\s+sole\s+discretion|sole\s+opinion)\b", raw, re.IGNORECASE):
            concerns.append('The phrase "at its sole discretion" gives one party unilateral control over this decision. This should be verified or clarified.')

        if re.search(r"\bmaterial\s+breach\b", raw, re.IGNORECASE) and not re.search(r"\bdefined\s+as\b", raw, re.IGNORECASE):
            concerns.append('The term "material breach" is not defined within this clause. Check whether the agreement defines what constitutes a material breach.')

        if re.search(r"\b(?:prompt\s+notice|promptly\s+notify)\b", raw, re.IGNORECASE) and not re.search(r"\b\d+\s*(?:business\s+days?|calendar\s+days?|days?|hours?)\b", raw, re.IGNORECASE):
            concerns.append('The clause requires "prompt notice" but does not define an exact number of business days or hours. Clarify the acceptable notice timeframe.')

        # 5. Unclear renewal or payment conditions
        clause_type = (result.clause_type or "").upper()
        if clause_type in {"RENEWAL", "DURATION"} or re.search(r"\bauto(?:matic(?:ally)?)?\s*renew", raw, re.IGNORECASE):
            if not re.search(r"\b\d+\s*(?:business\s+days?|calendar\s+days?|days?|months?|weeks?)\b", raw, re.IGNORECASE):
                concerns.append("The clause provides for automatic renewal, but the specific cancellation window or deadline is not specified in the available text.")

        if clause_type == "PAYMENT" and re.search(r"\b(?:additional\s+fees|expenses\s+shall\s+be\s+reimbursed|costs?\s+incurred|penalt(?:y|ies))\b", raw, re.IGNORECASE):
            if not (result.monetary_terms or result.percentages or re.search(r"\$\s*\d+|\b\d+\s*(?:dollars|usd|inr|eur|%|percent)\b", raw, re.IGNORECASE)):
                concerns.append("The clause references additional fees or expenses, but does not specify exact amounts or calculation limits in the available text.")

        unique_concerns = cls._unique(concerns)[:4]

        # 6. Complete clause with no concern
        if not unique_concerns:
            return ["No specific ambiguity or missing information was identified in the available clause text."]

        return unique_concerns

    # ================================================================
    # Batch analysis
    # ================================================================
    @classmethod
    def analyze(cls, clause):
        return cls.analyze_clause(clause)

    @classmethod
    def analyze_clauses(
        cls,
        clauses,
    ) -> list[ClauseAnalysis]:
        return [
            cls.analyze_clause(clause)
            for clause in clauses
        ]


