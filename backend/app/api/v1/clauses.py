from dataclasses import asdict
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.ownership import require_owned_contract
from app.core.database import get_db
from app.models.clause import Clause as ClauseModel
from app.models.clause_analysis import ClauseAnalysisRecord
from app.models.contract import Contract
from app.models.user import User
from app.schemas.clause import Clause as ClauseSchema, ClauseSegmentationResponse
from app.schemas.clause_analysis import ClauseAnalysis, ClauseAnalysisResponse
from app.schemas.clause_relationship import ClauseRelationshipResponse
from app.schemas.contract_summary import ContractSummary

from app.services.clause_classifier_service import (
    ClauseClassifierService,
)
from app.services.clause_segmentation_service import (
    ClauseSegmentationService,
)
from app.services.clause_storage_service import (
    ClauseStorageService,
)
from app.services.clause_analysis_service import (
    ClauseAnalysisService,
)
from app.services.clause_relationship_service import (
    ClauseRelationshipService,
)
from app.services.contract_summary_service import (
    ContractSummaryService,
)
from app.services.file_ingestion_service import (
    FileIngestionService,
)


router = APIRouter(
    prefix="/clauses",
    tags=["Clauses"],
)


def _relationship_to_schema(relationship):
    return {
        "source_clause_id": relationship.source_clause_id,
        "target_clause_id": relationship.target_clause_id,
        "relationship_type": relationship.relationship_type,
        "evidence": relationship.evidence,
        "confidence": relationship.confidence,
        "metadata": relationship.metadata,
    }


def _db_id_to_clause_id(db_id: str, contract_id: str) -> str:
    prefix = f"{contract_id}_"
    if db_id.startswith(prefix):
        return db_id[len(prefix):]
    return db_id


async def sync_clauses_to_db(
    db: AsyncSession,
    contract_id: str,
    clauses: list[ClauseSchema],
) -> list[ClauseModel]:
    """
    Persist or reconcile clauses for a contract in the Clause table.
    Uses deterministic IDs: f"{contract_id}_{clause.clause_id}".
    Prevents duplicates on repeated analysis.
    """
    result = await db.execute(
        select(ClauseModel)
        .where(ClauseModel.contract_id == contract_id)
    )
    existing_map = {c.id: c for c in result.scalars().all()}
    current_ids = set()

    persisted: list[ClauseModel] = []

    for clause in clauses:
        cid = f"{contract_id}_{clause.clause_id}"
        current_ids.add(cid)

        if cid in existing_map:
            db_clause = existing_map[cid]
            db_clause.clause_number = clause.clause_number
            db_clause.title = clause.title
            db_clause.text = clause.text
            db_clause.order = clause.order
            db_clause.character_count = clause.character_count
            db_clause.parent_clause = clause.parent_clause
            db_clause.clause_type = clause.clause_type
        else:
            db_clause = ClauseModel(
                id=cid,
                contract_id=contract_id,
                clause_number=clause.clause_number,
                title=clause.title,
                text=clause.text,
                order=clause.order,
                character_count=clause.character_count,
                parent_clause=clause.parent_clause,
                clause_type=clause.clause_type,
            )
            db.add(db_clause)

        persisted.append(db_clause)

    for old_id, old_clause in existing_map.items():
        if old_id not in current_ids:
            await db.delete(old_clause)

    await db.flush()
    return persisted


async def sync_clause_analyses_to_db(
    db: AsyncSession,
    contract_id: str,
    analyses: list,
) -> list[ClauseAnalysisRecord]:
    """
    Persist or reconcile clause analysis records in the ClauseAnalysisRecord table.
    Prevents duplicate analysis records on repeated analysis.
    """
    result = await db.execute(
        select(ClauseAnalysisRecord)
        .where(ClauseAnalysisRecord.contract_id == contract_id)
    )
    existing_map = {a.clause_id: a for a in result.scalars().all()}
    current_clause_ids = set()

    persisted: list[ClauseAnalysisRecord] = []

    for analysis in analyses:
        db_clause_id = f"{contract_id}_{analysis.clause_id}"
        current_clause_ids.add(db_clause_id)

        analysis_dict = asdict(analysis)
        analysis_json = json.dumps(analysis_dict, ensure_ascii=False)

        if db_clause_id in existing_map:
            rec = existing_map[db_clause_id]
            rec.clause_type = analysis.clause_type
            rec.risk_level = analysis.risk_level or "LOW"
            rec.risk_score = int(analysis.risk_score or 0)
            rec.meaning = analysis.meaning
            rec.analysis_data = analysis_json
        else:
            rec = ClauseAnalysisRecord(
                id=str(uuid.uuid4()),
                contract_id=contract_id,
                clause_id=db_clause_id,
                clause_type=analysis.clause_type,
                risk_level=analysis.risk_level or "LOW",
                risk_score=int(analysis.risk_score or 0),
                meaning=analysis.meaning,
                analysis_data=analysis_json,
            )
            db.add(rec)

        persisted.append(rec)

    for old_cid, old_rec in existing_map.items():
        if old_cid not in current_clause_ids:
            await db.delete(old_rec)

    await db.flush()
    return persisted


def _analysis_to_schema(analysis) -> ClauseAnalysis:
    data = asdict(analysis)

    clause_number = data["clause_number"]

    if clause_number is None:
        clause_id = str(data["clause_id"])

        if clause_id.startswith("clause-"):
            try:
                clause_number = clause_id.split("-", 1)[1]
            except IndexError:
                clause_number = None

    legal_references = data.get("legal_references", [])

    return ClauseAnalysis(
        clause_id=data["clause_id"],
        clause_number=clause_number,
        clause_type=data["clause_type"],
        title=data.get("title"),
        meaning=data["meaning"],
        key_points=[],

        # Entities
        entities=data["parties"],
        persons=data["persons"],
        organizations=data["organizations"],
        authorities=data["authorities"],
        jurisdictions=data["jurisdiction"],

        # Actions / effects
        obligations=data["obligations"],
        rights=data["rights"],
        permissions=data["permissions"],
        prohibitions=data["prohibitions"],
        duties=data["duties"],
        conditions=data["conditions"],
        exceptions=data["exceptions"],
        triggers=data["triggers"],
        consequences=data["consequences"],

        # Timing / financial
        dates=data["dates"],
        deadlines=data["deadlines"],
        durations=data["durations"],
        monetary_terms=data["monetary_terms"],
        currencies=data["currencies"],
        percentages=data["percentages"],
        quantities=data["quantities"],
        fees=data["fees"],
        penalties=data["penalties"],
        taxes=data["taxes"],

        # Legal references
        laws=data["laws"],
        regulations=data["regulations"],
        statutes=data["statutes"],
        sections=data["sections"],
        articles=data["articles"],
        rules=data["rules"],
        case_references=data["case_references"],
        citations=legal_references,
        legal_reference_explanations=[],

        # Additional API fields
        notices=data.get("notice_terms", []),
        decisions=[],
        orders=[],
        evidence=[],
        definitions=[],

        # Domain-specific fields
        employment_terms=data["employment_terms"],
        financial_terms=data["compensation_terms"],
        loan_terms=data["loan_terms"],
        property_terms=data["property_terms"],
        intellectual_property_terms=data["intellectual_property_terms"],
        privacy_terms=data["privacy_terms"],
        dispute_resolution_terms=data["dispute_terms"],
        confidentiality_terms=data["confidentiality_terms"],

        # Risk
        risk_level=data["risk_level"],
        risk_score=data["risk_score"],
        risk_reasons=data["risk_reasons"],
        user_impact=data["user_impact"],
        recommendations=data["recommendations"],

        # Analysis metadata
        detected_features=[],
        confidence=1.0,
    )


async def _load_clauses(file_id: str, db: AsyncSession | None = None) -> list[ClauseSchema]:
    # 1. If DB session available, check Clause table first
    if db is not None:
        result = await db.execute(
            select(ClauseModel)
            .where(ClauseModel.contract_id == file_id)
            .order_by(ClauseModel.order.asc())
        )
        db_clauses = result.scalars().all()
        if db_clauses:
            clauses = [
                ClauseSchema(
                    clause_id=_db_id_to_clause_id(c.id, file_id),
                    clause_number=c.clause_number,
                    title=c.title,
                    text=c.text,
                    order=c.order,
                    character_count=c.character_count,
                    parent_clause=c.parent_clause,
                    clause_type=c.clause_type,
                )
                for c in db_clauses
            ]

            if any(clause.clause_type is None for clause in clauses):
                clauses = ClauseClassifierService.classify_many(clauses)
                await sync_clauses_to_db(db, file_id, clauses)
                ClauseStorageService.save_clauses(file_id=file_id, clauses=clauses)

            return clauses

    # 2. Fallback to extracted text / ClauseStorageService
    try:
        clean_file_id = FileIngestionService.validate_file_id(file_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    extracted_path = (
        FileIngestionService.EXTRACTED_DIR
        / f"{clean_file_id}.txt"
    ).resolve()

    if (
        not extracted_path.is_relative_to(FileIngestionService.EXTRACTED_DIR.resolve())
        or not extracted_path.exists()
    ):
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    clauses = ClauseStorageService.load_clauses(
        clean_file_id
    )

    if not clauses:
        text = extracted_path.read_text(
            encoding="utf-8",
        )

        clauses = ClauseSegmentationService.segment(
            text
        )

        if not clauses:
            raise HTTPException(
                status_code=400,
                detail="No clauses could be detected.",
            )

        clauses = ClauseClassifierService.classify_many(
            clauses
        )

        ClauseStorageService.save_clauses(
            file_id=file_id,
            clauses=clauses,
        )

    elif any(
        clause.clause_type is None
        for clause in clauses
    ):
        clauses = ClauseClassifierService.classify_many(
            clauses
        )

        ClauseStorageService.save_clauses(
            file_id=file_id,
            clauses=clauses,
        )

    if db is not None:
        await sync_clauses_to_db(db, file_id, clauses)

    return clauses


@router.get(
    "/{file_id}/relationships",
    response_model=ClauseRelationshipResponse,
)
async def get_clause_relationships(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    clauses = await _load_clauses(file_id, db)

    relationships = ClauseRelationshipService.analyze_relationships(
        clauses
    )

    return ClauseRelationshipResponse(
        file_id=file_id,
        relationship_count=len(relationships),
        relationships=[
            _relationship_to_schema(relationship)
            for relationship in relationships
        ],
    )


@router.get(
    "/{file_id}",
    response_model=ClauseSegmentationResponse,
)
async def get_clauses(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClauseSegmentationResponse:

    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    clauses = await _load_clauses(file_id, db)
    await sync_clauses_to_db(db, file_id, clauses)
    await db.commit()

    return ClauseSegmentationResponse(
        file_id=file_id,
        clause_count=len(clauses),
        clauses=clauses,
    )


@router.get(
    "/{file_id}/analysis",
    response_model=ClauseAnalysisResponse,
)
async def get_clause_analysis(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClauseAnalysisResponse:

    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    clauses = await _load_clauses(file_id, db)
    await sync_clauses_to_db(db, file_id, clauses)

    analyses = ClauseAnalysisService.analyze_clauses(
        clauses
    )

    await sync_clause_analyses_to_db(db, file_id, analyses)

    high = sum(
        1
        for analysis in analyses
        if analysis.risk_level == "HIGH"
    )
    medium = sum(
        1
        for analysis in analyses
        if analysis.risk_level == "MEDIUM"
    )
    low = sum(
        1
        for analysis in analyses
        if analysis.risk_level == "LOW"
    )

    overall_risk = ContractSummaryService._calculate_overall_risk(
        high=high,
        medium=medium,
        low=low,
    )
    overall_risk_score = ContractSummaryService._calculate_overall_risk_score(
        analyses
    )

    result = await db.execute(
        select(Contract).where(
            Contract.id == file_id,
            Contract.user_id == current_user.id,
        )
    )
    contract_row = result.scalar_one_or_none()
    if contract_row:
        contract_row.overall_risk = overall_risk
        contract_row.overall_risk_score = overall_risk_score

    await db.commit()

    schema_analyses = [
        _analysis_to_schema(analysis)
        for analysis in analyses
    ]

    return ClauseAnalysisResponse(
        file_id=file_id,
        analysis_count=len(schema_analyses),
        analyses=schema_analyses,
    )


@router.get(
    "/{file_id}/summary",
    response_model=ContractSummary,
)
async def get_contract_summary(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractSummary:

    contract = await require_owned_contract(db, current_user, file_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted document not found.",
        )

    clauses = await _load_clauses(file_id, db)

    analyses = ClauseAnalysisService.analyze_clauses(
        clauses
    )

    summary = ContractSummaryService.generate(
        file_id=file_id,
        analyses=analyses,
    )

    result = await db.execute(
        select(Contract).where(
            Contract.id == file_id,
            Contract.user_id == current_user.id,
        )
    )
    contract_row = result.scalar_one_or_none()
    if contract_row:
        contract_row.overall_risk = summary.overall_risk
        contract_row.overall_risk_score = summary.overall_risk_score
        await db.commit()

    return summary

