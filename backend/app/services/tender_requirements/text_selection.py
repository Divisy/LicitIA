"""Select the most relevant portions of long pliego/anexo text for requirement extraction."""
from __future__ import annotations

import re

from app.services.tender_requirements.regex_extraction import normalize_text
from app.services.tender_requirements.toc_parser import (
    EXPERIENCE_TOC_KEYWORDS,
    locate_pages_from_toc,
    refine_page_window_with_heading,
)

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


def select_text_from_pages(
    pages: list[tuple[int, str]],
    page_numbers: list[int],
    max_chars: int,
) -> str:
    page_map = {page_no: text for page_no, text in pages}
    chunks: list[str] = []
    total = 0
    for page_no in page_numbers:
        chunk = page_map.get(page_no, "")
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
    return "\n\n".join(chunks)


def select_pliego_text_from_toc(
    pages: list[tuple[int, str]],
    max_chars: int,
) -> tuple[str, list[str]]:
    """Navigate the pliego index and return focused text plus trace notes."""
    notes: list[str] = []
    if not pages:
        return "", notes

    grouped_pages = locate_pages_from_toc(pages)
    if not grouped_pages.get("experiencia"):
        return "", notes

    experience_pages = refine_page_window_with_heading(
        pages,
        grouped_pages["experiencia"],
        (
            "exigencia minima de la experiencia",
            "exigencias minimas de la experiencia",
            "requisitos de experiencia son",
            "experiencia general",
        ),
    )
    selected_pages = set(experience_pages)
    for key in ("financiero", "legal"):
        selected_pages.update(grouped_pages.get(key, []))

    ordered_pages = sorted(selected_pages)
    text = select_text_from_pages(pages, ordered_pages, max_chars)
    if text.strip():
        notes.append(
            "Secciones localizadas por índice del pliego: "
            + ", ".join(f"{group} (págs. {min(pages_)}-{max(pages_)})" for group, pages_ in grouped_pages.items())
        )
    return text, notes


def select_requirement_relevant_text(text: str, max_chars: int) -> str:
    """Fallback: keep introduction plus windows around habilitation markers."""
    if not text or len(text) <= max_chars:
        return text

    normalized = normalize_text(text)
    ranges: list[tuple[int, int]] = [(0, min(len(text), 12_000))]

    for marker in _SECTION_MARKERS:
        for match in re.finditer(re.escape(marker), normalized):
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


def prepare_pliego_requirement_text(
    pages: list[tuple[int, str]],
    raw_text: str,
    max_chars: int,
) -> tuple[str, list[str]]:
    """Prefer TOC navigation; fall back to marker windows on the full text."""
    toc_text, notes = select_pliego_text_from_toc(pages, max_chars)
    if toc_text.strip():
        return toc_text, notes
    return select_requirement_relevant_text(raw_text, max_chars), notes
