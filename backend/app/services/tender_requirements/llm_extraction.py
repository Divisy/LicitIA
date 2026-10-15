"""LLM enrichment for tender requirements extraction (US 1.5)."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger
from app.services.tender_requirements.scoring_extraction import (
    _canonical_criterion_key,
    reconcile_sistema_puntos_items,
    sistema_puntos_sum_mismatch,
)

logger = get_logger(__name__)

LLM_EXPERIENCE_SECTIONS: tuple[str, ...] = (
    "experiencia_general",
    "experiencia_especifica",
)

LLM_FINANCIAL_SECTIONS: tuple[str, ...] = ("indicadores_financieros",)

LLM_SCORING_SECTIONS: tuple[str, ...] = ("sistema_puntos",)

LLM_LEGAL_SECTIONS: tuple[str, ...] = ()

LLM_ENRICHED_SECTIONS: tuple[str, ...] = (
    LLM_EXPERIENCE_SECTIONS + LLM_FINANCIAL_SECTIONS + LLM_SCORING_SECTIONS + LLM_LEGAL_SECTIONS
)

_FINANCIAL_LLM_ALLOWED_KEYS: frozenset[str] = frozenset(
    {"financial_summary", "accreditation_method", "financial_exemptions"}
)
_FINANCIAL_REGEX_PRIORITY_KEYS: frozenset[str] = frozenset(
    {
        "liquidez_corriente",
        "endeudamiento",
        "cobertura_intereses",
        "rentabilidad_patrimonio",
        "rentabilidad_activo",
        "capital_trabajo",
        "patrimonio_minimo",
        "matriz_2_reference",
        "qualification_score",
    }
)

_EXPERIENCE_FIELD_GUIDE: dict[str, list[tuple[str, str]]] = {
    "experiencia_general": [
        ("requirement_description", "Tipo de experiencia exigida (2–4 oraciones claras)"),
        ("min_percentage_budget", "Porcentaje mínimo respecto al Presupuesto Oficial"),
        ("time_window_years", "Ventana temporal (ej. últimos N años)"),
        ("min_amount_smmlv", "Monto mínimo en SMMLV, si aplica"),
        ("accreditation_method", "Cómo se acredita (Formato/Matriz/certificado)"),
    ],
    "experiencia_especifica": [
        ("specific_scope", "Alcance de la experiencia específica (2–4 oraciones)"),
        ("specific_area_phases", "Requisitos de área en m² por fase, si aplica (NO % del PO)"),
        ("specific_min_percentage", "Porcentaje mínimo específico del PO (solo si es explícito)"),
        ("activity_codes", "Códigos UNSPSC concretos (6–8 dígitos), no segmentos genéricos"),
        ("contracts_minimum", "Número de contratos para acreditar la específica"),
    ],
}

_FINANCIAL_FIELD_GUIDE: dict[str, list[tuple[str, str]]] = {
    "indicadores_financieros": [
        ("financial_summary", "Resumen de solvencia y capacidad financiera (2–4 oraciones)"),
        ("accreditation_method", "Cómo acreditar (RUP, Formatos, Matriz 2)"),
        ("financial_exemptions", "Excepciones o alternativas de acreditación"),
    ],
}

_SCORING_FIELD_GUIDE: dict[str, list[tuple[str, str]]] = {
    "sistema_puntos": [
        (
            "criterio_evaluacion",
            "Cada criterio con puntaje: key slug, label, max_points, criterion_type=evaluacion",
        ),
        ("total_points", "Fila total de la evaluación habilitante (normalmente 100)"),
        ("ajuste", "Descuentos al puntaje (max_points negativo, criterion_type=ajuste)"),
        ("desempate", "Reglas de desempate (sin puntos, criterion_type=desempate)"),
    ],
}

_LEGAL_FIELD_GUIDE: dict[str, list[tuple[str, str]]] = {
    "requisitos_legales": [
        ("legal_summary", "Resumen de habilitación jurídica (2–4 oraciones claras)"),
        ("rup_vigente", "Inscripción y certificado RUP vigente"),
        ("legal_capacity", "Capacidad jurídica e inhabilidades"),
        ("existence_representation", "Existencia y representación legal"),
        ("redam", "Certificado REDAM"),
        ("fiscal_responsibility", "Responsables fiscales / Contraloría"),
        ("social_security", "Seguridad social y aportes legales"),
        ("plural_proponent", "Proponente plural (UT/consorcio)"),
        ("carta_presentacion", "Carta de presentación (Formato 1)"),
        ("professional_license", "Matrícula profesional si aplica"),
        ("garantia_seriedad", "Garantía de seriedad de la oferta"),
        ("power_of_attorney", "Requisitos del apoderado"),
        ("accreditation_method", "Formatos y documentos para acreditar habilitantes"),
    ],
}

_FIELD_GUIDE: dict[str, list[tuple[str, str]]] = {
    **_EXPERIENCE_FIELD_GUIDE,
    **_FINANCIAL_FIELD_GUIDE,
    **_SCORING_FIELD_GUIDE,
    **_LEGAL_FIELD_GUIDE,
}

_openai_client: Optional[OpenAI] = None
if settings.OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(cleaned)


def _serialize_regex_hints(existing_sections: dict[str, list[dict[str, Any]]]) -> str:
    lines: list[str] = []
    for section_key in LLM_ENRICHED_SECTIONS:
        items = existing_sections.get(section_key) or []
        if not items:
            continue
        lines.append(f"[{section_key}]")
        for item in items:
            label = item.get("label") or item.get("key")
            if section_key == "sistema_puntos":
                value = item.get("value") if isinstance(item.get("value"), dict) else {}
                points = value.get("max_points")
                ctype = value.get("criterion_type", "evaluacion")
                if points is None:
                    display = item.get("display_value") or ctype
                else:
                    display = f"{points:g} pts ({ctype})"
                lines.append(f"- {label}: {display}")
            else:
                display = item.get("display_value") or item.get("value")
                lines.append(f"- {label}: {display}")
    return "\n".join(lines) if lines else "(sin borrador previo)"


def _build_prompt(
    *,
    tender_external_id: str,
    object_text: str,
    experience_excerpt: str,
    financial_excerpt: str,
    scoring_excerpt: str,
    legal_excerpt: str,
    regex_hints: str,
) -> str:
    field_lines: list[str] = []
    for section_key in LLM_ENRICHED_SECTIONS:
        if section_key == "sistema_puntos":
            field_lines.append('  "sistema_puntos": [')
            field_lines.append(
                '    {"key":"oferta_economica", "label":"Oferta económica", "max_points":48.5, '
                '"criterion_type":"evaluacion", "display_value":"48.5 puntos", '
                '"evidence":"...", "confidence":0.9}'
            )
            field_lines.append(
                '    // Incluye TODOS los criterios con puntaje, total_points, ajustes y desempate'
            )
            field_lines.append("  ],")
            continue
        fields = _FIELD_GUIDE[section_key]
        field_lines.append(f'  "{section_key}": [')
        for key, description in fields:
            field_lines.append(
                f'    {{"key":"{key}", "label":"...", "display_value":"...", '
                f'"evidence":"...", "confidence":0.0-1.0, "source_document":"pliego_condiciones"}} '
                f"// {description}"
            )
        field_lines.append("  ],")

    schema = "{\n  \"sections\": {\n" + "\n".join(field_lines) + "\n  }\n}"

    context_parts: list[str] = []
    if experience_excerpt.strip():
        context_parts.append(f"Experiencia:\n{experience_excerpt}")
    if financial_excerpt.strip():
        context_parts.append(f"Solvencia financiera:\n{financial_excerpt}")
    if scoring_excerpt.strip():
        context_parts.append(f"Sistema de puntos / evaluación habilitante:\n{scoring_excerpt}")
    if legal_excerpt.strip():
        context_parts.append(f"Habilitación jurídica:\n{legal_excerpt}")
    context_block = "\n\n".join(context_parts) if context_parts else "(sin extracto)"

    return (
        f"Licitación: {tender_external_id}\n"
        f"Objeto del contrato: {object_text}\n\n"
        f"Texto del pliego (extractos relevantes):\n{context_block}\n\n"
        f"Borrador automático previo (puede contener texto crudo del PDF — no copies tal cual):\n"
        f"{regex_hints}\n\n"
        f"Analiza el pliego y devuelve JSON con este esquema:\n{schema}\n\n"
        "Reglas obligatorias:\n"
        "- display_value: redacción clara y profesional para un contratista (español de Colombia). "
        "Resume y estructura; NO pegues párrafos largos ni texto con errores de OCR.\n"
        "- requirement_description / specific_scope / financial_summary: explica QUÉ se exige "
        "en pocas oraciones completas.\n"
        "- evidence: cita literal breve del pliego (máx. 200 caracteres) que respalde cada campo.\n"
        "- Solo incluye campos explícitos en el texto. Omite keys sin información.\n"
        "- confidence 0.70–1.0 según claridad del fragmento.\n"
        "- Porcentajes: formato legible (ej. \"100% del Presupuesto Oficial\", \"60% del PO\").\n"
        "- experiencia_especifica: NO uses la tabla de valor mínimo por número de contratos "
        "(75/120/150% del PO en SMMLV); esa tabla es de experiencia general. "
        "Si la específica exige área en m² o % del área del proyecto, usa specific_area_phases.\n"
        "- indicadores_financieros: NO inventes umbrales numéricos (liquidez, endeudamiento, etc.); "
        "solo redacta financial_summary, accreditation_method y financial_exemptions.\n"
        "- sistema_puntos: localiza la sección de criterios de evaluación y asignación de puntaje "
        "(puede estar en cualquier capítulo del pliego, no siempre es el IV). Extrae la tabla "
        "«Concepto | Puntaje máximo» y las subsecciones numeradas (4.x, 5.x, etc.). "
        "Devuelve un ítem por cada criterio con max_points numérico. "
        "Incluye total_points con key exacta \"total_points\". "
        "Los ajustes (descuentos) van con criterion_type=ajuste y max_points negativo. "
        "Las reglas de desempate van con criterion_type=desempate y max_points null. "
        "NO incluyas encabezados de página, versiones del documento ni texto legal ajeno al puntaje. "
        "La suma de criterios de evaluación debe coincidir con total_points.\n"
        "- requisitos_legales: lista cada habilitante jurídico explícito del pliego "
        "(RUP, capacidad jurídica, existencia/representación, REDAM, seguridad social, "
        "Formato 1/2/5, garantía de seriedad, etc.). NO inventes requisitos no mencionados.\n"
        "- Si el borrador previo tiene un dato correcto pero mal redactado, mejóralo en display_value."
    )


def _accept_llm_items(
    section_key: str,
    llm_items: list[dict[str, Any]],
    *,
    min_confidence: float,
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw in llm_items or []:
        key = raw.get("key") or f"llm_{section_key}_{len(accepted)}"
        if section_key == "indicadores_financieros" and key not in _FINANCIAL_LLM_ALLOWED_KEYS:
            continue
        confidence = float(raw.get("confidence", 0))
        if confidence < min_confidence:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        accepted.append(
            {
                "key": key,
                "label": raw.get("label") or "Requisito detectado",
                "value": raw.get("display_value"),
                "display_value": raw.get("display_value"),
                "confidence": confidence,
                "source_document": raw.get("source_document") or "pliego_condiciones",
                "source_document_id": None,
                "evidence": raw.get("evidence"),
                "extraction_method": "llm",
            }
        )
    return accepted


def _merge_with_regex_fallback(
    llm_items: list[dict[str, Any]],
    regex_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer LLM items; keep regex-only keys the model did not return."""
    if not llm_items:
        return regex_items
    llm_keys = {item["key"] for item in llm_items}
    merged = list(llm_items)
    for item in regex_items:
        if item["key"] not in llm_keys:
            merged.append(item)
    return merged


def _merge_financial_with_regex_priority(
    llm_items: list[dict[str, Any]],
    regex_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer regex for numeric indicators; LLM for narrative fields."""
    regex_by_key = {item["key"]: item for item in regex_items}
    llm_by_key = {item["key"]: item for item in llm_items}
    merged_keys = set(regex_by_key) | set(llm_by_key)
    merged: list[dict[str, Any]] = []
    for key in sorted(merged_keys):
        if key in _FINANCIAL_REGEX_PRIORITY_KEYS:
            if key in regex_by_key:
                merged.append(regex_by_key[key])
            elif key in llm_by_key:
                merged.append(llm_by_key[key])
        elif key in llm_by_key:
            merged.append(llm_by_key[key])
        elif key in regex_by_key:
            merged.append(regex_by_key[key])
    return merged


_PO_TIER_PERCENTAGES = {75.0, 120.0, 150.0}


def sanitize_experiencia_especifica_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop PO tier-table fields incorrectly assigned to experiencia específica."""
    has_area_phases = any(item.get("key") == "specific_area_phases" for item in items)
    sanitized: list[dict[str, Any]] = []
    for item in items:
        key = item.get("key")
        display = str(item.get("display_value") or "").lower()
        value = item.get("value")

        if key == "specific_min_percentage":
            if has_area_phases:
                continue
            if "segun nº de contratos" in display or "según nº de contratos" in display:
                continue
            if isinstance(value, (int, float)) and float(value) in _PO_TIER_PERCENTAGES:
                if "presupuesto oficial" in display and "area" not in display and "m2" not in display:
                    continue

        if key == "contracts_minimum" and has_area_phases:
            if "cinco" in display or "maximo 5" in display or "máximo 5" in display:
                continue

        if key == "activity_codes" and has_area_phases:
            if re.search(r"\[?\s*72\s*\]?\s*y\s*\[?\s*81\s*\]?", display, re.IGNORECASE):
                continue
            if display.strip() in {"72", "81", "72, 81"}:
                continue

        sanitized.append(item)
    return sanitized


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


def _accept_scoring_llm_items(
    llm_items: list[dict[str, Any]],
    *,
    min_confidence: float,
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw in llm_items or []:
        confidence = float(raw.get("confidence", 0))
        if confidence < min_confidence:
            continue
        key = str(raw.get("key") or f"llm_criterio_{len(accepted)}")
        if key in seen_keys:
            continue
        label = raw.get("label") or "Criterio de evaluación"
        criterion_type = str(raw.get("criterion_type") or "evaluacion")
        max_points: Optional[float]
        if raw.get("max_points") is None:
            max_points = None
        else:
            try:
                max_points = float(raw["max_points"])
            except (TypeError, ValueError):
                max_points = None

        if key == "total_points":
            criterion_type = "evaluacion"
            if max_points is None:
                continue
        elif criterion_type == "desempate":
            max_points = None
        elif criterion_type == "ajuste":
            if max_points is None or max_points >= 0:
                continue
        elif max_points is None:
            continue

        display = raw.get("display_value")
        if not display:
            if max_points is None:
                display = "Desempate"
            elif max_points < 0:
                display = f"{max_points:g} pts"
            else:
                display = f"{max_points:g} puntos"

        seen_keys.add(key)
        accepted.append(
            {
                "key": key,
                "label": label,
                "value": {
                    "max_points": max_points,
                    "assignment_rule": "",
                    "criterion_type": criterion_type,
                },
                "display_value": display,
                "confidence": confidence,
                "source_document": raw.get("source_document") or "pliego_condiciones",
                "source_document_id": None,
                "evidence": raw.get("evidence"),
                "extraction_method": "llm",
            }
        )
    return accepted


def _merge_scoring_with_regex_priority(
    llm_items: list[dict[str, Any]],
    regex_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer LLM criteria list; keep regex max_points when both agree on the same criterion."""
    if not llm_items:
        return regex_items
    if not regex_items:
        return llm_items

    llm_eval = [
        item
        for item in llm_items
        if _scoring_criterion_type(item) == "evaluacion" and item["key"] != "total_points"
    ]
    if not llm_eval:
        return regex_items

    regex_eval: dict[str, dict[str, Any]] = {}
    for item in regex_items:
        if _scoring_criterion_type(item) != "evaluacion" or item["key"] == "total_points":
            continue
        canonical = _canonical_criterion_key(item["key"], str(item.get("label") or ""))
        regex_eval[canonical] = item

    merged_eval: list[dict[str, Any]] = []
    seen_canonical: set[str] = set()
    for llm_item in llm_eval:
        item = dict(llm_item)
        canonical = _canonical_criterion_key(item["key"], str(item.get("label") or ""))
        regex_match = regex_eval.get(canonical)
        if regex_match is not None:
            regex_points = _scoring_item_points(regex_match)
            if regex_points is not None:
                value = dict(item.get("value") or {})
                value["max_points"] = regex_points
                value["criterion_type"] = "evaluacion"
                item["value"] = value
                item["display_value"] = (
                    f"{regex_points:g} pts" if regex_points < 0 else f"{regex_points:g} puntos"
                )
                item["extraction_method"] = "hybrid"
        merged_eval.append(item)
        seen_canonical.add(canonical)

    regex_only: list[dict[str, Any]] = []
    for canonical, regex_item in regex_eval.items():
        if canonical in seen_canonical:
            continue
        regex_only.append(dict(regex_item))
    regex_only.sort(
        key=lambda item: int((item.get("value") or {}).get("sort_order", 99))
    )
    merged_eval.extend(regex_only)

    regex_total = next((item for item in regex_items if item["key"] == "total_points"), None)
    llm_total = next((item for item in llm_items if item["key"] == "total_points"), None)
    total_item = regex_total or llm_total

    llm_secondary = [
        item
        for item in llm_items
        if _scoring_criterion_type(item) in {"ajuste", "desempate"}
    ]
    if not llm_secondary:
        llm_secondary = [
            item
            for item in regex_items
            if _scoring_criterion_type(item) in {"ajuste", "desempate"}
        ]

    merged: list[dict[str, Any]] = list(merged_eval)
    if total_item:
        merged.append(total_item)
    merged.extend(llm_secondary)
    return merged


def enrich_requirements_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    financial_context_excerpt: str = "",
    scoring_context_excerpt: str = "",
    legal_context_excerpt: str = "",
    existing_sections: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Refine experience, financial, scoring and legal requirements with gpt-4o-mini."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return existing_sections

    experience_excerpt = (context_excerpt or "").strip()
    financial_excerpt = (financial_context_excerpt or "").strip()
    scoring_excerpt = (scoring_context_excerpt or "").strip()
    legal_excerpt = (legal_context_excerpt or "").strip()
    if not any((experience_excerpt, financial_excerpt, scoring_excerpt, legal_excerpt)):
        return existing_sections

    max_chars = settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS
    active_excerpts = sum(
        1
        for excerpt in (experience_excerpt, financial_excerpt, scoring_excerpt, legal_excerpt)
        if excerpt
    )
    budget = max_chars // active_excerpts if active_excerpts > 1 else max_chars
    regex_hints = _serialize_regex_hints(existing_sections)
    prompt = _build_prompt(
        tender_external_id=tender_external_id,
        object_text=object_text or "",
        experience_excerpt=experience_excerpt[:budget],
        financial_excerpt=financial_excerpt[:budget],
        scoring_excerpt=scoring_excerpt[:budget],
        legal_excerpt=legal_excerpt[:budget],
        regex_hints=regex_hints,
    )

    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista senior de licitaciones públicas colombianas (SECOP). "
                        "Interpretas pliegos de condiciones y redactas requisitos de habilitación "
                        "de forma clara para empresas constructoras e interventoras. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=3500,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
        llm_sections = payload.get("sections", {})
    except Exception as exc:
        logger.warning("LLM requirements enrichment failed for %s: %s", tender_external_id, exc)
        return existing_sections

    merged = dict(existing_sections)
    min_confidence = settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE

    for section_key in LLM_EXPERIENCE_SECTIONS:
        accepted = _accept_llm_items(
            section_key,
            llm_sections.get(section_key, []),
            min_confidence=min_confidence,
        )
        regex_items = existing_sections.get(section_key, [])
        merged[section_key] = _merge_with_regex_fallback(accepted, regex_items)

    for section_key in LLM_FINANCIAL_SECTIONS:
        accepted = _accept_llm_items(
            section_key,
            llm_sections.get(section_key, []),
            min_confidence=min_confidence,
        )
        regex_items = existing_sections.get(section_key, [])
        merged[section_key] = _merge_financial_with_regex_priority(accepted, regex_items)

    for section_key in LLM_SCORING_SECTIONS:
        accepted = _accept_scoring_llm_items(
            llm_sections.get(section_key, []),
            min_confidence=min_confidence,
        )
        regex_items = existing_sections.get(section_key, [])
        merged[section_key] = _merge_scoring_with_regex_priority(accepted, regex_items)

    for section_key in LLM_LEGAL_SECTIONS:
        accepted = _accept_llm_items(
            section_key,
            llm_sections.get(section_key, []),
            min_confidence=min_confidence,
        )
        regex_items = existing_sections.get(section_key, [])
        merged[section_key] = _merge_with_regex_fallback(accepted, regex_items)

    return merged


def _build_scoring_fallback_prompt(
    *,
    tender_external_id: str,
    object_text: str,
    scoring_excerpt: str,
) -> str:
    schema = (
        '{\n'
        '  "sistema_puntos": [\n'
        '    {"key":"experiencia", "label":"Experiencia del proponente", "max_points":40, '
        '"criterion_type":"evaluacion", "display_value":"40 puntos", '
        '"evidence":"...", "confidence":0.92},\n'
        '    {"key":"total_points", "label":"Total evaluación habilitante", "max_points":100, '
        '"criterion_type":"evaluacion", "display_value":"100 puntos", '
        '"evidence":"...", "confidence":0.95}\n'
        "  ]\n"
        "}"
    )
    return (
        f"Licitación: {tender_external_id}\n"
        f"Objeto: {object_text or '(no indicado)'}\n\n"
        f"Fragmento del pliego (criterios de evaluación y puntaje):\n{scoring_excerpt}\n\n"
        f"Devuelve JSON con este esquema:\n{schema}\n\n"
        "Reglas obligatorias:\n"
        "- Localiza la TABLA RESUMEN de criterios de evaluación con sus puntajes máximos "
        "(puede decir «Concepto», «Criterio de evaluación» o «Puntaje máximo», y filas "
        "tipo «40 puntos» o número en línea aparte).\n"
        "- Un ítem por cada criterio de evaluación con max_points numérico explícito en el texto.\n"
        "- Incluye total_points con key exacta \"total_points\" y el total declarado en el pliego.\n"
        "- Los descuentos opcionales van con criterion_type=ajuste y max_points negativo.\n"
        "- Las reglas de desempate van con criterion_type=desempate y max_points null.\n"
        "- La suma de criterios de evaluación (sin total_points) DEBE coincidir con total_points.\n"
        "- NO inventes criterios ni puntajes que no aparezcan en el fragmento.\n"
        "- NO incluyas texto legal del decreto 1082 ni requisitos de experiencia sin puntaje.\n"
        "- evidence: cita literal breve (máx. 200 caracteres) del fragmento.\n"
        "- confidence 0.75–1.0 según claridad."
    )


def extract_scoring_fallback_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    scoring_excerpt: str,
) -> list[dict[str, Any]]:
    """Dedicated scoring-only LLM pass when regex/hybrid reconciliation fails."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM:
        return []
    if not settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK:
        return []
    if not _openai_client or not scoring_excerpt.strip():
        return []

    prompt = _build_scoring_fallback_prompt(
        tender_external_id=tender_external_id,
        object_text=object_text,
        scoring_excerpt=scoring_excerpt[: settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK_MAX_CHARS],
    )

    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista senior de licitaciones públicas colombianas (SECOP). "
                        "Extraes tablas de criterios de evaluación y puntaje con precisión numérica. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
        sections_payload = payload.get("sections")
        if isinstance(sections_payload, dict):
            raw_items = sections_payload.get("sistema_puntos") or []
        else:
            raw_items = payload.get("sistema_puntos") or payload.get("items") or []
    except Exception as exc:
        logger.warning(
            "LLM scoring fallback failed for %s: %s",
            tender_external_id,
            exc,
        )
        return []

    min_confidence = max(settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE, 0.75)
    accepted = _accept_scoring_llm_items(raw_items, min_confidence=min_confidence)
    if not accepted:
        return []

    for item in accepted:
        item["extraction_method"] = "llm_fallback"

    reconciled = reconcile_sistema_puntos_items(accepted, regex_items=None)
    if sistema_puntos_sum_mismatch(reconciled):
        logger.info(
            "LLM scoring fallback for %s still mismatched total; discarding",
            tender_external_id,
        )
        return []

    return reconciled


_GENERAL_EXPERIENCE_KEYS = (
    "requirement_description",
    "min_percentage_budget",
    "min_amount_smmlv",
    "time_window_years",
    "company_duration",
    "contracts_minimum",
    "experience_value_tiers",
)

# The year's salary was copied into an SMMLV column elsewhere. It is not a pliego minimum.
_SALARY_COPIED_AS_SMMLV = 81510.0


def _unwrap_general_experience_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if any(key in payload for key in _GENERAL_EXPERIENCE_KEYS):
        return payload
    nested = payload.get("experiencia_general")
    if isinstance(nested, dict):
        return nested
    return payload


def _bounded_number(value: Any, low: float, high: float) -> Optional[float]:
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace(" ", "").replace(",", ".")
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not low <= number <= high:
        return None
    return number


def _contract_range(value: Any) -> Optional[str]:
    numbers = re.findall(r"\d{1,2}", str(value or ""))
    if len(numbers) != 2:
        return None
    start, end = int(numbers[0]), int(numbers[1])
    if start <= 0 or end < start or end > 20:
        return None
    return f"{start}-{end}"


def _clean_evidence(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > 200:
        return text[:197] + "..."
    return text


def _fold_pliego_text(value: str) -> str:
    folded = value.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
    return re.sub(r"\s+", " ", folded)


def _company_duration_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) > 600:
        text = text[:597] + "..."
    if len(text) < 20:
        return None
    return text


def _years_belong_to_company_life(evidence: str, duration: str) -> bool:
    """Years added to the company's life are not the experience window."""
    sample = _fold_pliego_text(f"{evidence} {duration}")
    if re.search(r"ultim\w*\s+\d+\s+anos", sample):
        return False
    return any(
        phrase in sample
        for phrase in (
            "persona juridica",
            "liquidacion",
            "anos mas",
            "termino de duracion",
            "duracion de la sociedad",
            "duracion de la persona",
        )
    )


def parse_general_experience_llm_payload(payload: Any) -> dict[str, Any]:
    """Keep only general-experience fields the model actually returned as usable values."""
    raw = _unwrap_general_experience_payload(payload)
    evidence_raw = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
    parsed: dict[str, Any] = {}
    evidence: dict[str, str] = {}

    description = raw.get("requirement_description")
    if isinstance(description, str):
        text = re.sub(r"\s+", " ", description).strip()
        if len(text) > 4000:
            text = text[:3997] + "..."
        if len(text) >= 15:
            parsed["requirement_description"] = text
            evidence["requirement_description"] = _clean_evidence(evidence_raw.get("requirement_description"))

    percentage = _bounded_number(raw.get("min_percentage_budget"), 1, 300)
    if percentage is not None:
        parsed["min_percentage_budget"] = percentage
        evidence["min_percentage_budget"] = _clean_evidence(evidence_raw.get("min_percentage_budget"))

    amount = _bounded_number(raw.get("min_amount_smmlv"), 1, 50_000)
    if amount is not None and abs(amount - _SALARY_COPIED_AS_SMMLV) >= 1 and abs(amount - 81.51) >= 0.02:
        parsed["min_amount_smmlv"] = amount
        evidence["min_amount_smmlv"] = _clean_evidence(evidence_raw.get("min_amount_smmlv"))

    duration = _company_duration_text(raw.get("company_duration"))
    years = _bounded_number(raw.get("time_window_years"), 1, 25)
    years_evidence = _clean_evidence(evidence_raw.get("time_window_years"))
    if years is not None and _years_belong_to_company_life(years_evidence, duration or ""):
        if duration is None:
            duration = _company_duration_text(years_evidence)
        years = None
    if duration is not None:
        parsed["company_duration"] = duration
        evidence["company_duration"] = _clean_evidence(evidence_raw.get("company_duration")) or duration[:200]
    if years is not None:
        parsed["time_window_years"] = int(years)
        evidence["time_window_years"] = years_evidence

    contracts = raw.get("contracts_minimum")
    if isinstance(contracts, dict):
        minimum = _bounded_number(contracts.get("minimum"), 1, 20)
        maximum = _bounded_number(contracts.get("maximum"), 1, 20)
        if minimum is not None:
            value: dict[str, int] = {"minimum": int(minimum)}
            if maximum is not None and maximum >= minimum:
                value["maximum"] = int(maximum)
            parsed["contracts_minimum"] = value
            evidence["contracts_minimum"] = _clean_evidence(evidence_raw.get("contracts_minimum"))
    else:
        only_minimum = _bounded_number(contracts, 1, 20)
        if only_minimum is not None:
            parsed["contracts_minimum"] = {"minimum": int(only_minimum)}
            evidence["contracts_minimum"] = _clean_evidence(evidence_raw.get("contracts_minimum"))

    tiers_raw = raw.get("experience_value_tiers")
    tiers: list[dict[str, Any]] = []
    seen_ranges: set[str] = set()
    if isinstance(tiers_raw, list):
        for tier in tiers_raw:
            if not isinstance(tier, dict):
                continue
            contract_range = _contract_range(tier.get("contract_range"))
            tier_percentage = _bounded_number(tier.get("percentage"), 1, 300)
            if contract_range is None or tier_percentage is None or contract_range in seen_ranges:
                continue
            seen_ranges.add(contract_range)
            tiers.append({"contract_range": contract_range, "percentage": tier_percentage})
    if tiers:
        parsed["experience_value_tiers"] = tiers
        evidence["experience_value_tiers"] = _clean_evidence(evidence_raw.get("experience_value_tiers"))

    if evidence:
        parsed["evidence"] = evidence
    return parsed


def _general_experience_prompt(tender_external_id: str, excerpt: str) -> str:
    return (
        f"Licitación: {tender_external_id}\n\n"
        "Fragmento de experiencia general del pliego:\n"
        f"{excerpt}\n\n"
        "Devuelve únicamente este JSON, con null en cada dato que el fragmento no escriba:\n"
        "{\n"
        '  "requirement_description": null,\n'
        '  "min_percentage_budget": null,\n'
        '  "min_amount_smmlv": null,\n'
        '  "time_window_years": null,\n'
        '  "company_duration": null,\n'
        '  "contracts_minimum": null,\n'
        '  "experience_value_tiers": null,\n'
        '  "evidence": {}\n'
        "}\n\n"
        "Reglas:\n"
        "- Lee solo la experiencia general. Ignora experiencia específica, indicadores, puntaje y requisitos legales.\n"
        "- Devuelve siempre las claves. Si el pliego escribe el párrafo, el porcentaje, el monto en SMMLV, la ventana, la duración de la persona jurídica, el número de contratos y la tabla, guarda cada uno. No pongas null en una clave porque otra ya tenga valor.\n"
        "- Si un dato no está escrito en el fragmento, pon null. No completes con un porcentaje, una ventana o un número de contratos habitual.\n"
        "- min_percentage_budget es un número. min_amount_smmlv es un número de SMMLV solo cuando el pliego escribe la cifra. "
        "La frase «expresado en SMMLV» sin cifra va null.\n"
        "- time_window_years es el entero de años solo cuando los contratos de la experiencia deben haberse ejecutado o terminado en los últimos N años.\n"
        "- company_duration copia la frase de cuánto debe durar la persona jurídica. "
        "«Cinco (5) años más» después del plazo del contrato y su liquidación es duración de la empresa, no time_window_years.\n"
        "- contracts_minimum lleva minimum y maximum solo si el texto los dice.\n"
        "- experience_value_tiers solo cuando el porcentaje del presupuesto cambia según el número de contratos. "
        "contract_range con la forma mínimo-máximo, por ejemplo 1-2.\n"
        "- requirement_description es la copia literal del apartado de experiencia general, no un resumen.\n"
        "- contracts_minimum sale solo de la frase que dice cuántos contratos se presentan. "
        "Un número de códigos del RUP no es el máximo de contratos.\n"
        "- Un valor en pesos no es min_amount_smmlv.\n"
        "- evidence cita como máximo 200 caracteres del fragmento por campo presente."
    )


def _general_experience_vision_prompt(tender_external_id: str) -> str:
    return (
        f"Licitación: {tender_external_id}\n\n"
        "Las imágenes son las páginas del apartado de experiencia general del pliego. "
        "El texto interno del PDF puede estar dañado. Lee lo que está impreso.\n\n"
        "Devuelve únicamente este JSON, con null en cada dato que esas páginas no escriban:\n"
        "{\n"
        '  "requirement_description": null,\n'
        '  "min_percentage_budget": null,\n'
        '  "min_amount_smmlv": null,\n'
        '  "time_window_years": null,\n'
        '  "company_duration": null,\n'
        '  "contracts_minimum": null,\n'
        '  "experience_value_tiers": null,\n'
        '  "evidence": {}\n'
        "}\n\n"
        "Reglas:\n"
        "- requirement_description copia tal cual el apartado «Experiencia general habilitante del proponente», "
        "con el número de contratos y el objeto entre comillas. No lo resumas. Ignora membrete, correo, teléfono y pie de página.\n"
        "- Devuelve las claves. No pongas null en una porque otra ya tenga valor.\n"
        "- Si un dato no está impreso en esas páginas, pon null.\n"
        "- contracts_minimum sale de la frase que dice cuántos contratos o certificaciones se presentan, "
        "por ejemplo uno (1) o hasta dos (2). Un «cinco (5)» de códigos del RUP no es el máximo de contratos.\n"
        "- min_percentage_budget es un número. min_amount_smmlv es un número de SMMLV solo cuando la página de experiencia general escribe la cifra. "
        "«Expresado en SMMLV» sin cifra, un valor en pesos y el monto de la experiencia específica van null.\n"
        "- time_window_years es el entero de años solo cuando los contratos de la experiencia deben haberse ejecutado o terminado en los últimos N años.\n"
        "- company_duration copia la frase de cuánto debe durar la persona jurídica, por ejemplo el plazo del contrato, su liquidación y cinco (5) años más. "
        "Esos años no son time_window_years.\n"
        "- experience_value_tiers solo cuando el porcentaje cambia según el número de contratos.\n"
        "- evidence cita como máximo 200 caracteres de lo impreso por campo presente."
    )


def extract_general_experience_with_llm(
    *,
    tender_external_id: str,
    excerpt: str,
) -> Optional[dict[str, Any]]:
    """One general-experience reading. None means the call failed and the caller should retry."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return None
    fragment = (excerpt or "").strip()
    if not fragment:
        return None
    fragment = fragment[: settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS]
    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de pliegos de condiciones de Colombia. "
                        "Extraes solo la experiencia general que el texto escribe. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": _general_experience_prompt(tender_external_id, fragment)},
            ],
            temperature=0,
            max_tokens=900,
            timeout=45,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("General experience LLM failed for %s: %s", tender_external_id, exc)
        return None
    return parse_general_experience_llm_payload(payload)


def extract_general_experience_from_page_images(
    *,
    tender_external_id: str,
    page_images: list[bytes],
) -> Optional[dict[str, Any]]:
    """Read the printed general-experience pages. None means the call failed."""
    import base64

    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return None
    images = [image for image in page_images if image][:3]
    if not images:
        return None
    content: list[dict[str, Any]] = [
        {"type": "text", "text": _general_experience_vision_prompt(tender_external_id)}
    ]
    for image in images:
        encoded = base64.b64encode(image).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}", "detail": "high"},
            }
        )
    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de pliegos de condiciones de Colombia. "
                        "Copias la experiencia general tal como está impresa en las páginas. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": content},
            ],
            temperature=0,
            max_tokens=2200,
            timeout=60,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("General experience vision failed for %s: %s", tender_external_id, exc)
        return None
    return parse_general_experience_llm_payload(payload)
