"""Residual capacity (K) extraction from obra pública pliegos — §3.11 (US 1.8)."""
from __future__ import annotations

import re
from typing import Any, Optional
from uuid import UUID

from app.services.tender_requirements.regex_extraction import (
    _clean_requirement_text,
    _item,
    _snippet,
    normalize_text,
)

_FACTOR_SCORE_PATTERNS: dict[str, tuple[str, int]] = {
    "factor_experiencia": (r"experiencia\s*\(e\)\s*(\d+)", 120),
    "factor_capacidad_financiera": (r"capacidad financiera\s*\(cf\)\s*(\d+)", 40),
    "factor_capacidad_tecnica": (r"capacidad tecnica\s*\(ct\)\s*(\d+)", 40),
}


def _residual_section_region(normalized: str) -> str:
    matches = list(re.finditer(r"3\.11\.?\s*capacidad residual", normalized))
    if not matches:
        fallback = re.search(r"capacidad residual del proceso de contratacion", normalized)
        if fallback:
            matches = [fallback]
        else:
            return ""

    end_patterns = (
        r"capitulo iv\.?\s*criterios de evaluacion",
        r"4\.\s*capitulo iv",
        r"capitulo iv\.?\s*criterios",
    )
    candidates: list[str] = []
    for match in matches:
        start = match.start()
        tail = normalized[start + 10 :]
        end = len(normalized)
        for pattern in end_patterns:
            boundary = re.search(pattern, tail)
            if boundary:
                end = start + 10 + boundary.start()
                break
        candidates.append(normalized[start:end])

    for region in sorted(candidates, key=len, reverse=True):
        if "crpc" in region or "calculo de la capacidad residual del proceso" in region:
            return region
    return max(candidates, key=len) if candidates else ""


def _has_residual_markers(normalized: str) -> bool:
    if _residual_section_region(normalized):
        return True
    markers = (
        "3.11 capacidad residual",
        "calculo de la capacidad residual del proceso",
        "formato 5 capacidad residual",
        "crp >= crpc",
        "crp ≥ crpc",
    )
    return any(marker in normalized for marker in markers)


def _factor_max_score(region: str, key: str) -> int:
    pattern, default = _FACTOR_SCORE_PATTERNS[key]
    match = re.search(pattern, region)
    if match:
        return int(match.group(1))
    return default


def _crpc_formula_type(region: str) -> str:
    has_short = bool(re.search(r"menor o igual a 12 meses", region))
    has_long = bool(re.search(r"mayor a 12 meses", region))
    if has_short and has_long:
        return "both"
    if has_long:
        return "long_term"
    if has_short:
        return "short_term"
    return "unknown"


def extract_capacidad_residual(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    if not _has_residual_markers(normalized):
        return []

    region = _residual_section_region(normalized) or normalized
    items: list[dict[str, Any]] = []

    habilitante = re.search(
        r"(crp\s*(?:>=|≥)\s*crpc[^.]{0,220})",
        region,
    )
    habilitante_text = (
        _clean_requirement_text(habilitante.group(1), 280)
        if habilitante
        else "El proponente es hábil si CRP ≥ CRPC (capacidad residual del proponente mayor o igual a la del proceso)."
    )
    items.append(
        _item(
            key="residual_summary",
            label="Resumen",
            value={"rule": "crp_gte_crpc"},
            display_value=(
                "La capacidad residual (K de contratación) mide si el oferente puede asumir el contrato "
                "sin que otros compromisos contractuales afecten su cumplimiento. "
                f"Regla habilitante: {habilitante_text}"
            ),
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_snippet(text, 0, min(len(text), 400)),
            confidence=0.9,
        )
    )
    items.append(
        _item(
            key="habilitante_rule",
            label="Regla de habilitación",
            value={"operator": ">=", "left": "CRP", "right": "CRPC"},
            display_value="CRP ≥ CRPC",
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=habilitante_text,
            confidence=0.95,
        )
    )

    formula_type = _crpc_formula_type(region)
    if formula_type in {"short_term", "both"}:
        crpc_display = (
            "Si el plazo estimado es ≤ 12 meses: CRPC = POE − Anticipo (o pago anticipado)."
        )
    elif formula_type == "long_term":
        crpc_display = (
            "Si el plazo estimado es > 12 meses: CRPC = (POE − Anticipo) / Plazo estimado (meses) × 12."
        )
    else:
        crpc_display = (
            "CRPC = POE − Anticipo (plazo ≤ 12 meses) o CRPC = (POE − Anticipo) / Plazo × 12 (plazo > 12 meses)."
        )
    if formula_type == "both":
        crpc_display = (
            "Plazo ≤ 12 meses: CRPC = POE − Anticipo. "
            "Plazo > 12 meses: CRPC = (POE − Anticipo) / Plazo estimado (meses) × 12."
        )

    items.append(
        _item(
            key="crpc_formula",
            label="CRPC exigida por el proceso",
            value={
                "formula_type": formula_type,
                "short_term": "CRPC = POE - Anticipo",
                "long_term": "CRPC = (POE - Anticipo) / Plazo_meses * 12",
            },
            display_value=crpc_display,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_clean_requirement_text(
                re.search(
                    r"(calculo de la capacidad residual del proceso.{0,420})",
                    region,
                ).group(1)
                if re.search(r"calculo de la capacidad residual del proceso", region)
                else region[:280],
                420,
            ),
            confidence=0.92,
        )
    )

    crp_match = re.search(
        r"crp\s*=\s*co\s*\*\s*\[\s*\(\s*e\s*\+\s*ct\s*\+\s*cf\s*\)\s*/\s*100\s*\]\s*-\s*sce",
        region,
    )
    crp_display = (
        "CRP = CO × [(E + CT + CF) / 100] − SCE"
        if crp_match or "co *" in region.replace(" ", "")
        else "CRP = CO × [(E + CT + CF) / 100] − SCE (capacidad residual del proponente)."
    )
    items.append(
        _item(
            key="crp_formula",
            label="Fórmula CRP del proponente",
            value={
                "formula": "CRP = CO * ((E + CT + CF) / 100) - SCE",
            },
            display_value=crp_display,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_clean_requirement_text(
                re.search(
                    r"(calculo de la capacidad residual del proponente.{0,320})",
                    region,
                ).group(1)
                if re.search(r"calculo de la capacidad residual del proponente", region)
                else region[:280],
                360,
            ),
            confidence=0.92,
        )
    )

    factor_specs: tuple[tuple[str, str, str], ...] = (
        (
            "factor_experiencia",
            "Experiencia (E)",
            "Acreditar con Formato 5 — contratos del segmento 72 (construcción) y relación con el POE.",
        ),
        (
            "factor_capacidad_financiera",
            "Capacidad financiera (CF)",
            "Índice de liquidez (Activo corriente / Pasivo corriente); puntaje máximo según tabla del pliego.",
        ),
        (
            "factor_capacidad_tecnica",
            "Capacidad técnica (CT)",
            "Profesionales de arquitectura, ingeniería y geología vinculados; Formato 5.",
        ),
    )
    for key, label, accreditation in factor_specs:
        max_score = _factor_max_score(region, key)
        items.append(
            _item(
                key=key,
                label=label,
                value={"max_score": max_score, "accreditation": accreditation},
                display_value=f"Puntaje máximo: {max_score} pts. {accreditation}",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_clean_requirement_text(
                    re.search(
                        _FACTOR_SCORE_PATTERNS[key][0],
                        region,
                    ).group(0)
                    if re.search(_FACTOR_SCORE_PATTERNS[key][0], region)
                    else f"{label} — máximo {max_score}",
                    200,
                ),
                confidence=0.88,
            )
        )

    co_match = re.search(
        r"capacidad de organizacion \(co\)[^.]{0,280}",
        region,
    )
    co_text = (
        _clean_requirement_text(co_match.group(0), 360)
        if co_match
        else (
            "CO (capacidad de organización) es un multiplicador en pesos; "
            "corresponde a los ingresos operacionales del proponente."
        )
    )
    items.append(
        _item(
            key="factor_organizacion",
            label="Capacidad de organización (CO)",
            value={"role": "multiplier", "unit": "COP"},
            display_value=(
                "CO no tiene puntaje fijo: es un multiplicador en pesos colombianos "
                f"(ingresos operacionales). {co_text}"
            ),
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=co_text,
            confidence=0.86,
        )
    )

    sce_match = re.search(
        r"saldos contratos en ejecucion \(sce\)[^.]{0,320}",
        region,
    )
    sce_text = (
        _clean_requirement_text(sce_match.group(0), 400)
        if sce_match
        else "SCE: suma de montos por ejecutar de contratos vigentes (proporción lineal a 12 meses)."
    )
    items.append(
        _item(
            key="sce",
            label="Contratos en ejecución (SCE)",
            value={"effect": "subtract_from_crp"},
            display_value=(
                "SCE resta al CRP. Incluye montos por ejecutar de contratos de obra civiles "
                "en los 12 meses siguientes (Formato 5)."
            ),
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=sce_text,
            confidence=0.87,
        )
    )

    plural_match = re.search(
        r"crp del proponente plural[^.]{0,320}",
        region,
    )
    if plural_match or "proponente plural" in region:
        plural_text = (
            _clean_requirement_text(plural_match.group(0), 400)
            if plural_match
            else (
                "La CRP del proponente plural es la suma de la capacidad residual de cada integrante "
                "(sin porcentaje de participación)."
            )
        )
        items.append(
            _item(
                key="proponente_plural",
                label="Proponente plural",
                value={"aggregation": "sum_members"},
                display_value=plural_text,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=plural_text,
                confidence=0.85,
            )
        )

    formato_match = re.search(
        r"formato 5[^.]{0,200}capacidad residual",
        region,
    ) or re.search(r"formato 5\s*[-–]\s*capacidad residual", normalized)
    formato_text = (
        _clean_requirement_text(formato_match.group(0), 280)
        if formato_match
        else "Formato 5 — Capacidad residual (diligenciar y firmar según el pliego)."
    )
    items.append(
        _item(
            key="accreditation_formato_5",
            label="Cómo acreditar",
            value={"format": "formato_5", "document": "Formato 5 — Capacidad residual"},
            display_value=(
                "Diligenciar el Formato 5 — Capacidad residual con contratos segmento 72, "
                "profesionales vinculados, saldos en ejecución y firmas del representante legal "
                "(y revisor fiscal o contador, según aplique)."
            ),
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=formato_text,
            confidence=0.9,
        )
    )

    return items
