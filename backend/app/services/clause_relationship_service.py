from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClauseRelationship:
    source_clause_id: str
    target_clause_id: str | None
    relationship_type: str
    evidence: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ClauseRelationshipService:
    """
    Detect relationships between clauses using deterministic rules.

    Supported relationships:
    - SUBCLAUSE
    - REFERENCE
    - EXCEPTION
    - OVERRIDE
    - CONDITION
    - DEPENDENCY
    - MODIFICATION
    - DEFINITION
    """

    REFERENCE_PATTERNS = [
        r"\b(?:clause|section|article|paragraph|sub[- ]?section|subsection)"
        r"\s+(?:no\.?\s*)?([A-Za-z0-9]+(?:\([A-Za-z0-9]+\))?(?:\.[A-Za-z0-9]+)*)",

        r"\b(?:clause|section|article|paragraph|sub[- ]?section|subsection)"
        r"\s+([A-Za-z0-9]+(?:\s*(?:and|or)\s*[A-Za-z0-9]+)*)(?!\.[A-Za-z0-9])",

        r"\b(?:under|pursuant to|in accordance with|as provided in|as set out in)"
        r"\s+(?:clause|section|article|paragraph)\s+"
        r"([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)",
    ]

    EXCEPTION_PATTERNS = (
        "except",
        "except as",
        "except where",
        "except that",
        "unless",
        "unless otherwise",
        "subject to",
        "provided that",
        "provided however",
        "save as",
        "notwithstanding",
    )

    OVERRIDE_PATTERNS = (
        "notwithstanding",
        "shall prevail",
        "prevails over",
        "take precedence",
        "takes precedence",
        "supersede",
        "supersedes",
        "superseding",
        "override",
        "overrides",
        "in the event of conflict",
        "in case of conflict",
    )

    CONDITION_PATTERNS = (
        "if ",
        "if,",
        "when ",
        "where ",
        "wherever ",
        "provided that",
        "provided however",
        "subject to",
        "on condition that",
        "upon ",
        "following ",
        "in the event that",
        "in the event of",
        "unless ",
    )

    DEPENDENCY_PATTERNS = (
        "depends on",
        "dependent on",
        "subject to completion of",
        "subject to fulfillment of",
        "subject to satisfaction of",
        "after completion of",
        "after fulfillment of",
        "after satisfaction of",
        "following completion of",
        "following fulfillment of",
        "following satisfaction of",
        "upon completion of",
        "upon fulfillment of",
        "upon satisfaction of",
        "only after",
        "only upon",
        "provided that",
    )

    MODIFICATION_PATTERNS = (
        "amend",
        "amended",
        "amendment",
        "amends",
        "modify",
        "modified",
        "modifies",
        "modification",
        "vary",
        "varies",
        "varied",
        "variation",
        "replace",
        "replaced",
        "replacement",
        "supplement",
        "supplemented",
    )

    DEFINITION_PATTERNS = (
        "means",
        "mean",
        "shall mean",
        "defined as",
        "definition",
        "hereinafter referred to as",
        "hereinafter called",
        "for the purposes of this",
    )

    @classmethod
    def analyze_relationships(
        cls,
        clauses: list[Any],
    ) -> list[ClauseRelationship]:

        relationships: list[ClauseRelationship] = []

        normalized = [
            cls._normalize_clause(clause, index)
            for index, clause in enumerate(clauses, start=1)
        ]

        # ---------------------------------------------------------
        # 1. Detect structural parent/sub-clause relationships.
        # ---------------------------------------------------------
        for clause in normalized:

            source_id = clause["clause_id"]
            clause_number = clause["clause_number"]
            parent_clause = clause["parent_clause"]

            if not parent_clause:
                continue

            target_id = cls._find_clause_by_number(
                parent_clause,
                normalized,
                source_id,
            )

            if target_id:

                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=target_id,
                        relationship_type="SUBCLAUSE",
                        evidence=(
                            f"Clause {clause_number} is a sub-clause "
                            f"of clause {parent_clause}."
                        ),
                        confidence=1.0,
                        metadata={
                            "clause_number": clause_number,
                            "parent_clause": parent_clause,
                        },
                    )
                )

        # ---------------------------------------------------------
        # 2. Detect explicit textual references.
        # ---------------------------------------------------------
        for clause in normalized:

            source_id = clause["clause_id"]
            text = clause["text"]

            references = cls._extract_references(text)

            for reference in references:

                target_id = cls._resolve_reference(
                    reference["reference"],
                    normalized,
                    source_id,
                )

                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=target_id,
                        relationship_type="REFERENCE",
                        evidence=reference["evidence"],
                        confidence=(
                            0.95
                            if target_id
                            else 0.70
                        ),
                        metadata={
                            "reference": reference["reference"],
                        },
                    )
                )

            # -----------------------------------------------------
            # 3. Exception relationships.
            # -----------------------------------------------------
            lower = text.casefold()

            if cls._contains_any(
                lower,
                cls.EXCEPTION_PATTERNS,
            ):
                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=None,
                        relationship_type="EXCEPTION",
                        evidence=cls._find_evidence(
                            text,
                            cls.EXCEPTION_PATTERNS,
                        ),
                        confidence=0.90,
                    )
                )

            # -----------------------------------------------------
            # 4. Override relationships.
            # -----------------------------------------------------
            if cls._contains_any(
                lower,
                cls.OVERRIDE_PATTERNS,
            ):
                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=None,
                        relationship_type="OVERRIDE",
                        evidence=cls._find_evidence(
                            text,
                            cls.OVERRIDE_PATTERNS,
                        ),
                        confidence=0.90,
                    )
                )

            # -----------------------------------------------------
            # 5. Condition relationships.
            # -----------------------------------------------------
            if cls._contains_any(
                lower,
                cls.CONDITION_PATTERNS,
            ):
                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=None,
                        relationship_type="CONDITION",
                        evidence=cls._find_evidence(
                            text,
                            cls.CONDITION_PATTERNS,
                        ),
                        confidence=0.85,
                    )
                )

            # -----------------------------------------------------
            # 6. Dependency relationships.
            # -----------------------------------------------------
            if cls._contains_any(
                lower,
                cls.DEPENDENCY_PATTERNS,
            ):
                dependency_target_id = None

                # If the dependency statement explicitly references
                # another clause, resolve that clause as the target.
                dependency_references = cls._extract_references(
                    text
                )

                for dependency_reference in dependency_references:
                    dependency_target_id = cls._resolve_reference(
                        dependency_reference["reference"],
                        normalized,
                        source_id,
                    )

                    if dependency_target_id:
                        break

                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=dependency_target_id,
                        relationship_type="DEPENDENCY",
                        evidence=cls._find_evidence(
                            text,
                            cls.DEPENDENCY_PATTERNS,
                        ),
                        confidence=(
                            0.90
                            if dependency_target_id
                            else 0.80
                        ),
                        metadata={
                            "dependency_reference": (
                                dependency_target_id
                                is not None
                            )
                        },
                    )
                )

            # -----------------------------------------------------
            # 7. Modification relationships.
            # -----------------------------------------------------
            if cls._contains_any(
                lower,
                cls.MODIFICATION_PATTERNS,
            ):
                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=None,
                        relationship_type="MODIFICATION",
                        evidence=cls._find_evidence(
                            text,
                            cls.MODIFICATION_PATTERNS,
                        ),
                        confidence=0.80,
                    )
                )

            # -----------------------------------------------------
            # 7. Definition relationships.
            # -----------------------------------------------------
            if cls._contains_any(
                lower,
                cls.DEFINITION_PATTERNS,
            ):
                relationships.append(
                    ClauseRelationship(
                        source_clause_id=source_id,
                        target_clause_id=None,
                        relationship_type="DEFINITION",
                        evidence=cls._find_evidence(
                            text,
                            cls.DEFINITION_PATTERNS,
                        ),
                        confidence=0.85,
                    )
                )

        return cls._deduplicate(relationships)

    @classmethod
    def analyze(
        cls,
        clauses: list[Any],
    ) -> list[ClauseRelationship]:
        return cls.analyze_relationships(clauses)

    @staticmethod
    def _normalize_clause(
        clause: Any,
        fallback_number: int,
    ) -> dict[str, str]:

        if isinstance(clause, dict):

            clause_id = str(
                clause.get(
                    "clause_id",
                    f"clause-{fallback_number}",
                )
            )

            text = str(
                clause.get(
                    "text",
                    "",
                )
            )

            number = str(
                clause.get(
                    "clause_number",
                    fallback_number,
                )
            )

            parent_clause = clause.get(
                "parent_clause"
            )

            return {
                "clause_id": clause_id,
                "clause_number": number,
                "parent_clause": (
                    str(parent_clause)
                    if parent_clause is not None
                    else ""
                ),
                "text": text.strip(),
            }

        clause_id = str(
            getattr(
                clause,
                "clause_id",
                f"clause-{fallback_number}",
            )
        )

        text = str(
            getattr(
                clause,
                "text",
                "",
            )
        )

        number = getattr(
            clause,
            "clause_number",
            fallback_number,
        )

        parent_clause = getattr(
            clause,
            "parent_clause",
            None,
        )

        return {
            "clause_id": clause_id,
            "clause_number": str(number),
            "parent_clause": (
                str(parent_clause)
                if parent_clause is not None
                else ""
            ),
            "text": text.strip(),
        }

    @staticmethod
    def _find_clause_by_number(
        clause_number: str,
        clauses: list[dict[str, str]],
        source_clause_id: str,
    ) -> str | None:

        normalized_number = (
            str(clause_number)
            .strip()
            .casefold()
        )

        for clause in clauses:

            if clause["clause_id"] == source_clause_id:
                continue

            current_number = (
                str(clause["clause_number"])
                .strip()
                .casefold()
            )

            if current_number == normalized_number:
                return clause["clause_id"]

        return None

    @classmethod
    def _extract_references(
        cls,
        text: str,
    ) -> list[dict[str, str]]:

        found: list[dict[str, str]] = []

        for pattern in cls.REFERENCE_PATTERNS:

            try:

                for match in re.finditer(
                    pattern,
                    text,
                    re.IGNORECASE,
                ):

                    reference = match.group(1).strip()

                    if not cls._is_valid_reference_identifier(
                        reference
                    ):
                        continue

                    found.append(
                        {
                            "reference": reference,
                            "evidence": match.group(0).strip(),
                        }
                    )

            except re.error:
                continue

        unique = []
        seen_references = set()

        for item in found:

            reference = item["reference"].strip().casefold()

            if reference in seen_references:
                continue

            seen_references.add(reference)
            unique.append(item)

        return unique

    @staticmethod
    def _is_valid_reference_identifier(
        reference: str,
    ) -> bool:
        """
        Validate the identifier captured after a legal-document
        reference keyword such as Clause, Section, or Article.

        Valid examples:
        - 1
        - 1.2
        - 1.2.3
        - 3(a)
        - 3(a)(i)
        - IV
        - V.2

        Reject ordinary words such as:
        - modifies
        - applies
        - provides
        - states
        """

        value = reference.strip()

        if not value:
            return False

        # Numeric clause/section identifiers.
        if re.fullmatch(
            r"\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*",
            value,
        ):
            return True

        # Roman-numeral style identifiers.
        if re.fullmatch(
            r"[IVXLCDM]+(?:\.\d+)?(?:\([A-Za-z0-9]+\))*",
            value,
            re.IGNORECASE,
        ):
            return True

        # Single alphabetic identifiers are allowed for cases such
        # as Article A or Appendix A, but ordinary English words are
        # rejected.
        if re.fullmatch(
            r"[A-Za-z](?:\([A-Za-z0-9]+\))*",
            value,
        ):
            return True

        return False

    @classmethod
    def _resolve_reference(
        cls,
        reference: str,
        clauses: list[dict[str, str]],
        source_clause_id: str,
    ) -> str | None:

        normalized_reference = (
            reference
            .strip()
            .casefold()
        )

        for clause in clauses:

            if clause["clause_id"] == source_clause_id:
                continue

            if (
                str(clause["clause_number"])
                .strip()
                .casefold()
                == normalized_reference
            ):
                return clause["clause_id"]

        numeric_match = re.match(
            r"^(\d+)",
            normalized_reference,
        )

        if numeric_match:

            number = numeric_match.group(1)

            for clause in clauses:

                if clause["clause_id"] == source_clause_id:
                    continue

                if (
                    str(clause["clause_number"])
                    .strip()
                    .casefold()
                    == number.casefold()
                ):
                    return clause["clause_id"]

        return None

    @staticmethod
    def _contains_any(
        text: str,
        patterns: tuple[str, ...],
    ) -> bool:

        return any(
            pattern.casefold() in text
            for pattern in patterns
        )

    @staticmethod
    def _find_evidence(
        text: str,
        patterns: tuple[str, ...],
    ) -> str:

        lower = text.casefold()

        for pattern in patterns:

            position = lower.find(
                pattern.casefold()
            )

            if position >= 0:

                start = max(
                    0,
                    position - 50,
                )

                end = min(
                    len(text),
                    position + len(pattern) + 100,
                )

                return text[start:end].strip()

        return text[:200].strip()

    @classmethod
    def _unique_dicts(
        cls,
        values: list[dict[str, str]],
    ) -> list[dict[str, str]]:

        result = []
        seen = set()

        for value in values:

            key = (
                value.get(
                    "reference",
                    "",
                ).casefold(),
                value.get(
                    "evidence",
                    "",
                ).casefold(),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result

    @classmethod
    def _deduplicate(
        cls,
        relationships: list[ClauseRelationship],
    ) -> list[ClauseRelationship]:

        result = []
        seen = set()

        for relationship in relationships:

            key = (
                relationship.source_clause_id,
                relationship.target_clause_id,
                relationship.relationship_type,
                relationship.evidence.casefold(),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(relationship)

        return result