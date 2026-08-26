#!/usr/bin/env python3
"""Remove tenders that are no longer Publicado with apertura Abierto."""
from __future__ import annotations

import sys

from app.core.db import SessionLocal
from app.config import settings
from app.services.tender_lifecycle import purge_inactive_tenders


def main() -> int:
    db = SessionLocal()
    try:
        total_purged = 0
        while True:
            stats = purge_inactive_tenders(
                db,
                batch_size=settings.INACTIVE_TENDER_PURGE_BATCH_SIZE,
            )
            total_purged += stats["purged"]
            if stats["purged"] == 0:
                break
        print(f"Purged {total_purged} inactive tenders")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
