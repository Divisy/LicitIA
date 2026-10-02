"""Extract the contract object (experiencia específica) from an acta or certificate PDF."""
from __future__ import annotations

import re
from typing import Optional

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
    if len(cleaned) < 40:
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
