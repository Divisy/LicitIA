#!/usr/bin/env python3
"""Load Otto Harry and Beatriz experience into BEC."""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.db import SessionLocal
from app.services.bec_experience_import import (
    import_bec_experience_rows,
    parse_bec_experience_csv,
)

DEFAULT_CSV = (
    Path(__file__).resolve().parents[1] / "data" / "bec_experiencia_socios.csv"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa la experiencia de Otto Harry y Beatriz como experiencia de BEC."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    rows, errors = parse_bec_experience_csv(args.csv)
    for error in errors:
        print(f"aviso: {error}")
    if not rows:
        raise SystemExit("No se leyeron contratos.")

    db = SessionLocal()
    try:
        created, updated = import_bec_experience_rows(db, rows)
    finally:
        db.close()

    by_partner: dict[str, int] = {}
    for row in rows:
        by_partner[row.partner_name] = by_partner.get(row.partner_name, 0) + 1
    print(f"Contratos leídos: {len(rows)}")
    for name, count in sorted(by_partner.items()):
        print(f"  {name}: {count}")
    print(f"Nuevos: {created}")
    print(f"Actualizados: {updated}")


if __name__ == "__main__":
    main()
