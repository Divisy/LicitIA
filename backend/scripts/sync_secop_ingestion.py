#!/usr/bin/env python3
"""Manual SECOP ingestion catch-up (new tenders + state refresh)."""
from __future__ import annotations

import argparse
import sys

from app.services.tender_ingestion import fetch_and_store_new_tenders


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SECOP ingestion manually (same job as the scheduler)."
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Override SECOP_FETCH_LOOKBACK_DAYS for this run (e.g. 30 for catch-up)",
    )
    args = parser.parse_args()
    fetch_and_store_new_tenders(lookback_days=args.lookback_days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
