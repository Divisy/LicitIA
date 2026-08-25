"""Select the most relevant portions of long pliego/anexo text for requirement extraction."""
from __future__ import annotations

import re

from app.services.tender_requirements.regex_extraction import normalize_text

_SECTION_MARKERS: tuple[str, ...] = (
    "3.8 exigencias minimas de la experiencia",
    "3.8.1 exigencia minima de la experiencia del proponente",
    "requisitos de experiencia son",
    "experiencia general",
    "experiencia especifica",
    "solvencia economica y financiera",
    "indicadores financieros",
    "capacidad juridica",
    "registro unico de proponentes",
    "10.1 acreditacion de la experiencia del proponente",
    "matriz 1 - experiencia",
    "formato 3 - experiencia",
)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 500:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def select_requirement_relevant_text(text: str, max_chars: int) -> str:
    """Keep introduction plus windows around habilitation sections instead of head-only truncation."""
    if not text or len(text) <= max_chars:
        return text

    normalized = normalize_text(text)
    ranges: list[tuple[int, int]] = [(0, min(len(text), 12_000))]

    for marker in _SECTION_MARKERS:
        for match in re.finditer(re.escape(marker), normalized):
            # Map normalized offsets approximately to raw text positions.
            raw_start = max(0, int(match.start() * len(text) / max(len(normalized), 1)) - 800)
            raw_end = min(
                len(text),
                int(match.end() * len(text) / max(len(normalized), 1)) + 6_000,
            )
            ranges.append((raw_start, raw_end))

    merged = _merge_ranges(ranges)
    chunks: list[str] = []
    total = 0
    for start, end in merged:
        chunk = text[start:end]
        if not chunk.strip():
            continue
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break

    return "\n\n".join(chunks) if chunks else text[:max_chars]
