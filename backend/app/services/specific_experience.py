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
MAX_OCR_PAGES = 12
VISION_BATCH = 2
RENDER_SCALE = 1.6

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

_OBJETO_RES = (
    re.compile(
        r"(?:objeto(?:\s+del\s+(?:presente\s+)?contrato|\s+contractual)?)"
        r"\s*[:.\-–]\s*(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:objeto(?:\s+del\s+(?:presente\s+)?contrato|\s+contractual)?)"
        r"\s*\n+\s*(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:tiene\s+por\s+objeto|cuyo\s+objeto(?:\s+(?:fue|es|consisti[oó]|consiste))?)"
        r"\s*[:.\-–]?\s*(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:el\s+presente\s+contrato\s+(?:tiene\s+por\s+objeto|consiste\s+en))\s*(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
)

_PAGE_HINT = re.compile(
    r"objeto|contractual|acta|finalizaci[oó]n|recibo|consorcio|interventor",
    re.IGNORECASE,
)


def _clean_objeto(snippet: str) -> Optional[str]:
    text = (snippet or "").strip()
    stop = "|".join(_STOP)
    cut = re.search(rf"(?:\n|\.)\s*(?:{stop})\b", text, re.IGNORECASE)
    if cut:
        text = text[: cut.start()]
    text = re.sub(r"\s+", " ", text).strip(" :-.")
    if len(text) < 20:
        return None
    return text[:2000]


def extract_specific_experience_from_text(text: str) -> Optional[str]:
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    if len(cleaned) < 20:
        return None
    for pattern in _OBJETO_RES:
        match = pattern.search(cleaned)
        if not match:
            continue
        snippet = _clean_objeto(match.group(1))
        if snippet:
            return snippet
    return None


def extract_specific_experience_from_pdf_bytes(content: bytes) -> Optional[str]:
    """Native PDF text first; LLM on text; OCR/vision if there is no usable objeto."""
    pages = _page_texts(content or b"")
    native = "\n".join(pages) if pages else ""
    if not native:
        from app.services.rup_parser import extract_text_from_pdf_bytes

        native = extract_text_from_pdf_bytes(content or b"")
        pages = [native] if native else []

    for page in pages:
        from_page = extract_specific_experience_from_text(page)
        if from_page:
            return from_page
    from_text = extract_specific_experience_from_text(native)
    if from_text:
        return from_text

    if _letter_count(native) >= 80:
        from_llm = extract_objeto_from_text_with_llm(native)
        if from_llm:
            return from_llm

    return extract_specific_experience_with_vision(content, page_texts=pages)


def _letter_count(text: str) -> int:
    return sum(1 for ch in text or "" if ch.isalpha())


def _looks_like_scan(text: str) -> bool:
    raw = text or ""
    letters = _letter_count(raw)
    if letters < MIN_NATIVE_CHARS:
        return True
    if letters / max(len(raw), 1) < 0.35:
        return True
    words = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{4,}", raw)
    return len(words) < 15


def _page_texts(content: bytes) -> list[str]:
    if not content:
        return []
    try:
        import pymupdf

        doc = pymupdf.open(stream=content, filetype="pdf")
        try:
            return [(doc[index].get_text() or "") for index in range(doc.page_count)]
        finally:
            doc.close()
    except Exception as exc:
        logger.warning("Could not read acta page text: %s", exc)
        return []


def render_acta_page_jpegs(
    content: bytes,
    *,
    max_pages: int = MAX_OCR_PAGES,
    scale: float = RENDER_SCALE,
    page_numbers: Optional[list[int]] = None,
) -> list[tuple[int, bytes]]:
    import pymupdf

    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        images: list[tuple[int, bytes]] = []
        matrix = pymupdf.Matrix(scale, scale)
        if page_numbers:
            indices = [n - 1 for n in page_numbers if 1 <= n <= doc.page_count]
        else:
            indices = list(range(min(doc.page_count, max_pages)))
        for index in indices[:max_pages]:
            pixmap = doc[index].get_pixmap(matrix=matrix)
            images.append((index + 1, pixmap.tobytes("jpeg", jpg_quality=78)))
        return images
    finally:
        doc.close()


def _pages_to_ocr(page_texts: list[str], page_count: int) -> list[int]:
    hinted = [
        index + 1
        for index, text in enumerate(page_texts)
        if index < page_count and _PAGE_HINT.search(text or "")
    ]
    if hinted:
        ordered = []
        for number in hinted:
            if number not in ordered:
                ordered.append(number)
        extras = [n for n in range(1, min(page_count, MAX_OCR_PAGES) + 1) if n not in ordered]
        return (ordered + extras)[:MAX_OCR_PAGES]
    return list(range(1, min(page_count, MAX_OCR_PAGES) + 1))


def extract_objeto_from_text_with_llm(text: str) -> Optional[str]:
    if not settings.OPENAI_API_KEY:
        return None
    excerpt = re.sub(r"\s+", " ", text or "").strip()[:12000]
    if len(excerpt) < 40:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extraes el objeto contractual de actas o certificados de obra "
                        "colombianos. Responde únicamente JSON válido."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Extrae ÚNICAMENTE el objeto del contrato (obra, interventoría, "
                        "estudios o diseños). Devuelve JSON: {\"objeto\": \"texto\"}. "
                        "Si no está, {\"objeto\": null}. No inventes.\n\n"
                        f"{excerpt}"
                    ),
                },
            ],
            temperature=0.0,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Acta text LLM failed: %s", exc)
        return None
    return _clean_objeto(payload.get("objeto") or "") if isinstance(payload, dict) else None


def extract_specific_experience_with_vision(
    content: bytes,
    page_texts: Optional[list[str]] = None,
) -> Optional[str]:
    """Read the contract object from scanned acta page images."""
    if not settings.OPENAI_API_KEY:
        logger.warning("Acta OCR skipped: missing OPENAI_API_KEY")
        return None
    texts = page_texts if page_texts is not None else _page_texts(content)
    page_count = len(texts) or MAX_OCR_PAGES
    wanted = _pages_to_ocr(texts, page_count)
    try:
        pages = render_acta_page_jpegs(content, page_numbers=wanted)
    except Exception as exc:
        logger.warning("Could not render scanned acta pages: %s", exc)
        return None
    if not pages:
        return None

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    for start in range(0, len(pages), VISION_BATCH):
        batch = pages[start : start + VISION_BATCH]
        objeto = _vision_batch(client, batch)
        if objeto:
            return objeto
    return None


def _vision_batch(client, pages: list[tuple[int, bytes]]) -> Optional[str]:
    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Estas páginas son un certificado o acta de finalización de un contrato "
                "público colombiano, a menudo escaneado y a veces un compilado de varias "
                "actas. Extrae ÚNICAMENTE el objeto del contrato (objeto contractual / "
                "descripción de la obra o del proyecto). "
                "Devuelve JSON: {\"objeto\": \"texto\"}. "
                "Si no hay objeto en estas páginas, {\"objeto\": null}. "
                "No inventes. No copies firmas ni valores."
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
                    "detail": "low",
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
    return _clean_objeto(objeto)


def backfill_objetos_from_stored_actas(db, experiences, *, limit: int = 3) -> int:
    """Re-read stored acta PDFs when the object was not extracted on upload."""
    from datetime import datetime

    from app.services.document_storage import get_document_storage
    from app.services.experience_matching import extract_keywords

    pending = [
        row
        for row in experiences
        if not (getattr(row, "specific_experience", None) or "").strip()
        and (getattr(row, "specific_evidence_key", None) or "").strip()
    ]
    if not pending:
        return 0

    storage = get_document_storage()
    filled = 0
    for row in pending[:limit]:
        try:
            content = b"".join(storage.iter_file_chunks(row.specific_evidence_key))
        except Exception as exc:
            logger.warning(
                "Could not read stored acta %s: %s",
                row.specific_evidence_key,
                exc,
            )
            continue
        extracted = extract_specific_experience_from_pdf_bytes(content)
        if not extracted:
            logger.info(
                "Acta stored but objeto not found for experience %s (%s)",
                row.id,
                row.specific_evidence_filename,
            )
            continue
        row.specific_experience = extracted
        from app.services.rup_contract_kind import apply_kind_from_specific_experience

        apply_kind_from_specific_experience(row, extracted)
        from app.services.project_typology import apply_project_typologies

        apply_project_typologies(row)
        keywords = extract_keywords(extracted)
        if keywords:
            row.keywords = json.dumps(keywords)
        row.updated_at = datetime.utcnow()
        filled += 1
    if filled:
        db.commit()
    return filled
