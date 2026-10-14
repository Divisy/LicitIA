"""Match an uploaded acta to the experience row with the same contract number."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_STOP_WORDS = {
    "CONTRATO",
    "OBRA",
    "PUBLICA",
    "PUBLICO",
    "NO",
    "NRO",
    "NUMERO",
    "NUM",
    "DE",
    "DEL",
    "LA",
    "EL",
    "LOS",
    "LAS",
}

_CONTRACT_RES = (
    re.compile(
        r"contrato\s+(?:de\s+obra(?:\s+p[uú]blica)?\s+)?"
        r"(?:n[oº°\.]*|n[uú]mero|num\.?)?\s*[:\.]?\s*"
        r"([A-Za-z0-9][A-Za-z0-9./\-]*(?:\s+de\s+\d{1,2}\.?\d{3}|\s+de\s+\d{4})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"contrato\s+n[oº°\.]*\s*[:\.]?\s*([A-Za-z0-9][^\n,]{2,50})",
        re.IGNORECASE,
    ),
)

_FILENAME_RE = re.compile(
    r"contrato\s*(?:n[oº°\.]*|n[uú]mero)?\s*[:\.]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9./\- ]{1,50}?)(?:\.pdf)?$",
    re.IGNORECASE,
)


@dataclass
class ActaIdentity:
    contract_number: Optional[str] = None
    object_text: Optional[str] = None


@dataclass
class ContractMatch:
    status: str
    rows: list = field(default_factory=list)
    detail: str = ""


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper().replace(".", " ")


def _canon(token: str) -> str:
    if token.isdigit():
        return str(int(token))
    return token


def contract_parts(value: str) -> tuple[set[str], set[str]]:
    """Identifying tokens and years. Years do not identify the contract alone."""
    folded = _fold(value)
    folded = re.sub(r"[^A-Z0-9]+", " ", folded)
    keys: set[str] = set()
    years: set[str] = set()
    for raw in folded.split():
        if raw in _STOP_WORDS:
            continue
        token = _canon(raw)
        if re.fullmatch(r"(19|20)\d{2}", token):
            years.add(token)
            continue
        if len(token) >= 2 or token.isdigit():
            keys.add(token)
    return keys, years


def same_contract(stored: str, found: str) -> bool:
    """True when the acta number contains every identifier of the stored contract."""
    stored_keys, stored_years = contract_parts(stored)
    found_keys, found_years = contract_parts(found)
    if not stored_keys or not found_keys:
        return False
    if stored_years and found_years and stored_years.isdisjoint(found_years):
        return False
    return stored_keys.issubset(found_keys)


def match_contract_rows(experiences, found_number: str) -> ContractMatch:
    hits = [
        row
        for row in experiences
        if same_contract(getattr(row, "contract_number", None) or "", found_number)
    ]
    if not hits:
        return ContractMatch(
            status="unmatched",
            detail="Ningún contrato del RUP tiene ese número.",
        )
    groups: dict[tuple, list] = {}
    for row in hits:
        keys, years = contract_parts(getattr(row, "contract_number", None) or "")
        groups.setdefault((frozenset(keys), frozenset(years)), []).append(row)
    if len(groups) > 1:
        labels = sorted(
            {
                (getattr(row, "contract_number", None) or "").strip()
                for row in hits
            }
        )
        return ContractMatch(
            status="ambiguous",
            rows=hits,
            detail="El número coincide con más de un contrato: " + ", ".join(labels),
        )
    return ContractMatch(status="assigned", rows=hits)


def extract_contract_number_from_text(text: str) -> Optional[str]:
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    for pattern in _CONTRACT_RES:
        match = pattern.search(cleaned)
        if not match:
            continue
        number = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
        if contract_parts(number)[0]:
            return number[:80]
    return None


def extract_contract_number_from_filename(filename: str) -> Optional[str]:
    stem = re.sub(r"\.pdf$", "", (filename or "").strip(), flags=re.IGNORECASE)
    match = _FILENAME_RE.search(stem)
    if not match:
        return None
    number = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
    if not contract_parts(number)[0]:
        return None
    return number[:80]


def read_acta_identity(content: bytes) -> ActaIdentity:
    """Read the contract number and object. Scans use one vision call."""
    from app.services.specific_experience import (
        _letter_count,
        _page_texts,
        extract_objeto_from_text_with_llm,
        extract_specific_experience_from_text,
    )

    native = "\n".join(_page_texts(content or b""))
    if _letter_count(native) >= 40:
        objeto = extract_specific_experience_from_text(native)
        if not objeto:
            objeto = extract_objeto_from_text_with_llm(native)
        return ActaIdentity(
            contract_number=extract_contract_number_from_text(native),
            object_text=objeto,
        )
    return _vision_identity(content)


def _vision_identity(content: bytes) -> ActaIdentity:
    if not settings.OPENAI_API_KEY:
        logger.warning("Acta assignment OCR skipped: missing OPENAI_API_KEY")
        return ActaIdentity()
    from openai import OpenAI

    from app.services.specific_experience import _clean_objeto, render_acta_page_jpegs

    try:
        pages = render_acta_page_jpegs(content, page_numbers=[1, 2])
    except Exception as exc:
        logger.warning("Could not render acta for assignment: %s", exc)
        return ActaIdentity()
    if not pages:
        return ActaIdentity()

    import base64

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Este PDF es un certificado o acta de un contrato público colombiano. "
                "Devuelve JSON: {\"contract_number\": \"número y año\", \"objeto\": \"texto\"}. "
                "contract_number es el número del contrato, con el año si aparece. "
                "No uses la cédula, el NIT ni el valor. "
                "objeto es la frase de en qué consistió el contrato, no la lista numerada de obras. "
                "Si falta un dato, usa null. No inventes."
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
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=40.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Lees actas de obra colombianas. Responde únicamente JSON válido.",
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Acta assignment vision failed: %s", exc)
        return ActaIdentity()
    if not isinstance(payload, dict):
        return ActaIdentity()
    number = payload.get("contract_number")
    objeto = payload.get("objeto")
    cleaned_number = None
    if isinstance(number, str):
        cleaned_number = re.sub(r"\s+", " ", number).strip(" .,:;-")[:80] or None
        if cleaned_number and not contract_parts(cleaned_number)[0]:
            cleaned_number = None
    cleaned_object = _clean_objeto(objeto) if isinstance(objeto, str) else None
    return ActaIdentity(contract_number=cleaned_number, object_text=cleaned_object)
