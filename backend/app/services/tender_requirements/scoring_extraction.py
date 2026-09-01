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
    _item,
    _snippet,
    normalize_text,
)

_EVALUATION_START_MARKERS: tuple[str, ...] = (
    "capitulo iv. criterios de evaluacion",
    "capitulo iv criterios de evaluacion",
    "criterios de evaluacion y asignacion de puntaje",
    "criterios de evaluacion, asignacion de puntaje",
    "criterios de evaluacion",
    "asignacion de puntaje y criterios de desempate",
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

_TABLE_LABEL_SPECS: tuple[tuple[str, str, str], ...] = (
    (r"experiencia del proponente", "experiencia", "Experiencia del proponente"),
    (r"equipo de trabajo|personal clave evaluable", "equipo_trabajo", "Equipo de trabajo"),
    (r"factor de sostenibilidad", "sostenibilidad", "Factor de sostenibilidad"),
    (r"apoyo a la industria nacional|industria nacional", "industria_nacional", "Apoyo a la industria nacional"),
    (r"discapacidad", "discapacidad", "Vinculación personas con discapacidad"),
    (r"emprendimiento|empresas de mujeres", "empresas_mujeres", "Empresas de mujeres"),
    (r"mipyme", "mipyme", "MiPyme"),
    (r"capacidad financiera", "capacidad_financiera", "Capacidad financiera"),
    (r"capacidad organizacional", "capacidad_organizacional", "Capacidad organizacional"),
    (r"solvencia economica", "solvencia_economica", "Solvencia económica y financiera"),
    (r"formacion academica", "formacion_academica", "Formación académica"),
)

_ASSIGNMENT_SPECS: tuple[dict[str, Any], ...] = (
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
    "experiencia",
    "equipo_trabajo",
    "sostenibilidad",
    "industria_nacional",
    "discapacidad",
    "empresas_mujeres",
    "mipyme",
    "solvencia_economica",
    "capacidad_financiera",
    "capacidad_organizacional",
    "formacion_academica",
    "ajuste_obras_inconclusas",
    "ajuste_multas",
    "total_points",
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


def _parse_points_value(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(" ", "").replace(",", ".")
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


def _match_table_label(label: str) -> Optional[tuple[str, str]]:
    normalized = normalize_text(label)
    if normalized in {"total", "concepto", "puntaje", "maximo", "puntaje maximo"}:
        return None
    for pattern, key, display in _TABLE_LABEL_SPECS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return key, display
    if len(normalized) >= 12 and not _POINT_ONLY_RE.match(normalized.replace(" ", "")):
        slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:48]
        if slug:
            return slug, _clean_requirement_text(label, max_len=80)
    return None


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
    return "concepto" in normalized and "puntaje maximo" in normalized


def _table_region(main_body: str) -> str:
    if not main_body or not _has_summary_table_header(main_body):
        return ""

    start = main_body.find("concepto")
    if start < 0:
        return ""

    end = len(main_body)
    for marker in (
        "las entidades deben consultar",
        "se descontara un",
        "reducir durante la evaluacion",
        "4.1 forma de verificacion",
        "4.1 forma de verificacion y asignacion",
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


def _strip_table_header(region: str) -> str:
    stripped = region.strip()
    for pattern in (
        r"concepto\s+puntaje\s+maximo\s+",
        r"puntaje\s+maximo\s+",
        r"concepto\s+",
        r"criterios de evaluacion y puntaje:\s*",
    ):
        match = re.search(pattern, stripped, flags=re.IGNORECASE)
        if match:
            return stripped[match.end() :].strip()
    return stripped


def _parse_label_point_pairs(content: str) -> list[tuple[str, float]]:
    """Parse «label points label points …» rows (normalized single-line tables)."""
    content = _strip_table_header(content)
    if not content:
        return []

    tokens = re.split(r"\s+(\d{1,3}(?:[.,]\d+)?)\s*", content)
    if len(tokens) < 2:
        return []

    pairs: list[tuple[str, float]] = []
    label = tokens[0].strip()
    for index in range(1, len(tokens), 2):
        points = _parse_points_value(tokens[index])
        next_label = tokens[index + 1].strip() if index + 1 < len(tokens) else ""
        if points is not None and label:
            pairs.append((label, points))
        label = next_label
    return pairs


def _extract_summary_table(main_body: str) -> list[tuple[str, str, float, str]]:
    """Parse «Concepto | Puntaje máximo» summary tables (CMA-style)."""
    region = _table_region(main_body)
    if not region:
        return []

    rows: list[tuple[str, str, float, str]] = []
    seen_keys: set[str] = set()

    for label_raw, points in _parse_label_point_pairs(region):
        normalized_label = normalize_text(label_raw)
        if normalized_label == "total":
            rows.append(("total_points", "Total evaluación habilitante", points, f"Total: {points:g}"))
            continue

        matched = _match_table_label(label_raw)
        if matched and matched[0] not in seen_keys:
            seen_keys.add(matched[0])
            rows.append((matched[0], matched[1], points, f"{label_raw}: {points:g}"))

    if rows:
        return rows

    lines = _table_lines(region)
    index = 0
    while index < len(lines):
        line = lines[index]
        lowered = normalize_text(line)

        if lowered in {"concepto", "puntaje", "maximo", "puntaje maximo"}:
            index += 1
            continue

        same_line = re.match(r"^(.+?)\s+(\d{1,3}(?:[.,]\d+)?)\s*$", line, flags=re.IGNORECASE)
        if same_line:
            label_raw = same_line.group(1).strip()
            points = _parse_points_value(same_line.group(2))
            if points is not None:
                if normalize_text(label_raw) == "total":
                    rows.append(("total_points", "Total evaluación habilitante", points, label_raw))
                else:
                    matched = _match_table_label(label_raw)
                    if matched and matched[0] not in seen_keys:
                        seen_keys.add(matched[0])
                        rows.append((matched[0], matched[1], points, f"{label_raw}: {points:g}"))
            index += 1
            continue

        if index + 1 < len(lines):
            next_line = lines[index + 1].strip().replace(" ", "")
            if _POINT_ONLY_RE.match(next_line):
                points = _parse_points_value(next_line)
                label_raw = line
                if points is not None:
                    if normalize_text(label_raw) == "total":
                        rows.append(("total_points", "Total evaluación habilitante", points, f"Total: {points:g}"))
                    else:
                        matched = _match_table_label(label_raw)
                        if matched and matched[0] not in seen_keys:
                            seen_keys.add(matched[0])
                            rows.append((matched[0], matched[1], points, f"{label_raw}: {points:g}"))
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


def _extract_prose_criteria(main_body: str) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
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
            rule = _summarize_section(context)
            rows.append((key, label, points, rule or _snippet(main_body, match.start(), match.end() + 80)))
            break
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
    specs: tuple[tuple[str, str, str, float], ...] = (
        (
            r"descontara un \(1\) punto",
            "ajuste_obras_inconclusas",
            "Descuento por obras inconclusas (RED)",
            -1.0,
        ),
        (
            r"reducir.{0,60}dos \(2\) puntos",
            "ajuste_multas",
            "Descuento por multas o cláusulas penales",
            -2.0,
        ),
    )
    rows: list[tuple[str, str, float, str]] = []
    for pattern, key, label, points in specs:
        match = re.search(pattern, main_body, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
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

    main_body = _evaluation_main_body(normalized)
    if not main_body:
        if re.search(r"calificacion por solvencia.{0,60}puntaje", normalized):
            main_body = normalized[:30_000]
        else:
            return []

    table_rows = _extract_summary_table(main_body)
    if not table_rows:
        table_rows = _extract_prose_criteria(main_body)

    by_key: dict[str, tuple[str, str, float, str]] = {}
    for key, label, points, evidence in table_rows:
        if key == "total_points":
            continue
        by_key[key] = (key, label, points, evidence)

    items: list[RequirementItem] = []
    for key, label, points, evidence in by_key.values():
        rule = _assignment_rule_for_keys(main_body, (key,)) or evidence
        items.append(
            _make_scoring_item(
                key=key,
                label=label,
                max_points=points,
                assignment_rule=rule,
                criterion_type="evaluacion",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.92 if key in {"experiencia", "equipo_trabajo", "industria_nacional"} else 0.88,
            )
        )

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
        prose_total = _extract_total_from_prose(main_body)
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

    for key, label, points, evidence in _extract_point_adjustments(main_body):
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

    for key, label, rule in _extract_desempate_rules(normalized, main_body):
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

    order_map = {key: index for index, key in enumerate(_ITEM_ORDER)}

    def sort_key(item: RequirementItem) -> tuple[int, int, str]:
        value = item.get("value") if isinstance(item.get("value"), dict) else {}
        criterion_type = value.get("criterion_type", "evaluacion")
        type_order = {"evaluacion": 0, "ajuste": 1, "desempate": 2}.get(str(criterion_type), 3)
        if item["key"] == "total_points":
            return (0, 0, "")
        return (type_order, order_map.get(item["key"], 99), item["label"])

    items.sort(key=sort_key)
    if any(item["key"] == "total_points" for item in items):
        total = next(item for item in items if item["key"] == "total_points")
        others = [item for item in items if item["key"] != "total_points"]
        eval_and_adjust = [item for item in others if item["value"].get("criterion_type") != "desempate"]
        desempate = [item for item in others if item["value"].get("criterion_type") == "desempate"]
        items = eval_and_adjust + [total] + desempate

    return items
