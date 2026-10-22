import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

def main():
    import uuid
    reg_client = TestClient(app)
    reg_res = reg_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Live Validation User",
            "email": f"live-val-{uuid.uuid4()}@example.com",
            "password": "Password123!",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["access_token"]

    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    print("=" * 80)
    print("TERM SHIELD AI - ASK MY T&C LIVE API VALIDATION (SECTION 19)")
    print("=" * 80)

    contract_content = (
        "Agreement Title: Cloud Services & Software License Agreement\n\n"
        "1. Definitions and Interpretation\n"
        "In this Agreement, 'Customer Data' means all electronic data or information submitted by Customer.\n\n"
        "4. Fees and Payment\n"
        "Customer shall pay all undisputed fees within thirty (30) days of invoice date. Late payments incur 1.5% interest per month.\n\n"
        "7. Term and Renewal\n"
        "This agreement shall automatically renew for another 12 months unless either party provides 30 days written notice prior to the expiration of the current term.\n\n"
        "8. Termination for Cause\n"
        "Either party may terminate this agreement immediately upon written notice if the other party breaches any material term and fails to cure within 15 days.\n\n"
        "12. Notice Period and Truncated Clause\n"
        "This agreement shall automatically renew for another 12 months unless either party provides 30 da\n\n"
    )

    print("\n[Step 0] Uploading Real Contract...")
    upload_res = client.post(
        "/api/v1/ingestion/file",
        files={"file": ("live_master_agreement.txt", contract_content.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    file_id = upload_res.json()["file_id"]
    print(f"Uploaded successfully. Contract File ID: {file_id}")

    def ask(step_num: int, label: str, question: str, expected_lang: str = None):
        print("\n" + "-" * 80)
        print(f"Scenario {step_num}: {label}")
        print(f"USER: '{question}'")
        payload = {"question": question}
        if expected_lang:
            payload["language"] = expected_lang

        t0 = time.time()
        res = client.post(f"/api/v1/qa/{file_id}", json=payload)
        elapsed = time.time() - t0

        data = res.json()
        print(f"ASSISTANT (Language: {data.get('language')}, Confidence: {data.get('confidence')}, Time: {elapsed:.2f}s):")
        print(data.get("answer"))
        if data.get("evidence"):
            print(f"[Evidence Clauses: {[e.get('clause_number') for e in data.get('evidence')]}]")
        time.sleep(2)
        return data

    try:
        # 1. Explain Clause 7
        ask(1, "Explain Clause 7 (English)", "Explain Clause 7")

        # 2. Explain Clause 7 in Telugu
        ask(2, "Explain Clause 7 in Telugu", "Explain Clause 7 in Telugu")

        # 3. Explain Clause 7 in Hindi
        ask(3, "Explain Clause 7 in Hindi", "Explain Clause 7 in Hindi")

        # 4. Explain Clause 7 in Tamil
        ask(4, "Explain Clause 7 in Tamil", "Explain Clause 7 in Tamil")

        # Conversational flow with Clause 7:
        client.delete(f"/api/v1/qa/{file_id}/history")
        print("\n[Restarting chat for follow-up sequence 5 -> 6 -> 7 -> 8]")

        # Base turn: Explain Clause 7
        ask(5, "Base turn: Explain Clause 7", "Explain Clause 7")

        # 5. Follow-up: in Telugu
        ask(5, "Follow-up: in Telugu", "in Telugu")

        # 6. Follow-up: make it simple
        ask(6, "Follow-up: make it simple", "make it simple")

        # 7. Follow-up: what do I need to do?
        ask(7, "Follow-up: what do I need to do?", "what do I need to do?")

        # 8. Follow-up: what happens if I don't do it?
        ask(8, "Follow-up: what happens if I don't do it?", "what happens if I don't do it?")

        # 9. Ask a general contract question (payment notice period and deadline)
        ask(9, "What is the payment notice period and deadline?", "What is the payment notice period and deadline?")

        # 10. What is the termination period?
        ask(10, "What is the termination period?", "What is the termination period?")

        # 11. Test truncated clause
        ask(11, "Explain Clause 12 (Truncated clause ending in '30 da')", "Explain Clause 12")

        # 12. Clear chat
        print("\n" + "-" * 80)
        print("Scenario 12: Clear Chat")
        del_res = client.delete(f"/api/v1/qa/{file_id}/history")
        print(f"DELETE /api/v1/qa/{file_id}/history -> Status: {del_res.status_code}")
        print(f"Response: {del_res.json()}")

        # Verify chat is empty
        hist_res = client.get(f"/api/v1/qa/{file_id}/history")
        print(f"GET /api/v1/qa/{file_id}/history after clear -> Count: {len(hist_res.json())}")

        # 13. Ask Clause 4 after clearing chat
        ask(13, "Ask Clause 4 after clearing chat (fresh session)", "What does Clause 4 say about fees and payment?")

        # Verify history has exactly 1 new item
        hist_res2 = client.get(f"/api/v1/qa/{file_id}/history")
        print(f"GET /api/v1/qa/{file_id}/history -> Count: {len(hist_res2.json())}")

    finally:
        client.delete(f"/api/v1/contracts/{file_id}")
        print("\n[Done] Cleaned up live validation test contract.")

if __name__ == "__main__":
    main()
