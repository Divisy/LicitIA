"""Optional LLM enrichment for tender requirements extraction (US 1.5)."""
from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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


def enrich_requirements_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    pliego_excerpt: str,
    anexo_excerpt: str,
    existing_sections: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Fill missing requirement items using OpenAI when regex extraction is sparse."""
    if not settings.TENDER_REQUIREMENTS_USE_LLM or not _openai_client:
        return existing_sections

    sparse_sections = [
        key
        for key, items in existing_sections.items()
        if len(items) < 1 and key != "otros"
    ]
    if not sparse_sections:
        return existing_sections

    prompt = f"""Licitación: {tender_external_id}
Objeto: {object_text}

Texto pliego (extracto):
{pliego_excerpt[:12000]}

Texto anexo (extracto):
{anexo_excerpt[:12000]}

Extrae requisitos de participación en JSON con esta estructura:
{{
  "sections": {{
    "experiencia_general": [{{"key":"...", "label":"...", "display_value":"...", "evidence":"...", "confidence":0.0-1.0}}],
    "experiencia_especifica": [...],
    "indicadores_financieros": [...],
    "requisitos_legales": [...],
    "otros": [...]
  }}
}}

Solo incluye hechos presentes en el texto. confidence >= 0.70. Español."""

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
            max_tokens=1800,
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
        llm_sections = payload.get("sections", {})
    except Exception as exc:
        logger.warning("LLM requirements enrichment failed for %s: %s", tender_external_id, exc)
        return existing_sections

    merged = dict(existing_sections)
    min_confidence = settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE

    for section_key, llm_items in llm_sections.items():
        if section_key not in merged or merged[section_key]:
            continue
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
                }
            )
        if accepted:
            merged[section_key] = accepted

    return merged
