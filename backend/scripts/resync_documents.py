#!/usr/bin/env python3
"""Incremental SECOP document resync for already-processed tenders (US 1.2.3+)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import run_document_resync, summarize_document_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Re-sync SECOP key documents for tenders already marked as processed. "
            "Adds missing documents after classifier improvements without duplicating rows."
        )
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Tenders per batch (default: DOCUMENT_EXTRACTION_BATCH_SIZE)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum number of batches to run (default: until snapshot complete)",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Pause between batches to reduce SECOP pressure",
    )
    parser.add_argument(
        "--only-without-pliego",
        action="store_true",
        help="Limit resync to processed tenders missing pliego_condiciones",
    )
    parser.add_argument("--external-id", type=str, default=None, help="Filter by SECOP external_id")
    parser.add_argument("--reference", type=str, default=None, help="Filter by tender reference")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print eligible counts without processing",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary_before = summarize_document_storage(db)
        stats = run_document_resync(
            db,
            max_batches=args.max_batches,
            batch_size=args.batch_size,
            pause_seconds=args.pause_seconds,
            dry_run=args.dry_run,
            only_without_pliego=args.only_without_pliego,
            external_id=args.external_id,
            reference=args.reference,
        )
        result = {"summary_before": summary_before, "resync": stats}
        if not args.dry_run:
            result["summary_after"] = summarize_document_storage(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
