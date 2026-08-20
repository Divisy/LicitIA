#!/usr/bin/env python3
"""Validate US 1.2.3 acceptance criteria against production API."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read())


def validate(api_base: str) -> dict[str, list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []

    tenders_resp = _get(f"{api_base}/tenders?limit=500")
    total = tenders_resp["total"]
    items = tenders_resp["items"]

    with_docs = 0
    pending = 0
    processed_no_docs = 0
    doc_rows = 0

    for tender in items:
        docs = _get(f"{api_base}/tenders/{tender['id']}/documents")
        count = docs["total"]
        doc_rows += count
        if count > 0:
            with_docs += 1
        elif tender.get("documents_extraction_attempted_at"):
            processed_no_docs += 1
        else:
            pending += 1

    if total >= 215:
        passed.append(f"total_tenders={total}")
    else:
        warnings.append(f"total_tenders={total} (expected ~215)")

    if with_docs > 209:
        passed.append(f"coverage improved: tenders_with_documents={with_docs} (>209 baseline)")
    else:
        failed.append(f"coverage not above baseline: tenders_with_documents={with_docs}")

    if pending == 0:
        passed.append("pending_extraction=0")
    else:
        failed.append(f"pending_extraction={pending} (expected 0)")

    samples = [
        ("SPL-LP-004-2026", lambda types: "pliego_condiciones" in types, "Corpoamazonia pliego"),
        ("LP-002-2026", lambda types: len(types) >= 1, "Regression Sincelejo"),
        ("LP-013-2026", lambda types: len(types) >= 1, "Regression Barranquilla"),
    ]

    for ref_part, check, label in samples:
        tender = next((t for t in items if ref_part in (t.get("reference") or "")), None)
        if not tender:
            failed.append(f"{label}: tender not found ({ref_part})")
            continue
        detail = _get(f"{api_base}/tenders/{tender['id']}")
        docs = _get(f"{api_base}/tenders/{tender['id']}/documents")
        types = [d["document_type"] for d in docs["items"]]
        if not detail.get("documents_extraction_attempted_at"):
            failed.append(f"{label}: missing documents_extraction_attempted_at in API")
        if not check(types):
            failed.append(f"{label}: document types check failed ({types})")
            continue
        if docs["items"]:
            doc = docs["items"][0]
            url = f"{api_base}/tenders/{tender['id']}/documents/{doc['id']}/download"
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    body = response.read(4)
                if not body:
                    failed.append(f"{label}: empty download")
                else:
                    passed.append(f"{label}: download OK ({len(docs['items'])} docs)")
            except urllib.error.HTTPError as exc:
                failed.append(f"{label}: download HTTP {exc.code}")

    palmira = next((t for t in items if "CVC LP 008" in (t.get("reference") or "")), None)
    if palmira:
        docs = _get(f"{api_base}/tenders/{palmira['id']}/documents")
        types = [d["document_type"] for d in docs["items"]]
        if "presupuesto" not in types and palmira.get("documents_extraction_attempted_at"):
            passed.append("Palmira: no presupuesto in SECOP, tender processed (expected)")
        else:
            warnings.append(f"Palmira unexpected state: types={types}")

    return {
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "metrics": {
            "total_tenders": total,
            "tenders_with_documents": with_docs,
            "pending_extraction": pending,
            "processed_without_docs": processed_no_docs,
            "document_rows": doc_rows,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate US 1.2.3 acceptance criteria")
    parser.add_argument(
        "--api-base",
        default=os.environ.get(
            "LICITIA_API_BASE",
            "https://vigilant-joy-production.up.railway.app/api/v1",
        ),
    )
    args = parser.parse_args()

    result = validate(args.api_base.rstrip("/"))
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
