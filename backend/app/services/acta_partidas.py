"""Read executed line items from an acta, apart from the contract object."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

_MAX_CHARS = 8000

_HEADERS = (
    r"cantidades de obra",
    r"descripcion de (?:la |las )?obras? ejecutad",
    r"items? ejecutad",
    r"actividades ejecutad",
    r"relacion de cantidades",
    r"partidas(?: de obra)?",
    r"descripcion de los trabajos",
    r"especificaciones tecnicas",
)

_STOP = (
    r"en constancia",
    r"dado en",
    r"firma del",
    r"firmas",
    r"el contratista",
    r"el interventor",
)

_QTY = re.compile(
    r"\b\d[\d.,]*\s*(?:m2|m3|ml|und|un|gl|kg|km|ha|mes|unidad|unidades)\b"
    r"|\b(?:item|cantidad|cant\.)\b",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text or "")
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return raw.lower()


def _strip_objeto(text: str, objeto: Optional[str]) -> str:
    if not objeto:
        return text
    folded_text = _fold(text)
    folded_objeto = _fold(objeto).strip()
    if len(folded_objeto) < 20 or folded_objeto not in folded_text:
        return text
    start = folded_text.find(folded_objeto)
    return text[:start] + text[start + len(folded_objeto) :]


def extract_acta_partidas_from_text(text: str, objeto: Optional[str] = None) -> Optional[str]:
    """Return executed items, quantities and descriptions. Empty when the acta has none."""
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    if len(cleaned) < 40:
        return None
    body = _strip_objeto(cleaned, objeto)
    folded = _fold(body)
    header = re.search("|".join(_HEADERS), folded)
    if header:
        snippet = body[header.start() :]
        stop = re.search("|".join(_STOP), _fold(snippet)[40:])
        if stop:
            snippet = snippet[: 40 + stop.start()]
        snippet = re.sub(r"\s+", " ", snippet).strip()
        if len(snippet) >= 40:
            return snippet[:_MAX_CHARS]
    if not _QTY.search(body):
        return None
    snippet = re.sub(r"\s+", " ", body).strip()
    if len(snippet) < 40:
        return None
    return snippet[:_MAX_CHARS]


def extract_acta_partidas_from_pdf_bytes(content: bytes, objeto: Optional[str] = None) -> Optional[str]:
    from app.services.specific_experience import _page_texts

    pages = _page_texts(content or b"")
    native = "\n".join(pages) if pages else ""
    if not native:
        from app.services.rup_parser import extract_text_from_pdf_bytes

        native = extract_text_from_pdf_bytes(content or b"")
    return extract_acta_partidas_from_text(native, objeto)


def backfill_partidas_from_stored_actas(db, experiences, *, limit: int = 3) -> int:
    """Fill acta_partidas from PDFs already stored, without asking for the file again."""
    from datetime import datetime

    from app.services.document_storage import get_document_storage

    pending = [
        row
        for row in experiences
        if not (getattr(row, "acta_partidas", None) or "").strip()
        and (getattr(row, "specific_evidence_key", None) or "").strip()
    ]
    if not pending:
        return 0

    storage = get_document_storage()
    filled = 0
    for row in pending[:limit]:
        try:
            content = b"".join(storage.iter_file_chunks(row.specific_evidence_key))
        except Exception:
            continue
        extracted = extract_acta_partidas_from_pdf_bytes(
            content,
            objeto=getattr(row, "specific_experience", None),
        )
        if not extracted:
            continue
        row.acta_partidas = extracted
        row.updated_at = datetime.utcnow()
        filled += 1
    if filled:
        db.commit()
    return filled
