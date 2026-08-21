#!/usr/bin/env python3
"""Batch extract tender summaries (US 1.4)."""
import argparse

from app.core.db import SessionLocal
from app.models.tender import Tender
from app.services.tender_summary.service import build_tender_summary, persist_tender_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract US 1.4 tender summaries")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenders = (
            db.query(Tender)
            .order_by(Tender.updated_at.desc())
            .offset(args.offset)
            .limit(args.limit)
            .all()
        )
        for tender in tenders:
            payload = build_tender_summary(tender)
            persist_tender_summary(db, tender, payload)
            print(f"Extracted summary for {tender.external_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
