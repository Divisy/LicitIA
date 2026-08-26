"""Optional LLM enrichment for tender requirements extraction (US 1.5)."""
from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

LLM_EXPERIENCE_SECTIONS: tuple[str, ...] = (
    "experiencia_general",
    "experiencia_especifica",
)

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


def _sections_needing_llm(existing_sections: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Return experience sections where regex did not extract anything."""
    return [
        key
        for key in LLM_EXPERIENCE_SECTIONS
        if len(existing_sections.get(key, [])) < 1
    ]


def _build_prompt(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    target_sections: list[str],
) -> str:
    section_schema = ",\n    ".join(
        f'"{key}": [{{"key":"...", "label":"...", "display_value":"...", "evidence":"...", "confidence":0.0-1.0}}]'
        for key in target_sections
    )
    return f"""Licitación: {tender_external_id}
Objeto: {object_text}

Texto relevante (experiencia general y específica):
{context_excerpt}

Extrae únicamente requisitos de participación relacionados con experiencia en JSON:
{{
  "sections": {{
    {section_schema}
  }}
}}

Reglas:
- Solo incluye hechos explícitos en el texto (porcentajes, SMMLV, contratos, alcance).
- confidence entre 0.70 y 1.0 según claridad del fragmento.
- evidence: cita breve del pliego (máx. 200 caracteres).
- key sugeridos experiencia_general: min_percentage_budget, time_window_years, requirement_description, smmlv_minimum.
- key sugeridos experiencia_especifica: specific_scope, specific_min_percentage, contracts_minimum.
- Español."""


def _accept_llm_items(
    section_key: str,
    llm_items: list[dict[str, Any]],
    *,
    min_confidence: float,
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    for raw in llm_items or []:
        confidence = float(raw.get("confidence", 0))
        if confidence < min_confidence:
            continue
        accepted.append(
            {
                "key": raw.get("key") or f"llm_{section_key}",
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


def enrich_requirements_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    existing_sections: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Fill missing experience requirements using gpt-4o-mini when regex is sparse."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return existing_sections

    target_sections = _sections_needing_llm(existing_sections)
    if not target_sections:
        return existing_sections

    excerpt = (context_excerpt or "").strip()
    if not excerpt:
        return existing_sections

    max_chars = settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS
    prompt = _build_prompt(
        tender_external_id=tender_external_id,
        object_text=object_text or "",
        context_excerpt=excerpt[:max_chars],
        target_sections=target_sections,
    )

    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de licitaciones públicas colombianas. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
        llm_sections = payload.get("sections", {})
    except Exception as exc:
        logger.warning("LLM requirements enrichment failed for %s: %s", tender_external_id, exc)
        return existing_sections

    merged = dict(existing_sections)
    min_confidence = settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE

    for section_key in target_sections:
        if merged.get(section_key):
            continue
        accepted = _accept_llm_items(
            section_key,
            llm_sections.get(section_key, []),
            min_confidence=min_confidence,
        )
        if accepted:
            merged[section_key] = accepted

    return merged
