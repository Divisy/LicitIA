#!/usr/bin/env python3
"""Recover missing presupuesto documents via SECOP content classification (US 1.2.5 MVP)."""
from __future__ import annotations

import argparse

from app.core.db import SessionLocal
from app.services.document_backfill import run_presupuesto_content_extraction, summarize_document_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify SECOP OTRO PDF/XLSX files by content to recover presupuesto"
    )
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--pause-seconds", type=float, default=2.0)
    parser.add_argument("--external-id", type=str, default=None)
    parser.add_argument("--reference", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary_before = summarize_document_storage(db)
        stats = run_presupuesto_content_extraction(
            db,
            max_batches=args.max_batches,
            batch_size=args.batch_size,
            pause_seconds=args.pause_seconds,
            dry_run=args.dry_run,
            external_id=args.external_id,
            reference=args.reference,
        )
        result = {"summary_before": summary_before, "presupuesto_content": stats}
        if not args.dry_run:
            result["summary_after"] = summarize_document_storage(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
