#!/usr/bin/env python3
"""Accelerated historical document backfill for pending tenders (US 1.2.2)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import run_backfill, summarize_document_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill SECOP key documents for tenders not yet attempted"
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
        help="Maximum number of batches to run (default: until queue empty)",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Pause between batches to reduce SECOP pressure",
    )
    parser.add_argument(
        "--no-reconcile",
        action="store_true",
        help="Skip orphan reconciliation before backfill",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pending counts without processing",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = run_backfill(
            db,
            max_batches=args.max_batches,
            batch_size=args.batch_size,
            pause_seconds=args.pause_seconds,
            reconcile_first=not args.no_reconcile,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            stats["summary_after"] = summarize_document_storage(db)
        print(stats)
    finally:
        db.close()


if __name__ == "__main__":
    main()
