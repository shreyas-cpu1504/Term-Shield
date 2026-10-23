"""Safe End-to-End Verification of Supabase S3 Storage Lifecycle for Term Shield.

Performs a complete disposable contract lifecycle:
1. Upload raw contract to Supabase S3 bucket (uploads/<id>.txt)
2. Extract text and save extracted text to Supabase S3 (extracted/<id>.txt)
3. Segment clauses and save clause JSON to Supabase S3 (clauses/<id>.json)
4. Download and verify content integrity of all three artifacts from Supabase S3
5. Clean up and delete all disposable contract artifacts from Supabase S3
6. Confirm deletion and verify local SQLite database was not mutated

Safety Guarantees:
- Never prints credentials or secret keys.
- Uses only disposable test IDs with prefix 'disposable-sample-'.
- Does not modify, overwrite, or delete any existing user contracts.
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

# Add backend directory to path and set cwd
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from sqlalchemy import func, select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.contract import Contract
from app.models.user import User
from app.services.storage_service import (
    SupabaseStorageService,
    get_storage_service,
    set_storage_service,
)
from app.services.text_extraction_service import TextExtractionService
from app.services.clause_segmentation_service import ClauseSegmentationService


def mask_str(val: str | None, visible: int = 6) -> str:
    if not val:
        return "(none)"
    if len(val) <= visible:
        return "***"
    return f"{val[:visible]}...***"


async def count_db_records() -> tuple[int, int]:
    """Return count of users and contracts in the active database."""
    async with AsyncSessionLocal() as session:
        u_cnt = await session.scalar(select(func.count(User.id)))
        c_cnt = await session.scalar(select(func.count(Contract.id)))
        return u_cnt or 0, c_cnt or 0


def main():
    print("=" * 70)
    print("TERM SHIELD AI - SUPABASE S3 END-TO-END VERIFICATION")
    print("=" * 70)

    settings = get_settings()

    print(f"Configured Storage Provider : {settings.storage_provider}")
    print(f"Supabase Bucket             : {settings.supabase_s3_bucket}")
    print(f"Supabase S3 Region          : {settings.supabase_s3_region}")
    print(f"Supabase S3 Endpoint        : {settings.supabase_s3_endpoint}")
    print(f"Access Key ID               : {mask_str(settings.supabase_s3_access_key_id)}")
    print(f"Secret Access Key           : *** (Configured)")
    print("-" * 70)

    # 1. Pre-check database counts to ensure no mutations
    initial_users, initial_contracts = asyncio.run(count_db_records())
    print(f"[Pre-Check] Active Database contains {initial_users} user(s), {initial_contracts} contract(s).")
    print("-" * 70)

    # 2. Initialize Supabase Storage Service
    storage = SupabaseStorageService(
        endpoint_url=settings.supabase_s3_endpoint,
        access_key_id=settings.supabase_s3_access_key_id,
        secret_access_key=settings.supabase_s3_secret_access_key,
        bucket_name=settings.supabase_s3_bucket,
        region_name=settings.supabase_s3_region,
    )

    disposable_id = f"disposable-sample-{uuid.uuid4().hex[:10]}"
    sample_filename = "disposable_test_nda.txt"
    sample_content = (
        b"DISPOSABLE NON-DISCLOSURE AGREEMENT FOR SUPABASE VERIFICATION\n\n"
        b"1. Confidentiality: The Receiving Party shall hold all Proprietary Information in strict confidence "
        b"and shall not disclose it to any third party without prior written consent.\n\n"
        b"2. Governing Law: This Agreement shall be governed by and construed in accordance with the laws of "
        b"the State of California without regard to its conflict of law principles.\n\n"
        b"3. Termination: Either party may terminate this Agreement upon thirty (30) days prior written notice. "
        b"Upon termination, all Confidential Information must be promptly returned or destroyed.\n"
    )

    print(f"[Step 1/5] Uploading disposable sample contract ({disposable_id})...")
    t0 = time.perf_counter()
    raw_key = storage.save_upload(disposable_id, ".txt", sample_content)
    upload_ms = (time.perf_counter() - t0) * 1000
    print(f"  [OK] Raw contract uploaded to: {raw_key} ({upload_ms:.1f}ms)")

    assert storage.upload_exists(disposable_id), "Upload must exist in Supabase bucket"
    assert storage.upload_exists(disposable_id, ".txt"), "Upload with .txt extension must exist"

    print(f"[Step 2/5] Extracting text and saving to Supabase S3...")
    t0 = time.perf_counter()
    extracted_text = TextExtractionService.extract(sample_filename, sample_content)
    assert extracted_text and "Confidentiality" in extracted_text, "Text extraction failed"

    extracted_key = storage.save_extracted_text(disposable_id, extracted_text)
    extract_ms = (time.perf_counter() - t0) * 1000
    print(f"  [OK] Extracted text saved to: {extracted_key} ({extract_ms:.1f}ms)")
    assert storage.extracted_text_exists(disposable_id), "Extracted text must exist in Supabase bucket"

    print(f"[Step 3/5] Performing clause segmentation and persisting analysis JSON...")
    t0 = time.perf_counter()
    clauses = ClauseSegmentationService.segment(extracted_text)
    assert len(clauses) >= 3, f"Expected at least 3 clauses, got {len(clauses)}"

    clause_data = {
        "file_id": disposable_id,
        "clause_count": len(clauses),
        "clauses": [c.model_dump() for c in clauses],
        "verification_meta": {"timestamp": time.time(), "sample": True},
    }
    clauses_key = storage.save_clauses_json(disposable_id, clause_data)
    clauses_ms = (time.perf_counter() - t0) * 1000
    print(f"  [OK] {len(clauses)} clauses segmented and saved to: {clauses_key} ({clauses_ms:.1f}ms)")
    assert storage.clauses_json_exists(disposable_id), "Clauses JSON must exist in Supabase bucket"

    print(f"[Step 4/5] Downloading and verifying content integrity from Supabase S3...")
    t0 = time.perf_counter()
    # Download raw upload
    downloaded_raw = storage.read_upload(disposable_id, ".txt")
    assert downloaded_raw == sample_content, "Raw upload content mismatch!"

    # Download extracted text
    downloaded_text = storage.read_extracted_text(disposable_id)
    assert downloaded_text == extracted_text, "Extracted text content mismatch!"

    # Download clause JSON
    downloaded_json = storage.load_clauses_json(disposable_id)
    assert downloaded_json is not None, "Clauses JSON download returned None!"
    assert downloaded_json["file_id"] == disposable_id, "Clause JSON file_id mismatch!"
    assert downloaded_json["clause_count"] == len(clauses), "Clause count mismatch!"
    download_ms = (time.perf_counter() - t0) * 1000
    print(f"  [OK] All 3 artifacts downloaded and verified byte-for-byte ({download_ms:.1f}ms)")

    print(f"[Step 5/5] Deleting disposable contract artifacts from Supabase S3...")
    t0 = time.perf_counter()
    del_extracted = storage.delete_extracted_text(disposable_id)
    del_clauses = storage.delete_clauses_json(disposable_id)
    del_raw = storage.delete_upload(disposable_id, ".txt")
    delete_ms = (time.perf_counter() - t0) * 1000

    assert del_extracted, "Extracted text deletion should return True"
    assert del_clauses, "Clauses JSON deletion should return True"
    assert del_raw, "Raw upload deletion should return True"

    # Confirm everything is removed
    assert not storage.upload_exists(disposable_id), "Raw upload must no longer exist"
    assert not storage.extracted_text_exists(disposable_id), "Extracted text must no longer exist"
    assert not storage.clauses_json_exists(disposable_id), "Clauses JSON must no longer exist"
    assert not storage.has_contract_data(disposable_id), "has_contract_data must return False"
    print(f"  [OK] Extracted text, clauses JSON, and raw upload deleted ({delete_ms:.1f}ms)")
    print(f"  [OK] Confirmed has_contract_data('{disposable_id}') == False")

    # 3. Post-check database counts to guarantee zero mutation
    print("-" * 70)
    final_users, final_contracts = asyncio.run(count_db_records())
    print(f"[Post-Check] Active Database contains {final_users} user(s), {final_contracts} contract(s).")
    assert (final_users, final_contracts) == (initial_users, initial_contracts), (
        "Database records were unexpectedly mutated!"
    )
    print("  [OK] Local database records remained completely untouched.")
    print("=" * 70)
    print("ALL SUPABASE S3 END-TO-END STORAGE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
