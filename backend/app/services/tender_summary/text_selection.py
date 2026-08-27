"""Select focused pliego excerpts for summary extraction (anticipo, etc.)."""
from __future__ import annotations

import re

from app.services.tender_requirements.regex_extraction import normalize_text
from app.services.tender_requirements.text_selection import (
    _merge_ranges,
    select_text_from_pages,
)
from app.services.tender_requirements.toc_parser import (
    join_index_text,
    parse_toc_entries,
    rank_toc_entries,
    refine_page_window_with_heading,
)

_ANTICIPO_TOC_KEYWORDS: tuple[str, ...] = (
    "anticipo",
    "pago anticipado",
    "forma de pago",
    "condiciones de ejecucion del contrato",
    "minuta del contrato",
)

_ANTICIPO_MARKERS: tuple[str, ...] = (
    "anticipo y/o pago anticipado",
    "anticipo y/o pago anticipado",
    "8.3 anticipo",
    "anticipo del contrato",
    "valor del anticipo",
    "pago anticipado",
    "no entregara al contratista anticipo",
    "no entregará al contratista anticipo",
    "no se entregara anticipo",
    "no se entregará anticipo",
    "sin anticipo",
    "forma de pago",
    "anticipo",
)

_ANTICIPO_HEADING_KEYWORDS: tuple[str, ...] = (
    "anticipo y/o pago anticipado",
    "anticipo del contrato",
    "pago anticipado",
    "anticipo",
)


def _select_marker_windows(text: str, markers: tuple[str, ...], max_chars: int) -> str:
    if not text or len(text) <= max_chars:
        return text

    normalized = normalize_text(text)
    ranges: list[tuple[int, int]] = []
    for marker in markers:
        for match in re.finditer(re.escape(marker), normalized):
            raw_start = max(0, int(match.start() * len(text) / max(len(normalized), 1)) - 400)
            raw_end = min(
                len(text),
                int(match.end() * len(text) / max(len(normalized), 1)) + 2_500,
            )
            ranges.append((raw_start, raw_end))

    if not ranges:
        return text[:max_chars]

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


def _anticipo_pages_from_toc(pages: list[tuple[int, str]]) -> list[int]:
    index_text = join_index_text(pages)
    entries = parse_toc_entries(index_text)
    ranked = rank_toc_entries(entries, _ANTICIPO_TOC_KEYWORDS)
    if not ranked:
        return []

    max_page = pages[-1][0]
    page_numbers: list[int] = []
    for entry in ranked[:2]:
        start = max(1, entry.page - 1)
        end = min(max_page, entry.page + 4)
        page_numbers.extend(range(start, end + 1))
    return sorted(set(page_numbers))


def select_anticipo_text_for_llm(
    pages: list[tuple[int, str]] | None,
    pliego_text: str,
    max_chars: int,
) -> str:
    """Build a compact excerpt around anticipo / pago anticipado sections."""
    parts: list[str] = []
    budget = max_chars

    if pages:
        anticipo_pages = _anticipo_pages_from_toc(pages)
        if anticipo_pages:
            refined = refine_page_window_with_heading(
                pages,
                anticipo_pages,
                _ANTICIPO_HEADING_KEYWORDS,
            )
            excerpt = select_text_from_pages(pages, sorted(refined), budget)
            if excerpt.strip():
                parts.append(excerpt)
                budget = max(0, budget - len(excerpt))

    if not parts and pliego_text.strip() and budget > 0:
        parts.append(_select_marker_windows(pliego_text, _ANTICIPO_MARKERS, budget))

    combined = "\n\n".join(parts)
    return combined[:max_chars]
