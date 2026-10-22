"""Tests for Reports page state requirements:
- New user with 0 contracts
- User with 1+ contracts
- User-specific contract/analysis isolation
- Missing analysis vs server error
- Rejection of invalid/undefined contract IDs
"""
import uuid
from fastapi.testclient import TestClient
import pytest


def test_newly_registered_user_has_zero_contracts(client: TestClient):
    """A newly registered user has zero contracts, returning an empty list without error."""
    resp = client.get("/api/v1/contracts")
    assert resp.status_code == 200
    contracts = resp.json()
    assert isinstance(contracts, list)
    assert len(contracts) == 0


def test_invalid_or_undefined_contract_id_returns_404(client: TestClient):
    """Backend does not crash or expose data when queried with undefined/null/random contract ID."""
    invalid_ids = ["undefined", "null", str(uuid.uuid4())]

    for target_id in invalid_ids:
        summary_resp = client.get(f"/api/v1/clauses/{target_id}/summary")
        assert summary_resp.status_code == 404

        analysis_resp = client.get(f"/api/v1/clauses/{target_id}/analysis")
        assert analysis_resp.status_code == 404

        rel_resp = client.get(f"/api/v1/clauses/{target_id}/relationships")
        assert rel_resp.status_code == 404


def test_reports_isolation_new_user_cannot_access_other_users_report(
    client: TestClient, other_client: TestClient
):
    """User B (newly registered with 0 contracts) cannot see or generate reports for User A's contract."""
    # User A uploads a contract
    content = (
        b"1. Payment Terms\n"
        b"Client shall pay $10,000 net 30.\n\n"
        b"2. Liability\n"
        b"Liability is strictly limited to fees paid.\n"
    )
    upload_resp = client.post(
        "/api/v1/ingestion/file",
        files={"file": ("contract_a.txt", content, "text/plain")},
    )
    assert upload_resp.status_code == 200
    file_id_a = upload_resp.json()["file_id"]

    # Segment clauses for User A
    seg_resp = client.get(f"/api/v1/clauses/{file_id_a}")
    assert seg_resp.status_code == 200

    # User B checks their own contracts -> must be 0
    user_b_contracts = other_client.get("/api/v1/contracts").json()
    assert len(user_b_contracts) == 0

    # User B tries to access User A's summary or analysis -> must be 404
    summary_resp = other_client.get(f"/api/v1/clauses/{file_id_a}/summary")
    assert summary_resp.status_code == 404
    assert summary_resp.json()["detail"] == "Extracted document not found."

    analysis_resp = other_client.get(f"/api/v1/clauses/{file_id_a}/analysis")
    assert analysis_resp.status_code == 404

    rel_resp = other_client.get(f"/api/v1/clauses/{file_id_a}/relationships")
    assert rel_resp.status_code == 404


def test_user_with_contracts_can_generate_report(client: TestClient):
    """User with 1+ contracts can successfully fetch summary and analysis for reports."""
    content = (
        b"1. Term and Termination\n"
        b"This agreement shall terminate in 1 year unless renewed.\n\n"
        b"2. Governing Law\n"
        b"This agreement is governed by the laws of California.\n"
    )
    upload_resp = client.post(
        "/api/v1/ingestion/file",
        files={"file": ("user_report_contract.txt", content, "text/plain")},
    )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["file_id"]

    # User now has 1 contract
    contracts = client.get("/api/v1/contracts").json()
    assert len(contracts) == 1
    assert contracts[0]["id"] == file_id

    # Segment clauses
    seg_resp = client.get(f"/api/v1/clauses/{file_id}")
    assert seg_resp.status_code == 200

    # Fetch summary for report
    summary_resp = client.get(f"/api/v1/clauses/{file_id}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["file_id"] == file_id
    assert summary["total_clauses"] >= 1
    assert summary["overall_risk"] in ["LOW", "MEDIUM", "HIGH"]
