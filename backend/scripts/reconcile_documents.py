#!/usr/bin/env python3
"""Reconcile tender_documents metadata against R2/local storage (US 1.2.2)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import reconcile_orphan_documents, summarize_document_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and optionally fix orphan tender_documents rows (metadata without blob)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Delete orphan metadata and reset extraction attempt for affected tenders",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = summarize_document_storage(db)
        stats = reconcile_orphan_documents(db, fix=args.fix)
        print({"summary": summary, "reconcile": stats})
    finally:
        db.close()


if __name__ == "__main__":
    main()
