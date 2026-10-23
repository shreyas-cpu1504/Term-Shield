from app.schemas.clause import Clause
from app.services.clause_classifier_service import ClauseClassifierService
from app.services.clause_relationship_service import ClauseRelationshipService


def make_clause(
    clause_id: str,
    number: str,
    text: str,
) -> Clause:
    return Clause(
        clause_id=clause_id,
        clause_number=number,
        title=None,
        text=text,
        order=int(number.split(".")[0]) if number.split(".")[0].isdigit() else 1,
        character_count=len(text),
    )


def relationships(clauses):
    classified = ClauseClassifierService.classify_many(clauses)
    return ClauseRelationshipService.analyze_relationships(classified)


def test_reference_relationship():
    clauses = [
        make_clause("c1", "1", "The Customer shall pay the invoice."),
        make_clause(
            "c2",
            "2",
            "The payment obligation described in Clause 1 shall apply."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "REFERENCE"
        and r.source_clause_id == "c2"
        and r.target_clause_id == "c1"
        for r in result
    )


def test_dependency_relationship():
    clauses = [
        make_clause("c1", "1", "The Customer shall provide the required documents."),
        make_clause(
            "c2",
            "2",
            "The payment shall occur after completion of Clause 1."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "DEPENDENCY"
        and r.source_clause_id == "c2"
        for r in result
    )


def test_exception_relationship():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall comply with all requirements except where prohibited by law."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "EXCEPTION"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_override_relationship():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This provision shall override any conflicting provision."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "OVERRIDE"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_condition_relationship():
    clauses = [
        make_clause(
            "c1",
            "1",
            "If the Customer fails to pay, the Company may terminate the agreement."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "CONDITION"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_modification_relationship():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This clause modifies the payment terms stated in the agreement."
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "MODIFICATION"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_definition_relationship():
    clauses = [
        make_clause(
            "c1",
            "1",
            '"Confidential Information" means all non-public information disclosed by the Company.'
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "DEFINITION"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_relationship_deduplication():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This clause refers to Clause 2 and Clause 2."
        ),
        make_clause(
            "c2",
            "2",
            "The Customer shall pay the invoice."
        ),
    ]

    result = relationships(clauses)

    keys = [
        (
            r.source_clause_id,
            r.target_clause_id,
            r.relationship_type,
            r.evidence.casefold(),
        )
        for r in result
    ]

    assert len(keys) == len(set(keys))


def test_relationship_confidence_range():
    clauses = [
        make_clause(
            "c1",
            "1",
            "If the Customer fails to comply, this clause shall override conflicting terms."
        ),
    ]

    result = relationships(clauses)

    assert result
    assert all(
        0.0 <= relationship.confidence <= 1.0
        for relationship in result
    )


def test_empty_relationships():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall receive the product."
        ),
    ]

    result = relationships(clauses)

    assert isinstance(result, list)

def test_ordinary_word_after_clause_is_not_reference():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This clause modifies the payment terms stated in the agreement.",
        ),
    ]

    result = relationships(clauses)

    assert not any(
        r.relationship_type == "REFERENCE"
        for r in result
    )

    assert any(
        r.relationship_type == "MODIFICATION"
        and r.source_clause_id == "c1"
        for r in result
    )


def test_clause_number_is_reference():
    clauses = [
        make_clause(
            "c1",
            "1",
            "The Customer shall pay the invoice.",
        ),
        make_clause(
            "c2",
            "2",
            "The obligation described in Clause 1 shall apply.",
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "REFERENCE"
        and r.source_clause_id == "c2"
        and r.target_clause_id == "c1"
        for r in result
    )


def test_decimal_clause_number_is_reference():
    clauses = [
        make_clause(
            "c1",
            "1.2",
            "The Customer shall provide the required documents.",
        ),
        make_clause(
            "c2",
            "2",
            "The requirements in Clause 1.2 shall apply.",
        ),
    ]

    result = relationships(clauses)

    assert any(
        r.relationship_type == "REFERENCE"
        and r.source_clause_id == "c2"
        and r.target_clause_id == "c1"
        for r in result
    )


def test_common_clause_verb_is_not_reference():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This clause applies to all customers.",
        ),
    ]

    result = relationships(clauses)

    assert not any(
        r.relationship_type == "REFERENCE"
        for r in result
    )


def test_common_clause_noun_is_not_reference():
    clauses = [
        make_clause(
            "c1",
            "1",
            "This clause provides additional protection.",
        ),
    ]

    result = relationships(clauses)

    assert not any(
        r.relationship_type == "REFERENCE"
        for r in result
    )

