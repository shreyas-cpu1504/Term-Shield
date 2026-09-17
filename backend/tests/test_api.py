from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.file_ingestion_service import FileIngestionService


@pytest.fixture()
def unauth_client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(unauth_client):
    response = unauth_client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "Contract Simplifier API"
    assert data["version"] == "0.1.0"


def test_text_ingestion_endpoint(client):
    response = client.post(
        "/api/v1/ingestion/text",
        json={
            "input_type": "text",
            "content": "Payment shall be made within 30 days.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Text received successfully."
    assert data["input_type"] == "text"
    assert data["character_count"] == len(
        "Payment shall be made within 30 days."
    )


def test_text_ingestion_rejects_empty_content(client):
    response = client.post(
        "/api/v1/ingestion/text",
        json={
            "input_type": "text",
            "content": "",
        },
    )

    assert response.status_code == 422


def test_clause_endpoints_return_404_for_unknown_file(client):
    file_id = "api-test-file-that-does-not-exist"

    endpoints = [
        f"/api/v1/clauses/{file_id}",
        f"/api/v1/clauses/{file_id}/analysis",
        f"/api/v1/clauses/{file_id}/relationships",
        f"/api/v1/clauses/{file_id}/summary",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Extracted document not found."
        )


def test_file_upload_endpoint(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n"
    )

    response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "api_test_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_id"]
    assert data["filename"] == "api_test_contract.txt"
    assert data["file_type"] == "txt"
    assert data["size_bytes"] == len(content)
    assert data["character_count"] > 0
    assert "Payment" in data["extracted_text"]

    file_id = data["file_id"]

    extracted_path = (
        FileIngestionService.EXTRACTED_DIR
        / f"{file_id}.txt"
    )

    assert extracted_path.exists()

    uploaded_path = (
        FileIngestionService.UPLOAD_DIR
        / f"{file_id}.txt"
    )

    if uploaded_path.exists():
        uploaded_path.unlink()

    if extracted_path.exists():
        extracted_path.unlink()


def test_contract_analysis_pipeline(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay 10,000 USD within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n\n"
        b"3. Confidentiality\n"
        b"The receiving party shall keep all confidential information "
        b"strictly confidential.\n\n"
        b"4. Liability\n"
        b"The Customer shall have unlimited liability for all losses.\n"
    )

    upload_response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "pipeline_test_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        # ----------------------------------------------------------
        # 1. Clause segmentation
        # ----------------------------------------------------------
        clauses_response = client.get(
            f"/api/v1/clauses/{file_id}"
        )

        assert clauses_response.status_code == 200

        clauses_data = clauses_response.json()

        assert clauses_data["file_id"] == file_id
        assert clauses_data["clause_count"] >= 4
        assert clauses_data["clauses"]

        # ----------------------------------------------------------
        # 2. Clause analysis
        # ----------------------------------------------------------
        analysis_response = client.get(
            f"/api/v1/clauses/{file_id}/analysis"
        )

        assert analysis_response.status_code == 200

        analysis_data = analysis_response.json()

        assert analysis_data["file_id"] == file_id
        assert analysis_data["analysis_count"] >= 4
        assert analysis_data["analyses"]

        # Verify risk analysis actually detects
        # the unlimited-liability clause.
        risk_levels = {
            analysis["risk_level"]
            for analysis in analysis_data["analyses"]
        }

        assert "HIGH" in risk_levels

        # ----------------------------------------------------------
        # 3. Clause relationships
        # ----------------------------------------------------------
        relationships_response = client.get(
            f"/api/v1/clauses/{file_id}/relationships"
        )

        assert relationships_response.status_code == 200

        relationships_data = relationships_response.json()

        assert relationships_data["file_id"] == file_id
        assert "relationship_count" in relationships_data
        assert "relationships" in relationships_data

        # ----------------------------------------------------------
        # 4. Contract summary
        # ----------------------------------------------------------
        summary_response = client.get(
            f"/api/v1/clauses/{file_id}/summary"
        )

        assert summary_response.status_code == 200

        summary_data = summary_response.json()

        assert summary_data["file_id"] == file_id
        assert summary_data["total_clauses"] >= 4

        assert summary_data["overall_risk"] in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }

        assert summary_data["overall_risk"] == "HIGH"

        assert "risk_summary" in summary_data
        assert "summary_points" in summary_data

        # ----------------------------------------------------------
        # 5. Database risk persistence
        # ----------------------------------------------------------
        contracts_response = client.get("/api/v1/contracts")
        assert contracts_response.status_code == 200
        user_contracts = contracts_response.json()
        persisted = next((c for c in user_contracts if c["id"] == file_id), None)
        assert persisted is not None
        assert persisted["overall_risk"] == "HIGH"
        assert persisted["overall_risk_score"] > 0

    finally:
        # ----------------------------------------------------------
        # Clean up uploaded/extracted files
        # ----------------------------------------------------------
        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(
                    f"{file_id}.*"
                ):
                    path.unlink()

        # ----------------------------------------------------------
        # Clean up stored clauses
        # ----------------------------------------------------------
        clauses_path = (
            Path("storage/clauses")
            / f"{file_id}.json"
        )

        if clauses_path.exists():
            clauses_path.unlink()

def test_unauthenticated_requests_are_rejected(unauth_client):
    """Phase 3: protected endpoints must return 401 without a token."""

    protected = [
        ("post", "/api/v1/ingestion/text", {"json": {"input_type": "text", "content": "hello"}}),
        ("post", "/api/v1/ingestion/url", {"json": {"url": "https://example.com/x.pdf"}}),
        ("get", "/api/v1/clauses/some-file", {}),
        ("get", "/api/v1/clauses/some-file/analysis", {}),
        ("get", "/api/v1/clauses/some-file/relationships", {}),
        ("get", "/api/v1/clauses/some-file/summary", {}),
        ("post", "/api/v1/qa/some-file", {"json": {"question": "what?"}}),
    ]

    for method, url, kwargs in protected:
        response = getattr(unauth_client, method)(url, **kwargs)

        assert response.status_code == 401, f"{method} {url} -> {response.status_code}"
        assert response.json()["detail"] in {
            "Authentication required",
            "Invalid or expired authentication token",
        }


def test_user_cannot_access_another_users_contract(client, other_client):
    """Phase 3: users must only see their own contract data."""
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n"
    )

    upload_response = other_client.post(
        "/api/v1/ingestion/file",
        files={"file": ("isolation_test.txt", content, "text/plain")},
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        for url in (
            f"/api/v1/clauses/{file_id}",
            f"/api/v1/clauses/{file_id}/analysis",
            f"/api/v1/clauses/{file_id}/relationships",
            f"/api/v1/clauses/{file_id}/summary",
        ):
            response = client.get(url)

            assert response.status_code == 404, (
                f"{url} returned {response.status_code}"
            )
            assert response.json()["detail"] == "Extracted document not found."

        qa_response = client.post(
            f"/api/v1/qa/{file_id}",
            json={"question": "When is payment due?"},
        )

        assert qa_response.status_code == 404

        # Owner still has access
        owner_response = other_client.get(f"/api/v1/clauses/{file_id}")

        assert owner_response.status_code == 200
        assert owner_response.json()["file_id"] == file_id

    finally:
        import os

        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(f"{file_id}.*"):
                    path.unlink()

        clauses_path = Path("storage/clauses") / f"{file_id}.json"
        if clauses_path.exists():
            clauses_path.unlink()
