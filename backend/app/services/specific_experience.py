"""Extract the contract object (experiencia específica) from an acta or certificate PDF."""
from __future__ import annotations

import base64
import json
import re
from typing import Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MIN_NATIVE_CHARS = 40
MAX_OCR_PAGES = 5
RENDER_SCALE = 1.4

_STOP = (
    r"VALOR",
    r"PLAZO",
    r"FECHA",
    r"CONTRATANTE",
    r"CONTRATISTA",
    r"NIT",
    r"C[EÉ]DULA",
    r"CLAUSULA",
    r"CLÁUSULA",
    r"ART[IÍ]CULO",
    r"OBLIGACION",
    r"OBLIGACIÓN",
    r"CERTIFICA",
    r"DADO EN",
    r"EN CONSTANCIA",
    r"FIRMA",
)

_OBJETO_RE = re.compile(
    r"(?:objeto(?:\s+del\s+contrato|\s+contractual)?|descripci[oó]n\s+del\s+(?:contrato|proyecto)|alcance)\s*[:.\-]\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def extract_specific_experience_from_text(text: str) -> Optional[str]:
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    if len(cleaned) < 20:
        return None

    match = _OBJETO_RE.search(cleaned)
    if not match:
        return None
    snippet = match.group(1).strip()
    stop = "|".join(_STOP)
    cut = re.search(rf"(?:\n|\.)\s*(?:{stop})\b", snippet, re.IGNORECASE)
    if cut:
        snippet = snippet[: cut.start()]
    snippet = re.sub(r"\s+", " ", snippet).strip(" :-.")
    if len(snippet) < 20:
        return None
    return snippet[:2000]


def extract_specific_experience_from_pdf_bytes(content: bytes) -> Optional[str]:
    """Native PDF text first; OCR/vision if there is no usable objeto."""
    from app.services.rup_parser import extract_text_from_pdf_bytes

    native = extract_text_from_pdf_bytes(content or b"")
    from_text = extract_specific_experience_from_text(native)
    if from_text:
        return from_text
    # Scans often have a garbage text layer (symbols, page numbers) that is not the objeto.
    return extract_specific_experience_with_vision(content)


def _looks_like_scan(text: str) -> bool:
    raw = text or ""
    letters = sum(1 for ch in raw if ch.isalpha())
    if letters < MIN_NATIVE_CHARS:
        return True
    if letters / max(len(raw), 1) < 0.35:
        return True
    words = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{4,}", raw)
    return len(words) < 15


def render_acta_page_jpegs(
    content: bytes,
    *,
    max_pages: int = MAX_OCR_PAGES,
    scale: float = RENDER_SCALE,
) -> list[tuple[int, bytes]]:
    import pymupdf

    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        images: list[tuple[int, bytes]] = []
        matrix = pymupdf.Matrix(scale, scale)
        page_count = min(doc.page_count, max_pages)
        for index in range(page_count):
            pixmap = doc[index].get_pixmap(matrix=matrix)
            images.append((index + 1, pixmap.tobytes("jpeg", jpg_quality=72)))
        return images
    finally:
        doc.close()


def extract_specific_experience_with_vision(content: bytes) -> Optional[str]:
    """Read the contract object from scanned acta page images."""
    if not settings.OPENAI_API_KEY:
        logger.warning("Acta OCR skipped: missing OPENAI_API_KEY")
        return None
    try:
        pages = render_acta_page_jpegs(content)
    except Exception as exc:
        logger.warning("Could not render scanned acta pages: %s", exc)
        return None
    if not pages:
        return None

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Estas páginas son un certificado o acta de finalización de un contrato público "
                "colombiano, a menudo escaneado. Extrae ÚNICAMENTE el objeto del contrato "
                "(objeto contractual / descripción de la obra o del proyecto). "
                "Devuelve JSON: {\"objeto\": \"texto\"}. "
                "Si no hay objeto, {\"objeto\": null}. No inventes. No copies firmas ni valores."
            ),
        }
    ]
    for page_no, image_bytes in pages:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        user_content.append({"type": "text", "text": f"Página {page_no}:"})
        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded}",
                    "detail": "high",
                },
            }
        )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extraes el objeto contractual de actas de obra colombianas. "
                        "Responde únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Acta vision OCR failed: %s", exc)
        return None

    objeto = payload.get("objeto") if isinstance(payload, dict) else None
    if not isinstance(objeto, str):
        return None
    cleaned = re.sub(r"\s+", " ", objeto).strip(" :-.")
    if len(cleaned) < 20:
        return None
    return cleaned[:2000]
