"""Extract AIU percentage from presupuesto XLSX (Formulario 1)."""
from __future__ import annotations

import re
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService

logger = get_logger(__name__)


@dataclass
class PresupuestoExtraction:
    aiu_percentage: Optional[float] = None
    official_budget_total: Optional[float] = None
    budget_relation_note: Optional[str] = None


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def _parse_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = text.replace("$", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"[^\d.-]", "", cleaned)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_from_presupuesto_xlsx(
    document: TenderDocument,
    storage: DocumentStorageService,
) -> PresupuestoExtraction:
    result = PresupuestoExtraction()
    extension = (document.extension or "").lower()
    if extension not in {"xlsx", "xls", "xlsm"}:
        return result

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        local_path = storage.local_path(document.file_path)
        if local_path.is_file():
            workbook_path = local_path
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="licitia_xlsx_")
            workbook_path = Path(temp_dir.name) / Path(document.file_name).name
            with workbook_path.open("wb") as handle:
                for chunk in storage.iter_file_chunks(document.file_path):
                    handle.write(chunk)

        from openpyxl import load_workbook

        workbook = load_workbook(workbook_path, data_only=True, read_only=True)
        percentages: list[float] = []
        totals: list[float] = []

        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                cells = [cell for cell in row if cell is not None]
                if not cells:
                    continue
                labels = [_normalize(str(cell)) for cell in cells[:4] if isinstance(cell, str)]
                joined = " ".join(labels)

                if any(token in joined for token in ("administracion", "impuestos", "utilidad", "aiu")):
                    for cell in cells[1:6]:
                        number = _parse_number(cell)
                        if number is not None and 0 < number <= 100:
                            percentages.append(number)

                if "presupuesto oficial" in joined or "valor total" in joined or joined.startswith("total"):
                    for cell in reversed(cells):
                        number = _parse_number(cell)
                        if number is not None and number > 1000:
                            totals.append(number)
                            break

        workbook.close()

        if percentages:
            if len(percentages) >= 3:
                result.aiu_percentage = round(sum(percentages[:3]), 2)
            else:
                result.aiu_percentage = round(max(percentages), 2)

        if totals:
            result.official_budget_total = max(totals)

        if result.official_budget_total:
            result.budget_relation_note = "Presupuesto oficial identificado en Formulario 1"

        return result
    except Exception as exc:
        logger.warning("Failed to parse presupuesto XLSX %s: %s", document.file_name, exc)
        return result
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
