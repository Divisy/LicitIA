#!/usr/bin/env python3
"""Reset document extraction attempts for tenders without archived docs (US 1.2.3)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import reset_document_extraction_attempts, summarize_document_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reset documents_extraction_attempted_at for tenders with no tender_documents rows"
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Report counts without updating")
    parser.add_argument("--external-id", type=str, default=None, help="Filter by SECOP external_id")
    parser.add_argument("--reference", type=str, default=None, help="Filter by tender reference")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary_before = summarize_document_storage(db)
        stats = reset_document_extraction_attempts(
            db,
            dry_run=args.dry_run,
            external_id=args.external_id,
            reference=args.reference,
        )
        result = {"summary_before": summary_before, "reset": stats}
        if not args.dry_run:
            result["summary_after"] = summarize_document_storage(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
