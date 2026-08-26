#!/usr/bin/env python3
"""Report Cloudflare R2 bucket usage for tender documents."""
from __future__ import annotations

import sys

from app.config import settings
from app.services.document_storage import is_r2_configured, uses_r2_storage


def main() -> int:
    if not uses_r2_storage():
        print("R2 storage is not configured (DOCUMENT_STORAGE_BACKEND != r2).")
        return 1

    if not is_r2_configured():
        print("R2 credentials are incomplete.")
        return 1

    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name=settings.R2_REGION,
        config=Config(signature_version="s3v4"),
    )

    prefix = (settings.R2_PREFIX or "").strip("/")
    list_prefix = f"{prefix}/" if prefix else ""

    total_bytes = 0
    object_count = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME, Prefix=list_prefix):
        for obj in page.get("Contents", []):
            object_count += 1
            total_bytes += int(obj.get("Size", 0))

    gib = total_bytes / (1024**3)
    print(f"bucket={settings.R2_BUCKET_NAME}")
    print(f"prefix={prefix or '(root)'}")
    print(f"objects={object_count}")
    print(f"bytes={total_bytes}")
    print(f"gib={gib:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
