#!/usr/bin/env python3
"""Upload existing local tender documents to Cloudflare R2."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.models.tender_document import TenderDocument
from app.services.document_storage import get_document_storage, is_r2_configured, uses_r2_storage


def migrate_documents(delete_local: bool = False, limit: int | None = None) -> dict[str, int]:
    if not uses_r2_storage():
        raise RuntimeError(
            "R2 is not configured. Set DOCUMENT_STORAGE_BACKEND=r2 and R2_* env vars."
        )

    storage = get_document_storage()
    db = SessionLocal()
    uploaded = 0
    skipped = 0
    missing = 0

    try:
        query = db.query(TenderDocument).order_by(TenderDocument.created_at.asc())
        if limit:
            query = query.limit(limit)
        documents = query.all()

        for document in documents:
            key = document.file_path
            local_file = storage.local_path(key)

            if local_file.is_file():
                if storage.upload_local_copy(key):
                    uploaded += 1
                    if delete_local:
                        local_file.unlink(missing_ok=True)
                else:
                    missing += 1
                continue

            if storage.exists(key):
                skipped += 1
                continue

            missing += 1
    finally:
        db.close()

    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "missing_local": missing,
        "r2_configured": int(is_r2_configured()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local tender documents to Cloudflare R2")
    parser.add_argument("--delete-local", action="store_true", help="Delete local file after upload")
    parser.add_argument("--limit", type=int, default=None, help="Max documents to process")
    args = parser.parse_args()

    stats = migrate_documents(delete_local=args.delete_local, limit=args.limit)
    print(stats)


if __name__ == "__main__":
    main()
