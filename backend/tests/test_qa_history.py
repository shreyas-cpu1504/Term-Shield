import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.qa_history import QAHistory


def _upload_contract(client: TestClient, filename: str = "qa_history_test.txt") -> str:
    content = (
        b"1. Confidentiality\n"
        b"The recipient agrees to keep all information confidential for 5 years.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement with 30 days notice.\n\n"
        b"3. Payment Terms\n"
        b"Invoices are payable within 15 days of receipt.\n"
    )
    resp = client.post(
        "/api/v1/ingestion/file",
        files={"file": (filename, content, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["file_id"]


def test_qa_persistence_and_history_retrieval(client: TestClient):
    """Authenticated user creates QA history and can retrieve it."""
    file_id = _upload_contract(client, "qa_persist_1.txt")

    # Ask question
    qa_resp = client.post(
        f"/api/v1/qa/{file_id}",
        json={"question": "What is the confidentiality period?"},
    )
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert qa_data["question"] == "What is the confidentiality period?"
    assert qa_data["answer"]

    # Retrieve history
    hist_resp = client.get(f"/api/v1/qa/{file_id}/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    record = history[0]
    assert record["contract_id"] == file_id
    assert record["question"] == "What is the confidentiality period?"
    assert record["answer"] == qa_data["answer"]
    assert "created_at" in record
    assert "id" in record


def test_multiple_qa_preserves_chronological_order(client: TestClient):
    """Multiple Q&As preserve chronological order."""
    file_id = _upload_contract(client, "qa_chronological.txt")

    q1 = "What is the confidentiality period?"
    q2 = "What is the notice period for termination?"
    q3 = "When are invoices payable?"

    client.post(f"/api/v1/qa/{file_id}", json={"question": q1})
    client.post(f"/api/v1/qa/{file_id}", json={"question": q2})
    client.post(f"/api/v1/qa/{file_id}", json={"question": q3})

    hist_resp = client.get(f"/api/v1/qa/{file_id}/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 3
    assert history[0]["question"] == q1
    assert history[1]["question"] == q2
    assert history[2]["question"] == q3
    assert history[0]["created_at"] <= history[1]["created_at"] <= history[2]["created_at"]


def test_unauthenticated_history_access_rejected():
    """Unauthenticated access to history endpoint returns 401."""
    unauth_client = TestClient(app)
    resp = unauth_client.get("/api/v1/qa/some-fake-file-id/history")
    assert resp.status_code == 401


def test_cross_user_qa_isolation(client: TestClient, other_client: TestClient):
    """User B cannot access or view User A's QA history or ask questions on User A's contract."""
    file_id = _upload_contract(client, "user_a_contract.txt")

    # User A asks a question
    client.post(
        f"/api/v1/qa/{file_id}",
        json={"question": "What is the confidentiality period?"},
    )

    # User B attempts to access User A's QA history -> 404
    other_hist_resp = other_client.get(f"/api/v1/qa/{file_id}/history")
    assert other_hist_resp.status_code == 404

    # User B attempts to ask a question on User A's contract -> 404
    other_ask_resp = other_client.post(
        f"/api/v1/qa/{file_id}",
        json={"question": "What is the termination notice?"},
    )
    assert other_ask_resp.status_code == 404

    # User A can still retrieve their own history
    owner_hist_resp = client.get(f"/api/v1/qa/{file_id}/history")
    assert owner_hist_resp.status_code == 200
    assert len(owner_hist_resp.json()) == 1


def test_nonexistent_contract_history_returns_404(client: TestClient):
    """Querying history for a nonexistent contract returns 404."""
    resp = client.get("/api/v1/qa/non-existent-contract-id-12345/history")
    assert resp.status_code == 404


def test_history_isolated_per_contract(client: TestClient):
    """QA history is isolated per contract for the same user."""
    file_id_1 = _upload_contract(client, "contract_one.txt")
    file_id_2 = _upload_contract(client, "contract_two.txt")

    client.post(
        f"/api/v1/qa/{file_id_1}",
        json={"question": "What is the confidentiality period?"},
    )

    hist_1 = client.get(f"/api/v1/qa/{file_id_1}/history").json()
    hist_2 = client.get(f"/api/v1/qa/{file_id_2}/history").json()

    assert len(hist_1) == 1
    assert hist_1[0]["question"] == "What is the confidentiality period?"
    assert len(hist_2) == 0


@pytest.mark.asyncio
async def test_contract_deletion_removes_qa_history_safely(client: TestClient):
    """Deleting a contract cascades and cleans up all related QAHistory records."""
    file_id = _upload_contract(client, "delete_cascade_qa.txt")

    client.post(
        f"/api/v1/qa/{file_id}",
        json={"question": "What is the notice period for termination?"},
    )

    # Verify history exists in DB
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(QAHistory).where(QAHistory.contract_id == file_id)
        )
        assert len(res.scalars().all()) == 1

    # Delete contract
    del_resp = client.delete(f"/api/v1/contracts/{file_id}")
    assert del_resp.status_code == 200

    # Verify DB records for QAHistory are gone
    async with AsyncSessionLocal() as session:
        res_after = await session.execute(
            select(QAHistory).where(QAHistory.contract_id == file_id)
        )
        assert len(res_after.scalars().all()) == 0

    # Verify endpoint returns 404 now
    hist_resp = client.get(f"/api/v1/qa/{file_id}/history")
    assert hist_resp.status_code == 404
