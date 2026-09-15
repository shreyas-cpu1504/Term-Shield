from pathlib import Path

from app.services.file_ingestion_service import FileIngestionService


def test_contract_qa_endpoint(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n\n"
        b"3. Confidentiality\n"
        b"The receiving party shall keep all confidential information "
        b"strictly confidential.\n"
    )

    upload_response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "qa_test_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        response = client.post(
            f"/api/v1/qa/{file_id}",
            json={
                "question": "When must the customer pay the invoice?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["file_id"] == file_id
        assert data["question"] == (
            "When must the customer pay the invoice?"
        )

        assert data["answer"]
        assert data["evidence"]
        assert data["confidence"] > 0

        evidence = data["evidence"][0]

        assert evidence["clause_number"] == "1"
        assert "30 days" in evidence["text"]
        assert evidence["relevance_score"] > 0

    finally:
        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(
                    f"{file_id}.*"
                ):
                    path.unlink()

        clauses_path = (
            Path("storage/clauses")
            / f"{file_id}.json"
        )

        if clauses_path.exists():
            clauses_path.unlink()


def test_contract_qa_termination_question(client):
    content = (
        b"1. Payment\n"
        b"The Customer shall pay the invoice within 30 days.\n\n"
        b"2. Termination\n"
        b"Either party may terminate this agreement upon written notice.\n"
    )

    upload_response = client.post(
        "/api/v1/ingestion/file",
        files={
            "file": (
                "termination_qa_contract.txt",
                content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    try:
        response = client.post(
            f"/api/v1/qa/{file_id}",
            json={
                "question": "How can the agreement be terminated?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["answer"]
        assert data["evidence"]

        evidence = data["evidence"][0]

        assert evidence["clause_number"] == "2"
        assert "terminate" in evidence["text"].lower()

    finally:
        for directory in (
            FileIngestionService.UPLOAD_DIR,
            FileIngestionService.EXTRACTED_DIR,
        ):
            if directory.exists():
                for path in directory.glob(
                    f"{file_id}.*"
                ):
                    path.unlink()

        clauses_path = (
            Path("storage/clauses")
            / f"{file_id}.json"
        )

        if clauses_path.exists():
            clauses_path.unlink()


def test_contract_qa_unknown_file_returns_404(client):
    response = client.post(
        "/api/v1/qa/does-not-exist",
        json={
            "question": "What is the payment deadline?"
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Extracted document not found."
    )


def test_contract_qa_rejects_empty_question(client):
    response = client.post(
        "/api/v1/qa/some-file",
        json={
            "question": ""
        },
    )

    assert response.status_code == 422