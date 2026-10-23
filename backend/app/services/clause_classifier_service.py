import re
from dataclasses import dataclass, replace
from typing import Any

from app.schemas.clause import Clause


@dataclass(frozen=True)
class RetrievedClause:
    clause_id: str
    clause_number: str | None
    title: str | None
    text: str
    score: float


class ClauseClassifierService:

    # ================================================================
    # HIGH-CONFIDENCE PRIMARY LEGAL PATTERNS
    # ================================================================

    PRIMARY_PATTERNS = {

        "CANCELLATION": [
            r"\bcancel\s+this\s+agreement\b",
            r"\bmay\s+cancel\b",
            r"\bcan\s+cancel\b",
            r"\bcancellation\s+of\s+this\s+agreement\b",
            r"\bcancellation\s+charge\b",
            r"\bcancellation\s+fee\b",
            r"\bcancel(?:lation)?\s+fee\b",
            r"\bcancel(?:lation)?\s+charge\b",
            r"\bnon[-\s]?refundable\b",
        ],

        "TERMINATION": [
            r"\bmay\s+terminate\b",
            r"\bcan\s+terminate\b",
            r"\bshall\s+terminate\b",
            r"\bterminate\s+this\s+agreement\b",
            r"\btermination\s+of\s+this\s+agreement\b",
            r"\bright\s+to\s+terminate\b",
            r"\bgrounds\s+for\s+termination\b",
            r"\btermination\s+upon\b",
            r"\btermination\s+for\s+cause\b",
            r"\btermination\s+without\s+cause\b",
        ],

        "EMPLOYMENT": [
            r"\bemployer\b",
            r"\bemployee\b",
            r"\bemployment\b",
            r"\bemployment\s+agreement\b",
            r"\bjob\s+duties\b",
            r"\bworking\s+hours\b",
            r"\bleave\s+entitlement\b",
            r"\bprobation\s+period\b",
            r"\bmonthly\s+salary\b",
            r"\bannual\s+salary\b",
        ],

        "PAYMENT": [
            r"\b(?:shall|must|will|agrees?\s+to)\s+pay\b",
            r"\bpay\s+[\d,]+",
            r"\bpayment\s+terms\b",
            r"\bpayment\s+schedule\b",
            r"\bamount\s+payable\b",
            r"\bfees?\s+(?:shall|must|will)\s+be\s+paid\b",
            r"\binvoice\s+(?:shall|must|will)\s+be\s+paid\b",
            r"\binterest\s+rate\b",
            r"\binterest\s+(?:at|on)\b",
            r"\brepayment\b",
            r"\brepay\b",
            r"\binstallments?\b",
            r"\binstalments?\b",
            r"\bmonthly\s+installment\b",
            r"\bmonthly\s+instalment\b",
            r"\bequated\s+monthly\s+installment\b",
            r"\bemi\b",
        ],

        "CONFIDENTIALITY": [
            r"\bkeep\s+.*\bconfidential\b",
            r"\bkeep\s+.*\bstrictly\s+confidential\b",
            r"\bmaintain\s+.*\bconfidentiality\b",
            r"\bshall\s+not\s+disclose\b",
            r"\bmust\s+not\s+disclose\b",
            r"\bwill\s+not\s+disclose\b",
            r"\bconfidential\s+information\b",
            r"\bnon[-\s]?disclosure\b",
            r"\bduty\s+of\s+confidentiality\b",
        ],

        "FORCE_MAJEURE": [
            r"\bforce\s+majeure\b",
            r"\bbeyond\s+(?:its\s+)?reasonable\s+control\b",
            r"\bact\s+of\s+god\b",
            r"\bnatural\s+disaster\b",
            r"\bforce\s+majeure\s+event\b",
        ],

        "ASSIGNMENT": [
            r"\bmay\s+assign\b",
            r"\bshall\s+not\s+assign\b",
            r"\bmust\s+not\s+assign\b",
            r"\bright\s+to\s+assign\b",
            r"\bassignment\s+of\s+this\s+agreement\b",
            r"\bassign\s+or\s+transfer\b",
            r"\bassign(?:ment)?\s+of\s+(?:the\s+)?loan\b",
            r"\bsell(?:s)?\s*/?\s*assign(?:s)?\b",
        ],

        "GOVERNING_LAW": [
            r"\bgoverned\s+by\s+the\s+laws?\s+of\b",
            r"\bgoverning\s+law\b",
            r"\bconstrued\s+in\s+accordance\s+with\s+the\s+laws?\s+of\b",
            r"\bsubject\s+to\s+the\s+laws?\s+of\b",
        ],

        "DISPUTE_RESOLUTION": [
            r"\bshall\s+be\s+resolved\s+by\s+arbitration\b",
            r"\bsubject\s+to\s+arbitration\b",
            r"\bdisputes?\s+shall\s+be\s+resolved\b",
            r"\bdispute\s+resolution\b",
            r"\bsettled\s+by\s+arbitration\b",
            r"\bmediation\b",
            r"\barbitration\b",
        ],

        "WARRANTY": [
            r"\bwarrants?\s+that\b",
            r"\bwarranties?\s+that\b",
            r"\bprovided\s+that\s+the\s+products?\s+shall\s+conform\b",
            r"\bwarranty\s+period\b",
            r"\bwarranty\s+claims?\b",
        ],

        "REPRESENTATIONS_WARRANTIES": [
            r"\brepresents\s+and\s+warrants\b",
            r"\brepresentation(?:s)?\s+and\s+warrant(?:y|ies)\b",
            r"\brepresentations?\s+and\s+warrant(?:y|ies)\b",
            r"\bfull\s+authority\s+to\s+enter\b",
            r"\bduly\s+authorized\s+to\s+enter\b",
            r"\bduly\s+authorised\s+to\s+enter\b",
        ],

        "LIABILITY": [
            r"\blimitation\s+of\s+liability\b",
            r"\blimit(?:ation)?\s+.*\bliability\b",
            r"\bshall\s+not\s+be\s+liable\b",
            r"\bshall\s+not\s+be\s+responsible\b",
            r"\bshall\s+indemnify\b",
            r"\bindemnif(?:y|ication)\b",
            r"\bhold\s+harmless\b",
        ],

        "INSURANCE": [
            r"\bmaintain\s+.*\binsurance\b",
            r"\bmaintain\s+adequate\s+insurance\b",
            r"\binsurance\s+coverage\b",
            r"\bcertificate\s+of\s+insurance\b",
        ],

        "AUDIT": [
            r"\bmay\s+audit\b",
            r"\bright\s+to\s+audit\b",
            r"\baudit\s+rights?\b",
            r"\binspect\s+.*records?\b",
        ],

        "RENEWAL": [
            r"\bautomatically\s+renew\b",
            r"\bautomatically\s+renews\b",
            r"\bauto[-\s]?renew\b",
            r"\brenewal\s+term\b",
            r"\bnotice\s+of\s+non[-\s]?renewal\b",
        ],

        "SERVICE_LEVELS": [
            r"\bservice\s+level\s+agreement\b",
            r"\bservice\s+levels?\b",
            r"\buptime\s+(?:of|requirement|commitment)\b",
            r"\bresponse\s+time\s+(?:of|requirement)\b",
            r"\bresolution\s+time\s+(?:of|requirement)\b",
        ],

        "DATA_PROTECTION": [
            r"\bprocess\s+personal\s+data\b",
            r"\bprocessing\s+of\s+personal\s+data\b",
            r"\bpersonal\s+data\s+shall\s+be\b",
            r"\bdata\s+protection\s+requirements?\b",
            r"\bdata\s+processing\s+requirements?\b",
        ],

        "INTELLECTUAL_PROPERTY": [
            r"\bintellectual\s+property\s+rights?\b",
            r"\bcopyright\s+(?:ownership|rights?)\b",
            r"\btrademark\s+(?:ownership|rights?)\b",
            r"\bpatent\s+(?:ownership|rights?)\b",
            r"\bnon[-\s]?exclusive\s+license\b",
            r"\bexclusive\s+license\b",
            r"\blicense\s+to\s+use\b",
        ],

        "TAXES": [
            r"\bwithholding\s+tax\b",
            r"\bgoods\s+and\s+services\s+tax\b",
            r"\bGST\b",
            r"\btax\s+liability\b",
            r"\btaxes?\s+(?:shall|must|will)\s+be\s+paid\b",
            r"\bstamp\s+duty\b",
            r"\bstamp\s+dut(?:y|ies)\b",
        ],

        "SECURITY": [
            r"\bsecurity\s+measures?\b",
            r"\binformation\s+security\b",
            r"\bsecurity\s+controls?\b",
            r"\bcybersecurity\b",
            r"\btechnical\s+and\s+organizational\s+measures\b",
            r"\btechnical\s+and\s+organisational\s+measures\b",
        ],

        "COMPLIANCE": [
            r"\bshall\s+comply\s+with\b",
            r"\bmust\s+comply\s+with\b",
            r"\bcompliance\s+with\s+applicable\s+laws\b",
            r"\bregulatory\s+requirements?\b",
        ],

        "NOTICES": [
            r"\ball\s+notices?\s+under\s+this\s+agreement\b",
            r"\bnotice\s+shall\s+be\s+given\b",
            r"\bwritten\s+notice\s+shall\s+be\b",
            r"\bnotices?\s+in\s+writing\b",
            r"\baddress\s+for\s+communication\b",
            r"\bnotice\s+board\b",
            r"\bgrievance\s+redressal\b",
        ],

        "DEFINITIONS": [
            r"\bfor\s+purposes\s+of\s+this\s+agreement\b",
            r"\bfor\s+the\s+purposes\s+of\s+this\s+agreement\b",
            r"\bhereinafter\s+referred\s+to\s+as\b",
            r"\bshall\s+mean\b",
            r"\bdefined\s+as\b",
            r"\bdefined\s+hereinafter\b",
        ],

        "CONDITIONS": [
            r"\bconditional\s+upon\b",
            r"\bconditions?\s+precedent\b",
            r"\bsubject\s+to\s+the\s+condition\b",
            r"\bprovided\s+that\b",
            r"\bupon\s+the\s+occurrence\b",
            r"\bupon\s+satisfaction\b",
        ],

        "COVENANT": [
            r"\bcovenant(?:s|ed)?\b",
            r"\bundertakes?\s+that\b",
            r"\bundertakes?\s+to\b",
            r"\bundertaking\b",
            r"\nagrees?\s+to\s+maintain\b",
            r"\bagrees?\s+to\s+comply\b",
        ],
    }

    # ================================================================
    # WEIGHTED KEYWORD TAXONOMY
    # ================================================================

    KEYWORDS = {

        "CANCELLATION": [
            ("cancel", 6.0),
            ("cancellation", 7.0),
            ("cancellation charge", 8.0),
            ("cancellation fee", 8.0),
            ("cancel fee", 7.0),
            ("cancel charge", 7.0),
            ("non-refundable", 6.0),
            ("non refundable", 6.0),
        ],

        "PAYMENT": [
            ("pay", 4.0),
            ("payment", 4.0),
            ("payment terms", 6.0),
            ("payment schedule", 6.0),
            ("invoice", 3.0),
            ("fee", 3.0),
            ("fees", 3.0),
            ("price", 2.0),
            ("interest rate", 6.0),
            ("interest", 3.0),
            ("repayment", 5.0),
            ("repay", 4.0),
            ("installment", 5.0),
            ("instalment", 5.0),
            ("emi", 6.0),
            ("principal amount", 5.0),
            ("amount payable", 5.0),
            ("charges", 3.0),
        ],

        "TERMINATION": [
            ("terminate", 3.0),
            ("termination", 3.0),
            ("terminate this agreement", 5.0),
            ("end this agreement", 5.0),
            ("notice of termination", 5.0),
            ("terminate upon", 4.0),
        ],

        "CONFIDENTIALITY": [
            ("confidential", 3.0),
            ("confidentiality", 4.0),
            ("disclose", 2.5),
            ("non-disclosure", 5.0),
            ("non disclosure", 5.0),
            ("receiving party", 2.0),
            ("confidential information", 5.0),
        ],

        "LIABILITY": [
            ("liable", 3.0),
            ("liability", 5.0),
            ("damages", 3.0),
            ("indemnify", 5.0),
            ("indemnification", 5.0),
            ("hold harmless", 5.0),
            ("losses", 2.0),
            ("third-party claims", 4.0),
            ("third party claims", 4.0),
            ("limitation of liability", 6.0),
        ],

        "GOVERNING_LAW": [
            ("governing law", 6.0),
            ("governed by", 5.0),
            ("laws of", 4.0),
            ("applicable law", 3.0),
            ("jurisdiction", 3.0),
            ("construed in accordance with the laws", 6.0),
        ],

        "DISPUTE_RESOLUTION": [
            ("dispute", 3.0),
            ("disputes", 3.0),
            ("arbitration", 6.0),
            ("arbitral", 5.0),
            ("mediation", 6.0),
            ("mediator", 5.0),
            ("alternative dispute resolution", 6.0),
            ("dispute resolution", 6.0),
        ],

        "INTELLECTUAL_PROPERTY": [
            ("intellectual property", 6.0),
            ("intellectual property rights", 6.0),
            ("copyright", 5.0),
            ("copyrights", 5.0),
            ("trademark", 5.0),
            ("trademarks", 5.0),
            ("patent", 5.0),
            ("patents", 5.0),
            ("trade secret", 5.0),
            ("trade secrets", 5.0),
            ("ownership of intellectual property", 6.0),
            ("license", 3.0),
            ("licensor", 4.0),
            ("licensee", 4.0),
            ("software rights", 4.0),
        ],

        "DATA_PROTECTION": [
            ("personal data", 6.0),
            ("personal information", 6.0),
            ("data protection", 6.0),
            ("privacy", 5.0),
            ("privacy policy", 5.0),
            ("data processing", 5.0),
            ("data processor", 5.0),
            ("data controller", 5.0),
            ("processing of personal data", 6.0),
            ("data subject", 5.0),
        ],

        "ASSIGNMENT": [
            ("assign", 4.0),
            ("assignment", 5.0),
            ("transfer this agreement", 5.0),
            ("transfer its rights", 4.0),
            ("transfer its obligations", 4.0),
            ("assignment of the loan", 6.0),
            ("sell assign", 6.0),
        ],

        "EMPLOYMENT": [
            ("employee", 4.0),
            ("employer", 4.0),
            ("employment", 5.0),
            ("employment agreement", 6.0),
            ("job duties", 4.0),
            ("probation", 4.0),
            ("salary", 3.0),
            ("leave entitlement", 4.0),
            ("working hours", 4.0),
        ],

        "WARRANTY": [
            ("warrant", 5.0),
            ("warrants", 5.0),
            ("warranty", 6.0),
            ("warranties", 6.0),
            ("warranted", 5.0),
            ("conform to the specifications", 5.0),
            ("merchantability", 6.0),
            ("fitness for a particular purpose", 6.0),
        ],

        "REPRESENTATIONS_WARRANTIES": [
            ("represents and warrants", 7.0),
            ("representation and warranty", 7.0),
            ("representations and warranties", 7.0),
            ("represents", 4.0),
            ("representation", 4.0),
            ("full authority to enter", 5.0),
            ("duly authorized", 5.0),
            ("duly authorised", 5.0),
        ],

        "FORCE_MAJEURE": [
            ("force majeure", 8.0),
            ("beyond its reasonable control", 6.0),
            ("beyond reasonable control", 6.0),
            ("act of god", 6.0),
            ("natural disaster", 5.0),
            ("pandemic", 4.0),
            ("epidemic", 4.0),
            ("war", 4.0),
            ("strike", 3.0),
            ("government action", 4.0),
        ],

        "INSURANCE": [
            ("insurance", 6.0),
            ("insured", 5.0),
            ("insurer", 5.0),
            ("insurance coverage", 7.0),
            ("insurance policy", 6.0),
            ("maintain adequate insurance", 7.0),
            ("certificate of insurance", 6.0),
        ],

        "DELIVERY": [
            ("deliver", 5.0),
            ("delivery", 6.0),
            ("shipment", 5.0),
            ("shipping", 5.0),
            ("dispatch", 5.0),
            ("delivered to", 5.0),
            ("purchase order", 3.0),
        ],

        "SERVICE_LEVELS": [
            ("service level", 7.0),
            ("service levels", 7.0),
            ("service level agreement", 7.0),
            ("sla", 7.0),
            ("uptime", 7.0),
            ("availability", 4.0),
            ("response time", 5.0),
            ("resolution time", 5.0),
            ("performance standard", 5.0),
        ],

        "AUDIT": [
            ("audit", 6.0),
            ("audits", 6.0),
            ("audit rights", 7.0),
            ("right to audit", 7.0),
            ("audit records", 6.0),
            ("inspect records", 5.0),
            ("inspection rights", 6.0),
        ],

        "RENEWAL": [
            ("renew", 6.0),
            ("renewal", 7.0),
            ("renew automatically", 7.0),
            ("automatically renew", 7.0),
            ("auto-renew", 7.0),
            ("non-renewal", 7.0),
            ("renewal term", 6.0),
        ],

        "NOTICES": [
            ("notice", 3.0),
            ("notices", 4.0),
            ("written notice", 4.0),
            ("notice address", 5.0),
            ("notice shall be given", 5.0),
            ("provided in writing", 3.0),
            ("address for communication", 6.0),
            ("notice board", 5.0),
        ],

        "COMPLIANCE": [
            ("compliance", 6.0),
            ("comply with", 5.0),
            ("applicable laws and regulations", 6.0),
            ("laws and regulations", 5.0),
            ("regulatory requirements", 5.0),
            ("regulatory compliance", 6.0),
        ],

        "TAXES": [
            ("tax", 5.0),
            ("taxes", 6.0),
            ("taxation", 5.0),
            ("tax liability", 6.0),
            ("withholding tax", 7.0),
            ("goods and services tax", 7.0),
            ("gst", 6.0),
            ("stamp duty", 7.0),
        ],

        "SECURITY": [
            ("security measures", 6.0),
            ("information security", 6.0),
            ("security controls", 6.0),
            ("technical and organizational measures", 7.0),
            ("technical and organisational measures", 7.0),
            ("cybersecurity", 7.0),
            ("information security measures", 7.0),
            ("security incident", 6.0),
            ("security interest", 7.0),
            ("collateral", 7.0),
            ("continuing security", 7.0),
        ],

        "DEFINITIONS": [
            ("means", 6.0),
            ("shall mean", 7.0),
            ("defined as", 7.0),
            ("definition", 7.0),
            ("definitions", 7.0),
            ("for purposes of this agreement", 6.0),
            ("for the purposes of this agreement", 6.0),
            ("hereinafter referred to as", 7.0),
            ("defined hereinafter", 7.0),
        ],

        "CONDITIONS": [
            ("conditional upon", 7.0),
            ("conditions precedent", 7.0),
            ("subject to the condition", 6.0),
            ("provided that", 5.0),
            ("provided however", 5.0),
            ("upon the occurrence", 6.0),
            ("upon satisfaction", 6.0),
        ],

        "COVENANT": [
            ("covenant", 6.0),
            ("covenants", 6.0),
            ("agrees to maintain", 4.0),
            ("agrees to comply", 4.0),
            ("undertakes to", 6.0),
            ("undertakes that", 6.0),
            ("undertaking", 5.0),
        ],

        "OBLIGATION": [
            ("shall", 0.25),
            ("must", 0.25),
            ("required to", 0.5),
            ("agrees to", 0.5),
            ("obligation", 0.75),
            ("duties", 0.5),
        ],
    }

    # ================================================================
    # EXPLICIT TITLES
    # ================================================================

    TITLE_CLASSIFICATIONS = {
        "GENERAL": "GENERAL",
        "LIABILITY": "LIABILITY",
        "PAYMENT": "PAYMENT",
        "PAYMENT TERMS": "PAYMENT",
        "CONFIDENTIALITY": "CONFIDENTIALITY",
        "TERM AND TERMINATION": "TERMINATION",
        "TERMINATION": "TERMINATION",
        "SCOPE OF SERVICES": "OBLIGATION",
        "GOVERNING LAW": "GOVERNING_LAW",
        "GOVERNING LAW AND DISPUTE RESOLUTION": "GOVERNING_LAW",
        "DISPUTE RESOLUTION": "DISPUTE_RESOLUTION",
        "CANCELLATION": "CANCELLATION",
        "EMPLOYMENT": "EMPLOYMENT",
        "FORCE MAJEURE": "FORCE_MAJEURE",
        "ASSIGNMENT": "ASSIGNMENT",
        "WARRANTY": "WARRANTY",
        "INSURANCE": "INSURANCE",
        "AUDIT": "AUDIT",
        "RENEWAL": "RENEWAL",
        "INTELLECTUAL PROPERTY": "INTELLECTUAL_PROPERTY",
        "DATA PROTECTION": "DATA_PROTECTION",
        "SERVICE LEVELS": "SERVICE_LEVELS",
        "TAXES": "TAXES",
        "SECURITY": "SECURITY",
        "COMPLIANCE": "COMPLIANCE",
        "NOTICES": "NOTICES",
        "DEFINITIONS": "DEFINITIONS",
        "CONDITIONS": "CONDITIONS",
        "COVENANT": "COVENANT",
    }

    # ================================================================
    # KEYWORD SCORING
    # ================================================================

    @staticmethod
    def _keyword_score(
        text: str,
        keyword: str,
        weight: float,
    ) -> float:

        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"

        return (
            len(
                re.findall(
                    pattern,
                    text.lower(),
                    flags=re.IGNORECASE,
                )
            )
            * weight
        )

    # ================================================================
    # PRIMARY CLASSIFICATION
    # ================================================================

    @classmethod
    def _primary_classification(
        cls,
        text: str,
    ) -> str | None:

        text_lower = text.lower()

        # Strong patterns are scored rather than simply returning
        # the first category encountered.
        scores: dict[str, float] = {}

        for clause_type, patterns in cls.PRIMARY_PATTERNS.items():

            score = 0.0

            for pattern in patterns:

                matches = re.findall(
                    pattern,
                    text_lower,
                    flags=re.IGNORECASE,
                )

                if matches:
                    # Strong legal patterns receive a high score.
                    score += len(matches) * 10.0

            if score > 0:
                scores[clause_type] = score

        if not scores:
            return None

        # Additional domain-specific tie breakers.
        #
        # Liability should beat generic payment language.
        if (
            "LIABILITY" in scores
            and re.search(
                r"\bshall\s+not\s+be\s+liable\b|\blimitation\s+of\s+liability\b",
                text_lower,
                re.IGNORECASE,
            )
        ):
            return "LIABILITY"

        # Assignment should beat generic payment language when
        # assignment/transfer of a loan is the actual subject.
        if (
            "ASSIGNMENT" in scores
            and re.search(
                r"\bassign(?:ment)?\b|\btransfer\b|\bsell(?:s)?\s*/?\s*assign",
                text_lower,
                re.IGNORECASE,
            )
        ):
            return "ASSIGNMENT"

        # Representations and warranties should beat generic warranty.
        if "REPRESENTATIONS_WARRANTIES" in scores:
            return "REPRESENTATIONS_WARRANTIES"

        return max(
            scores,
            key=scores.get,
        )

    # ================================================================
    # CLAUSE OBJECT COPY
    # ================================================================

    @staticmethod
    def _copy_with_type(
        clause: Any,
        clause_type: str,
    ) -> Clause:

        # Normal application path: Pydantic Clause.
        if hasattr(clause, "model_copy"):
            return clause.model_copy(
                update={
                    "clause_type": clause_type,
                }
            )

        # Compatibility with older Pydantic versions.
        if hasattr(clause, "copy"):
            try:
                return clause.copy(
                    update={
                        "clause_type": clause_type,
                    }
                )
            except TypeError:
                pass

        # Dataclass compatibility.
        if hasattr(clause, "__dataclass_fields__"):
            try:
                return replace(
                    clause,
                    clause_type=clause_type,
                )
            except Exception:
                pass

        # Generic Python object compatibility.
        try:
            data = dict(vars(clause))
            data["clause_type"] = clause_type
            return Clause(**data)

        except Exception as exc:
            raise TypeError(
                "ClauseClassifierService.classify() expects a "
                "Pydantic Clause or a compatible object."
            ) from exc

    # ================================================================
    # CHECK WHETHER TITLE IS A REAL TITLE
    # ================================================================

    @staticmethod
    def _is_real_title(
        title: str | None,
    ) -> bool:

        if not title:
            return False

        title = " ".join(
            title.strip().split()
        )

        if not title:
            return False

        upper = title.upper()

        # Known clean section titles.
        if upper in ClauseClassifierService.TITLE_CLASSIFICATIONS:
            return True

        # If the title is actually a long sentence extracted from the
        # beginning of the clause, do not treat it as a title.
        if len(title) > 80:
            return False

        # Sentence-like titles usually contain these indicators.
        if re.search(
            r"\b(?:shall|must|will|agrees?|undertakes?|hereby|borrower|company|client)\b",
            title,
            re.IGNORECASE,
        ):
            return False

        # A title containing a colon can still be legitimate.
        if title.endswith(":"):
            return True

        # Short uppercase headings are generally safe.
        if title == upper and len(title.split()) <= 8:
            return True

        return False

    # ================================================================
    # SINGLE CLAUSE CLASSIFICATION
    # ================================================================

    @classmethod
    def classify(
        cls,
        clause: Clause,
    ) -> Clause:

        title = getattr(
            clause,
            "title",
            None,
        )

        body = getattr(
            clause,
            "text",
            "",
        ) or ""

        clause_number = getattr(
            clause,
            "clause_number",
            None,
        )

        # ------------------------------------------------------------
        # Phase 0: explicit real section titles
        # ------------------------------------------------------------

        if cls._is_real_title(title):

            title_upper = title.strip().upper()

            explicit_type = cls.TITLE_CLASSIFICATIONS.get(
                title_upper
            )

            if explicit_type:
                return cls._copy_with_type(
                    clause,
                    explicit_type,
                )

        # ------------------------------------------------------------
        # Unnumbered introductory text
        # ------------------------------------------------------------

        if (
            clause_number is None
            and not title
        ):
            return cls._copy_with_type(
                clause,
                "GENERAL",
            )

        # ------------------------------------------------------------
        # Build text for semantic classification.
        #
        # IMPORTANT:
        # If title is a sentence extracted from the clause, body is
        # more trustworthy than the title.
        # ------------------------------------------------------------

        text = " ".join(
            part
            for part in [
                title if cls._is_real_title(title) else None,
                body,
            ]
            if part
        )

        # ------------------------------------------------------------
        # Phase 1: strong legal-purpose classification
        # ------------------------------------------------------------

        primary_type = cls._primary_classification(
            text
        )

        if primary_type:
            return cls._copy_with_type(
                clause,
                primary_type,
            )

        # ------------------------------------------------------------
        # Phase 2: weighted keyword classification
        # ------------------------------------------------------------

        scores: dict[str, float] = {}

        for clause_type, keywords in cls.KEYWORDS.items():

            score = 0.0

            for keyword, weight in keywords:

                score += cls._keyword_score(
                    text,
                    keyword,
                    weight,
                )

            if score > 0:
                scores[clause_type] = score

        # ------------------------------------------------------------
        # Domain-specific scoring adjustments
        # ------------------------------------------------------------

        text_lower = text.lower()

        # Loan/security agreement specific rules.

        if re.search(
            r"\bloan\b.*\butili[sz]ed\b|\bloan proceeds\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["COVENANT"] = (
                scores.get("COVENANT", 0.0)
                + 8.0
            )

        if re.search(
            r"\bborrower\b.*\bundertakes?\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["COVENANT"] = (
                scores.get("COVENANT", 0.0)
                + 10.0
            )

        if re.search(
            r"\bstamp duty\b|\bstamp duties\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["TAXES"] = (
                scores.get("TAXES", 0.0)
                + 10.0
            )

        if re.search(
            r"\bgrievance\s+redressal\b|\bnotice\s+board\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["NOTICES"] = (
                scores.get("NOTICES", 0.0)
                + 10.0
            )

        if re.search(
            r"\bassign(?:s|ed|ment)?\b.*\bloan\b"
            r"|\bloan\b.*\bassign(?:s|ed|ment)?\b"
            r"|\bsell\s*/\s*assign\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["ASSIGNMENT"] = (
                scores.get("ASSIGNMENT", 0.0)
                + 15.0
            )

        if re.search(
            r"\brepresent(?:s|ation)?\b"
            r".*\b(?:warrant|confirm|declare)\b",
            text_lower,
            re.IGNORECASE,
        ):
            scores["REPRESENTATIONS_WARRANTIES"] = (
                scores.get(
                    "REPRESENTATIONS_WARRANTIES",
                    0.0,
                )
                + 12.0
            )

        # ------------------------------------------------------------
        # No match
        # ------------------------------------------------------------

        if not scores:
            return cls._copy_with_type(
                clause,
                "GENERAL",
            )

        # ------------------------------------------------------------
        # Choose best score.
        # ------------------------------------------------------------

        best_type = max(
            scores,
            key=scores.get,
        )

        return cls._copy_with_type(
            clause,
            best_type,
        )

    # ================================================================
    # CLASSIFY MANY
    # ================================================================

    @classmethod
    def classify_many(
        cls,
        clauses: list[Clause],
    ) -> list[Clause]:

        return [
            cls.classify(clause)
            for clause in clauses
        ]