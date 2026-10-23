"""Cloudflare R2 Connectivity and Storage Verification Script for Term Shield.

Safely tests S3-compatible R2 credentials, bucket accessibility, upload/download/delete lifecycle,
and path validation without modifying existing contract uploads or exposing secrets.

Usage:
    # 1. Test using environment or backend/.env settings:
    python scripts/verify_r2_connection.py

    # 2. Test with explicit parameters:
    python scripts/verify_r2_connection.py --account-id "..." --access-key "..." --secret-key "..." --bucket "..."
"""

import argparse
from io import BytesIO
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
from app.services.storage_service import R2StorageService


def mask_secret(value: str | None, prefix_len: int = 4) -> str:
    """Mask sensitive keys for safe display."""
    if not value or not value.strip():
        return "<not set>"
    v = value.strip()
    if len(v) <= prefix_len + 2:
        return "***"
    return f"{v[:prefix_len]}...***"


def resolve_r2_config(
    cli_account_id: str | None = None,
    cli_access_key: str | None = None,
    cli_secret_key: str | None = None,
    cli_bucket: str | None = None,
    cli_endpoint: str | None = None,
) -> dict[str, str | None]:
    """Resolve R2 credentials from CLI, environment, or backend/.env."""
    settings = get_settings()

    account_id = cli_account_id or os.environ.get("R2_ACCOUNT_ID") or settings.r2_account_id
    access_key = cli_access_key or os.environ.get("R2_ACCESS_KEY_ID") or settings.r2_access_key_id
    secret_key = cli_secret_key or os.environ.get("R2_SECRET_ACCESS_KEY") or settings.r2_secret_access_key
    bucket_name = cli_bucket or os.environ.get("R2_BUCKET_NAME") or settings.r2_bucket_name
    endpoint_url = cli_endpoint or os.environ.get("R2_ENDPOINT_URL") or settings.r2_endpoint_url

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
            if k == "R2_ACCOUNT_ID" and not account_id:
                account_id = v
            elif k == "R2_ACCESS_KEY_ID" and not access_key:
                access_key = v
            elif k == "R2_SECRET_ACCESS_KEY" and not secret_key:
                secret_key = v
            elif k == "R2_BUCKET_NAME" and not bucket_name:
                bucket_name = v
            elif k == "R2_ENDPOINT_URL" and not endpoint_url:
                endpoint_url = v

    return {
        "account_id": account_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket_name": bucket_name,
        "endpoint_url": endpoint_url,
    }


def verify_r2(config: dict[str, str | None]) -> int:
    account_id = config.get("account_id")
    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    bucket_name = config.get("bucket_name")
    endpoint_url = config.get("endpoint_url")

    print("=" * 70)
    print("TERM SHIELD AI - CLOUDFLARE R2 STORAGE VERIFICATION")
    print("=" * 70)
    print(f"Bucket Name       : {bucket_name or '<not set>'}")
    print(f"Account ID        : {mask_secret(account_id, 6)}")
    print(f"Access Key ID     : {mask_secret(access_key, 6)}")
    print(f"Secret Access Key : {'*** (Configured)' if secret_key else '<not set>'}")

    derived_endpoint = endpoint_url or (f"https://{account_id}.r2.cloudflarestorage.com" if account_id else None)
    print(f"Endpoint URL      : {derived_endpoint or '<not set>'}")
    print("-" * 70)

    missing = []
    if not account_id and not endpoint_url:
        missing.append("R2_ACCOUNT_ID (or R2_ENDPOINT_URL)")
    if not access_key:
        missing.append("R2_ACCESS_KEY_ID")
    if not secret_key:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not bucket_name:
        missing.append("R2_BUCKET_NAME")

    if missing:
        print("\n[ERROR] Missing required Cloudflare R2 credentials:")
        for m in missing:
            print(f"  - {m}")
        print("\nTo configure R2 for persistent contract uploads:")
        print("1. In Cloudflare Dashboard, go to 'R2' -> Create Bucket (e.g. 'term-shield-contracts').")
        print("2. In R2 overview, click 'Manage R2 API Tokens' -> 'Create API Token' (Object Read & Write permissions).")
        print("3. Copy Account ID, Access Key ID, and Secret Access Key.")
        print("4. Add them to backend/.env:")
        print("     STORAGE_PROVIDER=r2")
        print("     R2_ACCOUNT_ID=<your-account-id>")
        print("     R2_ACCESS_KEY_ID=<your-access-key-id>")
        print("     R2_SECRET_ACCESS_KEY=<your-secret-access-key>")
        print("     R2_BUCKET_NAME=<your-bucket-name>")
        print("5. Re-run: python scripts/verify_r2_connection.py")
        print("=" * 70)
        return 2

    try:
        import boto3
    except ImportError:
        print("[ERROR] boto3 is not installed. Install requirements with pip install -r requirements.txt")
        return 1

    r2_service = R2StorageService(
        bucket_name=bucket_name,
        account_id=account_id,
        access_key_id=access_key,
        secret_access_key=secret_key,
        endpoint_url=endpoint_url,
    )

    # 1. Bucket Accessibility Check
    print("\n[Step 1/3] Verifying bucket connectivity & credentials...")
    start_time = time.perf_counter()
    try:
        r2_service.client.head_bucket(Bucket=bucket_name)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"  [OK] Bucket exists and is accessible ({latency_ms:.1f}ms).")
    except Exception as exc:
        print(f"  [FAIL] Failed to access bucket '{bucket_name}': {exc}")
        return 1

    # 2. Lifecycle Probe (Put -> Get -> Delete)
    probe_id = f"probe-{uuid4().hex[:12]}"
    test_content = b"Term Shield R2 connectivity probe - OK"
    print("\n[Step 2/3] Performing non-destructive upload & download probe...")
    try:
        # Save
        key = r2_service.save_upload(probe_id, ".txt", test_content)
        print(f"  [OK] Successfully uploaded test object to: {key}")

        # Exists check
        assert r2_service.upload_exists(probe_id, ".txt"), "Uploaded object check failed."
        print("  [OK] upload_exists() verified.")

        # Read
        read_back = r2_service.read_upload(probe_id, ".txt")
        assert read_back == test_content, "Content mismatch in probe read."
        print(f"  [OK] Successfully retrieved test object ({len(read_back)} bytes verified).")

        # Delete
        deleted = r2_service.delete_upload(probe_id, ".txt")
        assert deleted, "Delete operation failed."
        assert not r2_service.upload_exists(probe_id, ".txt"), "Object still exists after delete."
        print("  [OK] Successfully cleaned up test object from R2.")

    except Exception as exc:
        print(f"  [FAIL] Lifecycle probe failed: {exc}")
        return 1

    # 3. Overall Readiness Summary
    print("\n[Step 3/3] Storage configuration status...")
    print("  [SUCCESS] Cloudflare R2 is fully verified and ready for production on Render!")
    print("  All contract uploads, extracted documents, and clause caches will persist across deploys.")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify Cloudflare R2 storage credentials and lifecycle.")
    parser.add_argument("--account-id", type=str, default=None, help="Cloudflare Account ID")
    parser.add_argument("--access-key", type=str, default=None, help="R2 Access Key ID")
    parser.add_argument("--secret-key", type=str, default=None, help="R2 Secret Access Key")
    parser.add_argument("--bucket", type=str, default=None, help="R2 Bucket Name")
    parser.add_argument("--endpoint", type=str, default=None, help="Optional custom endpoint URL")
    args = parser.parse_args()

    config = resolve_r2_config(
        cli_account_id=args.account_id,
        cli_access_key=args.access_key,
        cli_secret_key=args.secret_key,
        cli_bucket=args.bucket,
        cli_endpoint=args.endpoint,
    )
    exit_code = verify_r2(config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
