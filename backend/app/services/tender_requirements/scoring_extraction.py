"""Extract evaluation scoring from pliego by topic (US 1.6).

Uses the same topic-section strategy as legal/experience extraction:
locate «criterios de evaluación», parse summary tables, enrich with
per-criterion assignment sections, and extract tie-break (desempate) rules.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from uuid import UUID

from app.services.tender_requirements.regex_extraction import (
    RequirementItem,
    _clean_pliego_section_body,
    _clean_requirement_text,
    _extract_lettered_requirements,
    _find_topic_section,
    _is_toc_occurrence,
    _item,
    _snippet,
    normalize_text,
)

_EVALUATION_START_MARKERS: tuple[str, ...] = (
    "criterio de evaluacion puntaje maximo",
    "criterios de evaluacion y asignacion de puntaje",
    "criterios de evaluacion, asignacion de puntaje",
    "asignacion de puntaje y criterios de desempate",
    "criterios de evaluacion y puntaje",
    "criterios de evaluacion",
    "evaluacion habilitante",
    "asignacion de puntaje",
    "metodo de seleccion objetiva",
    "sistema de evaluacion de las ofertas",
    "capitulo iv. criterios de evaluacion",
    "capitulo iv criterios de evaluacion",
    "capitulo v. criterios de evaluacion",
    "capitulo v criterios de evaluacion",
    "capitulo iii. criterios de evaluacion",
    "capitulo iii criterios de evaluacion",
)

_EVALUATION_STOP_MARKERS: tuple[str, ...] = (
    "capitulo v.",
    "capitulo v ",
    "capitulo x.",
    "capitulo x ",
    "5. presentacion de las ofertas",
    "presentacion de las ofertas",
    "acreditacion de la experiencia del proponente",
)

_DESEMPATE_START_MARKERS: tuple[str, ...] = (
    "criterios de desempate",
    "criterio de desempate",
)

_DESEMPATE_STOP_MARKERS: tuple[str, ...] = (
    "capitulo v",
    "presentacion de las ofertas",
    "capitulo x",
    "anexos del pliego",
    "formato 1",
)

_TABLE_LABEL_ALIASES: tuple[tuple[str, str, str], ...] = (
    (r"oferta economica", "oferta_economica", "Oferta económica"),
    (r"factor de calidad", "factor_calidad", "Factor de calidad"),
    (r"experiencia del proponente|experiencia especifica", "experiencia", "Experiencia del proponente"),
    (r"equipo de trabajo|personal de equipo|personal clave evaluable", "equipo_trabajo", "Equipo de trabajo"),
    (r"factor de sostenibilidad", "sostenibilidad", "Factor de sostenibilidad"),
    (r"apoyo a la industria nacional|industria nacional|incentivo a la industria nacional", "industria_nacional", "Apoyo a la industria nacional"),
    (r"generacion de empleo territorial|empleo territorial", "empleo_territorial", "Generación de empleo territorial"),
    (r"discapacidad|personas con discapacidad|empleadores de personas con discapacidad", "discapacidad", "Vinculación personas con discapacidad"),
    (r"emprendimiento|empresas de mujeres", "empresas_mujeres", "Empresas de mujeres"),
    (r"mipyme", "mipyme", "MiPyme"),
    (r"capacidad financiera", "capacidad_financiera", "Capacidad financiera"),
    (r"capacidad organizacional", "capacidad_organizacional", "Capacidad organizacional"),
    (r"solvencia economica", "solvencia_economica", "Solvencia económica y financiera"),
    (r"formacion academica", "formacion_academica", "Formación académica"),
)

_ASSIGNMENT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "keys": ("oferta_economica",),
        "start_markers": ("4.1 oferta economica",),
        "stop_markers": ("4.2", "factor de calidad"),
        "prefer_phrases": ("propuesta economica", "correccion aritmetica", "presupuesto oficial"),
    },
    {
        "keys": ("factor_calidad",),
        "start_markers": ("4.2 factor de calidad",),
        "stop_markers": ("4.3", "apoyo a la industria nacional", "las entidades estatal"),
        "prefer_phrases": ("gerencia de proyectos", "maquinaria de obra", "plan de calidad"),
    },
    {
        "keys": ("experiencia",),
        "start_markers": (
            "4.1 forma de verificacion y asignacion de puntaje por la experiencia",
            "asignacion de puntaje por la experiencia del proponente",
            "forma de verificacion y asignacion de puntaje por la experiencia",
        ),
        "stop_markers": ("4.2", "equipo de trabajo", "personal clave evaluable"),
        "prefer_phrases": ("promedio de los contratos", "trm", "metodo de ponderacion"),
    },
    {
        "keys": ("equipo_trabajo",),
        "start_markers": (
            "4.2 equipo de trabajo",
            "equipo de trabajo (personal clave evaluable)",
        ),
        "stop_markers": ("4.3", "factor de sostenibilidad"),
        "prefer_phrases": ("experiencia adicional del personal", "formacion academica adicional"),
    },
    {
        "keys": ("sostenibilidad",),
        "start_markers": ("4.3 factor de sostenibilidad", "factor de sostenibilidad"),
        "stop_markers": ("4.4", "apoyo a la industria nacional"),
        "prefer_phrases": ("formato 12", "asignara un (1) punto"),
    },
    {
        "keys": ("industria_nacional",),
        "start_markers": ("4.4 apoyo a la industria nacional", "apoyo a la industria nacional"),
        "stop_markers": ("4.5", "vinculacion de personas", "discapacidad"),
        "prefer_phrases": ("servicios nacionales", "formato 7"),
    },
    {
        "keys": ("discapacidad",),
        "start_markers": (
            "4.5 vinculacion de personas en condicion de discapacidad",
            "vinculacion de personas en condicion de discapacidad",
        ),
        "stop_markers": ("4.6", "emprendimientos y empresas de mujeres"),
        "prefer_phrases": ("formato 6", "asignara un (1) punto"),
    },
    {
        "keys": ("empresas_mujeres",),
        "start_markers": ("4.6 emprendimientos y empresas de mujeres", "empresas de mujeres"),
        "stop_markers": ("4.7", "mipyme"),
        "prefer_phrases": ("formato 13", "0.25"),
    },
    {
        "keys": ("mipyme",),
        "start_markers": ("4.7 mipyme", "mipyme domiciliada en colombia"),
        "stop_markers": ("criterios de desempate", "capitulo v"),
        "prefer_phrases": ("registro unico de proponentes", "0.25"),
    },
    {
        "keys": ("capacidad_financiera",),
        "start_markers": ("4.2 capacidad financiera", "capacidad financiera"),
        "stop_markers": ("4.3", "capacidad organizacional"),
        "prefer_phrases": ("puntaje maximo", "matriz 2"),
    },
    {
        "keys": ("capacidad_organizacional",),
        "start_markers": ("4.3 capacidad organizacional",),
        "stop_markers": ("4.4", "capitulo v", "criterios de desempate"),
        "prefer_phrases": ("puntaje maximo",),
    },
    {
        "keys": ("solvencia_economica",),
        "start_markers": ("solvencia economica y financiera", "calificacion por solvencia"),
        "stop_markers": ("experiencia general", "capitulo iv", "indicadores financieros"),
        "prefer_phrases": ("puntaje", "calificacion"),
    },
)

_PROSE_CRITERION_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "experiencia",
        "Experiencia del proponente",
        (
            r"asignacion de puntaje por la experiencia",
            r"puntaje\s+(?:maximo\s+)?(?:asignado\s+a\s+)?la\s+experiencia",
            r"experiencia\s+del\s+proponente[^.\n]{0,200}puntaje",
        ),
    ),
    (
        "capacidad_financiera",
        "Capacidad financiera",
        (
            r"capacidad\s+financiera[^.\n]{0,200}puntaje",
            r"puntaje\s+(?:maximo\s+)?(?:por\s+)?capacidad\s+financiera",
        ),
    ),
    (
        "capacidad_organizacional",
        "Capacidad organizacional",
        (
            r"capacidad\s+organizacional[^.\n]{0,200}puntaje",
            r"puntaje\s+(?:maximo\s+)?(?:por\s+)?capacidad\s+organizacional",
        ),
    ),
    (
        "solvencia_economica",
        "Solvencia económica y financiera",
        (
            r"calificacion por solvencia[^.\n]{0,80}puntaje",
            r"solvencia\s+economica[^.\n]{0,200}puntaje",
        ),
    ),
)

_ITEM_ORDER: tuple[str, ...] = (
    "oferta_economica",
    "factor_calidad",
    "experiencia",
    "equipo_trabajo",
    "sostenibilidad",
    "industria_nacional",
    "discapacidad",
    "empresas_mujeres",
    "mipyme",
    "empleo_territorial",
    "solvencia_economica",
    "capacidad_financiera",
    "capacidad_organizacional",
    "formacion_academica",
    "ajuste_obras_inconclusas",
    "ajuste_multas",
    "total_points",
)

_NOISE_LABELS = frozenset(
    {
        "total",
        "concepto",
        "puntaje",
        "maximo",
        "puntaje maximo",
        "criterio",
        "criterios",
    }
)

_NUMBERED_SECTION_RE = re.compile(
    r"\b(4\.\d+(?:\.\d+)?)\s+(.+?)(?=\s+4\.\d+(?:\.\d+)?\s+|\s+criterios de desempate|\s+capitulo v\b|\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)

_LABEL_NOISE_PATTERNS: tuple[str, ...] = (
    r"^documento base",
    r"^version\b",
    r"^pagina\b",
    r"^codigo\b",
    r"^cce-",
    r"^del$",
    r"^de$",
    r"^de conformidad",
    r"licitacion de (obra|infraestructura)",
    r"tarjeta de circulacion",
    r"obra publica de infraestructura",
)

_SCORING_KEYWORD_HINTS: tuple[str, ...] = (
    "oferta",
    "experiencia",
    "calidad",
    "industria",
    "discapacidad",
    "mujer",
    "mipyme",
    "financier",
    "organizacional",
    "sostenibilidad",
    "equipo",
    "solvencia",
    "empleo",
    "territorial",
    "ponderacion",
)

_HEADER_NOISE_RE = re.compile(
    r"^(codigo|pagina|version|documento base|cce-|interventoria de obra)",
    re.IGNORECASE,
)
_POINT_ONLY_RE = re.compile(r"^\d{1,3}(?:[.,]\d+)?$")


def _document_has_scoring_signals(normalized: str) -> bool:
    return bool(
        re.search(
            r"evaluacion habilitante|puntaje total|asignacion de puntaje|"
            r"criterios de evaluacion|concepto\s+puntaje|puntaje\s+maximo|"
            r"calificacion por solvencia.{0,40}puntaje|tendra un puntaje de",
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _looks_like_section_number(raw: str) -> bool:
    cleaned = raw.strip().replace(" ", "").replace(",", ".")
    return bool(re.match(r"^[4-9]\.\d+$", cleaned))


def _parse_points_value(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(" ", "").replace(",", ".")
    if _looks_like_section_number(cleaned):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if -10 <= value <= 100:
        return value
    return None


def _parse_points_from_prose(window: str) -> Optional[float]:
    patterns: tuple[str, ...] = (
        r"(?:sera de|sera|de hasta|maximo de|asignado de|tendra un puntaje de)\s+"
        r"(?:[a-z\s]{0,30}\s+)?\(\s*(\d{1,3})\s*\)\s*puntos?",
        r"(?:sera de|de hasta|maximo de|asignado de|hasta|tendra un puntaje de)\s+"
        r"(\d{1,3}(?:[.,]\d+)?)\s*puntos?",
        r"(\d{1,3}(?:[.,]\d+)?)\s*puntos",
    )
    for pattern in patterns:
        match = re.search(pattern, window, flags=re.IGNORECASE)
        if not match:
            continue
        value = _parse_points_value(match.group(1))
        if value is not None:
            return value
    paren_only = re.search(r"\(\s*(\d{1,3}(?:[.,]\d+)?)\s*\)", window)
    if paren_only:
        return _parse_points_value(paren_only.group(1))
    return None


def _is_noise_criterion_label(label: str) -> bool:
    normalized = normalize_text(label)
    if len(normalized) < 3:
        return True
    if normalized in {"del", "de", "la", "el", "los", "las", "version", "pagina"}:
        return True
    if re.search(r"^del\s+decreto\s+\d+", normalized):
        return True
    if normalized.endswith(")") and "(" not in normalized:
        return True
    if "decreto" in normalized and "puntaje" not in normalized and len(normalized) < 96:
        return True
    for pattern in _LABEL_NOISE_PATTERNS:
        if re.search(pattern, normalized):
            return True
    word_count = len(normalized.split())
    if word_count == 1 and normalized not in {"mipyme"}:
        return True
    if len(normalized) > 72 and not any(hint in normalized for hint in _SCORING_KEYWORD_HINTS):
        return True
    return False


def _canonical_criterion_key(key: str, label: str) -> str:
    normalized = normalize_text(label)
    for pattern, alias_key, _ in _TABLE_LABEL_ALIASES:
        if key == alias_key or re.search(pattern, normalized, flags=re.IGNORECASE):
            return alias_key
    return key


def _label_to_key(label: str) -> str:
    normalized = normalize_text(label)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:56]
    return slug or "criterio"


def _unique_key(base: str, seen: set[str]) -> str:
    if base not in seen:
        return base
    suffix = 2
    while f"{base}_{suffix}" in seen:
        suffix += 1
    return f"{base}_{suffix}"


def _resolve_criterion_label(label: str) -> Optional[tuple[str, str]]:
    normalized = normalize_text(label)
    if not normalized or normalized in _NOISE_LABELS:
        return None
    if _POINT_ONLY_RE.match(normalized.replace(" ", "")):
        return None
    if re.match(r"^\d", normalized) and not any(
        re.search(pattern, normalized, flags=re.IGNORECASE)
        for pattern, _, _ in _TABLE_LABEL_ALIASES
    ):
        return None

    matches: list[tuple[int, int, str, str]] = []
    for pattern, key, display in _TABLE_LABEL_ALIASES:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), len(match.group()), key, display))
    if matches:
        _, _, key, display = max(matches, key=lambda item: (item[1], item[0]))
        return key, display

    if _is_noise_criterion_label(label):
        return None

    cleaned = _clean_requirement_text(label, max_len=96)
    if len(normalized) < 3:
        return None
    return _label_to_key(label), cleaned


def _scoring_chapter_body(normalized: str) -> str:
    """Best scoring-section slice (any chapter) for tables and assignment rules."""
    candidates: list[tuple[int, int]] = []
    for marker in _EVALUATION_START_MARKERS:
        search_from = 0
        while True:
            index = normalized.find(marker, search_from)
            if index < 0:
                break
            if _is_toc_occurrence(normalized, index, len(marker)):
                search_from = index + len(marker)
                continue
            window_end = min(len(normalized), index + 12_000)
            window = normalized[index:window_end]
            score = index  # prefer later (content) over early (TOC)
            if "concepto" in window and "puntaje maximo" in window:
                score += 500_000
            if "criterio de evaluacion" in window and "puntaje maximo" in window:
                score += 500_000
            if re.search(r"puntaje\s+total\s+100\s+puntos", window):
                score += 300_000
            if "4.1" in window:
                score += 50_000
            candidates.append((score, index))
            search_from = index + len(marker)

    if not candidates:
        return _evaluation_main_body(normalized)

    start = max(candidates, key=lambda item: item[0])[1]
    end = len(normalized)
    for stop in _EVALUATION_STOP_MARKERS + (
        "capitulo vi",
        "acreditacion de la experiencia del proponente",
    ):
        stop_idx = normalized.find(stop, start + 200)
        if stop_idx >= 0:
            end = min(end, stop_idx)
    return _clean_pliego_section_body(normalized[start:end])


def _match_table_label(label: str) -> Optional[tuple[str, str]]:
    return _resolve_criterion_label(label)


def _evaluation_main_body(normalized: str) -> str:
    return _find_topic_section(
        normalized,
        _EVALUATION_START_MARKERS,
        _EVALUATION_STOP_MARKERS,
        max_window=55_000,
        prefer_phrases=(
            "concepto",
            "puntaje maximo",
            "criterios de evaluacion y puntaje",
            "asignacion de puntaje",
        ),
    )


def _has_summary_table_header(text: str) -> bool:
    normalized = normalize_text(text)
    if "puntaje maximo" not in normalized:
        return False
    return any(
        marker in normalized
        for marker in (
            "concepto",
            "criterio de evaluacion",
            "criterios de evaluacion",
        )
    )


_SCORING_SUMMARY_TABLE_RE = re.compile(
    r"(?:concepto|criterio(?:s)? de evaluacion)\s+puntaje\s+maximo"
    r".{20,4000}?"
    r"puntaje\s+total\s+(\d{1,3}(?:[.,]\d+)?)\s+puntos?",
    re.IGNORECASE,
)


def _find_scoring_summary_window(normalized: str) -> str:
    best = ""
    best_score = -1
    for match in _SCORING_SUMMARY_TABLE_RE.finditer(normalized):
        window = match.group()
        score = window.count(" puntos") * 100
        if "puntaje maximo" in window:
            score += 500
        try:
            score += float(match.group(1).replace(",", "."))
        except (TypeError, ValueError):
            pass
        if score > best_score:
            best_score = score
            best = window
    if not best:
        return ""
    return _trim_scoring_excerpt_at_stops(best)


def _table_region(main_body: str) -> str:
    if not main_body or not _has_summary_table_header(main_body):
        return ""

    normalized = normalize_text(main_body)
    start = -1
    for marker in (
        "criterio de evaluacion puntaje maximo",
        "criterios de evaluacion puntaje maximo",
        "concepto puntaje maximo",
        "concepto",
        "criterio de evaluacion",
    ):
        index = normalized.find(marker)
        if index >= 0 and (start < 0 or index < start):
            start = index

    if start < 0:
        start = main_body.find("concepto")
    if start < 0:
        return ""

    total_match = re.search(
        r"\b(?:puntaje\s+total|total)\s+\d{1,3}(?:[.,]\d+)?(?:\s+puntos)?",
        main_body[start:],
        flags=re.IGNORECASE,
    )
    if total_match:
        return main_body[start : start + total_match.end()]

    end = len(main_body)
    for marker in (
        "las entidades deben consultar",
        "se descontara un",
        "reducir durante la evaluacion",
        "nota 2:",
    ):
        idx = main_body.find(marker, start)
        if idx >= 0:
            end = min(end, idx)
    return main_body[start:end]


def _table_lines(region: str) -> list[str]:
    lines: list[str] = []
    for raw in region.replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or _HEADER_NOISE_RE.match(line):
            continue
        lines.append(line)
    return lines


def _extract_embedded_header_row(
    region: str,
) -> tuple[Optional[tuple[str, float]], str]:
    """Some PDFs merge «Concepto | row1 | Puntaje máximo | pts» on one line."""
    match = re.search(
        r"concepto\s+(.+?)\s+puntaje\s+maximo\s+(\d{1,3}(?:[.,]\d+)?)\s*",
        region,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, region

    label = match.group(1).strip()
    normalized_label = normalize_text(label)
    if normalized_label in {"puntaje", "maximo", "puntaje maximo"}:
        return None, region

    points = _parse_points_value(match.group(2))
    if points is None:
        return None, region

    return (label, points), region[match.end() :].strip()


def _strip_table_header(region: str) -> str:
    stripped = region.strip()
    for pattern in (
        r"^criterio de evaluacion\s+puntaje\s+maximo\s+",
        r"^criterios de evaluacion\s+puntaje\s+maximo\s+",
        r"^concepto\s+puntaje\s+maximo\s+",
        r"^puntaje\s+maximo\s+",
        r"^concepto\s+",
        r"^criterios de evaluacion y puntaje:\s*",
    ):
        match = re.match(pattern, stripped, flags=re.IGNORECASE)
        if match:
            return stripped[match.end() :].strip()
    return stripped


def _parse_label_point_pairs(content: str) -> list[tuple[str, float]]:
    """Parse «label points label points …» rows (normalized single-line tables)."""
    pairs: list[tuple[str, float]] = []
    embedded, content = _extract_embedded_header_row(content)
    if embedded:
        pairs.append(embedded)

    content = _strip_table_header(content)
    if not content:
        return pairs

    tokens = re.split(r"\s+(\d{1,3}(?:[.,]\d+)?)\s*", content)
    if len(tokens) < 2:
        return pairs

    label = tokens[0].strip()
    for index in range(1, len(tokens), 2):
        points = _parse_points_value(tokens[index])
        next_label = tokens[index + 1].strip() if index + 1 < len(tokens) else ""
        if points is not None and label:
            pairs.append((label, points))
            if normalize_text(label) == "total":
                break
        label = next_label
    return pairs


def _parse_label_puntos_pairs(content: str) -> list[tuple[str, float]]:
    """Parse «label 40 puntos label 45 puntos …» rows (concurso de méritos)."""
    stripped = _strip_table_header(content)
    if not stripped:
        return []

    pairs: list[tuple[str, float]] = []
    pattern = re.compile(
        r"(.+?)\s+(\d{1,3}(?:[.,]\d+)?)\s+puntos?\b",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(stripped):
        label = re.sub(r"\s+", " ", match.group(1)).strip(" .;:-")
        points = _parse_points_value(match.group(2))
        if not label or points is None:
            continue
        normalized_label = normalize_text(label)
        if normalized_label in {"puntaje", "maximo", "criterio de evaluacion", "criterios de evaluacion"}:
            continue
        if "puntaje maximo" in normalized_label:
            label = re.sub(r"^.*puntaje maximo\s*", "", label, flags=re.IGNORECASE).strip(" .;:-")
            if not label:
                continue
        pairs.append((label, points))
    return pairs


def _salvage_contaminated_table_label(label_raw: str) -> str:
    """Recover criterion text when a 4.x section header interrupts the summary table."""
    stripped = label_raw.strip()
    if not re.match(r"4\.\d+\s", normalize_text(stripped)):
        return stripped

    normalized = normalize_text(stripped)
    matches: list[tuple[int, int, str]] = []
    for pattern, _, _ in _TABLE_LABEL_ALIASES:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), len(match.group()), match.group()))
    if matches:
        start, _, _ = max(matches, key=lambda item: (item[0], item[1]))
        return stripped[start:].strip()

    tail = re.split(r"\.{3,}", stripped)[-1].strip()
    return tail or stripped


def _append_table_row(
    rows: list[tuple[str, str, float, str]],
    seen_keys: set[str],
    label_raw: str,
    points: float,
) -> None:
    normalized_label = normalize_text(label_raw)
    if normalized_label in {"total", "puntaje total"}:
        rows.append(("total_points", "Total evaluación habilitante", points, f"Total: {points:g}"))
        return

    label_raw = _salvage_contaminated_table_label(label_raw)
    resolved = _resolve_criterion_label(label_raw)
    if not resolved:
        return
    key, display = resolved
    canonical = _canonical_criterion_key(key, display)
    if canonical in seen_keys:
        return
    seen_keys.add(canonical)
    rows.append((canonical, display, points, f"{label_raw}: {points:g}"))


def _region_uses_puntos_suffix(region: str) -> bool:
    return len(re.findall(r"\d{1,3}(?:[.,]\d+)?\s+puntos?\b", region, flags=re.IGNORECASE)) >= 3


def _extract_summary_table(main_body: str) -> list[tuple[str, str, float, str]]:
    """Parse «Concepto | Puntaje máximo» summary tables (CMA-style)."""
    region = _table_region(main_body)
    if not region:
        return []

    rows: list[tuple[str, str, float, str]] = []
    seen_keys: set[str] = set()

    if _region_uses_puntos_suffix(region):
        label_point_iter = _parse_label_puntos_pairs(region)
    else:
        label_point_iter = _parse_label_point_pairs(region)

    for label_raw, points in label_point_iter:
        _append_table_row(rows, seen_keys, label_raw, points)

    if not rows:
        fallback_iter = (
            _parse_label_point_pairs(region)
            if _region_uses_puntos_suffix(region)
            else _parse_label_puntos_pairs(region)
        )
        for label_raw, points in fallback_iter:
            _append_table_row(rows, seen_keys, label_raw, points)

    if rows:
        return rows

    lines = _table_lines(region)
    index = 0
    while index < len(lines):
        line = lines[index]
        lowered = normalize_text(line)

        if lowered in _NOISE_LABELS:
            index += 1
            continue

        same_line = re.match(r"^(.+?)\s+(\d{1,3}(?:[.,]\d+)?)\s*$", line, flags=re.IGNORECASE)
        if same_line:
            label_raw = same_line.group(1).strip()
            points = _parse_points_value(same_line.group(2))
            if points is not None:
                _append_table_row(rows, seen_keys, label_raw, points)
            index += 1
            continue

        if index + 1 < len(lines):
            next_line = lines[index + 1].strip().replace(" ", "")
            if _POINT_ONLY_RE.match(next_line):
                points = _parse_points_value(next_line)
                if points is not None:
                    _append_table_row(rows, seen_keys, line, points)
                index += 2
                continue

        index += 1

    return rows


def _summarize_section(body: str, *, max_len: int = 260) -> str:
    if not body:
        return ""
    sentences = re.findall(r"[^.!?]{25,320}[.!?]", body)
    if sentences:
        return _clean_requirement_text(" ".join(sentences[:2]), max_len=max_len)
    return _clean_requirement_text(body, max_len=max_len)


def _section_title_label(section_number: str, raw_title: str) -> str:
    title = re.sub(r"\s+", " ", raw_title).strip()
    title = re.split(r"\s{2,}|\.\s+la entidad|\.\s+para ", title, maxsplit=1)[0]
    title = title.strip(" .;:-")
    if len(title) > 100:
        title = title[:100].rsplit(" ", 1)[0]
    return _clean_requirement_text(title or raw_title, max_len=96)


def _extract_numbered_criteria_sections(
    chapter_body: str,
) -> list[tuple[str, str, Optional[float], str]]:
    """Parse 4.x assignment sections when summary table is missing or incomplete."""
    rows: list[tuple[str, str, Optional[float], str]] = []
    seen_keys: set[str] = set()

    for match in _NUMBERED_SECTION_RE.finditer(chapter_body):
        section_number = match.group(1)
        raw_title = match.group(2)
        body = _clean_pliego_section_body(raw_title)
        if len(body) < 30:
            continue

        title_line = _section_title_label(section_number, body[:160])
        if normalize_text(title_line) in {"criterios de desempate", "nota"}:
            continue
        if re.search(r"desempate|aclaracion|nota\s+\d", title_line, flags=re.IGNORECASE):
            continue

        resolved = _resolve_criterion_label(title_line)
        if not resolved:
            continue
        key, label = resolved
        key = _unique_key(f"{_label_to_key(label)}_{section_number.replace('.', '_')}", seen_keys)
        seen_keys.add(key)

        points = _parse_points_from_prose(body[:900])
        if points is None:
            table_points = _parse_label_point_pairs(body[:500])
            if len(table_points) == 1:
                points = table_points[0][1]

        rule = _summarize_section(body)
        rows.append((key, label, points, rule or f"{section_number} {title_line}"))

    return rows


def _extract_generic_prose_criteria(chapter_body: str) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
    seen_keys: set[str] = set()

    for match in re.finditer(
        r"\b4\.\d+(?:\.\d+)?\s+([^.\n]{5,120})",
        chapter_body,
        flags=re.IGNORECASE,
    ):
        title = _section_title_label(match.group(0)[:12], match.group(1))
        if normalize_text(title) in _NOISE_LABELS:
            continue
        context = chapter_body[match.start() : min(len(chapter_body), match.start() + 900)]
        if "desempate" in normalize_text(context[:120]) and "puntaje maximo" not in context[:200]:
            continue
        points = _parse_points_from_prose(context)
        if points is None:
            continue
        resolved = _resolve_criterion_label(title)
        if not resolved:
            continue
        key, label = resolved
        key = _unique_key(key, seen_keys)
        seen_keys.add(key)
        rule = _summarize_section(context)
        rows.append((key, label, points, rule or _snippet(chapter_body, match.start(), match.end() + 80)))

    return rows


def _assignment_rule_for_keys(main_body: str, keys: tuple[str, ...]) -> str:
    for spec in _ASSIGNMENT_SPECS:
        if not set(spec["keys"]).intersection(keys):
            continue
        section = _find_topic_section(
            main_body,
            spec["start_markers"],
            spec["stop_markers"],
            max_window=12_000,
            prefer_phrases=spec.get("prefer_phrases", ()),
        )
        summary = _summarize_section(section)
        if summary:
            return summary
    return ""


def _assignment_rule_for_criterion(
    chapter_body: str,
    key: str,
    label: str,
    numbered_sections: list[tuple[str, str, Optional[float], str]],
) -> str:
    rule = _assignment_rule_for_keys(chapter_body, (key,))
    if rule:
        return rule

    label_norm = normalize_text(label)
    for section_key, section_label, _, section_rule in numbered_sections:
        if section_key == key or normalize_text(section_label) == label_norm:
            if section_rule:
                return section_rule

    words = [word for word in re.findall(r"[a-z]{4,}", label_norm) if word not in {"puntaje", "maximo"}][:3]
    if words:
        pattern = r"\b4\.\d+(?:\.\d+)?\s+[^.\n]{0,30}" + r"[^.\n]{0,30}".join(re.escape(word) for word in words[:2])
        match = re.search(pattern, chapter_body, flags=re.IGNORECASE)
        if match:
            return _summarize_section(chapter_body[match.start() : match.start() + 10_000])

    section = _find_topic_section(
        chapter_body,
        (label_norm[:60], label_norm[:40]),
        ("capitulo v", "criterios de desempate", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8"),
        max_window=10_000,
        prefer_phrases=("asignara", "puntaje", "evaluara", "verificacion"),
    )
    return _summarize_section(section)


def _extract_prose_criteria(main_body: str) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
    seen_keys: set[str] = set()

    for key, label, patterns in _PROSE_CRITERION_SPECS:
        for pattern in patterns:
            match = re.search(pattern, main_body, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            context = main_body[max(0, match.start() - 40) : min(len(main_body), match.end() + 180)]
            if "desempate" in context and "evaluacion habilitante" not in context:
                continue
            points = _parse_points_from_prose(context)
            if points is None:
                continue
            item_key = _unique_key(key, seen_keys)
            seen_keys.add(item_key)
            rule = _summarize_section(context)
            rows.append((item_key, label, points, rule or _snippet(main_body, match.start(), match.end() + 80)))
            break

    for row in _extract_generic_prose_criteria(main_body):
        if row[0] not in seen_keys:
            seen_keys.add(row[0])
            rows.append(row)

    return rows


def _extract_total_from_prose(main_body: str) -> Optional[tuple[float, str]]:
    patterns: tuple[str, ...] = (
        r"evaluacion habilitante[^.\n]{0,160}?cien\s*\(\s*100\s*\)",
        r"evaluacion habilitante[^.\n]{0,160}?(\d{2,3})\s*puntos",
        r"puntaje total[^.\n]{0,100}?(\d{2,3})\s*puntos",
    )
    for pattern in patterns:
        match = re.search(pattern, main_body, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        if "cien" in match.group(0).lower() and "100" in match.group(0):
            return 100.0, _snippet(main_body, match.start(), match.end() + 40)
        if match.lastindex:
            value = _parse_points_value(match.group(1))
            if value is not None:
                return value, _snippet(main_body, match.start(), match.end() + 40)
    return None


def _extract_point_adjustments(main_body: str) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
    seen_keys: set[str] = set()

    for match in re.finditer(
        r"descontar[a]?\s+(?:un\s+)?\(?\s*(\d{1,2})\s*\)?\s*puntos?",
        main_body,
        flags=re.IGNORECASE,
    ):
        points = -float(match.group(1))
        context = normalize_text(_snippet(main_body, match.start(), match.end() + 120))
        if "obras" in context or "inconclus" in context or "red" in context:
            key, label = "ajuste_obras_inconclusas", "Descuento por obras inconclusas (RED)"
        else:
            key = _unique_key(f"ajuste_descuento_{int(abs(points))}", seen_keys)
            label = f"Descuento de {abs(points):g} punto(s)"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append((key, label, points, _snippet(main_body, match.start(), match.end() + 120)))

    for match in re.finditer(
        r"reducir.{0,160}?\(?\s*(\d{1,2})\s*\)?\s+puntos?",
        main_body,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        points = -float(match.group(1))
        context = normalize_text(_snippet(main_body, max(0, match.start() - 80), match.end() + 120))
        if "multa" in context or "clausula" in context or "penal" in context:
            key, label = "ajuste_multas", "Descuento por multas o cláusulas penales"
        else:
            key = _unique_key(f"ajuste_reduccion_{int(abs(points))}", seen_keys)
            label = f"Reducción de {abs(points):g} punto(s)"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append((key, label, points, _snippet(main_body, match.start(), match.end() + 120)))

    return rows


def _extract_desempate_rules(normalized: str, main_body: str) -> list[tuple[str, str, str]]:
    desempate_body = _find_topic_section(
        normalized,
        _DESEMPATE_START_MARKERS,
        _DESEMPATE_STOP_MARKERS,
        max_window=10_000,
        prefer_phrases=("en caso de empate", "deberan aplicarse las siguientes reglas"),
    )
    if not desempate_body and "criterios de desempate" in main_body.lower():
        start = main_body.lower().find("criterios de desempate")
        desempate_body = main_body[start : start + 8_000]

    if not desempate_body:
        return []

    lettered = _extract_lettered_requirements(
        desempate_body,
        key_prefix="desempate",
        label_prefix="Desempate",
        stop_phrase="capitulo v",
    )
    if lettered:
        return [(key, label, text) for key, label, text in lettered]

    rules: list[tuple[str, str, str]] = []
    for index, match in enumerate(
        re.finditer(
            r"(?:^|\n)\s*(?:\d+\.|[-•])\s+(.{30,320})",
            desempate_body,
            flags=re.MULTILINE,
        ),
        start=1,
    ):
        text = _clean_requirement_text(match.group(1), max_len=280)
        if len(text) < 25:
            continue
        rules.append((f"desempate_{index}", f"Desempate {index}", text))
        if len(rules) >= 6:
            break

    if not rules:
        summary = _summarize_section(desempate_body, max_len=320)
        if summary:
            rules.append(("desempate_resumen", "Criterios de desempate", summary))
    return rules


def _make_scoring_item(
    *,
    key: str,
    label: str,
    max_points: Optional[float],
    assignment_rule: str,
    criterion_type: str,
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str,
    confidence: float = 0.88,
) -> RequirementItem:
    if max_points is None:
        display_value = "Desempate"
    elif max_points < 0:
        display_value = f"{max_points:g} pts"
    else:
        display_value = f"{max_points:g} puntos"

    return _item(
        key=key,
        label=label,
        value={
            "max_points": max_points,
            "assignment_rule": assignment_rule,
            "criterion_type": criterion_type,
        },
        display_value=display_value,
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=evidence[:220],
        confidence=confidence,
    )


def _trim_scoring_excerpt_at_stops(text: str) -> str:
    end = len(text)
    for stop in _EVALUATION_STOP_MARKERS + (
        "capitulo iv. presentacion",
        "capitulo iv presentacion",
        "capitulo v. presentacion",
        "capitulo v presentacion",
    ):
        idx = text.find(stop)
        if idx >= 80:
            end = min(end, idx)
    return text[:end].strip()


def _resolve_scoring_body(normalized: str) -> str:
    """Locate scoring content regardless of chapter number."""
    summary = _find_scoring_summary_window(normalized)
    if summary.strip():
        return summary

    body = _scoring_chapter_body(normalized)
    if not body.strip():
        body = _evaluation_main_body(normalized)
    if not body.strip():
        match = re.search(r"calificacion por solvencia", normalized, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 600)
            body = normalized[start : start + 3_000]
    if body.strip():
        return _trim_scoring_excerpt_at_stops(body)
    return ""


_POINTS_TOLERANCE = 0.01
_METHOD_PRIORITY = {"hybrid": 0, "regex": 1, "llm": 2}


def _scoring_criterion_type(item: dict[str, Any]) -> str:
    value = item.get("value")
    if isinstance(value, dict):
        return str(value.get("criterion_type") or "evaluacion")
    return "evaluacion"


def _scoring_item_points(item: dict[str, Any]) -> Optional[float]:
    value = item.get("value")
    if isinstance(value, dict) and value.get("max_points") is not None:
        try:
            return float(value["max_points"])
        except (TypeError, ValueError):
            return None
    return None


def _points_equal(left: float, right: float) -> bool:
    return abs(left - right) <= _POINTS_TOLERANCE


def _item_rank(item: dict[str, Any]) -> tuple[int, float]:
    method = str(item.get("extraction_method") or "regex")
    confidence = float(item.get("confidence", 0))
    return (_METHOD_PRIORITY.get(method, 3), -confidence)


def _eval_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    value = item.get("value") if isinstance(item.get("value"), dict) else {}
    order_map = {key: index for index, key in enumerate(_ITEM_ORDER)}
    return (
        int(value.get("sort_order", 99)),
        order_map.get(item["key"], 50),
        str(item.get("label") or ""),
    )


def _split_scoring_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    eval_items: list[dict[str, Any]] = []
    total_item: Optional[dict[str, Any]] = None
    adjustments: list[dict[str, Any]] = []
    desempate: list[dict[str, Any]] = []
    for item in items:
        if item.get("key") == "total_points":
            total_item = item
            continue
        criterion_type = _scoring_criterion_type(item)
        if criterion_type == "evaluacion":
            eval_items.append(item)
        elif criterion_type == "ajuste":
            adjustments.append(item)
        elif criterion_type == "desempate":
            desempate.append(item)
    return eval_items, total_item, adjustments, desempate


def _dedupe_eval_by_canonical(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        canonical = _canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or ""))
        existing = best.get(canonical)
        if existing is None or _item_rank(item) < _item_rank(existing):
            best[canonical] = item
    return best


def _combine_eval_items(
    regex_item: Optional[dict[str, Any]],
    merged_item: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if regex_item and merged_item:
        item = dict(merged_item)
        value = dict(item.get("value") or {})
        regex_value = regex_item.get("value") if isinstance(regex_item.get("value"), dict) else {}
        regex_points = regex_value.get("max_points")
        if regex_points is not None:
            value["max_points"] = regex_points
        if regex_value.get("sort_order") is not None:
            value["sort_order"] = regex_value["sort_order"]
        value["criterion_type"] = "evaluacion"
        item["value"] = value
        points = _scoring_item_points(item)
        if points is not None:
            item["display_value"] = f"{points:g} pts" if points < 0 else f"{points:g} puntos"
        if merged_item.get("extraction_method") == "llm" and regex_item.get("extraction_method") == "regex":
            item["extraction_method"] = "hybrid"
        return item
    if regex_item:
        return dict(regex_item)
    if merged_item:
        return dict(merged_item)
    return None


def _ordered_eval_canonical_keys(
    regex_map: dict[str, dict[str, Any]],
    merged_map: dict[str, dict[str, Any]],
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in sorted(regex_map.values(), key=_eval_sort_key):
        canonical = _canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or ""))
        if canonical in seen:
            continue
        ordered.append(canonical)
        seen.add(canonical)
    for item in sorted(merged_map.values(), key=_eval_sort_key):
        canonical = _canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or ""))
        if canonical in seen:
            continue
        ordered.append(canonical)
        seen.add(canonical)
    return ordered


def _build_eval_list(
    canonical_keys: list[str],
    regex_map: dict[str, dict[str, Any]],
    merged_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    eval_items: list[dict[str, Any]] = []
    for canonical in canonical_keys:
        combined = _combine_eval_items(regex_map.get(canonical), merged_map.get(canonical))
        if combined is not None:
            eval_items.append(combined)
    return eval_items


def _eval_points_sum(eval_items: list[dict[str, Any]]) -> float:
    return sum(_scoring_item_points(item) or 0.0 for item in eval_items)


def _sort_scoring_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []

    order_map = {key: index for index, key in enumerate(_ITEM_ORDER)}

    def sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
        value = item.get("value") if isinstance(item.get("value"), dict) else {}
        criterion_type = value.get("criterion_type", "evaluacion")
        type_order = {"evaluacion": 0, "ajuste": 1, "desempate": 2}.get(str(criterion_type), 3)
        if item["key"] == "total_points":
            return (0, 0, 0, "")
        sort_order = int(value.get("sort_order", 99))
        return (type_order, order_map.get(item["key"], 50), sort_order, str(item.get("label") or ""))

    sorted_items = sorted(items, key=sort_key)
    if not any(item["key"] == "total_points" for item in sorted_items):
        return sorted_items

    total = next(item for item in sorted_items if item["key"] == "total_points")
    others = [item for item in sorted_items if item["key"] != "total_points"]
    eval_and_adjust = [item for item in others if _scoring_criterion_type(item) != "desempate"]
    desempate = [item for item in others if _scoring_criterion_type(item) == "desempate"]
    return eval_and_adjust + [total] + desempate


def sistema_puntos_sum_mismatch(items: list[dict[str, Any]]) -> bool:
    """True when evaluation criteria do not sum to the declared total_points."""
    total_item = next((item for item in items if item.get("key") == "total_points"), None)
    if not total_item:
        return False

    target = (total_item.get("value") or {}).get("max_points")
    if target is None:
        return False

    try:
        target_points = float(target)
    except (TypeError, ValueError):
        return False

    eval_sum = 0.0
    for item in items:
        if item.get("key") == "total_points":
            continue
        value = item.get("value") or {}
        if value.get("criterion_type") != "evaluacion":
            continue
        points = value.get("max_points")
        if points is None:
            continue
        try:
            eval_sum += float(points)
        except (TypeError, ValueError):
            continue

    return not _points_equal(eval_sum, target_points)


def merge_scoring_fallback_items(
    failed_items: list[dict[str, Any]],
    fallback_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace failed eval/total rows with LLM fallback; keep ajustes/desempate from prior pass."""
    if not fallback_items:
        return failed_items

    fallback_keys = {str(item.get("key") or "") for item in fallback_items}
    secondary = [
        dict(item)
        for item in failed_items
        if _scoring_criterion_type(item) in {"ajuste", "desempate"}
        and str(item.get("key") or "") not in fallback_keys
    ]
    combined = [dict(item) for item in fallback_items] + secondary
    return reconcile_sistema_puntos_items(combined, regex_items=None)


def find_scoring_summary_window(text: str) -> str:
    """Return the best inline scoring summary table window (chapter-agnostic)."""
    if not text or not text.strip():
        return ""
    return _find_scoring_summary_window(normalize_text(text))


def reconcile_sistema_puntos_items(
    items: list[dict[str, Any]],
    regex_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Ensure evaluation criteria sum exactly to the declared total (typically 100)."""
    if not items and not regex_items:
        return []

    regex_eval, regex_total, regex_adjustments, regex_desempate = _split_scoring_items(regex_items or [])
    merged_eval, merged_total, adjustments, desempate = _split_scoring_items(items or [])

    target_total = _scoring_item_points(merged_total) if merged_total else None
    if target_total is None and regex_total:
        target_total = _scoring_item_points(regex_total)
    if target_total is None:
        return _sort_scoring_items(items or [])

    regex_map = _dedupe_eval_by_canonical(regex_eval)
    merged_map = _dedupe_eval_by_canonical(merged_eval)

    canonical_keys = _ordered_eval_canonical_keys(regex_map, merged_map)
    final_eval = _build_eval_list(canonical_keys, regex_map, merged_map)

    if not _points_equal(_eval_points_sum(final_eval), target_total) and regex_map:
        regex_only_keys = [key for key in canonical_keys if key in regex_map]
        regex_only_eval = _build_eval_list(regex_only_keys, regex_map, merged_map)
        if _points_equal(_eval_points_sum(regex_only_eval), target_total):
            final_eval = regex_only_eval
            canonical_keys = regex_only_keys

    if _eval_points_sum(final_eval) < target_total - _POINTS_TOLERANCE and regex_map:
        present = {_canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or "")) for item in final_eval}
        for canonical, regex_item in sorted(regex_map.items(), key=lambda pair: _eval_sort_key(pair[1])):
            if canonical in present:
                continue
            final_eval.append(dict(regex_item))
            present.add(canonical)
            if _eval_points_sum(final_eval) >= target_total - _POINTS_TOLERANCE:
                break

    if _eval_points_sum(final_eval) > target_total + _POINTS_TOLERANCE and regex_map:
        present_keys = [
            _canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or ""))
            for item in final_eval
        ]
        merged_only = [key for key in present_keys if key not in regex_map]
        merged_only.sort(key=lambda key: _item_rank(merged_map[key]), reverse=True)
        for canonical in merged_only:
            final_eval = [
                item
                for item in final_eval
                if _canonical_criterion_key(str(item.get("key") or ""), str(item.get("label") or "")) != canonical
            ]
            if _eval_points_sum(final_eval) <= target_total + _POINTS_TOLERANCE:
                break

    if not _points_equal(_eval_points_sum(final_eval), target_total) and regex_map:
        regex_only_eval = _build_eval_list(list(regex_map.keys()), regex_map, merged_map)
        if _points_equal(_eval_points_sum(regex_only_eval), target_total):
            final_eval = regex_only_eval

    total_item = merged_total or regex_total
    if total_item:
        total_value = dict(total_item.get("value") or {})
        total_value["max_points"] = target_total
        total_value["criterion_type"] = "evaluacion"
        total_item = dict(total_item)
        total_item["value"] = total_value
        total_item["display_value"] = f"{target_total:g} puntos"

    reconciled = list(final_eval)
    reconciled.extend(adjustments or regex_adjustments)
    if total_item:
        reconciled.append(total_item)
    reconciled.extend(desempate or regex_desempate)
    return _sort_scoring_items(reconciled)


def extract_sistema_puntos(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    """Extract evaluation scoring, assignment rules and tie-break criteria."""
    if not text.strip():
        return []

    normalized = normalize_text(text)
    if not _document_has_scoring_signals(normalized):
        return []

    chapter_body = _resolve_scoring_body(normalized)
    if not chapter_body:
        return []

    numbered_sections = _extract_numbered_criteria_sections(chapter_body)
    table_rows = _extract_summary_table(chapter_body)
    has_complete_table = bool(table_rows) and any(row[0] == "total_points" for row in table_rows)

    if not table_rows:
        prose_rows = [
            (key, label, float(points), evidence)
            for key, label, points, evidence in _extract_prose_criteria(chapter_body)
            if points is not None
        ]
        if prose_rows and not any("decreto" in normalize_text(label) for _, label, _, _ in prose_rows):
            table_rows = prose_rows
    elif not has_complete_table:
        known_labels = {normalize_text(label) for _, label, _, _ in table_rows if label}
        for key, label, points, evidence in numbered_sections:
            if points is None:
                continue
            canonical = _canonical_criterion_key(key, label)
            if normalize_text(label) in known_labels or canonical in {
                _canonical_criterion_key(row_key, row_label)
                for row_key, row_label, _, _ in table_rows
                if row_key != "total_points"
            }:
                continue
            table_rows.append((canonical, label, float(points), evidence))
            known_labels.add(normalize_text(label))

    by_key: dict[str, tuple[str, str, float, str]] = {}
    criterion_order: dict[str, int] = {}
    for index, (key, label, points, evidence) in enumerate(table_rows):
        if key == "total_points":
            continue
        canonical = _canonical_criterion_key(key, label)
        if canonical in by_key:
            continue
        criterion_order[canonical] = index
        by_key[canonical] = (canonical, label, points, evidence)

    items: list[RequirementItem] = []
    for key, label, points, evidence in by_key.values():
        rule = _assignment_rule_for_criterion(chapter_body, key, label, numbered_sections) or evidence
        item = _make_scoring_item(
                key=key,
                label=label,
                max_points=points,
                assignment_rule=rule,
                criterion_type="evaluacion",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.9 if key in criterion_order and criterion_order[key] < 8 else 0.86,
            )
        value = dict(item["value"])
        value["sort_order"] = criterion_order.get(key, 99)
        item["value"] = value
        items.append(item)

    total_row = next((row for row in table_rows if row[0] == "total_points"), None)
    if total_row:
        _, label, points, evidence = total_row
        items.append(
            _make_scoring_item(
                key="total_points",
                label=label,
                max_points=points,
                assignment_rule="",
                criterion_type="evaluacion",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.93,
            )
        )
    else:
        prose_total = _extract_total_from_prose(chapter_body)
        if prose_total:
            points, evidence = prose_total
            items.append(
                _make_scoring_item(
                    key="total_points",
                    label="Total evaluación habilitante",
                    max_points=points,
                    assignment_rule="",
                    criterion_type="evaluacion",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=evidence,
                    confidence=0.9,
                )
            )
        elif items:
            eval_points = [
                float(item["value"]["max_points"])
                for item in items
                if isinstance(item.get("value"), dict)
                and item["value"].get("max_points") is not None
                and float(item["value"]["max_points"]) > 0
            ]
            if eval_points:
                inferred = sum(eval_points)
                if 50 <= inferred <= 100:
                    items.append(
                        _make_scoring_item(
                            key="total_points",
                            label="Total evaluación habilitante",
                            max_points=inferred,
                            assignment_rule="Suma de criterios detectados en el pliego.",
                            criterion_type="evaluacion",
                            source_document=source_document,
                            source_document_id=source_document_id,
                            evidence="Suma de los criterios detectados en el pliego.",
                            confidence=0.72,
                        )
                    )

    for key, label, points, evidence in _extract_point_adjustments(chapter_body):
        items.append(
            _make_scoring_item(
                key=key,
                label=label,
                max_points=points,
                assignment_rule=evidence,
                criterion_type="ajuste",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.86,
            )
        )

    for key, label, rule in _extract_desempate_rules(normalized, chapter_body):
        items.append(
            _make_scoring_item(
                key=key,
                label=label,
                max_points=None,
                assignment_rule=rule,
                criterion_type="desempate",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=rule,
                confidence=0.84,
            )
        )

    if not items:
        return []

    return reconcile_sistema_puntos_items(items)


def extract_scoring_context_for_llm(text: str, max_chars: int) -> str:
    """Return the scoring/evaluation section for LLM enrichment (chapter-agnostic)."""
    if not text or not text.strip() or max_chars <= 0:
        return ""

    normalized = normalize_text(text)
    if not _document_has_scoring_signals(normalized):
        return ""

    body = _resolve_scoring_body(normalized)
    if not body.strip():
        return ""

    return body[:max_chars]
