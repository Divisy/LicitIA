"""LLM extraction for tender summary fields (US 1.4)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger
from app.services.tender_summary.pliego_extraction import extract_advance_payment_from_text

logger = get_logger(__name__)

_openai_client: Optional[OpenAI] = None
if settings.OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass(frozen=True)
class AnticipoExtraction:
    percentage: float
    display_value: str
    confidence: float
    extraction_method: str
    evidence: Optional[str] = None


def format_anticipo_display(percentage: float) -> str:
    if percentage <= 0:
        return "0% — Sin anticipo"
    return f"{percentage:.2f}%"


def _parse_json_content(content: str) -> dict:
    cleaned = content.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(cleaned)


def extract_anticipo_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    regex_hint: Optional[float] = None,
) -> Optional[AnticipoExtraction]:
    if not settings.TENDER_SUMMARY_USE_LLM_FOR_ANTICIPO or not _openai_client:
        return None

    excerpt = (context_excerpt or "").strip()
    if not excerpt:
        return None

    hint = ""
    if regex_hint is not None:
        hint = f"Borrador automático (regex): {regex_hint:.2f}%\n"

    prompt = (
        f"Licitación: {tender_external_id}\n"
        f"Objeto: {object_text}\n\n"
        f"Fragmento del pliego (anticipo / pago anticipado):\n"
        f"{excerpt[: settings.TENDER_SUMMARY_ANTICIPO_LLM_MAX_CHARS]}\n\n"
        f"{hint}"
        "Devuelve JSON con:\n"
        "{\n"
        '  "advance_payment_percentage": number,  // 0 si no hay anticipo\n'
        '  "display_value": "texto corto para UI",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "evidence": "cita breve del pliego (máx. 200 caracteres)"\n'
        "}\n\n"
        "Reglas:\n"
        "- Si el pliego dice que NO se entrega anticipo / pago anticipado, usa 0.\n"
        "- Si indica un porcentaje, extrae solo el % del anticipo (no confundir con AIU, retención, etc.).\n"
        "- display_value en español de Colombia (ej. \"20% del valor del contrato\" o \"0% — Sin anticipo\").\n"
        "- Solo responde con información explícita en el fragmento."
    )

    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de licitaciones públicas colombianas (obra pública SECOP). "
                        "Extraes el porcentaje de anticipo del pliego. Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("LLM anticipo extraction failed for %s: %s", tender_external_id, exc)
        return None

    confidence = float(payload.get("confidence", 0))
    if confidence < settings.TENDER_SUMMARY_ANTICIPO_LLM_MIN_CONFIDENCE:
        return None

    raw_pct = payload.get("advance_payment_percentage")
    if raw_pct is None:
        return None

    percentage = max(0.0, float(raw_pct))
    display = payload.get("display_value") or format_anticipo_display(percentage)
    return AnticipoExtraction(
        percentage=percentage,
        display_value=display,
        confidence=confidence,
        extraction_method="llm",
        evidence=payload.get("evidence"),
    )


def resolve_anticipo_extraction(
    *,
    tender_external_id: str,
    object_text: str,
    excerpt: str,
    fallback_text: str = "",
) -> Optional[AnticipoExtraction]:
    """Regex on focused excerpt first, then LLM, then full-text regex fallback."""
    focused = (excerpt or "").strip()
    regex_text = focused or fallback_text

    pct = extract_advance_payment_from_text(regex_text) if regex_text else None
    if pct is not None:
        return AnticipoExtraction(
            percentage=pct,
            display_value=format_anticipo_display(pct),
            confidence=0.88 if focused else 0.72,
            extraction_method="regex",
        )

    if focused:
        llm_result = extract_anticipo_with_llm(
            tender_external_id=tender_external_id,
            object_text=object_text,
            context_excerpt=focused,
            regex_hint=pct,
        )
        if llm_result is not None:
            return llm_result

    if focused and fallback_text and fallback_text != regex_text:
        pct = extract_advance_payment_from_text(fallback_text)
        if pct is not None:
            return AnticipoExtraction(
                percentage=pct,
                display_value=format_anticipo_display(pct),
                confidence=0.65,
                extraction_method="regex",
            )

    return None
