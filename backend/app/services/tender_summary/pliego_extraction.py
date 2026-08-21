"""Regex-based extraction from pliego PDF text."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

_SPANISH_CARDINAL = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "noventa": 90,
    "cien": 100,
    "ciento": 100,
}

_PLAZO_REGION_MARKERS = (
    r"presupuesto\s+oficial[^.\n]{0,60}plazo\s+y\s+ubicaci[oó]n",
    r"plazo\s+y\s+ubicaci[oó]n",
    r"plazo\s+del\s+contrato",
    r"1\.1\s+objeto[^.\n]{0,60}plazo",
)

_PAYMENT_REGION_MARKERS = (
    r"forma de pago",
    r"modalidad de pago",
    r"acuerdos comerciales",
    r"cap[ií]tulo\s+vi\b",
)

_KNOWN_PAYMENT_TYPES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"precios\s+unitarios", re.IGNORECASE), "Precios unitarios"),
    (re.compile(r"suma\s+alzada", re.IGNORECASE), "Suma alzada"),
    (re.compile(r"pago\s+global", re.IGNORECASE), "Pago global"),
    (re.compile(r"administraci[oó]n\s+delegada", re.IGNORECASE), "Administración delegada"),
    (re.compile(r"pagos\s+parciales", re.IGNORECASE), "Pagos parciales"),
)


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


def _spanish_word_to_int(word: str) -> Optional[int]:
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    return _SPANISH_CARDINAL.get(cleaned)


def _plazo_search_regions(text: str) -> list[str]:
    regions: list[str] = []
    for marker in _PLAZO_REGION_MARKERS:
        match = re.search(marker, text, flags=re.IGNORECASE)
        if match:
            regions.append(text[match.start() : match.end() + 2500])
    regions.append(text)
    return regions


def _payment_search_regions(text: str) -> list[str]:
    regions: list[str] = []
    for marker in _PAYMENT_REGION_MARKERS:
        match = re.search(marker, text, flags=re.IGNORECASE)
        if match:
            regions.append(text[max(0, match.start() - 100) : match.end() + 1800])
    regions.append(text)
    return regions


def _clean_payment_snippet(value: str) -> Optional[str]:
    cleaned = re.sub(r"\s+", " ", value).strip().rstrip(".")
    if len(cleaned) < 3 or len(cleaned) > 160:
        return None
    if re.search(r"\.{4,}|riesgo asociado|manual colombia|lugar geografico", cleaned, re.IGNORECASE):
        return None
    cleaned = re.split(r"\.\s+el anexo|\.\s+cuando el presupuesto", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    cleaned = cleaned.strip().rstrip(".")
    for pattern, label in _KNOWN_PAYMENT_TYPES:
        if pattern.search(cleaned):
            return label
    if cleaned:
        return cleaned[0].upper() + cleaned[1:]
    return None


def _extract_execution_duration(text: str) -> Optional[str]:
    for region in _plazo_search_regions(text):
        duration = _extract_execution_duration_from_region(region)
        if duration:
            return duration
    return None


def _extract_execution_duration_from_region(region: str) -> Optional[str]:
    lowered = region.lower()

    word_combo = re.search(
        r"\b([a-záéíóúñ]+)\s+meses?\s+y\s+([a-záéíóúñ]+)\s+d[ií]as?\b",
        lowered,
        flags=re.IGNORECASE,
    )
    if word_combo:
        months = _spanish_word_to_int(word_combo.group(1))
        days = _spanish_word_to_int(word_combo.group(2))
        if months is not None and days is not None:
            return f"{months} meses y {days} días"

    digit_combo = re.search(
        r"(\d+)\s*meses?\s+y\s+(\d+)\s*d[ií]as?",
        lowered,
        flags=re.IGNORECASE,
    )
    if digit_combo:
        return f"{digit_combo.group(1)} meses y {digit_combo.group(2)} días"

    paren_months = re.search(
        r"(?:\b[a-záéíóúñ]+\s+)?\(\s*(\d+)\s*\)\s*meses?",
        lowered,
        flags=re.IGNORECASE,
    )
    if paren_months:
        return f"{paren_months.group(1)} meses"

    months_match = re.search(r"(\d+)\s*meses?", lowered, flags=re.IGNORECASE)
    if months_match:
        return f"{months_match.group(1)} meses"

    days_match = re.search(
        r"(\d+)\s*d[ií]as?(?:\s+calendario|\s+corrientes)?",
        lowered,
        flags=re.IGNORECASE,
    )
    if days_match:
        return f"{days_match.group(1)} días"

    deadline_match = re.search(
        r"hasta\s+(?:el\s+)?(\d{1,2})\s+de\s+"
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
        r"\s+de\s+(\d{4})",
        lowered,
        flags=re.IGNORECASE,
    )
    if deadline_match:
        day, month, year = deadline_match.groups()
        return f"Hasta {day} de {month.title()} de {year}"

    generic_match = re.search(
        r"(?:plazo|duraci[oó]n|termino|t[eé]rmino)"
        r"(?:\s+de\s+(?:ejecuci[oó]n|contrato|obra))?"
        r"[^.\n]{0,120}?"
        r"(\d+)\s*(d[ií]as|meses|a[nñ]os)",
        lowered,
        flags=re.IGNORECASE,
    )
    if generic_match:
        return f"{generic_match.group(1)} {generic_match.group(2)}"

    return None


def _extract_payment_method(text: str) -> Optional[str]:
    explicit_patterns = (
        r"forma de pago(?:\s+del\s+contrato)?\s+es\s+(?:por\s+)?([^.\n]{3,160})",
        r"forma de pago(?:\s+del\s+contrato)?[^.\n]{0,80}ser[aá]\s+por\s+([^.\n]{3,160})",
        r"modalidad de pago\s+(?:es\s+|ser[aá]\s+|seleccionada[^.\n]{0,40}?)?([^.\n]{3,160})",
        r"(?:forma de pago|modalidad de pago)[:\s-]+([^.\n]{10,220})",
    )

    for region in _payment_search_regions(text):
        for pattern in explicit_patterns:
            match = re.search(pattern, region, flags=re.IGNORECASE)
            if not match:
                continue
            cleaned = _clean_payment_snippet(match.group(1))
            if cleaned:
                return cleaned

        forma_match = re.search(r"forma de pago.{0,220}", region, flags=re.IGNORECASE | re.DOTALL)
        if forma_match:
            chunk = forma_match.group(0)
            for pattern, label in _KNOWN_PAYMENT_TYPES:
                if pattern.search(chunk):
                    return label

    return None


def _extract_advance_payment(text: str) -> Optional[float]:
    patterns = (
        r"(?:el\s+)?anticipo(?:\s+ser[aá]|\s+equivaldr[aá]|[^.\n]{0,30}?del)[^.\n]{0,80}?(\d{1,2}(?:[.,]\d+)?)\s*(?:%|por ciento)",
        r"(\d{1,2}(?:[.,]\d+)?)\s*(?:%|por ciento)[^.\n]{0,60}?(?:del\s+)?(?:valor\s+del\s+)?anticipo",
        r"anticipo[^.\n]{0,120}?(\d{1,2}(?:[.,]\d+)?)\s*(?:%|por ciento)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        snippet = match.group(0).lower()
        if re.search(r"\bx\s*\d", snippet):
            continue
        return float(match.group(1).replace(",", "."))
    return None


def extract_from_pliego_text(text: str) -> PliegoExtraction:
    normalized = _normalize(text)
    lowered = normalized.lower()
    result = PliegoExtraction()

    result.execution_duration = _extract_execution_duration(normalized)

    advance = _extract_advance_payment(lowered)
    if advance is not None:
        result.advance_payment_percentage = advance

    result.payment_method = _extract_payment_method(normalized)

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
