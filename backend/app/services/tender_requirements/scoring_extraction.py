"""Extract habilitation scoring weights from pliego text (US 1.6).

Scoring rules appear in different places depending on the entity/template:
- Capítulo IV (CCE / INVIAS)
- Capítulo III next to solvencia or experiencia
- Standalone sections titled «asignación de puntaje»
This module searches by topic, not by a fixed chapter number.
"""
from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from app.services.tender_requirements.regex_extraction import (
    RequirementItem,
    _clean_requirement_text,
    _item,
    _snippet,
    normalize_text,
)

_CRITERION_ORDER: tuple[str, ...] = (
    "experiencia",
    "solvencia_economica",
    "capacidad_financiera",
    "capacidad_organizacional",
    "formacion_academica",
    "otros_criterios",
)

_CRITERION_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "experiencia",
        "Experiencia del proponente",
        (
            r"asignacion de puntaje por la experiencia",
            r"puntaje\s+(?:maximo\s+)?(?:asignado\s+a\s+)?la\s+experiencia",
            r"experiencia\s+del\s+proponente[^.\n]{0,200}puntaje",
            r"calificacion[^.\n]{0,80}experiencia[^.\n]{0,120}puntaje",
            r"experiencia[^.\n]{0,120}calificacion[^.\n]{0,80}puntos",
        ),
    ),
    (
        "solvencia_economica",
        "Solvencia económica y financiera",
        (
            r"calificacion por solvencia[^.\n]{0,80}puntaje",
            r"solvencia\s+economica[^.\n]{0,200}puntaje",
            r"solvencia\s+economica\s+y\s+financiera[^.\n]{0,200}puntaje",
            r"puntaje[^.\n]{0,80}solvencia\s+economica",
        ),
    ),
    (
        "capacidad_financiera",
        "Capacidad financiera",
        (
            r"capacidad\s+financiera[^.\n]{0,200}puntaje",
            r"puntaje\s+(?:maximo\s+)?(?:por\s+)?capacidad\s+financiera",
            r"calificacion[^.\n]{0,80}capacidad\s+financiera[^.\n]{0,120}puntos",
        ),
    ),
    (
        "capacidad_organizacional",
        "Capacidad organizacional",
        (
            r"capacidad\s+organizacional[^.\n]{0,200}puntaje",
            r"puntaje\s+(?:maximo\s+)?(?:por\s+)?capacidad\s+organizacional",
            r"calificacion[^.\n]{0,80}capacidad\s+organizacional[^.\n]{0,120}puntos",
        ),
    ),
    (
        "formacion_academica",
        "Formación académica",
        (
            r"formacion\s+academica[^.\n]{0,200}puntaje",
            r"experiencia\s+y\s+formacion\s+academica[^.\n]{0,200}puntaje",
        ),
    ),
)

_SCORING_SIGNAL_PATTERN = re.compile(
    r"evaluacion habilitante|puntaje total|asignacion de puntaje|sistema de puntaje|"
    r"puntaje maximo|calificacion de los requisitos habilitantes|"
    r"puntaje de\s+\d{1,3}\s+puntos|tendra un puntaje de",
    flags=re.IGNORECASE,
)

_SCORING_CONTEXT_PATTERN = re.compile(
    r"puntaje|puntuacion|calificacion|puntos?\s+maxim",
    flags=re.IGNORECASE,
)

_SCORING_NOISE_MARKERS: tuple[str, ...] = (
    "desempate",
    "empresas de mujeres",
    "mipyme",
    "empresa emergente",
    "0,25",
    "0.25",
)

_REGION_END_MARKERS: tuple[str, ...] = (
    "capitulo v.",
    "capitulo v ",
    "capitulo vi",
    "5. presentacion de las ofertas",
    "5.1 presentacion de las ofertas",
    "etapa de ofertas",
    "apertura de las ofertas",
    "anexos del pliego",
)

_REGION_START_MARKERS: tuple[str, ...] = (
    "capitulo iv. criterios de evaluacion",
    "capitulo iv criterios de evaluacion",
    "capitulo iv criterios de evaluacion y asignacion",
    "criterios de evaluacion y asignacion de puntaje",
    "criterios de evaluacion",
    "asignacion de puntaje por la experiencia",
    "sistema de puntaje",
    "evaluacion habilitante",
    "calificacion de los requisitos habilitantes",
)

_TOPIC_SECTION_MARKERS: tuple[str, ...] = (
    "solvencia economica y financiera",
    "solvencia economica",
    "capacidad financiera",
    "capacidad organizacional",
    "exigencias minimas de la experiencia",
    "exigencia minima de la experiencia",
    "experiencia del proponente",
    "forma de verificacion y asignacion de puntaje",
)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 400:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _region_end(normalized: str, start: int, *, default_span: int = 4500) -> int:
    end = min(len(normalized), start + default_span)
    for marker in _REGION_END_MARKERS:
        idx = normalized.find(marker, start + 200)
        if idx >= 0:
            end = min(end, idx)
    return end


def _collect_scoring_regions(normalized: str) -> list[str]:
    ranges: list[tuple[int, int]] = []

    for marker in _REGION_START_MARKERS:
        start = 0
        while True:
            idx = normalized.find(marker, start)
            if idx < 0:
                break
            ranges.append((idx, _region_end(normalized, idx, default_span=6000)))
            start = idx + len(marker)

    for match in re.finditer(
        r"(?:\d+\.\d+\s+)?[^.\n]{8,140}(?:asignacion de puntaje|puntaje maximo|calificacion).{0,60}",
        normalized,
        flags=re.IGNORECASE,
    ):
        start = max(0, match.start() - 120)
        ranges.append((start, _region_end(normalized, match.start(), default_span=3200)))

    for marker in _TOPIC_SECTION_MARKERS:
        start = 0
        while True:
            idx = normalized.find(marker, start)
            if idx < 0:
                break
            end = _region_end(normalized, idx, default_span=2800)
            window = normalized[idx:end]
            if _SCORING_CONTEXT_PATTERN.search(window):
                ranges.append((max(0, idx - 80), end))
            start = idx + len(marker)

    merged = _merge_ranges(ranges)
    if merged:
        return [normalized[start:end] for start, end in merged]

    if _SCORING_SIGNAL_PATTERN.search(normalized):
        return [normalized]

    return []


def _document_has_scoring_signals(normalized: str) -> bool:
    return bool(_SCORING_SIGNAL_PATTERN.search(normalized))


def _is_scoring_noise(context: str) -> bool:
    if any(marker in context for marker in _SCORING_NOISE_MARKERS):
        if "evaluacion habilitante" in context or "puntaje maximo" in context:
            return False
        if "desempate" in context or "mipyme" in context:
            return True
    return False


def _has_scoring_context(context: str) -> bool:
    if not _SCORING_CONTEXT_PATTERN.search(context):
        return False
    return not _is_scoring_noise(context)


def _parse_points_value(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if 0 < value <= 100:
        return value
    return None


def _extract_points_from_window(window: str) -> Optional[float]:
    patterns: tuple[str, ...] = (
        r"(?:sera de|sera|de hasta|maximo de|asignado de|equivalente a|tendra un puntaje de)\s+"
        r"(?:[a-z\s]{0,30}\s+)?\(\s*(\d{1,3})\s*\)\s*puntos?",
        r"(?:sera de|de hasta|maximo de|asignado de|hasta|tendra un puntaje de)\s+(\d{1,3})\s*puntos?",
        r"(\d{1,3})\s*puntos",
    )
    for pattern in patterns:
        match = re.search(pattern, window, flags=re.IGNORECASE)
        if not match:
            continue
        value = _parse_points_value(match.group(1))
        if value is not None:
            return value

    paren_only = re.search(r"\(\s*(\d{1,3})\s*\)", window)
    if paren_only:
        return _parse_points_value(paren_only.group(1))

    return None


def _sentence_at(text: str, position: int, *, window: int = 320) -> str:
    start = max(0, position - 40)
    end = min(len(text), position + window)
    chunk = text[start:end]
    match = re.search(r"[^.]{20,280}\.", chunk)
    if match:
        return _clean_requirement_text(match.group(0), max_len=260)
    return _clean_requirement_text(chunk, max_len=260)


def _match_specificity(region_len: int, full_len: int) -> float:
    if full_len <= 0:
        return 0.0
    ratio = region_len / full_len
    return max(0.0, min(1.0, 1.0 - ratio))


def _find_best_criterion_match(
    regions: list[str],
    patterns: tuple[str, ...],
    *,
    full_len: int,
) -> Optional[tuple[float, str, int, float]]:
    best: Optional[tuple[float, str, int, float]] = None

    for region in regions:
        for pattern in patterns:
            for match in re.finditer(pattern, region, flags=re.IGNORECASE | re.DOTALL):
                context_start = max(0, match.start() - 100)
                context_end = min(len(region), match.end() + 220)
                context = region[context_start:context_end]
                if not _has_scoring_context(context):
                    continue
                points = _extract_points_from_window(context)
                if points is None:
                    continue
                specificity = _match_specificity(len(region), full_len)
                candidate = (
                    points,
                    _sentence_at(region, match.start()),
                    match.start(),
                    specificity + (0.05 if points >= 5 else 0),
                )
                if best is None or candidate[3] > best[3]:
                    best = candidate

    if best is None:
        return None
    return best[0], best[1], best[2], best[3]


def _extract_total_points(regions: list[str]) -> Optional[tuple[float, str]]:
    patterns: tuple[str, ...] = (
        r"evaluacion habilitante[^.\n]{0,160}?cien\s*\(\s*100\s*\)",
        r"evaluacion habilitante[^.\n]{0,160}?(\d{2,3})\s*puntos",
        r"puntaje total[^.\n]{0,100}?cien\s*\(\s*100\s*\)",
        r"puntaje total[^.\n]{0,100}?(\d{2,3})\s*puntos",
        r"total[^.\n]{0,60}?cien\s*\(\s*100\s*\)\s*puntos",
        r"suma[^.\n]{0,80}?(\d{2,3})\s*puntos",
        r"total\s+de\s+puntos[^.\n]{0,40}?(\d{2,3})",
    )
    for region in regions:
        for pattern in patterns:
            match = re.search(pattern, region, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            context = region[match.start() : min(len(region), match.end() + 60)]
            if _is_scoring_noise(context) and "evaluacion habilitante" not in context:
                continue
            if "cien" in match.group(0) and "100" in match.group(0):
                return 100.0, _snippet(region, match.start(), match.end() + 40)
            if match.lastindex:
                value = _parse_points_value(match.group(1))
                if value is not None:
                    return value, _snippet(region, match.start(), match.end() + 40)
            points = _extract_points_from_window(context)
            if points is not None:
                return points, _snippet(region, match.start(), match.end() + 40)
    return None


def _append_criterion_item(
    items: list[RequirementItem],
    seen_keys: set[str],
    *,
    key: str,
    label: str,
    max_points: float,
    assignment_rule: str,
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str,
) -> None:
    if key in seen_keys:
        return
    seen_keys.add(key)
    points_display = f"{max_points:g}"
    items.append(
        _item(
            key=key,
            label=label,
            value={
                "max_points": max_points,
                "assignment_rule": assignment_rule,
            },
            display_value=f"{points_display} puntos",
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=evidence[:220],
            confidence=0.88,
        )
    )


def extract_sistema_puntos(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    """Extract habilitation scoring weights from pliego text."""
    if not text.strip():
        return []

    normalized = normalize_text(text)
    if not _document_has_scoring_signals(normalized):
        return []

    regions = _collect_scoring_regions(normalized)
    if not regions:
        return []

    items: list[RequirementItem] = []
    seen_keys: set[str] = set()
    full_len = len(normalized)

    for key, label, patterns in _CRITERION_SPECS:
        found = _find_best_criterion_match(regions, patterns, full_len=full_len)
        if not found:
            continue
        max_points, assignment_rule, _position, _specificity = found
        _append_criterion_item(
            items,
            seen_keys,
            key=key,
            label=label,
            max_points=max_points,
            assignment_rule=assignment_rule,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=assignment_rule,
        )

    total = _extract_total_points(regions)
    if total:
        total_points, evidence = total
        items.append(
            _item(
                key="total_points",
                label="Total evaluación habilitante",
                value=total_points,
                display_value=f"{total_points:g} puntos",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.9,
            )
        )
    elif items:
        criterion_points = [
            float(item["value"]["max_points"])
            for item in items
            if isinstance(item.get("value"), dict) and item["value"].get("max_points") is not None
        ]
        if criterion_points:
            inferred_total = sum(criterion_points)
            if 50 <= inferred_total <= 100:
                items.append(
                    _item(
                        key="total_points",
                        label="Total evaluación habilitante",
                        value=inferred_total,
                        display_value=f"{inferred_total:g} puntos (suma de criterios)",
                        source_document=source_document,
                        source_document_id=source_document_id,
                        evidence="Suma de los criterios detectados en el pliego.",
                        confidence=0.72,
                    )
                )

    if not items:
        return []

    order_map = {key: index for index, key in enumerate(_CRITERION_ORDER)}
    items.sort(
        key=lambda item: (
            0 if item["key"] == "total_points" else 1,
            order_map.get(item["key"], 99),
            item["label"],
        )
    )
    return items
