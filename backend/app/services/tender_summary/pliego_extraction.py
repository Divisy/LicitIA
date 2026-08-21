"""Regex-based extraction from pliego PDF text."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass
class PliegoExtraction:
    execution_duration: Optional[str] = None
    advance_payment_percentage: Optional[float] = None
    payment_method: Optional[str] = None
    price_adjustment: Optional[str] = None
    lots_groups: Optional[str] = None
    budget_contract_relation: Optional[str] = None
    award_date: Optional[str] = None


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip()


def extract_from_pliego_text(text: str) -> PliegoExtraction:
    normalized = _normalize(text)
    lowered = normalized.lower()
    result = PliegoExtraction()

    duration_match = re.search(
        r"(?:plazo|duraci[oó]n|termino|t[eé]rmino)(?:\s+de\s+(?:ejecuci[oó]n|contrato|obra))?[^.\n]{0,80}?"
        r"(\d+)\s*(d[ií]as|meses|a[nñ]os)",
        lowered,
        flags=re.IGNORECASE,
    )
    if duration_match:
        result.execution_duration = f"{duration_match.group(1)} {duration_match.group(2)}"

    advance_match = re.search(
        r"anticipo[^.\n]{0,120}?(\d{1,2}(?:[.,]\d+)?)\s*(?:%|por ciento)",
        lowered,
        flags=re.IGNORECASE,
    )
    if advance_match:
        result.advance_payment_percentage = float(advance_match.group(1).replace(",", "."))

    payment_match = re.search(
        r"(forma de pago|pagos parciales|modalidad de pago)[:\s-]+([^.\n]{10,220})",
        normalized,
        flags=re.IGNORECASE,
    )
    if payment_match:
        result.payment_method = payment_match.group(2).strip()

    if re.search(r"ajuste de precios|reajuste|formula polin[oó]mica", lowered):
        if re.search(r"no\s+habr[aá]|sin ajuste|no aplica", lowered):
            result.price_adjustment = "No"
        else:
            result.price_adjustment = "Sí"
    elif "ajuste" in lowered:
        result.price_adjustment = "Revisar pliego"

    if re.search(r"\blotes?\b|\bgrupos?\b|\bpaquetes?\b", lowered):
        result.lots_groups = "Sí"
    else:
        result.lots_groups = "No"

    if re.search(r"presupuesto oficial|formulario 1|propuesta econ[oó]mica", lowered):
        result.budget_contract_relation = "Debe ajustarse al presupuesto oficial / Formulario 1"

    award_match = re.search(
        r"fecha(?:\s+de)?\s+adjudicaci[oó]n[:\s-]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        normalized,
        flags=re.IGNORECASE,
    )
    if award_match:
        result.award_date = award_match.group(1)

    return result
