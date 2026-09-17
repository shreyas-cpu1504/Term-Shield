import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.clause import Clause
from app.models.clause_analysis import ClauseAnalysisRecord
from app.models.contract import Contract


def _upload_contract(client: TestClient, filename: str = "clause_persist_test.txt") -> str:
    content = (
        b"1. Confidentiality\n"
        b"The recipient agrees to keep all proprietary information confidential for a period of 5 years.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement with 30 days written notice to the other party.\n\n"
        b"3. Unlimited Liability\n"
        b"The Vendor shall be subject to unlimited liability for any direct or indirect loss or damages.\n"
    )
    resp = client.post(
        "/api/v1/ingestion/file",
        files={"file": (filename, content, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["file_id"]


@pytest.mark.asyncio
async def test_clause_persistence_and_ordering(client: TestClient):
    """Segmenting and classifying clauses persists Clause records in document order."""
    file_id = _upload_contract(client, "test_order.txt")

    resp = client.get(f"/api/v1/clauses/{file_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["clause_count"] == 3

    # Inspect DB records directly
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Clause)
            .where(Clause.contract_id == file_id)
            .order_by(Clause.order.asc())
        )
        db_clauses = result.scalars().all()

        assert len(db_clauses) == 3
        # Check ordering
        assert [c.order for c in db_clauses] == [1, 2, 3]
        # Check titles / content
        assert "Confidentiality" in (db_clauses[0].title or "")
        assert "Termination" in (db_clauses[1].title or "")
        assert "Unlimited Liability" in (db_clauses[2].title or "")
        # Check clause types
        assert db_clauses[0].clause_type == "CONFIDENTIALITY"
        assert db_clauses[1].clause_type == "TERMINATION"
        assert db_clauses[2].clause_type == "LIABILITY"
        # Check character counts
        assert all(c.character_count > 0 for c in db_clauses)
        assert all(c.contract_id == file_id for c in db_clauses)


@pytest.mark.asyncio
async def test_clause_analysis_persistence(client: TestClient):
    """Analyzing clauses persists ClauseAnalysisRecord rows with risk details."""
    file_id = _upload_contract(client, "test_analysis.txt")

    resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_count"] == 3

    async with AsyncSessionLocal() as session:
        # Check ClauseAnalysisRecord rows
        result = await session.execute(
            select(ClauseAnalysisRecord)
            .where(ClauseAnalysisRecord.contract_id == file_id)
        )
        analyses = result.scalars().all()
        assert len(analyses) == 3

        # Verify risk levels and scores
        risk_levels = {a.risk_level for a in analyses}
        assert "HIGH" in risk_levels  # Unlimited liability

        high_risk_record = next(a for a in analyses if a.risk_level == "HIGH")
        assert high_risk_record.risk_score >= 70
        assert high_risk_record.analysis_data is not None

        parsed_data = json.loads(high_risk_record.analysis_data)
        assert "risk_reasons" in parsed_data
        assert "recommendations" in parsed_data

        # Verify Contract overall_risk is updated
        contract_res = await session.execute(
            select(Contract).where(Contract.id == file_id)
        )
        contract = contract_res.scalar_one()
        assert contract.overall_risk == "HIGH"
        assert contract.overall_risk_score > 0


@pytest.mark.asyncio
async def test_reanalysis_does_not_create_duplicate_clauses_or_analyses(client: TestClient):
    """Repeated analysis requests reconcile existing records and never create duplicate rows."""
    file_id = _upload_contract(client, "test_reanalysis.txt")

    # Run 1: Initial analysis
    resp1 = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp1.status_code == 200

    async with AsyncSessionLocal() as session:
        c1 = (await session.execute(select(Clause).where(Clause.contract_id == file_id))).scalars().all()
        a1 = (await session.execute(select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id))).scalars().all()
        clause_count_initial = len(c1)
        analysis_count_initial = len(a1)
        assert clause_count_initial == 3
        assert analysis_count_initial == 3

    # Run 2: Second analysis call
    resp2 = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp2.status_code == 200

    # Run 3: Clause retrieval call
    resp3 = client.get(f"/api/v1/clauses/{file_id}")
    assert resp3.status_code == 200

    # Run 4: Third analysis call
    resp4 = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp4.status_code == 200

    # Verify no duplicate records were inserted
    async with AsyncSessionLocal() as session:
        c_final = (await session.execute(select(Clause).where(Clause.contract_id == file_id))).scalars().all()
        a_final = (await session.execute(select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id))).scalars().all()
        assert len(c_final) == clause_count_initial
        assert len(a_final) == analysis_count_initial


def test_cross_user_clause_isolation(client: TestClient, other_client: TestClient):
    """User B cannot access User A's clauses or analysis."""
    file_id = _upload_contract(client, "user_a_clauses.txt")

    # User A analyzes contract
    resp_owner = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp_owner.status_code == 200

    # User B attempts to access User A's clauses
    assert other_client.get(f"/api/v1/clauses/{file_id}").status_code == 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/analysis").status_code == 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/relationships").status_code == 404
    assert other_client.get(f"/api/v1/clauses/{file_id}/summary").status_code == 404


def test_nonexistent_contract_clause_endpoints_return_404(client: TestClient):
    """Nonexistent contracts return 404 across all clause endpoints."""
    fake_id = "nonexistent-contract-uuid-12345"
    assert client.get(f"/api/v1/clauses/{fake_id}").status_code == 404
    assert client.get(f"/api/v1/clauses/{fake_id}/analysis").status_code == 404
    assert client.get(f"/api/v1/clauses/{fake_id}/relationships").status_code == 404
    assert client.get(f"/api/v1/clauses/{fake_id}/summary").status_code == 404


@pytest.mark.asyncio
async def test_contract_deletion_removes_persisted_clauses_and_analyses(client: TestClient):
    """Deleting a contract removes all associated Clause and ClauseAnalysisRecord rows."""
    file_id = _upload_contract(client, "delete_cascade_clauses.txt")

    # Analyze to populate DB
    resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert resp.status_code == 200

    # Confirm rows exist
    async with AsyncSessionLocal() as session:
        c_before = (await session.execute(select(Clause).where(Clause.contract_id == file_id))).scalars().all()
        a_before = (await session.execute(select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id))).scalars().all()
        assert len(c_before) > 0
        assert len(a_before) > 0

    # Delete contract
    del_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert del_resp.status_code == 200

    # Confirm rows are removed
    async with AsyncSessionLocal() as session:
        c_after = (await session.execute(select(Clause).where(Clause.contract_id == file_id))).scalars().all()
        a_after = (await session.execute(select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id))).scalars().all()
        assert len(c_after) == 0
        assert len(a_after) == 0


def test_existing_clause_api_response_behavior(client: TestClient):
    """All existing clause endpoints return valid schema structures."""
    file_id = _upload_contract(client, "api_behavior.txt")

    # 1. Segmentation
    seg_resp = client.get(f"/api/v1/clauses/{file_id}")
    assert seg_resp.status_code == 200
    seg_data = seg_resp.json()
    assert "file_id" in seg_data
    assert "clause_count" in seg_data
    assert "clauses" in seg_data
    assert seg_data["clause_count"] == 3

    # 2. Analysis
    ana_resp = client.get(f"/api/v1/clauses/{file_id}/analysis")
    assert ana_resp.status_code == 200
    ana_data = ana_resp.json()
    assert "file_id" in ana_data
    assert "analysis_count" in ana_data
    assert "analyses" in ana_data
    assert ana_data["analysis_count"] == 3

    # 3. Relationships
    rel_resp = client.get(f"/api/v1/clauses/{file_id}/relationships")
    assert rel_resp.status_code == 200
    rel_data = rel_resp.json()
    assert "file_id" in rel_data
    assert "relationship_count" in rel_data
    assert "relationships" in rel_data

    # 4. Summary
    sum_resp = client.get(f"/api/v1/clauses/{file_id}/summary")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert "file_id" in sum_data
    assert "total_clauses" in sum_data
    assert "overall_risk" in sum_data
    assert "overall_risk_score" in sum_data
