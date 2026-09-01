"""Parse pliego table of contents to locate experience and habilitation sections."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.tender_requirements.regex_extraction import normalize_text

EXPERIENCE_TOC_KEYWORDS: tuple[str, ...] = (
    "exigencias minimas de la experiencia",
    "exigencia minima de la experiencia",
    "experiencia del proponente",
    "experiencia y formacion academica",
    "acreditacion de la experiencia",
    "condiciones de acreditacion de la experiencia",
    "requisitos de participacion",
    "capacidad de experiencia",
    "3.5 experiencia",
    "relacion de los contratos frente al presupuesto oficial",
)

FINANCIAL_TOC_KEYWORDS: tuple[str, ...] = (
    "solvencia economica",
    "indicadores financieros",
    "capacidad financiera",
    "capacidad organizacional",
)

LEGAL_TOC_KEYWORDS: tuple[str, ...] = (
    "capacidad juridica",
    "requisitos legales",
    "requisitos de participacion",
    "habilitacion",
    "existencia y representacion legal",
    "seguridad social",
    "registro unico de proponentes",
    "carta de presentacion",
    "3.2 capacidad juridica",
    "3.3 existencia",
    "3.4 seguridad",
)

TOC_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"((?:\d+\.)+\d*)\s+(.{8,160}?)\s+\.{3,}\s*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"((?:\d+\.)+\d*)\s+(.{8,160}?)\s+(\d{1,3})\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"(capitulo\s+[ivxlc\d]+)\s+(.{8,160}?)\s+\.{2,}\s*(\d{1,3})\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class TocEntry:
    section_id: str
    title: str
    page: int
    score: float = 0.0


def _keyword_score(title: str, keywords: tuple[str, ...]) -> float:
    normalized = normalize_text(title)
    score = 0.0
    for keyword in keywords:
        if keyword in normalized:
            score += 1.0
    return score


def parse_toc_entries(index_text: str) -> list[TocEntry]:
    """Parse TOC lines from the first pages of a pliego."""
    entries: list[TocEntry] = []
    seen: set[tuple[str, int]] = set()

    for pattern in TOC_LINE_PATTERNS:
        for match in pattern.finditer(index_text):
            section_id = match.group(1).strip()
            title = re.sub(r"\s+", " ", match.group(2)).strip(" .")
            page = int(match.group(3))
            key = (normalize_text(title), page)
            if key in seen or page <= 0 or page > 500:
                continue
            seen.add(key)
            entries.append(TocEntry(section_id=section_id, title=title, page=page))

    return entries


def rank_toc_entries(
    entries: list[TocEntry],
    keywords: tuple[str, ...],
) -> list[TocEntry]:
    ranked: list[TocEntry] = []
    for entry in entries:
        score = _keyword_score(entry.title, keywords)
        if score > 0:
            ranked.append(
                TocEntry(
                    section_id=entry.section_id,
                    title=entry.title,
                    page=entry.page,
                    score=score,
                )
            )
    return sorted(ranked, key=lambda item: (-item.score, item.page))


def locate_pages_from_toc(
    pages: list[tuple[int, str]],
    *,
    pages_before: int = 2,
    pages_after: int = 12,
) -> dict[str, list[int]]:
    """Return 1-based PDF page numbers to read for each requirement group."""
    if not pages:
        return {}

    index_text = join_index_text(pages)
    entries = parse_toc_entries(index_text)
    if not entries:
        return {}

    max_page = pages[-1][0]
    toc_hint_max = max((entry.page for entry in entries), default=0) + pages_after
    effective_max_page = max(max_page, toc_hint_max)
    selected: dict[str, list[int]] = {}

    for group, keywords in (
        ("experiencia", EXPERIENCE_TOC_KEYWORDS),
        ("financiero", FINANCIAL_TOC_KEYWORDS),
        ("legal", LEGAL_TOC_KEYWORDS),
    ):
        ranked = rank_toc_entries(entries, keywords)
        if not ranked:
            continue
        page_numbers: list[int] = []
        for entry in ranked[:2]:
            start = max(1, entry.page - pages_before)
            end = min(effective_max_page, entry.page + pages_after)
            page_numbers.extend(range(start, end + 1))
        selected[group] = sorted(set(page_numbers))

    return selected


def join_index_text(pages: list[tuple[int, str]], max_pages: int = 20) -> str:
    return "\n".join(text for page_no, text in pages if page_no <= max_pages)


def refine_page_window_with_heading(
    pages: list[tuple[int, str]],
    target_pages: list[int],
    heading_keywords: tuple[str, ...],
) -> list[int]:
    """Expand window if the TOC page does not contain the expected heading."""
    if not target_pages:
        return target_pages

    page_map = {page_no: text for page_no, text in pages}
    for page_no in target_pages:
        normalized = normalize_text(page_map.get(page_no, ""))
        if any(keyword in normalized for keyword in heading_keywords):
            return target_pages

    # Search nearby pages for the real section start.
    anchor = min(target_pages)
    extra: list[int] = []
    for page_no, text in pages:
        if page_no < anchor - 3 or page_no > anchor + 15:
            continue
        normalized = normalize_text(text)
        if any(keyword in normalized for keyword in heading_keywords):
            extra.extend(range(page_no, min(pages[-1][0], page_no + 12) + 1))
    if extra:
        return sorted(set(target_pages + extra))
    return target_pages
