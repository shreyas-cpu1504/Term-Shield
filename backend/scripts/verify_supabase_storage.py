"""Supabase S3 Storage Connectivity Verification Script for Term Shield.

Safely tests S3-compatible Supabase storage credentials, bucket accessibility,
path-style addressing, and upload/download/delete lifecycle without modifying existing contracts.

Usage:
    # 1. Test using environment or backend/.env settings:
    python scripts/verify_supabase_storage.py

    # 2. Test with explicit parameters:
    python scripts/verify_supabase_storage.py --endpoint "..." --access-key "..." --secret-key "..." --bucket "term-shield-contracts"
"""

import argparse
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings
from app.services.storage_service import SupabaseStorageService


def mask_secret(value: str | None, prefix_len: int = 4) -> str:
    """Mask sensitive keys for safe display."""
    if not value or not value.strip():
        return "<not set>"
    v = value.strip()
    if len(v) <= prefix_len + 2:
        return "***"
    return f"{v[:prefix_len]}...***"


def resolve_supabase_config(
    cli_endpoint: str | None = None,
    cli_access_key: str | None = None,
    cli_secret_key: str | None = None,
    cli_bucket: str | None = None,
    cli_region: str | None = None,
) -> dict[str, str | None]:
    """Resolve Supabase S3 credentials from CLI, environment, or backend/.env."""
    settings = get_settings()

    endpoint = cli_endpoint or os.environ.get("SUPABASE_S3_ENDPOINT") or settings.supabase_s3_endpoint
    access_key = cli_access_key or os.environ.get("SUPABASE_S3_ACCESS_KEY_ID") or settings.supabase_s3_access_key_id
    secret_key = cli_secret_key or os.environ.get("SUPABASE_S3_SECRET_ACCESS_KEY") or settings.supabase_s3_secret_access_key
    bucket_name = cli_bucket or os.environ.get("SUPABASE_S3_BUCKET") or settings.supabase_s3_bucket or "term-shield-contracts"
    region_name = cli_region or os.environ.get("SUPABASE_S3_REGION") or settings.supabase_s3_region or "ap-northeast-2"

    # Fallback to check backend/.env directly if pydantic didn't pick up dynamic values
    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().lstrip("\ufeff")
            v = v.strip()
            if k == "SUPABASE_S3_ENDPOINT" and not endpoint:
                endpoint = v
            elif k == "SUPABASE_S3_ACCESS_KEY_ID" and not access_key:
                access_key = v
            elif k == "SUPABASE_S3_SECRET_ACCESS_KEY" and not secret_key:
                secret_key = v
            elif k == "SUPABASE_S3_BUCKET" and not bucket_name:
                bucket_name = v
            elif k == "SUPABASE_S3_REGION" and not region_name:
                region_name = v

    return {
        "endpoint": endpoint,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket_name": bucket_name,
        "region_name": region_name,
    }


def verify_supabase(config: dict[str, str | None]) -> int:
    endpoint = config.get("endpoint")
    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    bucket_name = config.get("bucket_name") or "term-shield-contracts"
    region_name = config.get("region_name") or "ap-northeast-2"

    print("=" * 70)
    print("TERM SHIELD AI - SUPABASE S3 STORAGE VERIFICATION")
    print("=" * 70)
    print(f"Bucket Name       : {bucket_name}")
    print(f"Region            : {region_name}")
    print(f"Endpoint URL      : {endpoint or '<not set>'}")
    print(f"Access Key ID     : {mask_secret(access_key, 6)}")
    print(f"Secret Access Key : {'*** (Configured)' if secret_key else '<not set>'}")
    print(f"Addressing Style  : path (required for Supabase S3 API)")
    print("-" * 70)

    missing = []
    if not endpoint:
        missing.append("SUPABASE_S3_ENDPOINT")
    if not access_key:
        missing.append("SUPABASE_S3_ACCESS_KEY_ID")
    if not secret_key:
        missing.append("SUPABASE_S3_SECRET_ACCESS_KEY")

    if missing:
        print("\n[ERROR] Missing required Supabase S3 credentials:")
        for m in missing:
            print(f"  - {m}")
        print("\nTo configure Supabase Storage for persistent uploads:")
        print("1. In Supabase Dashboard -> Storage -> Create bucket: 'term-shield-contracts' (Private).")
        print("2. In Project Settings -> Storage -> S3 Access Keys -> Generate S3 Access Key.")
        print("3. Copy the Endpoint URL, Access Key ID, and Secret Access Key.")
        print("4. Add them to backend/.env (leave DATABASE_URL on SQLite for local dev):")
        print("     STORAGE_PROVIDER=supabase")
        print("     SUPABASE_S3_ENDPOINT=https://<project-ref>.storage.supabase.co/storage/v1/s3")
        print("     SUPABASE_S3_ACCESS_KEY_ID=<your-access-key-id>")
        print("     SUPABASE_S3_SECRET_ACCESS_KEY=<your-secret-access-key>")
        print("     SUPABASE_S3_BUCKET=term-shield-contracts")
        print("5. Re-run: python scripts/verify_supabase_storage.py")
        print("=" * 70)
        return 2

    try:
        import boto3
    except ImportError:
        print("[ERROR] boto3 is not installed. Install requirements with: pip install -r requirements.txt")
        return 1

    svc = SupabaseStorageService(
        endpoint_url=endpoint,
        access_key_id=access_key,
        secret_access_key=secret_key,
        bucket_name=bucket_name,
        region_name=region_name,
    )

    # 1. Bucket Accessibility Check
    print("\n[Step 1/3] Verifying bucket connectivity & credentials...")
    start_time = time.perf_counter()
    try:
        svc.client.head_bucket(Bucket=bucket_name)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"  [OK] Bucket '{bucket_name}' exists and is accessible ({latency_ms:.1f}ms).")
    except Exception as exc:
        print(f"  [FAIL] Failed to access bucket '{bucket_name}': {exc}")
        print("\nTroubleshooting tips for Supabase S3:")
        print("  - Confirm the bucket 'term-shield-contracts' exists in Supabase Storage.")
        print("  - Verify S3 Access Keys were generated under Project Settings -> Storage -> S3 Credentials.")
        print("  - Confirm the endpoint format: https://<project-ref>.storage.supabase.co/storage/v1/s3")
        return 1

    # 2. Lifecycle Probe (Put -> Get -> Delete)
    probe_id = f"probe-{uuid4().hex[:12]}"
    test_content = b"Term Shield Supabase S3 connectivity probe - OK"
    print("\n[Step 2/3] Performing non-destructive upload & download probe...")
    try:
        # Save
        key = svc.save_upload(probe_id, ".txt", test_content)
        print(f"  [OK] Successfully uploaded test object to: {key}")

        # Exists check
        assert svc.upload_exists(probe_id, ".txt"), "Uploaded object check failed."
        print("  [OK] upload_exists() verified.")

        # Read
        read_back = svc.read_upload(probe_id, ".txt")
        assert read_back == test_content, "Content mismatch in probe read."
        print(f"  [OK] Successfully retrieved test object ({len(read_back)} bytes verified).")

        # Delete
        deleted = svc.delete_upload(probe_id, ".txt")
        assert deleted, "Delete operation failed."
        assert not svc.upload_exists(probe_id, ".txt"), "Object still exists after delete."
        print("  [OK] Successfully cleaned up test object from Supabase.")

    except Exception as exc:
        print(f"  [FAIL] Lifecycle probe failed: {exc}")
        return 1

    # 3. Overall Readiness Summary
    print("\n[Step 3/3] Storage configuration status...")
    print("  [SUCCESS] Supabase Storage S3-compatible API is fully verified and ready for production on Render!")
    print("  All contract uploads, extracted documents, and clause caches will persist across deploys.")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify Supabase S3 storage credentials and lifecycle.")
    parser.add_argument("--endpoint", type=str, default=None, help="Supabase S3 endpoint URL")
    parser.add_argument("--access-key", type=str, default=None, help="Supabase S3 Access Key ID")
    parser.add_argument("--secret-key", type=str, default=None, help="Supabase S3 Secret Access Key")
    parser.add_argument("--bucket", type=str, default=None, help="Supabase Bucket Name")
    parser.add_argument("--region", type=str, default=None, help="Supabase S3 Region")
    args = parser.parse_args()

    config = resolve_supabase_config(
        cli_endpoint=args.endpoint,
        cli_access_key=args.access_key,
        cli_secret_key=args.secret_key,
        cli_bucket=args.bucket,
        cli_region=args.region,
    )
    exit_code = verify_supabase(config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
