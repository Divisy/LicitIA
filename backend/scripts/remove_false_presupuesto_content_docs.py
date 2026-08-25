#!/usr/bin/env python3
"""Remove presupuesto rows misclassified by content classification (US 1.2.5 cleanup)."""
from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.document_storage import get_document_storage

# False positives identified after first prod reproceso (2026-08-25).
FALSE_POSITIVE_FILES: tuple[tuple[str, str], ...] = (
    ("CO1.REQ.10808168", "4. Matriz 1-Experiencia INTERV. PUENTE ZONA INDUSTRIAL.xlsx"),
    ("CO1.REQ.10811671", "CERTIFICADO_PDA 2026_13739.pdf"),
    ("CO1.REQ.10837005", "Matriz 2 -Indicadores Financieros y Organizacionales Consultoria V2 12-12-2024.pdf"),
    ("CO1.REQ.10735893", "Autorizacion de vigencias futuras obra.pdf"),
)


def remove_false_positives(db: Session, *, dry_run: bool = True) -> dict[str, int]:
    storage = get_document_storage()
    stats = {"matched": 0, "deleted": 0, "errors": 0}

    for external_id, file_name in FALSE_POSITIVE_FILES:
        tender = db.query(Tender).filter(Tender.external_id == external_id).first()
        if not tender:
            continue

        document = (
            db.query(TenderDocument)
            .filter(
                TenderDocument.tender_id == tender.id,
                TenderDocument.document_type == "presupuesto",
                TenderDocument.file_name == file_name,
            )
            .first()
        )
        if not document:
            continue

        stats["matched"] += 1
        if dry_run:
            continue

        try:
            storage.delete_object(document.file_path)
            db.delete(document)
            stats["deleted"] += 1
        except Exception:
            stats["errors"] += 1

    if not dry_run:
        db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove known false-positive presupuesto documents")
    parser.add_argument("--apply", action="store_true", help="Delete rows and blobs (default is dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = remove_false_positives(db, dry_run=not args.apply)
        print({"dry_run": not args.apply, **stats})
    finally:
        db.close()


if __name__ == "__main__":
    main()
