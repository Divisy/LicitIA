#!/usr/bin/env python3
"""Extract participation requirements for tenders (US 1.5 MVP)."""
from __future__ import annotations

import argparse
import json

from app.core.db import SessionLocal
from app.models.tender import Tender
from app.services.tender_requirements.service import (
    build_tender_requirements,
    persist_tender_requirements,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract tender participation requirements")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist results")
    parser.add_argument("--batch-size", type=int, default=25, help="Max tenders to process")
    parser.add_argument("--reference", type=str, help="Process a single tender by reference or external_id")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Tender).order_by(Tender.updated_at.desc())
        if args.reference:
            query = query.filter(
                (Tender.reference == args.reference) | (Tender.external_id == args.reference)
            )
        tenders = query.limit(args.batch_size).all()

        stats = {"processed": 0, "with_items": 0, "saved": 0}
        for tender in tenders:
            payload = build_tender_requirements(tender)
            item_count = sum(len(section.get("items", [])) for section in payload.get("sections", []))
            stats["processed"] += 1
            if item_count:
                stats["with_items"] += 1
            if not args.dry_run:
                persist_tender_requirements(db, tender, payload)
                stats["saved"] += 1
            print(
                f"{tender.external_id}: {item_count} items, "
                f"warnings={len(payload.get('warnings', []))}"
            )

        print(json.dumps(stats, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
