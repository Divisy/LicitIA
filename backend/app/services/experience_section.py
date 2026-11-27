"""Cut the experience chapter out of a pliego.

Tipo and non-tipo documents put the requirement, the notes, and the value
in different places. The chapter is whatever sits between the experience
heading and the next requirement (financial capacity, scoring, and so on).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from app.services.tender_requirements.regex_extraction import (
    _extract_contracts_for_experience,
    extract_experience_value_tiers,
    normalize_text,
)

EXPERIENCE_SECTION_VERSION = 2
_SECTION_MAX_CHARS = 14_000
_HEAD_CHARS = 6_500

_START_MARKERS = (
    "experiencia general",
    "exigencia minima de la experiencia",
    "exigencias minimas de la experiencia",
    "requisitos minimos de experiencia",
    "requisitos de experiencia son",
)

_END_MARKERS = (
    "capacidad financiera",
    "indicadores financieros",
    "solvencia economica",
    "capital de trabajo",
    "capacidad organizacional",
    "capacidad residual",
    "criterios de evaluacion",
    "criterios de calificacion",
    "factores de evaluacion",
)

_KEEP_IF_CUT = (
    "experiencia especifica",
    "de 1 hasta 2",
    "valor minimo a certificar",
)

_SPECIFIC_STOPS = (
    "valor minimo a certificar",
    "capacidad financiera",
    "indicadores financieros",
    "solvencia economica",
    "criterios de evaluacion",
    "b. estar relacionados",
    "b. el proponente",
    "formato 3",
)


def _fold(text: str) -> tuple[str, list[int]]:
    """Lowercase, unaccented text, and the original index of each folded character."""
    folded: list[str] = []
    origins: list[int] = []
    previous_space = True
    for index, char in enumerate(text or ""):
        base = unicodedata.normalize("NFKD", char)
        base = "".join(piece for piece in base if not unicodedata.combining(piece)).lower()
        if not base:
            continue
        if base.isspace():
            if previous_space:
                continue
            folded.append(" ")
            origins.append(index)
            previous_space = True
            continue
        for piece in base:
            folded.append(piece)
            origins.append(index)
        previous_space = False
    return "".join(folded), origins


def _is_index_line(folded: str, index: int) -> bool:
    """A table-of-contents row leads the heading to a page number with dots."""
    return "...." in folded[index : index + 180]


def _first_marker(folded: str, markers: tuple[str, ...], after: int = 0) -> Optional[int]:
    hits: list[int] = []
    for marker in markers:
        index = after
        while index < len(folded):
            found = folded.find(marker, index)
            if found < 0:
                break
            if not _is_index_line(folded, found):
                hits.append(found)
                break
            index = found + len(marker)
    return min(hits) if hits else None


def _slice_original(text: str, origins: list[int], start: int, end: int) -> str:
    if start >= end or start >= len(origins):
        return ""
    last = min(end, len(origins)) - 1
    return text[origins[start] : origins[last] + 1]


def _fit_section(section: str, max_chars: int) -> str:
    """Keep the opening and any value or specific block that fell past the cut."""
    cleaned = section.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    folded, origins = _fold(cleaned)
    parts = [_slice_original(cleaned, origins, 0, min(len(folded), _HEAD_CHARS))]
    head_end = min(len(folded), _HEAD_CHARS)
    for marker in _KEEP_IF_CUT:
        index = folded.rfind(marker)
        if index < head_end:
            continue
        window_end = min(len(folded), index + 900)
        window_start = max(head_end, index - 400)
        parts.append(_slice_original(cleaned, origins, window_start, window_end))
    combined = "\n\n".join(part.strip() for part in parts if part.strip())
    return combined[:max_chars]


def experience_section_excerpt(text: str, max_chars: int = _SECTION_MAX_CHARS) -> str:
    """The experience chapter, from its heading through the value rule, excluding the next chapter."""
    folded, origins = _fold(text)
    if "experiencia" not in folded:
        return ""
    start = _first_marker(folded, _START_MARKERS)
    if start is None:
        start = folded.find("experiencia")
    end = _first_marker(folded, _END_MARKERS, after=start + 40)
    if end is None:
        end = len(folded)
    return _fit_section(_slice_original(text, origins, start, end), max_chars)


def labeled_specific_scope(excerpt: str) -> Optional[str]:
    """The text that follows the specific-experience label, when the pliego writes one."""
    folded, origins = _fold(excerpt)
    start = folded.find("experiencia especifica")
    if start < 0:
        return None
    body_start = start + len("experiencia especifica")
    end = _first_marker(folded, _SPECIFIC_STOPS, after=body_start + 20)
    if end is None:
        end = min(len(folded), body_start + 2_500)
    body = _slice_original(excerpt, origins, body_start, end).strip(" :-\n\t")
    if len(body) < 40:
        return None
    return body[:4_000]


def _spanish_number(token: str) -> Optional[float]:
    cleaned = token.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def amount_is_project_band(excerpt: str, amount: float) -> bool:
    """True when the figure is the band of this project's value, not the experience to certify."""
    folded = normalize_text(excerpt)
    for match in re.finditer(r"entre\s+([\d\.]+)\s+y\s+([\d\.]+)\s+smmlv", folded):
        low = _spanish_number(match.group(1))
        if low is None:
            continue
        if abs(low - amount) > max(1.0, amount * 0.02):
            continue
        window = folded[max(0, match.start() - 220) : match.end() + 80]
        if any(word in window for word in ("complejidad", "presupuesto", "proyecto", "monto", "localidad")):
            return True
    return False


def reconcile_general_fields(fields: Optional[dict], excerpt: str) -> dict[str, Any]:
    """Keep the chapter's value table when the model stored the project's own SMMLV band."""
    reconciled = dict(fields or {})
    normalized = normalize_text(excerpt)
    tiers = extract_experience_value_tiers(normalized)
    if tiers:
        reconciled["experience_value_tiers"] = tiers
        reconciled.pop("min_amount_smmlv", None)
    amount = reconciled.get("min_amount_smmlv")
    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        if amount_is_project_band(excerpt, float(amount)):
            reconciled.pop("min_amount_smmlv", None)
    contracts = _extract_contracts_for_experience(
        normalized,
        "pliego_condiciones",
        None,
        from_general=True,
    )
    current = reconciled.get("contracts_minimum")
    if contracts and (not isinstance(current, dict) or current.get("maximum") is None):
        reconciled["contracts_minimum"] = contracts["value"]
    return reconciled


def reconcile_specific_fields(fields: Optional[dict], excerpt: str) -> dict[str, Any]:
    """Use the labeled specific-experience block when the model copied the activity being contracted."""
    reconciled = dict(fields or {})
    block = labeled_specific_scope(excerpt)
    if not block:
        return reconciled
    scope_fold = normalize_text(str(reconciled.get("specific_scope") or ""))[:80]
    if scope_fold and scope_fold in normalize_text(block):
        return reconciled
    reconciled["specific_scope"] = block
    return reconciled
