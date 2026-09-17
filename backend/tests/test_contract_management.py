import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.models.clause import Clause
from app.models.clause_analysis import ClauseAnalysisRecord
from app.models.contract import Contract
from app.models.qa_history import QAHistory
from app.core.database import AsyncSessionLocal
from sqlalchemy import select


def _upload_contract(client: TestClient, filename: str = "test_contract.txt") -> str:
    content = (
        b"1. Confidentiality Agreement\n"
        b"The recipient agrees to keep all information confidential for 5 years.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement with 30 days notice.\n\n"
        b"3. Unlimited Liability\n"
        b"Vendor shall have unlimited liability for all direct and indirect damages.\n"
    )
    resp = client.post(
        "/api/v1/ingestion/file",
        files={"file": (filename, content, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["file_id"]


def test_delete_contract_owner_success(client: TestClient):
    """Authenticated owner can delete their contract and it disappears from GET /contracts."""
    file_id = _upload_contract(client, "owner_test.txt")

    # Verify contract exists in library
    list_resp = client.get("/api/v1/contracts")
    assert list_resp.status_code == 200
    contracts = list_resp.json()
    assert any(c["id"] == file_id for c in contracts)

    # Delete the contract
    delete_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert delete_resp.status_code == 200, delete_resp.text
    delete_data = delete_resp.json()
    assert delete_data["id"] == file_id
    assert "deleted successfully" in delete_data["message"]

    # Verify it is no longer in GET /contracts
    list_after_resp = client.get("/api/v1/contracts")
    assert list_after_resp.status_code == 200
    contracts_after = list_after_resp.json()
    assert not any(c["id"] == file_id for c in contracts_after)

    # Verify querying its clauses returns 404
    clauses_resp = client.get(f"/api/v1/clauses/{file_id}")
    assert clauses_resp.status_code == 404


def test_delete_contract_unauthenticated():
    """Unauthenticated delete request is rejected with 401."""
    from app.main import app
    unauth = TestClient(app)
    resp = unauth.delete("/api/v1/contracts/some-random-id")
    assert resp.status_code == 401
    assert resp.json()["detail"] in {
        "Authentication required",
        "Invalid or expired authentication token",
    }


def test_user_cannot_delete_another_users_contract(client: TestClient, other_client: TestClient):
    """User B cannot delete User A's contract; returns authorization-safe 404."""
    file_id = _upload_contract(client, "user_a_contract.txt")

    # Attempt to delete from other_client (User B)
    bad_delete_resp = other_client.delete(f"/api/v1/contracts/{file_id}")
    assert bad_delete_resp.status_code == 404
    assert bad_delete_resp.json()["detail"] == "Contract not found"

    # Verify contract still exists for User A
    list_resp = client.get("/api/v1/contracts")
    assert any(c["id"] == file_id for c in list_resp.json())


def test_delete_nonexistent_contract(client: TestClient):
    """Deleting a nonexistent contract returns 404."""
    resp = client.delete(f"/api/v1/contracts/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Contract not found"


@pytest.mark.asyncio
async def test_delete_contract_with_dependent_records_integrity(client: TestClient):
    """Deleting a contract with clauses, analyses, and QA records cleanly cascades without integrity errors."""
    file_id = _upload_contract(client, "dependent_records_test.txt")

    # Attach dependent records in DB
    clause_id = f"clause-{file_id}-1"
    async with AsyncSessionLocal() as session:
        clause = Clause(
            id=clause_id,
            contract_id=file_id,
            clause_number="1",
            title="Liability",
            text="Unlimited liability clause text.",
            order=1,
            character_count=32,
        )
        session.add(clause)

        analysis = ClauseAnalysisRecord(
            contract_id=file_id,
            clause_id=clause_id,
            risk_level="HIGH",
            risk_score=90,
            meaning="Unlimited liability",
        )
        session.add(analysis)

        qa = QAHistory(
            contract_id=file_id,
            question="What is liability?",
            answer="Unlimited liability applies.",
        )
        session.add(qa)
        await session.commit()

    # Verify records exist in database
    async with AsyncSessionLocal() as session:
        clauses_res = await session.execute(
            select(Clause).where(Clause.contract_id == file_id)
        )
        assert len(clauses_res.scalars().all()) == 1

        analyses_res = await session.execute(
            select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id)
        )
        assert len(analyses_res.scalars().all()) == 1

        qa_res = await session.execute(
            select(QAHistory).where(QAHistory.contract_id == file_id)
        )
        assert len(qa_res.scalars().all()) == 1

    # Delete contract via DELETE endpoint
    delete_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert delete_resp.status_code == 200

    # Verify in DB that contract and all dependent records are completely gone
    async with AsyncSessionLocal() as session:
        contract_res = await session.execute(
            select(Contract).where(Contract.id == file_id)
        )
        assert contract_res.scalar_one_or_none() is None

        clauses_after = await session.execute(
            select(Clause).where(Clause.contract_id == file_id)
        )
        assert len(clauses_after.scalars().all()) == 0

        analyses_after = await session.execute(
            select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == file_id)
        )
        assert len(analyses_after.scalars().all()) == 0

        qa_after = await session.execute(
            select(QAHistory).where(QAHistory.contract_id == file_id)
        )
        assert len(qa_after.scalars().all()) == 0
