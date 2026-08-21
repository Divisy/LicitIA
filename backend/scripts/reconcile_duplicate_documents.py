#!/usr/bin/env python3
"""Remove duplicate tender_documents rows and unused blobs (SECOP catalog duplicates)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import (
    reconcile_duplicate_documents,
    summarize_document_storage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and optionally remove duplicate tender_documents by filename"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Delete duplicate rows and unused blobs from storage",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary_before = summarize_document_storage(db)
        stats = reconcile_duplicate_documents(db, fix=args.fix)
        result = {"summary_before": summary_before, "duplicate_cleanup": stats}
        if args.fix:
            result["summary_after"] = summarize_document_storage(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
