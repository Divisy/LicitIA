"""LLM enrichment for tender requirements extraction (US 1.5)."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

LLM_EXPERIENCE_SECTIONS: tuple[str, ...] = (
    "experiencia_general",
    "experiencia_especifica",
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
    for section_key in LLM_EXPERIENCE_SECTIONS:
        items = existing_sections.get(section_key) or []
        if not items:
            continue
        lines.append(f"[{section_key}]")
        for item in items:
            label = item.get("label") or item.get("key")
            display = item.get("display_value") or item.get("value")
            lines.append(f"- {label}: {display}")
    return "\n".join(lines) if lines else "(sin borrador previo)"


def _build_prompt(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    regex_hints: str,
) -> str:
    field_lines: list[str] = []
    for section_key in LLM_EXPERIENCE_SECTIONS:
        fields = _EXPERIENCE_FIELD_GUIDE[section_key]
        field_lines.append(f'  "{section_key}": [')
        for key, description in fields:
            field_lines.append(
                f'    {{"key":"{key}", "label":"...", "display_value":"...", '
                f'"evidence":"...", "confidence":0.0-1.0, "source_document":"pliego_condiciones"}} '
                f"// {description}"
            )
        field_lines.append("  ],")

    schema = "{\n  \"sections\": {\n" + "\n".join(field_lines) + "\n  }\n}"

    return (
        f"Licitación: {tender_external_id}\n"
        f"Objeto del contrato: {object_text}\n\n"
        f"Texto del pliego (sección de experiencia):\n{context_excerpt}\n\n"
        f"Borrador automático previo (puede contener texto crudo del PDF — no copies tal cual):\n"
        f"{regex_hints}\n\n"
        f"Analiza el pliego y devuelve JSON con este esquema:\n{schema}\n\n"
        "Reglas obligatorias:\n"
        "- display_value: redacción clara y profesional para un contratista (español de Colombia). "
        "Resume y estructura; NO pegues párrafos largos ni texto con errores de OCR.\n"
        "- requirement_description / specific_scope: explica QUÉ experiencia se exige "
        "(tipo de obra/interventoría, actividades, umbrales) en pocas oraciones completas.\n"
        "- evidence: cita literal breve del pliego (máx. 200 caracteres) que respalde cada campo.\n"
        "- Solo incluye campos explícitos en el texto. Omite keys sin información.\n"
        "- confidence 0.70–1.0 según claridad del fragmento.\n"
        "- Porcentajes: formato legible (ej. \"100% del Presupuesto Oficial\", \"60% del PO\").\n"
        "- experiencia_especifica: NO uses la tabla de valor mínimo por número de contratos "
        "(75/120/150% del PO en SMMLV); esa tabla es de experiencia general. "
        "Si la específica exige área en m² o % del área del proyecto, usa specific_area_phases.\n"
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
        confidence = float(raw.get("confidence", 0))
        if confidence < min_confidence:
            continue
        key = raw.get("key") or f"llm_{section_key}_{len(accepted)}"
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


def enrich_requirements_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    existing_sections: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Refine experience requirements with gpt-4o-mini (replaces raw regex dumps when possible)."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return existing_sections

    excerpt = (context_excerpt or "").strip()
    if not excerpt:
        return existing_sections

    max_chars = settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS
    regex_hints = _serialize_regex_hints(existing_sections)
    prompt = _build_prompt(
        tender_external_id=tender_external_id,
        object_text=object_text or "",
        context_excerpt=excerpt[:max_chars],
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
                        "Interpretas pliegos de condiciones y redactas requisitos de experiencia "
                        "de forma clara para empresas constructoras e interventoras. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
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

    return merged
