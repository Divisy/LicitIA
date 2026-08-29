"""LLM extraction for tender summary fields (US 1.4)."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger
from app.services.tender_summary.pliego_extraction import extract_advance_payment_from_text
from app.services.tender_summary.pdf_ocr import vision_detail_level
from app.services.tender_summary.presupuesto_extraction import (
    PresupuestoExtraction,
    extract_aiu_percentage_from_text,
    format_aiu_display,
    has_presupuesto_aiu_context,
    is_credible_aiu_extraction,
    normalize_aiu_percentages,
    is_plausible_aiu_range,
)

logger = get_logger(__name__)

_openai_client: Optional[OpenAI] = None
if settings.OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass(frozen=True)
class AiuExtraction:
    percentage: float
    display_value: str
    confidence: float
    extraction_method: str
    admin_percentage: Optional[float] = None
    imprevistos_percentage: Optional[float] = None
    utilidad_percentage: Optional[float] = None
    evidence: Optional[str] = None


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


def _presupuesto_to_aiu_result(
    parsed: PresupuestoExtraction,
    *,
    extraction_method: str,
    confidence: float,
) -> Optional[AiuExtraction]:
    if parsed.aiu_percentage is None:
        return None
    parsed = normalize_aiu_percentages(parsed)
    if not is_plausible_aiu_range(parsed):
        return None
    return AiuExtraction(
        percentage=parsed.aiu_percentage,
        display_value=format_aiu_display(parsed),
        confidence=confidence,
        extraction_method=extraction_method,
        admin_percentage=parsed.aiu_admin_percentage,
        imprevistos_percentage=parsed.aiu_imprevistos_percentage,
        utilidad_percentage=parsed.aiu_utilidad_percentage,
    )


def _optional_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_aiu_with_llm(
    *,
    tender_external_id: str,
    object_text: str,
    context_excerpt: str,
    regex_hint: Optional[PresupuestoExtraction] = None,
) -> Optional[AiuExtraction]:
    if not settings.TENDER_SUMMARY_USE_LLM_FOR_AIU or not _openai_client:
        return None

    excerpt = (context_excerpt or "").strip()
    if not excerpt:
        return None

    hint = ""
    if regex_hint and regex_hint.aiu_percentage is not None:
        hint = f"Borrador automático (regex): {format_aiu_display(regex_hint)}\n"

    prompt = (
        f"Licitación: {tender_external_id}\n"
        f"Objeto: {object_text}\n\n"
        f"Fragmento del presupuesto oficial (Formulario 1 / AIU):\n"
        f"{excerpt[: settings.TENDER_SUMMARY_AIU_LLM_MAX_CHARS]}\n\n"
        f"{hint}"
        "Devuelve JSON con:\n"
        "{\n"
        '  "aiu_percentage": number,\n'
        '  "admin_percentage": number or null,\n'
        '  "imprevistos_percentage": number or null,\n'
        '  "utilidad_percentage": number or null,\n'
        '  "display_value": "texto corto para UI",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "evidence": "cita breve del presupuesto (máx. 200 caracteres)"\n'
        "}\n\n"
        "Reglas:\n"
        "- aiu_percentage es el total AIU (A+I+U). Si hay A=, I=, U=, súmalos.\n"
        "- Busca solo la fila A.I.U. / ADMINISTRACION (A) / IMPREVISTOS (I) / UTILIDAD (U) del presupuesto de obra.\n"
        "- NO uses porcentajes de experiencia del contratista, anticipo, interventoría ni IVA.\n"
        '- display_value ejemplo: "30% (A 24% · I 1% · U 5%)".\n'
        "- Solo información explícita en el fragmento."
    )

    try:
        response = _openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de licitaciones públicas colombianas (obra pública SECOP). "
                        "Extraes el porcentaje AIU del presupuesto oficial. Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("LLM AIU extraction failed for %s: %s", tender_external_id, exc)
        return None

    confidence = float(payload.get("confidence", 0))
    if confidence < settings.TENDER_SUMMARY_AIU_LLM_MIN_CONFIDENCE:
        return None

    raw_pct = payload.get("aiu_percentage")
    if raw_pct is None:
        return None

    parsed = PresupuestoExtraction(
        aiu_percentage=round(float(raw_pct), 2),
        aiu_admin_percentage=_optional_float(payload.get("admin_percentage")),
        aiu_imprevistos_percentage=_optional_float(payload.get("imprevistos_percentage")),
        aiu_utilidad_percentage=_optional_float(payload.get("utilidad_percentage")),
    )
    parsed = normalize_aiu_percentages(parsed)
    evidence = payload.get("evidence")
    if not is_credible_aiu_extraction(parsed, evidence=evidence):
        return None
    return AiuExtraction(
        percentage=parsed.aiu_percentage,
        display_value=format_aiu_display(parsed),
        confidence=confidence,
        extraction_method="llm",
        admin_percentage=parsed.aiu_admin_percentage,
        imprevistos_percentage=parsed.aiu_imprevistos_percentage,
        utilidad_percentage=parsed.aiu_utilidad_percentage,
        evidence=evidence,
    )


def extract_aiu_with_vision(
    *,
    tender_external_id: str,
    object_text: str,
    page_images: list[tuple[int, bytes]],
) -> Optional[AiuExtraction]:
    """Extract AIU directly from scanned presupuesto page images."""
    if not settings.TENDER_SUMMARY_USE_LLM_FOR_AIU or not _openai_client:
        return None
    if not page_images:
        return None

    model = settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL or settings.OPENAI_MODEL_NAME
    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"Licitación: {tender_external_id}\n"
                f"Objeto: {object_text}\n\n"
                "Extrae el porcentaje AIU (Administración + Imprevistos + Utilidad) "
                "del resumen del presupuesto de obra en la imagen. "
                "Busca la fila A.I.U. o los porcentajes A=, I=, U=. "
                "Devuelve JSON:\n"
                "{\n"
                '  "aiu_percentage": number,\n'
                '  "admin_percentage": number or null,\n'
                '  "imprevistos_percentage": number or null,\n'
                '  "utilidad_percentage": number or null,\n'
                '  "display_value": "texto corto para UI",\n'
                '  "confidence": 0.0-1.0,\n'
                '  "evidence": "cita breve"\n'
                "}\n"
                "Reglas: aiu_percentage = A+I+U. "
                "Los porcentajes son enteros (ej. A=24, I=1, U=5, total=30), NO decimales como 0.24. "
                "NO uses experiencia del contratista, anticipo, interventoría, RETILAP ni IVA."
            ),
        }
    ]
    for page_no, image_bytes in page_images[:1]:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content.append({"type": "text", "text": f"Página {page_no}:"})
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded}",
                    "detail": vision_detail_level(),
                },
            }
        )

    try:
        response = _openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de licitaciones públicas colombianas (obra pública SECOP). "
                        "Extraes AIU de presupuestos escaneados. Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": content},
            ],
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_content(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Vision AIU extraction failed for %s: %s", tender_external_id, exc)
        return None

    confidence = float(payload.get("confidence", 0))
    if confidence < settings.TENDER_SUMMARY_AIU_LLM_MIN_CONFIDENCE:
        return None

    raw_pct = payload.get("aiu_percentage")
    if raw_pct is None:
        return None

    parsed = PresupuestoExtraction(
        aiu_percentage=round(float(raw_pct), 2),
        aiu_admin_percentage=_optional_float(payload.get("admin_percentage")),
        aiu_imprevistos_percentage=_optional_float(payload.get("imprevistos_percentage")),
        aiu_utilidad_percentage=_optional_float(payload.get("utilidad_percentage")),
    )
    parsed = normalize_aiu_percentages(parsed)
    evidence = payload.get("evidence")
    if not is_credible_aiu_extraction(parsed, evidence=evidence):
        return None
    return AiuExtraction(
        percentage=parsed.aiu_percentage,
        display_value=format_aiu_display(parsed),
        confidence=confidence,
        extraction_method="vision",
        admin_percentage=parsed.aiu_admin_percentage,
        imprevistos_percentage=parsed.aiu_imprevistos_percentage,
        utilidad_percentage=parsed.aiu_utilidad_percentage,
        evidence=evidence,
    )


def resolve_aiu_extraction(
    *,
    tender_external_id: str,
    object_text: str,
    excerpt: str,
    fallback_text: str = "",
    xlsx_parsed: Optional[PresupuestoExtraction] = None,
    vision_page_images: Optional[list[tuple[int, bytes]]] = None,
) -> Optional[AiuExtraction]:
    """Regex on focused presupuesto excerpt first, then LLM, then vision fallback."""
    if xlsx_parsed and xlsx_parsed.aiu_percentage is not None:
        return _presupuesto_to_aiu_result(
            xlsx_parsed,
            extraction_method="presupuesto",
            confidence=0.92,
        )

    focused = (excerpt or "").strip()
    regex_text = focused or fallback_text
    parsed = PresupuestoExtraction()
    text_has_aiu_context = has_presupuesto_aiu_context(regex_text)

    if regex_text and text_has_aiu_context:
        parsed = extract_aiu_percentage_from_text(regex_text)
        result = _presupuesto_to_aiu_result(
            parsed,
            extraction_method="regex",
            confidence=0.88 if focused else 0.72,
        )
        if result is not None:
            return result

        llm_result = extract_aiu_with_llm(
            tender_external_id=tender_external_id,
            object_text=object_text,
            context_excerpt=focused or regex_text,
            regex_hint=parsed if parsed.aiu_percentage is not None else None,
        )
        if llm_result is not None:
            return llm_result

    if vision_page_images:
        vision_result = extract_aiu_with_vision(
            tender_external_id=tender_external_id,
            object_text=object_text,
            page_images=vision_page_images,
        )
        if vision_result is not None:
            return vision_result

    if fallback_text and has_presupuesto_aiu_context(fallback_text) and fallback_text != regex_text:
        parsed = extract_aiu_percentage_from_text(fallback_text)
        return _presupuesto_to_aiu_result(
            parsed,
            extraction_method="regex",
            confidence=0.65,
        )

    return None


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
