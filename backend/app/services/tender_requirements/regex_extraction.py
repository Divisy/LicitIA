"""Regex-based extraction of participation requirements from pliego/anexo text (US 1.5)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional
from uuid import UUID

RequirementItem = dict[str, Any]

SECTION_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("experiencia_general", "Experiencia general", "pliego_condiciones"),
    ("experiencia_especifica", "Experiencia específica", "anexo_tecnico"),
    ("indicadores_financieros", "Indicadores financieros y solvencia", "indicadores_financieros"),
    ("requisitos_legales", "Requisitos legales y habilitación", "pliego_condiciones"),
    ("sistema_puntos", "Sistema de puntos", "pliego_condiciones"),
)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _snippet(text: str, start: int, end: int, max_len: int = 220) -> str:
    fragment = text[start:end].strip()
    if len(fragment) > max_len:
        fragment = fragment[: max_len - 3] + "..."
    return fragment


def _region_near_marker(text: str, markers: tuple[str, ...], window: int = 1200) -> list[str]:
    normalized = normalize_text(text)
    regions: list[str] = []
    for marker in markers:
        for match in re.finditer(re.escape(marker), normalized):
            start = max(0, match.start() - 200)
            end = min(len(normalized), match.end() + window)
            regions.append(normalized[start:end])
    return regions


def _item(
    *,
    key: str,
    label: str,
    value: Any,
    display_value: str,
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str,
    confidence: float = 0.85,
) -> RequirementItem:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display_value": display_value,
        "confidence": confidence,
        "source_document": source_document,
        "source_document_id": str(source_document_id) if source_document_id else None,
        "evidence": evidence,
    }


def _clean_requirement_text(value: str, max_len: int = 500) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .;:-")
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def _extract_labeled_block(normalized: str, label: str, stop_labels: tuple[str, ...]) -> Optional[str]:
    stop_pattern = "|".join(re.escape(stop) for stop in stop_labels)
    pattern = rf"{re.escape(label)}\s*[:\-]\s*(.+?)(?=(?:{stop_pattern})|\s+a\.\s|\s+b\.\s|$)"
    matches = list(re.finditer(pattern, normalized, flags=re.IGNORECASE | re.DOTALL))
    if not matches:
        return None

    best: Optional[str] = None
    for match in matches:
        candidate = _clean_requirement_text(match.group(1))
        if not candidate or candidate.startswith("["):
            continue
        if len(candidate) < 25:
            continue
        if best is None or len(candidate) > len(best):
            best = candidate
    return best


def _merge_items(existing: list[RequirementItem], new_items: list[RequirementItem]) -> list[RequirementItem]:
    merged = list(existing)
    seen = {item["key"] for item in merged}
    for item in new_items:
        if item["key"] in seen:
            continue
        merged.append(item)
        seen.add(item["key"])
    return merged


def _general_experience_region(normalized: str) -> str:
    """Text window likely describing general experience (before specific matrix rows)."""
    start_candidates: list[int] = []
    for marker in (
        "3.5 experiencia",
        "exigencia minima de la experiencia",
        "experiencia general",
        "capacidad de experiencia",
    ):
        index = normalized.find(marker)
        if index >= 0:
            start_candidates.append(index)
    start = min(start_candidates) if start_candidates else 0
    end_match = re.search(r"\bespecifica\s+con la sumatoria", normalized[start:])
    end = start + end_match.start() if end_match else len(normalized)
    return normalized[start:end]


def _specific_experience_region(normalized: str) -> str:
    """Collect paragraphs around experiencia específica / matriz markers."""
    chunks: list[str] = []
    for marker in (
        "experiencia especifica",
        "experiencia específica",
        "tipo de experiencia requisito",
    ):
        for match in re.finditer(re.escape(marker), normalized):
            start = max(0, match.start() - 80)
            end = min(len(normalized), match.end() + 1600)
            chunks.append(normalized[start:end])
    for match in re.finditer(r"\bespecifica\b", normalized):
        start = match.start()
        end = min(len(normalized), match.start() + 1600)
        chunk = normalized[start:end]
        if chunk not in chunks:
            chunks.append(chunk)
    return " ".join(chunks)


def _parse_tier_rows(text: str) -> list[dict[str, Any]]:
    tier_patterns: tuple[tuple[str, str], ...] = (
        (r"de\s+1\s+hasta\s+2\s+(\d{2,3})\s*%", "1-2"),
        (r"de\s+3\s+hasta\s+4\s+(\d{2,3})\s*%", "3-4"),
        (r"hasta\s+5\s+(\d{2,3})\s*%", "1-5"),
    )
    tiers: list[dict[str, Any]] = []
    seen_ranges: set[str] = set()
    for pattern, contract_range in tier_patterns:
        if contract_range in seen_ranges:
            continue
        match = re.search(pattern, text)
        if not match:
            continue
        percentage = float(match.group(1))
        if not 50 <= percentage <= 200:
            continue
        tiers.append({"contract_range": contract_range, "percentage": percentage})
        seen_ranges.add(contract_range)
    order = {"1-2": 0, "3-4": 1, "1-5": 2}
    tiers.sort(key=lambda tier: order.get(str(tier["contract_range"]), 99))
    return tiers


def extract_experience_value_tiers(normalized: str) -> list[dict[str, Any]]:
    """Parse tiered 'valor mínimo a certificar' tables (% PO) by contract count."""
    anchor = re.search(r"valor\s+minimo\s+a\s+certificar", normalized)
    if anchor:
        window = normalized[anchor.start() : min(len(normalized), anchor.start() + 900)]
        tiers = _parse_tier_rows(window)
        if len(tiers) >= 2:
            return tiers

    tiers = _parse_tier_rows(normalized)
    if len(tiers) >= 2:
        return tiers
    return []


def _extract_contracts_for_experience(
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
    *,
    from_general: bool = False,
) -> Optional[RequirementItem]:
    if not region.strip():
        return None

    patterns: tuple[tuple[str, int, int, str], ...] = (
        (
            r"minimo\s+(?:uno|\(?\s*1\s*\)?)\s*(?:\(\s*1\s*\))?\s*y\s+maximo\s+"
            r"(?:cinco|\(?\s*5\s*\)?)\s*(?:\(\s*5\s*\))?\s+contratos",
            1,
            5,
            "Mínimo 1 y máximo 5 contratos",
        ),
        (
            r"al\s+menos\s+un\s*\(\s*1\s*\)\s+contrato\s+y\s+hasta\s+un\s+maximo\s+de\s+cinco\s*\(\s*5\s*\)",
            1,
            5,
            "Mínimo 1 y máximo 5 contratos",
        ),
        (
            r"se\s+deben\s+presentar\s+al\s+menos\s+un\s*\(\s*1\s*\)\s+contrato\s+y\s+hasta\s+"
            r"un\s+maximo\s+de\s+cinco\s*\(\s*5\s*\)",
            1,
            5,
            "Mínimo 1 y máximo 5 contratos",
        ),
        (
            r"(?:uno o hasta|hasta)\s+maximo\s+dos\s*\(\s*2\s*\)\s+de los contratos\s+validos"
            r"(?:\s+aportados\s+como\s+experiencia\s+general)?",
            1,
            2,
            "1 o 2 contratos de la experiencia general",
        ),
        (
            r"con\s+la\s+sumatoria\s+de\s+uno\s+o\s+hasta\s+maximo\s+dos\s*\(\s*2\s*\)\s+"
            r"de los contratos\s+validos",
            1,
            2,
            "1 o 2 contratos de la experiencia general",
        ),
    )

    for pattern, minimum, maximum, display in patterns:
        match = re.search(pattern, region)
        if not match:
            continue
        if from_general and minimum == 1 and maximum == 2:
            continue
        value: dict[str, Any] = {"minimum": minimum, "maximum": maximum}
        if not from_general and minimum == 1 and maximum == 2:
            value["from_general_experience"] = True
        return _item(
            key="contracts_minimum",
            label="Número de contratos",
            value=value,
            display_value=display,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_snippet(region, match.start(), match.end() + 80),
            confidence=0.9,
        )
    return None


def _extract_min_certified_percentage_item(
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
    *,
    item_key: str = "min_percentage_budget",
    label: str = "Valor mínimo a certificar",
) -> Optional[RequirementItem]:
    """Single % PO minimum when there is no multi-row tier table."""
    if extract_experience_value_tiers(region):
        return None

    patterns = (
        r"valor\s+minimo\s+a\s+certificar[^%]{0,220}?"
        r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|por ciento)",
        r"cien\s+por\s+ciento\s*\(\s*(\d{1,3})\s*%",
        r"contratos?\s+aportados?\s+como\s+experiencia[^%]{0,160}?(\d{1,3})\s*%",
    )
    for pattern in patterns:
        match = re.search(pattern, region)
        if not match:
            continue
        percentage = float(match.group(1).replace(",", "."))
        if not 10 <= percentage <= 200:
            continue
        smmlv = bool(re.search(r"smmlv|salario\s+minimo", region[match.start() : match.end() + 120]))
        display = f"{percentage:g}% del Presupuesto Oficial"
        if smmlv:
            display += " (en SMMLV)"
        return _item(
            key=item_key,
            label=label,
            value=percentage,
            display_value=display,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_snippet(region, match.start(), match.end() + 80),
            confidence=0.88,
        )
    return None


def _append_certification_supplements(
    items: list[RequirementItem],
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
    *,
    section: str,
) -> list[RequirementItem]:
    """Attach número de contratos and valor mínimo a certificar within a section region."""
    if not region.strip():
        return items

    from_general = section == "general"
    percentage_key = "min_percentage_budget" if from_general else "specific_min_percentage"

    tiers = extract_experience_value_tiers(region)
    if tiers and not any(item["key"] == "experience_value_tiers" for item in items):
        percentages = [f"{tier['percentage']:g}%" for tier in tiers]
        items.append(
            _item(
                key="experience_value_tiers",
                label="Valor mínimo a certificar",
                value=tiers,
                display_value=f"Según nº de contratos: {' / '.join(percentages)} del PO (SMMLV)",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence="Valor mínimo a certificar según número de contratos (% del PO)",
                confidence=0.92,
            )
        )
        if not any(item["key"] == "min_amount_smmlv" for item in items):
            items.append(
                _item(
                    key="min_amount_smmlv",
                    label="Monto en SMMLV",
                    value="smmlv",
                    display_value="Expresado en SMMLV",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence="Valores de experiencia expresados en SMMLV",
                    confidence=0.88,
                )
            )
    elif not any(item["key"] in {percentage_key, "experience_value_tiers"} for item in items):
        single_pct = _extract_min_certified_percentage_item(
            region,
            source_document,
            source_document_id,
            item_key=percentage_key,
            label="Valor mínimo a certificar",
        )
        if single_pct:
            items.append(single_pct)

    contracts_item = _extract_contracts_for_experience(
        region,
        source_document,
        source_document_id,
        from_general=from_general,
    )
    if contracts_item and not any(item["key"] == "contracts_minimum" for item in items):
        items.append(contracts_item)

    tier_percentages = {
        float(tier["percentage"])
        for item in items
        if item["key"] == "experience_value_tiers"
        for tier in (item.get("value") or [])
        if isinstance(tier, dict) and tier.get("percentage") is not None
    }
    percentage_keys = {percentage_key, "min_percentage_budget", "specific_min_percentage"}
    if tier_percentages:
        items = [
            item
            for item in items
            if not (item["key"] in percentage_keys and item.get("value") in tier_percentages)
        ]

    return items


def _resolve_phase_label_before(normalized: str, match_start: int) -> Optional[str]:
    before = normalized[max(0, match_start - 1500):match_start]
    fase_ii_matches = list(re.finditer(r"fase\s+ii\b", before))
    fase_i_matches: list[re.Match[str]] = []
    for phase_match in re.finditer(r"fase\s+i\b", before):
        if phase_match.end() < len(before) and before[phase_match.end() : phase_match.end() + 1] == "i":
            continue
        fase_i_matches.append(phase_match)

    if fase_ii_matches and (
        not fase_i_matches or fase_ii_matches[-1].start() > fase_i_matches[-1].start()
    ):
        return "Fase II"
    if fase_i_matches:
        return "Fase I"
    return None


def extract_specific_area_phases(normalized: str) -> list[dict[str, Any]]:
    """Extract Matriz 1 specific experience by project area (m²), often per project phase."""
    pattern = re.compile(
        r"especifica\s+con la sumatoria de uno o hasta\s+maximo dos\s*\(\s*2\s*\)"
        r"[^%]{0,600}?"
        r"(?:igual o superior al|superior al)\s*\(?\s*(\d{1,3})\s*%?\s*\)?\s*"
        r"del total de metros cuadrados[^.\d]{0,160}?(\d+(?:[.,]\d+)?)\s*m2",
        re.DOTALL,
    )
    phases: list[dict[str, Any]] = []
    roman_labels = ("Fase I", "Fase II", "Fase III")
    for index, match in enumerate(pattern.finditer(normalized)):
        percentage = float(match.group(1))
        total_m2 = float(match.group(2).replace(",", "."))
        minimum_m2 = round(total_m2 * percentage / 100, 1)
        phase_label = _resolve_phase_label_before(normalized, match.start()) or (
            roman_labels[index] if index < len(roman_labels) else f"Fase {index + 1}"
        )
        phases.append(
            {
                "phase": phase_label,
                "area_percentage": percentage,
                "total_m2": total_m2,
                "minimum_m2": minimum_m2,
                "max_contracts": 2,
            }
        )
    return phases


def _format_specific_area_phases_display(phases: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for phase in phases:
        label = phase.get("phase") or "Fase"
        pct = phase.get("area_percentage")
        minimum = phase.get("minimum_m2")
        total = phase.get("total_m2")
        if pct is None or minimum is None or total is None:
            continue
        parts.append(
            f"{label}: ≥{pct:g}% del área ({minimum:g} m² de {total:g} m²)"
        )
    return "; ".join(parts)


def _is_weak_specific_scope(scope: str) -> bool:
    cleaned = _clean_requirement_text(scope, max_len=400).lower()
    if len(cleaned) < 30:
        return True
    if re.fullmatch(r"acreditar(?:\s+los)?\s+smmlv", cleaned):
        return True
    return False


def extract_experiencia_general(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)

    general_block = _extract_labeled_block(
        normalized,
        "experiencia general",
        ("experiencia especifica", "experiencia específica", "requisitos de experiencia"),
    )
    if general_block:
        items.append(
            _item(
                key="requirement_description",
                label="Descripción del requisito",
                value=general_block,
                display_value=general_block,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=general_block[:220],
                confidence=0.92,
            )
        )

    section_region_match = re.search(
        r"contratos?\s+aportados?\s+como\s+experiencia[^.\n]{0,200}presupuesto\s+oficial",
        normalized,
        flags=re.DOTALL,
    )
    section_region = section_region_match.group(0) if section_region_match else normalized

    hundred_match = re.search(
        r"cien\s+por\s+ciento\s*\(\s*100\s*%|"
        r"contratos?\s+aportados?\s+como\s+experiencia[^.\n]{0,160}100\s*%",
        section_region,
    )
    if hundred_match and not any(item["key"] == "min_percentage_budget" for item in items):
        items.append(
            _item(
                key="min_percentage_budget",
                label="Porcentaje mínimo del presupuesto",
                value=100,
                display_value="100% del Presupuesto Oficial (en SMMLV)",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(section_region, hundred_match.start(), hundred_match.end() + 120),
                confidence=0.9,
            )
        )

    regions = _region_near_marker(
        text,
        (
            "experiencia general",
            "exigencia minima de la experiencia del proponente",
            "exigencias minimas de la experiencia",
            "capacidad de experiencia",
        ),
    )
    if not regions:
        regions = [section_region[:8000]]

    for region in regions:
        if "experiencia especifica" in region and "experiencia general" not in region[:160]:
            continue

        if any(item["key"] == "min_percentage_budget" for item in items):
            pass
        else:
            percent_match = re.search(
                r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|por ciento)[^.\n]{0,80}"
                r"(?:del\s+)?(?:presupuesto|valor|contrato)",
                region,
            )
            if percent_match:
                pct = float(percent_match.group(1).replace(",", "."))
                items.append(
                    _item(
                        key="min_percentage_budget",
                        label="Porcentaje mínimo del presupuesto",
                        value=pct,
                        display_value=f"{pct:g}%",
                        source_document=source_document,
                        source_document_id=source_document_id,
                        evidence=_snippet(region, percent_match.start(), percent_match.end() + 80),
                    )
                )

        years_match = re.search(
            r"(?:ultimos?|últimos?)\s+(\d{1,2})\s+anos?",
            region,
        )
        if years_match and not any(item["key"] == "time_window_years" for item in items):
            years = int(years_match.group(1))
            items.append(
                _item(
                    key="time_window_years",
                    label="Ventana temporal de experiencia",
                    value=years,
                    display_value=f"Últimos {years} años",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(region, years_match.start(), years_match.end() + 40),
                )
            )

        smmlv_match = re.search(
            r"expresado\s+en\s+smmlv|(\d+(?:[.,]\d+)?)\s*smmlv",
            region,
        )
        if smmlv_match and not any(item["key"] == "min_amount_smmlv" for item in items):
            if smmlv_match.lastindex and smmlv_match.group(1):
                amount = float(smmlv_match.group(1).replace(",", "."))
                display = f"{amount:g} SMMLV"
                value: Any = amount
            else:
                display = "Expresado en SMMLV"
                value = "smmlv"
            items.append(
                _item(
                    key="min_amount_smmlv",
                    label="Monto mínimo en SMMLV",
                    value=value,
                    display_value=display,
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(region, smmlv_match.start(), smmlv_match.end() + 40),
                )
            )

    accreditation_match = re.search(
        r"(formato\s*3\s*[-–]?\s*experiencia|matriz\s*1\s*[-–]?\s*experiencia|"
        r"certificad[oa]s?\s+de\s+experiencia)",
        normalized,
    )
    if accreditation_match:
        items.append(
            _item(
                key="accreditation_method",
                label="Cómo se acredita la experiencia",
                value=accreditation_match.group(1),
                display_value=accreditation_match.group(1).title(),
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(
                    normalized,
                    accreditation_match.start(),
                    accreditation_match.end() + 60,
                ),
                confidence=0.88,
            )
        )

    if not any(item["key"] == "requirement_description" for item in items):
        desc_match = re.search(
            r"experiencia general[^.\n]{0,20}[:\-]?\s*([^.\n]{20,240})",
            normalized,
        )
        if desc_match:
            items.append(
                _item(
                    key="requirement_description",
                    label="Descripción del requisito",
                    value=desc_match.group(1).strip(),
                    display_value=_clean_requirement_text(desc_match.group(1)),
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(normalized, desc_match.start(), desc_match.end()),
                    confidence=0.72,
                )
            )

    general_region = _general_experience_region(normalized)
    return _append_certification_supplements(
        items,
        general_region,
        source_document,
        source_document_id,
        section="general",
    )


def extract_experiencia_especifica(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)
    area_phases = extract_specific_area_phases(normalized)

    if area_phases:
        display = _format_specific_area_phases_display(area_phases)
        items.append(
            _item(
                key="specific_area_phases",
                label="Área mínima por fase",
                value=area_phases,
                display_value=display,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=display[:220],
                confidence=0.94,
            )
        )
        items.append(
            _item(
                key="specific_scope",
                label="Alcance exigido",
                value=display,
                display_value=display,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=display[:220],
                confidence=0.9,
            )
        )
        specific_region = _specific_experience_region(normalized)
        return _append_certification_supplements(
            items,
            specific_region,
            source_document,
            source_document_id,
            section="specific",
        )

    specific_block = _extract_labeled_block(
        normalized,
        "experiencia especifica",
        ("a. la experiencia", "b. el proponente", "requisitos de experiencia"),
    )
    if specific_block and not _is_weak_specific_scope(specific_block):
        items.append(
            _item(
                key="specific_scope",
                label="Alcance exigido",
                value=specific_block,
                display_value=specific_block,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=specific_block[:220],
                confidence=0.92,
            )
        )

        percent_in_block = re.search(
            r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|por ciento)[^.\n]{0,80}"
            r"(?:presupuesto\s+oficial|valor\s+del\s+presente\s+proceso)",
            specific_block,
        )
        if percent_in_block:
            pct = float(percent_in_block.group(1).replace(",", "."))
            items.append(
                _item(
                    key="specific_min_percentage",
                    label="Porcentaje mínimo específico",
                    value=pct,
                    display_value=f"{pct:g}% del Presupuesto Oficial",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(specific_block, percent_in_block.start(), percent_in_block.end() + 40),
                    confidence=0.9,
                )
            )

    regions = _region_near_marker(
        text,
        (
            "experiencia especifica",
            "experiencia específica",
            "experiencia relacionada",
            "requisitos de experiencia son",
        ),
    )
    if not regions:
        regions = [normalized[:8000]]

    for region in regions:
        percent_match = re.search(
            r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|por ciento)[^.\n]{0,120}"
            r"(?:presupuesto\s+oficial|valor\s+del\s+presente\s+proceso|valor\s+de\s+presupuesto)",
            region,
        )
        if percent_match and not any(item["key"] == "specific_min_percentage" for item in items):
            pct = float(percent_match.group(1).replace(",", "."))
            items.append(
                _item(
                    key="specific_min_percentage",
                    label="Porcentaje mínimo específico",
                    value=pct,
                    display_value=f"{pct:g}% del Presupuesto Oficial",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(region, percent_match.start(), percent_match.end() + 60),
                    confidence=0.85,
                )
            )

        if not any(item["key"] == "specific_scope" for item in items):
            scope_match = re.search(
                r"(?:experiencia especifica|experiencia específica|experiencia relacionada)"
                r"[^.\n]{0,30}[:\-]?\s*([^.\n]{20,400})",
                region,
            )
            if scope_match:
                scope = _clean_requirement_text(scope_match.group(1))
                if not _is_weak_specific_scope(scope):
                    items.append(
                        _item(
                            key="specific_scope",
                            label="Alcance exigido",
                            value=scope,
                            display_value=scope,
                            source_document=source_document,
                            source_document_id=source_document_id,
                            evidence=_snippet(region, scope_match.start(), scope_match.end()),
                            confidence=0.78,
                        )
                    )

    matriz_activity = re.search(
        r"requisitos de experiencia son:\s*([\d.]+\s+[a-z0-9\s]+(?:vias?|terciarias?|obras?)[^.]{0,160})",
        normalized,
    )
    if matriz_activity and not any(item["key"] == "specific_scope" for item in items):
        scope = _clean_requirement_text(matriz_activity.group(1), max_len=280)
        items.append(
            _item(
                key="specific_scope",
                label="Alcance exigido (Matriz 1)",
                value=scope,
                display_value=scope,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, matriz_activity.start(), matriz_activity.end()),
                confidence=0.84,
            )
        )

    code_matches = re.findall(
        r"(?:codigo(?:s)?|c[oó]digo(?:s)?\s+unspsc|unspsc|clasificador)"
        r"[^.\n]{0,40}?(\d{6,8}(?:\s*[,/]\s*\d{6,8})*)",
        normalized,
    )
    unspsc_codes: list[str] = []
    for raw_codes in code_matches:
        unspsc_codes.extend(
            code for code in re.findall(r"\d{6,8}", raw_codes) if not code.startswith(("19", "20"))
        )
    classification_region = re.search(
        r"clasificacion de la experiencia[^.]{0,2200}",
        normalized,
    )
    if classification_region:
        for match in re.finditer(r"\b(\d{2})\s+(\d{2})\s+(\d{2})\s+", classification_region.group(0)):
            code = f"{match.group(1)}{match.group(2)}{match.group(3)}"
            if code.startswith("72"):
                unspsc_codes.append(code)
    if unspsc_codes:
        unique_codes = list(dict.fromkeys(unspsc_codes))
        if not any(item["key"] == "activity_codes" for item in items):
            items.append(
                _item(
                    key="activity_codes",
                    label="Códigos de actividad",
                    value=unique_codes,
                    display_value=", ".join(unique_codes),
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=", ".join(unique_codes),
                    confidence=0.8,
                )
            )

    specific_region = _specific_experience_region(normalized)
    return _append_certification_supplements(
        items,
        specific_region,
        source_document,
        source_document_id,
        section="specific",
    )


def _parse_threshold(raw: str) -> Optional[float]:
    cleaned = raw.strip().rstrip(".")
    if not cleaned:
        return None
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None


def _financial_cluster_region(normalized: str) -> str:
    """Window around clustered financial indicator mentions (traditional pliegos)."""
    markers = (
        "indice de liquidez",
        "liquidez corriente",
        "activo corriente/pasivo corriente",
        "activo corriente / pasivo corriente",
        "endeudamiento",
        "cobertura de intereses",
        "capital de trabajo",
        "patrimonio minimo",
        "patrimonio activo total",
        "patrimonio liquido",
        "capacidad financiera",
        "solvencia economica",
        "rentabilidad del patrimonio",
        "rentabilidad del activo",
    )
    hits: list[int] = []
    for marker in markers:
        for match in re.finditer(re.escape(marker), normalized):
            snippet = normalized[match.start() : match.end() + 30]
            if re.search(r"\.{8,}", snippet):
                continue
            hits.append(match.start())
    if len(hits) < 2:
        return ""
    start = max(0, min(hits) - 300)
    end = min(len(normalized), max(hits) + 4000)
    return normalized[start:end]


def _resolve_financial_search_region(normalized: str) -> str:
    """Alias kept for tests — prefer _financial_pliego_region in new code."""
    return _financial_pliego_region(normalized)


FINANCIAL_REGION_MARKERS: tuple[str, ...] = (
    "solvencia economica y financiera",
    "capacidad financiera",
    "indicadores financieros",
    "3.5 capacidad financiera",
    "3.6 capacidad financiera",
    "3.6 capital de trabajo",
    "3.7 capital de trabajo",
    "3.7 capacidad organizacional",
    "3.9 capacidad organizacional",
    "matriz 2 - indicadores",
    "indice de liquidez",
    "liquidez corriente",
    "patrimonio minimo",
    "patrimonio activo total",
)


def _financial_pliego_region(normalized: str) -> str:
    """Text window for financial solvency (like _general_experience_region for experience)."""
    section = _financial_section_region(normalized)
    cluster = _financial_cluster_region(normalized)
    if section and cluster:
        return section if len(section) >= len(cluster) else cluster
    return section or cluster or ""


def _append_financial_supplements(
    items: list[RequirementItem],
    region: str,
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    """Attach structured financial metrics from the pliego region (mirrors certification supplements)."""
    effective_region = region.strip() or _financial_pliego_region(normalized)
    if not effective_region.strip():
        effective_region = normalized[:80_000]

    matriz_2_referenced = bool(re.search(r"matriz\s*2\b", effective_region))

    for item in _extract_financial_indicator_items(
        effective_region,
        source_document,
        source_document_id,
        matriz_2_referenced=matriz_2_referenced,
    ):
        if not any(existing["key"] == item["key"] for existing in items):
            items.append(item)

    org_region = _organizational_section_region(normalized, effective_region)
    if org_region:
        org_matriz = bool(re.search(r"matriz\s*2\b", org_region))
        for item in _extract_financial_indicator_items(
            org_region,
            source_document,
            source_document_id,
            matriz_2_referenced=org_matriz or matriz_2_referenced,
            section="organizational",
        ):
            if not any(existing["key"] == item["key"] for existing in items):
                items.append(item)

    capital_item = _extract_capital_trabajo_item(normalized, source_document, source_document_id)
    if capital_item:
        items = [item for item in items if item["key"] != "capital_trabajo"]
        items.append(capital_item)

    if not any(item["key"] == "accreditation_method" for item in items):
        accreditation = _extract_financial_accreditation_item(
            effective_region, source_document, source_document_id
        )
        if not accreditation:
            accreditation = _extract_financial_accreditation_item(
                normalized, source_document, source_document_id
            )
        if accreditation:
            items.append(accreditation)

    if not any(item["key"] == "financial_exemptions" for item in items):
        exemptions = _extract_financial_exemptions_item(
            normalized, source_document, source_document_id
        )
        if exemptions:
            items.append(exemptions)

    if matriz_2_referenced and not any(item["key"] == "matriz_2_reference" for item in items):
        items.append(
            _item(
                key="matriz_2_reference",
                label="Matriz 2",
                value="Matriz 2 – Indicadores financieros y organizacionales",
                display_value="Umbrales numéricos en Matriz 2 del proceso",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence="Matriz 2 – Indicadores financieros y organizacionales",
                confidence=0.95,
            )
        )

    if not any(item["key"] == "qualification_score" for item in items):
        score_match = re.search(
            r"capacidad\s+financiera[^.\n]{0,120}"
            r"(?:puntaje|puntuaci[oó]n)[^.\n]{0,60}"
            r"(\d{1,3}(?:[.,]\d+)?)\s*(?:puntos?)?",
            normalized,
        )
        if not score_match:
            score_match = re.search(
                r"solvencia[^.\n]{0,120}"
                r"(?:puntaje|puntuaci[oó]n|calificaci[oó]n)[^.\n]{0,80}"
                r"(\d{1,3}(?:[.,]\d+)?)\s*(?:puntos?)?",
                effective_region,
            )
        if score_match:
            score = float(score_match.group(1).replace(",", "."))
            items.append(
                _item(
                    key="qualification_score",
                    label="Puntaje financiero",
                    value=score,
                    display_value=f"Hasta {score:g} puntos",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(normalized, score_match.start(), score_match.end() + 60),
                    confidence=0.75,
                )
            )

    return items


_FINANCIAL_BLOCK_MARKERS: tuple[tuple[str, str], ...] = (
    ("liquidez_corriente", r"indice\s+de\s+liquidez|liquidez\s+corriente|activo\s+corriente\s*/\s*pasivo\s+corriente"),
    ("endeudamiento", r"\bendeudamiento\b|pasivo\s+total\s*/\s*activo\s+total"),
    (
        "cobertura_intereses",
        r"cobertura\s+de\s+intereses|razon\s+de\s+cobertura\s+de\s+intereses",
    ),
    ("capital_trabajo", r"capital\s+de\s+trabajo"),
    (
        "patrimonio_minimo",
        r"patrimonio\s+minimo|patrimonio\s+liquido|patrimonio\s+neto|"
        r"patrimonio\s*\(\s*activo\s+total|patrimonio\s+activo\s+total\s*[-–]",
    ),
    ("rentabilidad_patrimonio", r"rentabilidad\s+del\s+patrimonio|rentabilidad\s+sobre\s+patrimonio"),
    ("rentabilidad_activo", r"rentabilidad\s+del\s+activo"),
)


def _split_financial_blocks(region: str) -> dict[str, str]:
    markers: list[tuple[int, str]] = []
    for key, pattern in _FINANCIAL_BLOCK_MARKERS:
        for match in re.finditer(pattern, region):
            snippet = region[match.start() : match.end() + 40]
            if re.search(r"\.{8,}", snippet):
                continue
            markers.append((match.start(), key))
            break

    markers.sort(key=lambda entry: entry[0])
    blocks: dict[str, str] = {}
    for index, (start, key) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else min(len(region), start + 550)
        blocks[key] = region[start:end]
    return blocks


def _parse_cop_amount(raw: str) -> Optional[int]:
    digits = re.sub(r"\D", "", raw)
    if not digits or len(digits) < 6:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _parse_indicator_threshold(
    block: str,
    key: str,
    default_operator: str,
) -> tuple[Optional[str], Optional[float], dict[str, Any]]:
    extras: dict[str, Any] = {}

    if key in {"capital_trabajo", "patrimonio_minimo"}:
        cop_match = re.search(
            r"(?:mayor\s+o\s+igual\s+a|>=)\s*\$?\s*([\d]{1,3}(?:\.\d{3})+|\d{6,})",
            block,
        )
        if cop_match:
            amount = _parse_cop_amount(cop_match.group(1))
            if amount:
                extras["min_amount_cop"] = amount
                return ">=", float(amount), extras

    lte_pct = re.search(r"menor\s+o\s+igual\s+a\s*(?:al\s+)?(\d{1,3})\s*%", block)
    if lte_pct:
        percentage = float(lte_pct.group(1))
        threshold = percentage / 100 if percentage > 1 else percentage
        return "<=", threshold, extras

    lte_ratio = re.search(r"menor\s+o\s+igual\s+a\s*(0[.,]\d+)", block)
    if lte_ratio and key == "endeudamiento":
        threshold = _parse_threshold(lte_ratio.group(1))
        if threshold is not None:
            return "<=", threshold, extras

    gte_match = re.search(
        r"mayor\s+o\s+igual\s+a\s*(\d{1,3}(?:[.,]\d+)?)",
        block,
    )
    if gte_match:
        threshold = _parse_threshold(gte_match.group(1))
        if threshold is not None:
            return ">=", threshold, extras

    if default_operator:
        fallback = _find_operator_threshold(block)
        if fallback:
            operator, threshold = fallback
            if key == "endeudamiento" and operator == ">=" and threshold <= 2:
                pass
            else:
                return operator, threshold, extras

    return None, None, extras


def _financial_section_region(normalized: str) -> str:
    """Body text for capacidad financiera / organizacional (§3.5–§3.9), excluding TOC."""
    start = -1
    for pattern in (
        r"3\.5\s+capacidad financiera",
        r"3\.6\s+capacidad financiera",
    ):
        for match in re.finditer(pattern, normalized):
            window = normalized[match.start() : match.start() + 600]
            if re.search(r"proponentes\s+deberan|matriz\s*2", window):
                start = match.start()
                break
        if start >= 0:
            break
    if start < 0:
        for marker in ("solvencia economica y financiera", "indicadores financieros"):
            idx = normalized.find(marker)
            if idx >= 0:
                start = idx
                break
    if start < 0:
        return ""

    end = len(normalized)
    for marker in (
        "3.8 exigencias minimas de la experiencia",
        "3.8 experiencia",
        "3.10 acreditacion de la capacidad financiera",
        "capitulo iv. criterios de evaluacion",
    ):
        idx = normalized.find(marker, start + 100)
        if idx >= 0:
            end = min(end, idx)
    return normalized[start:end]


def _organizational_section_region(normalized: str, effective_region: str) -> str:
    """Locate capacidad organizacional (traditional §3.7 or obra documento base §3.9)."""
    for source in (effective_region, normalized):
        if not source.strip():
            continue
        for pattern in (
            r"3\.9\.?\s*capacidad organizacional",
            r"3\.7\.?\s*capacidad organizacional",
        ):
            match = re.search(pattern, source)
            if match:
                return source[match.start() : match.start() + 1_400]
    return ""


def _capital_trabajo_region(normalized: str) -> str:
    anchor = re.search(r"ct\s*=\s*ac\s*-\s*pc", normalized)
    if anchor:
        start = max(0, anchor.start() - 400)
    else:
        match = re.search(r"3\.(?:6|7)\.?\s*capital de trabajo", normalized)
        if not match:
            return ""
        start = match.start()
    end = len(normalized)
    for marker in (
        "3.7 capacidad organizacional",
        "3.8 patrimonio",
        "3.9 capacidad organizacional",
        "3.10 acreditacion de la capacidad financiera",
    ):
        idx = normalized.find(marker, start + 40)
        if idx >= 0:
            end = min(end, idx)
            break
    if end == len(normalized):
        end = min(len(normalized), start + 2800)
    return normalized[start:end]


def _find_operator_threshold(region: str) -> Optional[tuple[str, float]]:
    patterns: tuple[tuple[str, str], ...] = (
        (r"(?:>=?|≥|mayor\s+o\s+igual\s+a)\s*([\d]+(?:[.,]\d+)?)", ">="),
        (r"(?:<=?|≤|menor\s+o\s+igual\s+a)\s*([\d]+(?:[.,]\d+)?)", "<="),
    )
    for pattern, operator in patterns:
        match = re.search(pattern, region)
        if not match:
            continue
        threshold = _parse_threshold(match.group(1))
        if threshold is not None:
            return operator, threshold
    return None


def _format_threshold_display(operator: str, threshold: float) -> str:
    symbol = "≥" if operator == ">=" else "≤"
    return f"{symbol} {threshold:g}".replace(".", ",") if "," in str(threshold) else f"{symbol} {threshold:g}"


def _build_financial_indicator_item(
    *,
    key: str,
    label: str,
    formula: str,
    operator: Optional[str],
    threshold: Optional[float],
    threshold_note: Optional[str],
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str,
    confidence: float,
    extras: Optional[dict[str, Any]] = None,
    display_value_override: Optional[str] = None,
) -> RequirementItem:
    value: dict[str, Any] = {
        "indicator": key,
        "formula": formula,
        "requirement_type": "habilitante",
    }
    if extras:
        value.update(extras)
    if operator:
        value["operator"] = operator
    if threshold is not None:
        value["threshold"] = threshold
    if threshold_note:
        value["threshold_note"] = threshold_note

    min_cop = value.get("min_amount_cop")
    resolved_display = formula
    if isinstance(min_cop, (int, float)) and min_cop > 0:
        cop_display = f"${int(min_cop):,}".replace(",", ".")
        resolved_display = f"{formula} ≥ {cop_display}"
    elif operator and threshold is not None:
        if key == "endeudamiento" and threshold <= 1:
            resolved_display = f"{formula} {_format_threshold_display(operator, threshold * 100)}%"
            if operator == "<=":
                resolved_display = f"{formula} ≤ {threshold * 100:g}%"
        else:
            resolved_display = f"{formula} {_format_threshold_display(operator, threshold)}"
    elif threshold_note:
        resolved_display = f"{formula} — {threshold_note}"

    return _item(
        key=key,
        label=label,
        value=value,
        display_value=display_value_override or resolved_display,
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=evidence,
        confidence=confidence,
    )


_FINANCIAL_INDICATOR_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "liquidez_corriente",
        "label": "Índice de liquidez",
        "formula": "AC / PC",
        "default_operator": ">=",
        "patterns": (r"indice\s+de\s+liquidez", r"liquidez\s+corriente"),
    },
    {
        "key": "endeudamiento",
        "label": "Índice de endeudamiento",
        "formula": "PT / AT",
        "default_operator": "<=",
        "patterns": (r"indice\s+de\s+endeudamiento", r"nivel\s+de\s+endeudamiento", r"\bendeudamiento\b"),
    },
    {
        "key": "cobertura_intereses",
        "label": "Razón de cobertura de intereses",
        "formula": "UO / Gastos por intereses",
        "default_operator": ">=",
        "patterns": (
            r"razon\s+de\s+cobertura\s+de\s+intereses",
            r"cobertura\s+de\s+intereses",
            r"utilidad\s+operacional\s*/\s*gastos?\s+por\s+intereses?",
        ),
    },
    {
        "key": "patrimonio_minimo",
        "label": "Patrimonio mínimo",
        "formula": "AT − PT",
        "default_operator": ">=",
        "patterns": (
            r"patrimonio\s+minimo",
            r"patrimonio\s+liquido",
            r"patrimonio\s+neto",
            r"patrimonio\s*\(\s*activo\s+total",
            r"patrimonio\s+activo\s+total\s*[-–]",
        ),
    },
    {
        "key": "rentabilidad_patrimonio",
        "label": "Rentabilidad del patrimonio (ROE)",
        "formula": "UO / Patrimonio",
        "default_operator": ">=",
        "patterns": (r"rentabilidad\s+del\s+patrimonio", r"rentabilidad\s+sobre\s+patrimonio"),
    },
    {
        "key": "rentabilidad_activo",
        "label": "Rentabilidad del activo (ROA)",
        "formula": "UO / Activo total",
        "default_operator": ">=",
        "patterns": (r"rentabilidad\s+del\s+activo",),
    },
)


def _extract_financial_indicator_items(
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
    *,
    matriz_2_referenced: bool,
    section: str = "financial",
) -> list[RequirementItem]:
    items: list[RequirementItem] = []
    seen: set[str] = set()
    blocks = _split_financial_blocks(region)

    matriz_defaults = {
        "liquidez_corriente",
        "endeudamiento",
        "cobertura_intereses",
    }
    if section == "organizational":
        matriz_defaults = {"rentabilidad_patrimonio", "rentabilidad_activo"}

    for spec in _FINANCIAL_INDICATOR_SPECS:
        key = str(spec["key"])
        if section == "financial" and key in {"rentabilidad_patrimonio", "rentabilidad_activo"}:
            continue
        if section == "organizational" and key not in {"rentabilidad_patrimonio", "rentabilidad_activo"}:
            continue
        if key == "capital_trabajo":
            continue

        block = blocks.get(key, "")
        match: Optional[re.Match[str]] = None
        if not block:
            for pattern in spec["patterns"]:
                for candidate in re.finditer(pattern, region):
                    snippet = region[candidate.start() : candidate.end() + 40]
                    if re.search(r"\.{8,}", snippet):
                        continue
                    if key == "patrimonio_minimo":
                        prefix = region[max(0, candidate.start() - 30) : candidate.start()]
                        if "rentabilidad" in prefix:
                            continue
                    match = candidate
                    block = region[candidate.start() : min(len(region), candidate.end() + 400)]
                    break
                if match or block:
                    break

        if not block and not (matriz_2_referenced and key in matriz_defaults):
            continue

        threshold_note: Optional[str] = None
        default_operator = str(spec["default_operator"])
        operator: Optional[str] = default_operator
        threshold: Optional[float] = None
        extras: dict[str, Any] = {}

        if block:
            parsed_operator, parsed_threshold, parsed_extras = _parse_indicator_threshold(
                block,
                key,
                default_operator,
            )
            if parsed_operator:
                operator = parsed_operator
            if parsed_threshold is not None:
                threshold = parsed_threshold
            extras = parsed_extras
            block_start = region.find(block[: min(30, len(block))])
            evidence = _snippet(region, max(0, block_start), block_start + len(block))
        else:
            evidence = "Indicadores definidos en Matriz 2 – Indicadores financieros y organizacionales"

        if threshold is None and matriz_2_referenced and key in matriz_defaults:
            threshold_note = "Umbrales según Matriz 2 (ver anexo del proceso)"

        if key in seen:
            continue
        seen.add(key)

        items.append(
            _build_financial_indicator_item(
                key=key,
                label=str(spec["label"]),
                formula=str(spec["formula"]),
                operator=operator,
                threshold=threshold,
                threshold_note=threshold_note,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
                confidence=0.9 if threshold is not None or extras else 0.82,
                extras=extras,
            )
        )

    return items


def _extract_capital_trabajo_item(
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> Optional[RequirementItem]:
    blocks = _split_financial_blocks(normalized)
    traditional_block = blocks.get("capital_trabajo", "")
    if traditional_block:
        operator, threshold, extras = _parse_indicator_threshold(
            traditional_block,
            "capital_trabajo",
            ">=",
        )
        if extras.get("min_amount_cop") or threshold is not None:
            block_start = normalized.find(traditional_block[: min(30, len(traditional_block))])
            return _build_financial_indicator_item(
                key="capital_trabajo",
                label="Capital de trabajo",
                formula="CT = AC − PC",
                operator=operator or ">=",
                threshold=threshold,
                threshold_note=None,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, max(0, block_start), block_start + len(traditional_block)),
                confidence=0.92,
                extras={**extras, "compare_to": "mínimo exigido"},
            )

    region = _capital_trabajo_region(normalized)
    if not region:
        inline = re.search(
            r"capital\s+de\s+trabajo[^.]{0,220}(?:activo\s+corriente|ac)\s*[-–]\s*"
            r"(?:pasivo\s+corriente|pc)[^.]{0,120}(?:mayor\s+o\s+igual|>=)",
            normalized,
        )
        if inline:
            region = normalized[max(0, inline.start() - 40) : inline.end() + 120]
        else:
            return None

    value: dict[str, Any] = {
        "indicator": "capital_trabajo",
        "formula": "CT = AC − PC",
        "operator": ">=",
        "compare_to": "CTd",
        "requirement_type": "habilitante",
    }
    display_parts = ["CT = AC − PC ≥ CTd"]

    cop_match = re.search(
        r"(?:mayor\s+o\s+igual\s+a|>=)\s*\$?\s*([\d]{1,3}(?:\.\d{3})+|\d{6,})",
        region,
    )
    if cop_match:
        amount = _parse_cop_amount(cop_match.group(1))
        if amount:
            value["min_amount_cop"] = amount
            cop_display = f"${amount:,}".replace(",", ".")
            display_parts = [f"CT = AC − PC ≥ {cop_display}"]

    ctd_pct_match = re.search(
        r"ctd\s*=\s*\(\s*poe\s*-\s*anticipo[^)]*\)\s*x\s*(\d{1,3})\s*%",
        region,
    )
    if ctd_pct_match:
        percentage = float(ctd_pct_match.group(1))
        value["ctd_formula"] = "(POE − Anticipo) × {pct}%".format(pct=percentage)
        value["ctd_percentage"] = percentage
        display_parts.append(f"CTd = (POE − Anticipo) × {percentage:g}%")
    else:
        generic_ctd = re.search(
            r"capital\s+de\s+trabajo\s+demandado[^.]{0,200}?(\d{1,3})\s*%",
            region,
        )
        if generic_ctd:
            percentage = float(generic_ctd.group(1))
            value["ctd_percentage"] = percentage
            display_parts.append(f"CTd: {percentage:g}% del PO")

    if re.search(r"menor\s+a\s+doce\s*\(\s*12\s*\)\s+meses", region):
        value["ctd_condition"] = "Plazo de ejecución < 12 meses"
        display_parts.append("Aplica si plazo < 12 meses")

    if re.search(r"no\s+excedera\s+el\s+valor\s+del\s+presupuesto\s+oficial", region):
        value["ctd_cap"] = "No excede el Presupuesto Oficial"

    anchor = re.search(r"ct\s*=\s*ac\s*-\s*pc", region)
    evidence_start = anchor.start() if anchor else 0
    return _item(
        key="capital_trabajo",
        label="Capital de trabajo",
        value=value,
        display_value=" · ".join(display_parts),
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=_snippet(region, evidence_start, evidence_start + 220),
        confidence=0.92,
    )


def _extract_financial_accreditation_item(
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> Optional[RequirementItem]:
    anchor = re.search(
        r"3\.7\.1\s+acreditacion de la capacidad financiera",
        region,
    )
    if not anchor:
        anchor = re.search(r"evaluacion financiera y organizacional", region)
    if not anchor:
        anchor = re.search(
            r"registro\s+unico\s+de\s+proponentes|\brup\b",
            region,
        )
    if not anchor:
        return None

    window = region[anchor.start() : min(len(region), anchor.start() + 900)]
    uses_rup = bool(re.search(r"registro\s+unico\s+de\s+proponentes|\brup\b", window))
    display = (
        "Información del RUP vigente y en firme (Decreto 1082 de 2015)"
        if uses_rup
        else "Estados financieros y documentos del numeral 3.7.1"
    )
    return _item(
        key="accreditation_method",
        label="Cómo acreditar",
        value=display,
        display_value=display,
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=_snippet(region, anchor.start(), anchor.start() + 200),
        confidence=0.9,
    )


def _extract_financial_exemptions_item(
    region: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> Optional[RequirementItem]:
    exemptions: list[str] = []
    if re.search(r"no\s+tiene\s+pasivos\s+corrientes[^.]{0,120}habilitado[^.]{0,80}liquidez", region):
        exemptions.append("Sin pasivos corrientes: habilitado en liquidez")
    if re.search(
        r"no\s+tiene\s+gastos\s+de\s+intereses[^.]{0,160}cobertura\s+de\s+intereses",
        region,
    ):
        exemptions.append(
            "Sin gastos por intereses: habilitado en cobertura de intereses (UO ≥ 0)"
        )
    if re.search(r"mipyme\s+domiciliada", region):
        exemptions.append("Mipyme: indicadores según Matriz 2 (certificado RUP)")

    if not exemptions:
        return None

    display = "; ".join(exemptions)
    return _item(
        key="financial_exemptions",
        label="Excepciones y casos especiales",
        value=exemptions,
        display_value=display,
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=display,
        confidence=0.86,
    )


_MATRIZ_INDICATOR_ROW_PATTERNS: dict[str, re.Pattern[str]] = {
    "liquidez_corriente": re.compile(
        r"indice de liquidez\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)"
    ),
    "endeudamiento": re.compile(
        r"indice de endeudamiento\s*(<=?|≤)\s*([0-9]+(?:[.,][0-9]+)?)\s*(<=?|≤)\s*([0-9]+(?:[.,][0-9]+)?)"
    ),
    "cobertura_intereses": re.compile(
        r"razon de cobertura de intereses\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)"
    ),
    "rentabilidad_patrimonio": re.compile(
        r"rentabilidad del patrimonio\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)"
    ),
    "rentabilidad_activo": re.compile(
        r"rentabilidad del activo\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)\s*(>=?|≥)\s*([0-9]+(?:[.,][0-9]+)?)"
    ),
}

_FINANCIAL_METRIC_KEYS = frozenset(
    {
        "liquidez_corriente",
        "endeudamiento",
        "cobertura_intereses",
        "patrimonio_minimo",
        "rentabilidad_patrimonio",
        "rentabilidad_activo",
    }
)

_PLIEGO_FINANCIAL_PRIORITY_KEYS = frozenset(
    {
        "capital_trabajo",
        "accreditation_method",
        "financial_exemptions",
        "financial_summary",
        "qualification_score",
    }
)

_FINANCIAL_ITEM_ORDER: tuple[str, ...] = (
    "financial_summary",
    "liquidez_corriente",
    "endeudamiento",
    "cobertura_intereses",
    "capital_trabajo",
    "patrimonio_minimo",
    "rentabilidad_patrimonio",
    "rentabilidad_activo",
    "matriz_2_reference",
    "accreditation_method",
    "financial_exemptions",
    "qualification_score",
)


def _is_matriz_indicadores_document(source_document: str, normalized: str) -> bool:
    if source_document == "indicadores_financieros":
        return True
    return bool(
        re.search(r"matriz\s*2\b", normalized[:400])
        and "valor concertado" in normalized
        and "rango 1" in normalized
        and "indice de liquidez" in normalized
    )


def _matriz_table_section(normalized: str, *, demas_proponentes: bool) -> str:
    if demas_proponentes:
        start_match = re.search(r"demas proponentes", normalized)
        if not start_match:
            return ""
        start = start_match.start()
        end_match = re.search(
            r"indicadores de capacidad financiera y organizacional para el rango",
            normalized[start:],
        )
        end = start + end_match.start() if end_match else len(normalized)
        return normalized[start:end]

    start_match = re.search(
        r"indices de capacidad financiera y organizacionales para mipyme",
        normalized,
    )
    if not start_match:
        return ""
    start = start_match.start()
    end_match = re.search(r"demas proponentes", normalized[start:])
    end = start + end_match.start() if end_match else len(normalized)
    return normalized[start:end]


def _operator_from_matriz_symbol(symbol: str) -> str:
    return "<=" if "≤" in symbol or "<=" in symbol else ">="


def _format_matriz_dual_threshold(
    key: str,
    operator_1: str,
    threshold_1: float,
    operator_2: str,
    threshold_2: float,
) -> str:
    if key == "endeudamiento":
        return (
            f"≤ {threshold_1 * 100:g}% (R1) · "
            f"≤ {threshold_2 * 100:g}% (R2)"
        )
    symbol_1 = "≥" if operator_1 == ">=" else "≤"
    symbol_2 = "≥" if operator_2 == ">=" else "≤"
    return f"{symbol_1} {threshold_1:g} (R1) · {symbol_2} {threshold_2:g} (R2)"


_MATRIZ_PROSE_FINANCIAL_HEAD = re.compile(
    r"indice de liquidez mayor o igual a\s*([\d.,]+)\s*"
    r"indice de endeudamiento menor o igual a\s*([\d.,]+)\s*%?\s*"
    r"razon(?: de)? cobertura de intereses mayor o igual a\s*([\d.,]+)",
    re.IGNORECASE,
)


def _parse_matriz_prose_percentage_threshold(raw: str) -> Optional[float]:
    threshold = _parse_threshold(raw)
    if threshold is None:
        return None
    if threshold >= 1:
        return threshold / 100
    return threshold


def _parse_matriz_prose_rentabilidad(segment: str) -> dict[str, tuple[str, float]]:
    parsed: dict[str, tuple[str, float]] = {}
    roe_match = re.search(
        r"rentabilidad del patrimonio mayor o igual a\s*([\d.,]+)\s*%",
        segment,
    )
    if roe_match:
        threshold = _parse_matriz_prose_percentage_threshold(roe_match.group(1))
        if threshold is not None:
            parsed["rentabilidad_patrimonio"] = (">=", threshold)
    roa_match = re.search(
        r"rentabilidad del activo mayor o igual a\s*([\d.,]+)\s*%",
        segment,
    )
    if roa_match:
        threshold = _parse_matriz_prose_percentage_threshold(roa_match.group(1))
        if threshold is not None:
            parsed["rentabilidad_activo"] = (">=", threshold)
    return parsed


def _parse_matriz_prose_financial_blocks(normalized: str) -> list[dict[str, Any]]:
    """
    Parse entity-specific Matriz 2 PDFs that list thresholds in prose instead of tables.

  Example: "índice de liquidez mayor o igual a 1,1 índice de endeudamiento menor o igual a 70% ..."
    """
    matches = list(_MATRIZ_PROSE_FINANCIAL_HEAD.finditer(normalized))
    if not matches:
        return []

    blocks: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        chunk = normalized[match.start() : match.start() + 450]
        block: dict[str, Any] = {
            "liquidez_corriente": (">=", _parse_threshold(match.group(1))),
            "endeudamiento": ("<=", _parse_matriz_prose_percentage_threshold(match.group(2))),
            "cobertura_intereses": (">=", _parse_threshold(match.group(3))),
        }

        capital_match = re.search(
            r"capital de trabajo(?:\s+grupo)? mayor o igual a\s*\$?\s*([\d]{1,3}(?:\.\d{3})+)",
            chunk,
        )
        if capital_match:
            amount = _parse_cop_amount(capital_match.group(1))
            if amount:
                block["capital_trabajo"] = (">=", float(amount))

        if index + 1 < len(matches):
            between = normalized[match.end() : matches[index + 1].start()]
            if index == 0:
                block.update(_parse_matriz_prose_rentabilidad(between))
        else:
            tail = normalized[match.end() : match.end() + 500]
            block.update(_parse_matriz_prose_rentabilidad(tail))

        blocks.append(block)

    return blocks


def _build_matriz_item_from_ranges(
    *,
    key: str,
    spec: dict[str, Any],
    ranges: list[tuple[str, float, dict[str, Any]]],
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str,
) -> RequirementItem:
    operator_1, threshold_1, extras_1 = ranges[0]
    extras: dict[str, Any] = dict(extras_1)
    display_override: Optional[str] = None

    if len(ranges) > 1:
        operator_2, threshold_2, extras_2 = ranges[1]
        if threshold_1 != threshold_2 or operator_1 != operator_2:
            dual_display = _format_matriz_dual_threshold(
                key,
                operator_1,
                threshold_1,
                operator_2,
                threshold_2,
            )
            display_override = f"{spec['formula']} {dual_display}"
            extras["threshold_by_range"] = {
                "rango_1": {"operator": operator_1, "threshold": threshold_1},
                "rango_2": {"operator": operator_2, "threshold": threshold_2},
            }

    if key == "capital_trabajo" and extras.get("min_amount_cop"):
        display_override = None

    return _build_financial_indicator_item(
        key=key,
        label=str(spec["label"]),
        formula=str(spec["formula"]),
        operator=operator_1,
        threshold=threshold_1,
        threshold_note=None,
        source_document=source_document,
        source_document_id=source_document_id,
        evidence=evidence[:220],
        confidence=0.92,
        extras=extras,
        display_value_override=display_override,
    )


def _append_matriz_prose_indicator_items(
    items: list[RequirementItem],
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
    spec_by_key: dict[str, dict[str, Any]],
) -> list[RequirementItem]:
    prose_blocks = _parse_matriz_prose_financial_blocks(normalized)
    if not prose_blocks:
        return items

    metric_keys = (
        "liquidez_corriente",
        "endeudamiento",
        "cobertura_intereses",
        "capital_trabajo",
        "rentabilidad_patrimonio",
        "rentabilidad_activo",
    )

    for key in metric_keys:
        if any(item["key"] == key for item in items):
            continue
        spec = spec_by_key.get(key)
        if not spec and key == "capital_trabajo":
            spec = {
                "key": "capital_trabajo",
                "label": "Capital de trabajo",
                "formula": "CT = AC − PC",
            }
        if not spec:
            continue

        ranges: list[tuple[str, float, dict[str, Any]]] = []
        for block in prose_blocks:
            entry = block.get(key)
            if not entry:
                continue
            operator, threshold = entry
            if threshold is None:
                continue
            extras: dict[str, Any] = {}
            if key == "capital_trabajo":
                extras["min_amount_cop"] = int(threshold)
                extras["compare_to"] = "mínimo exigido"
            ranges.append((operator, threshold, extras))

        if not ranges:
            continue

        evidence_match = _MATRIZ_PROSE_FINANCIAL_HEAD.search(normalized)
        evidence = evidence_match.group(0) if evidence_match else normalized[:220]
        items.append(
            _build_matriz_item_from_ranges(
                key=key,
                spec=spec,
                ranges=ranges,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=evidence,
            )
        )

    return items


def _extract_matriz_2_indicators(
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    """Parse Matriz 2 table rows (Rango 1 / Rango 2) from the indicadores document."""
    items: list[RequirementItem] = []
    spec_by_key = {str(spec["key"]): spec for spec in _FINANCIAL_INDICATOR_SPECS}

    demas_section = _matriz_table_section(normalized, demas_proponentes=True)
    mipyme_section = _matriz_table_section(normalized, demas_proponentes=False)
    primary_section = demas_section or mipyme_section or normalized

    summary = (
        "Indicadores de capacidad financiera y organizacional según Matriz 2, "
        "con umbrales por rango de presupuesto (Rango 1 / Rango 2 en SMMLV)."
    )
    if _parse_matriz_prose_financial_blocks(normalized):
        summary = (
            "Indicadores de capacidad financiera y organizacional según el análisis "
            "financiero del proceso (Matriz 2), con umbrales para Mipyme y demás proponentes."
        )
    items.append(
        _item(
            key="financial_summary",
            label="Resumen",
            value=summary,
            display_value=summary,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_snippet(primary_section, 0, min(220, len(primary_section))),
            confidence=0.93,
        )
    )

    for key, pattern in _MATRIZ_INDICATOR_ROW_PATTERNS.items():
        match = pattern.search(primary_section) or pattern.search(mipyme_section)
        if not match:
            continue

        spec = spec_by_key[key]
        operator_1 = _operator_from_matriz_symbol(match.group(1))
        threshold_1 = _parse_threshold(match.group(2))
        operator_2 = _operator_from_matriz_symbol(match.group(3))
        threshold_2 = _parse_threshold(match.group(4))
        if threshold_1 is None or threshold_2 is None:
            continue

        dual_display = _format_matriz_dual_threshold(
            key,
            operator_1,
            threshold_1,
            operator_2,
            threshold_2,
        )
        items.append(
            _build_financial_indicator_item(
                key=key,
                label=str(spec["label"]),
                formula=str(spec["formula"]),
                operator=operator_1,
                threshold=threshold_1,
                threshold_note=None,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=match.group(0)[:220],
                confidence=0.94,
                extras={
                    "threshold_by_range": {
                        "rango_1": {"operator": operator_1, "threshold": threshold_1},
                        "rango_2": {"operator": operator_2, "threshold": threshold_2},
                    }
                },
                display_value_override=f"{spec['formula']} {dual_display}",
            )
        )

    if re.search(r"registro\s+unico\s+de\s+proponentes|\brup\b", normalized):
        items.append(
            _item(
                key="accreditation_method",
                label="Cómo acreditar",
                value="Registro Único de Proponentes (RUP) vigente y en firme",
                display_value="RUP vigente y en firme",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence="Registro Único de Proponentes",
                confidence=0.88,
            )
        )

    if re.search(r"\bmipyme\b", normalized):
        exemptions = _extract_financial_exemptions_item(
            normalized, source_document, source_document_id
        )
        if exemptions:
            items.append(exemptions)

    if not any(item["key"] in _FINANCIAL_METRIC_KEYS for item in items):
        items = _append_matriz_prose_indicator_items(
            items,
            normalized,
            source_document,
            source_document_id,
            spec_by_key,
        )

    if not any(item["key"] in _FINANCIAL_METRIC_KEYS for item in items):
        items = _append_matriz_template_indicator_items(
            items,
            normalized,
            source_document,
            source_document_id,
            spec_by_key,
        )

    return items


_MATRIZ_TEMPLATE_INDICATOR_PATTERNS: tuple[tuple[str, str], ...] = (
    ("liquidez_corriente", r"indice de liquidez"),
    ("endeudamiento", r"indice de endeudamiento"),
    ("cobertura_intereses", r"razon de cobertura de intereses"),
    ("rentabilidad_patrimonio", r"rentabilidad del patrimonio"),
    ("rentabilidad_activo", r"rentabilidad del activo"),
)


def _append_matriz_template_indicator_items(
    items: list[RequirementItem],
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
    spec_by_key: dict[str, dict[str, Any]],
) -> list[RequirementItem]:
    """Emit Matriz 2 indicator rows when the template lists them without numeric valores."""
    if "valor concertado" not in normalized or "indice de liquidez" not in normalized:
        return items

    for key, pattern in _MATRIZ_TEMPLATE_INDICATOR_PATTERNS:
        if any(item["key"] == key for item in items):
            continue
        if not re.search(pattern, normalized):
            continue
        spec = spec_by_key.get(key)
        if not spec:
            continue
        items.append(
            _build_financial_indicator_item(
                key=key,
                label=str(spec["label"]),
                formula=str(spec["formula"]),
                operator=str(spec["default_operator"]),
                threshold=None,
                threshold_note="Umbrales según Matriz 2 (ver anexo del proceso)",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=f"Indicador listado en Matriz 2: {spec['label']}",
                confidence=0.84,
            )
        )

    return items


def _financial_item_has_numeric_threshold(item: Optional[RequirementItem]) -> bool:
    if not item:
        return False
    value = item.get("value")
    if not isinstance(value, dict):
        return False
    return value.get("threshold") is not None or value.get("min_amount_cop") is not None


def merge_financial_requirement_items(
    matriz_items: list[RequirementItem],
    pliego_items: list[RequirementItem],
    *,
    has_matriz_document: bool,
) -> list[RequirementItem]:
    """Combine Matriz 2 numeric indicators with pliego capital de trabajo and accreditation."""
    matriz_by_key = {item["key"]: item for item in matriz_items}
    pliego_by_key = {item["key"]: item for item in pliego_items}
    merged: dict[str, RequirementItem] = {}

    for key in _FINANCIAL_ITEM_ORDER:
        chosen: Optional[RequirementItem] = None
        if key == "matriz_2_reference":
            if not has_matriz_document:
                chosen = pliego_by_key.get(key)
        elif key in _FINANCIAL_METRIC_KEYS:
            matriz_item = matriz_by_key.get(key)
            if _financial_item_has_numeric_threshold(matriz_item):
                chosen = matriz_item
            else:
                chosen = pliego_by_key.get(key) or matriz_item
        elif key in _PLIEGO_FINANCIAL_PRIORITY_KEYS:
            matriz_item = matriz_by_key.get(key)
            pliego_item = pliego_by_key.get(key)
            if key == "capital_trabajo":
                matriz_value = matriz_item.get("value") if matriz_item else None
                if isinstance(matriz_value, dict) and matriz_value.get("min_amount_cop"):
                    chosen = matriz_item
                else:
                    chosen = pliego_item or matriz_item
            else:
                chosen = pliego_item or matriz_item
        else:
            chosen = matriz_by_key.get(key) or pliego_by_key.get(key)
        if chosen:
            merged[key] = chosen

    for item in matriz_items + pliego_items:
        key = item["key"]
        if has_matriz_document and key == "matriz_2_reference":
            continue
        if key not in merged:
            merged[key] = item

    return [merged[key] for key in _FINANCIAL_ITEM_ORDER if key in merged] + [
        merged[key]
        for key in merged
        if key not in _FINANCIAL_ITEM_ORDER
    ]


def extract_indicadores_financieros(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    normalized = normalize_text(text)
    if _is_matriz_indicadores_document(source_document, normalized):
        return _extract_matriz_2_indicators(normalized, source_document, source_document_id)

    items: list[RequirementItem] = []

    for label, stop_labels in (
        (
            "solvencia economica y financiera",
            ("experiencia general", "requisitos legales", "capitulo iv"),
        ),
        (
            "capacidad financiera",
            ("capital de trabajo", "experiencia general", "capitulo iv"),
        ),
        (
            "indicadores financieros",
            ("experiencia general", "requisitos legales"),
        ),
    ):
        financial_block = _extract_labeled_block(normalized, label, stop_labels)
        if financial_block and len(financial_block) > 40:
            items.append(
                _item(
                    key="financial_summary",
                    label="Resumen",
                    value=financial_block,
                    display_value=_clean_requirement_text(financial_block, max_len=320),
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=financial_block[:220],
                    confidence=0.88,
                )
            )
            break

    regions = _region_near_marker(text, FINANCIAL_REGION_MARKERS)
    financial_region = _financial_pliego_region(normalized)
    if not regions:
        regions = [financial_region[:8000]] if financial_region else [normalized[:8000]]

    matriz_2_referenced = bool(
        re.search(r"matriz\s*2\b", financial_region or normalized[:60_000])
    )

    for region in regions:
        if (
            "experiencia general" in region[:220]
            and "solvencia" not in region[:400]
            and "capacidad financiera" not in region[:400]
        ):
            continue

        if not any(item["key"] == "accreditation_method" for item in items):
            accreditation_match = re.search(
                r"(?:formato\s*4|matriz\s*2|registro\s+unico\s+de\s+proponentes|\brup\b)",
                region,
            )
            if accreditation_match:
                display = (
                    "Información del RUP vigente y en firme"
                    if "rup" in accreditation_match.group(0)
                    else accreditation_match.group(0).title()
                )
                items.append(
                    _item(
                        key="accreditation_method",
                        label="Cómo acreditar",
                        value=display,
                        display_value=display,
                        source_document=source_document,
                        source_document_id=source_document_id,
                        evidence=_snippet(
                            region,
                            accreditation_match.start(),
                            accreditation_match.end() + 80,
                        ),
                        confidence=0.85,
                    )
                )

    if not any(item["key"] == "financial_summary" for item in items):
        summary = (
            "Acreditar indicadores de capacidad financiera y organizacional según "
            "Matriz 2 y numeral 3.7.1 del pliego."
            if matriz_2_referenced
            else "Acreditar los indicadores financieros de habilitación definidos en el pliego."
        )
        evidence_region = financial_region or (regions[0] if regions else normalized)
        items.append(
            _item(
                key="financial_summary",
                label="Resumen",
                value=summary,
                display_value=summary,
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(evidence_region, 0, min(220, len(evidence_region))),
                confidence=0.9,
            )
        )

    return _append_financial_supplements(
        items,
        financial_region,
        normalized,
        source_document,
        source_document_id,
    )


_LEGAL_TOPIC_STOP_MARKERS: tuple[str, ...] = (
    "existencia y representacion legal",
    "seguridad social",
    "solvencia economica",
    "capacidad financiera",
    "indicadores financieros",
    "experiencia general",
    "exigencias minimas de la experiencia",
    "capitulo iv",
    "carta de presentacion",
)

_LEGAL_TOPIC_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key_prefix": "capacidad_juridica",
        "label": "Capacidad jurídica",
        "start_markers": (
            "3.2 capacidad juridica",
            "capacidad juridica",
            "requisitos legales",
            "habilitacion juridica",
        ),
        "stop_markers": _LEGAL_TOPIC_STOP_MARKERS + ("3.3",),
        "lettered_debe_phrase": "los proponentes deben",
        "prefer_phrases": ("los proponentes deben", "no estar incursos"),
    },
    {
        "key_prefix": "existencia_representacion",
        "label": "Existencia y representación legal",
        "start_markers": (
            "3.3 existencia y representacion legal",
            "existencia y representacion legal",
        ),
        "stop_markers": (
            "seguridad social",
            "capacidad financiera",
            "experiencia general",
            "solvencia economica",
            "3.4",
        ),
        "prefer_phrases": ("3.3.1 personas naturales", "deben presentar"),
        "subsection_markers": (
            ("personas naturales", "personas_naturales", "Personas naturales"),
            ("personas juridicas", "personas_juridicas", "Personas jurídicas"),
            ("proponentes plurales", "proponentes_plurales", "Proponentes plurales"),
            ("entidades estatales", "entidades_estatales", "Entidades estatales"),
        ),
    },
    {
        "key_prefix": "seguridad_social",
        "label": "Seguridad social y aportes legales",
        "start_markers": (
            "3.4 certificacion de pagos al sistema de seguridad social",
            "seguridad social y aportes legales",
            "certificacion de pagos al sistema de seguridad social",
            "seguridad social",
        ),
        "stop_markers": (
            "capacidad financiera",
            "solvencia economica",
            "experiencia general",
            "capital de trabajo",
            "indicadores financieros",
            "3.5",
        ),
        "prefer_phrases": ("3.4.1 personas juridicas", "formato 5"),
        "subsection_markers": (
            ("personas juridicas", "personas_juridicas", "Personas jurídicas"),
            ("personas naturales", "personas_naturales", "Personas naturales"),
            ("proponentes plurales", "proponentes_plurales", "Proponentes plurales"),
            (
                "seguridad social para la suscripcion del contrato",
                "suscripcion_contrato",
                "Para la suscripción del contrato",
            ),
        ),
    },
)


def _clean_pliego_section_body(text: str, *, max_len: int = 4_000) -> str:
    cleaned = re.sub(
        r"documento base.{0,160}?version\s+no\.?\s*\d+",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r"codigo cce-[a-z0-9-]+.{0,60}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"pagina\s+\d+\s+de\s+\d+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"interventoria de obra publica.{0,80}", " ", cleaned, flags=re.IGNORECASE)
    return _clean_requirement_text(cleaned, max_len=max_len)


def _is_toc_occurrence(normalized: str, index: int, marker_len: int) -> bool:
    after = normalized[index + marker_len : index + marker_len + 16]
    return bool(re.match(r"\s*\.{4,}", after))


def _find_topic_section(
    normalized: str,
    start_markers: tuple[str, ...],
    stop_markers: tuple[str, ...],
    *,
    max_window: int = 8_000,
    prefer_phrases: tuple[str, ...] = (),
) -> str:
    candidates: list[tuple[str, int]] = []
    for marker in start_markers:
        search_from = 0
        while True:
            index = normalized.find(marker, search_from)
            if index < 0:
                break
            if _is_toc_occurrence(normalized, index, len(marker)):
                search_from = index + len(marker)
                continue
            fragment = normalized[index + len(marker) :]
            end = min(max_window, len(fragment))
            for stop in stop_markers:
                stop_idx = fragment.lower().find(stop.lower())
                if stop_idx >= 0:
                    end = min(end, stop_idx)
            body = _clean_pliego_section_body(fragment[:end])
            if len(body) > 50:
                score = len(body)
                for phrase in prefer_phrases:
                    if phrase.lower() in body.lower():
                        score += 10_000
                candidates.append((body, score))
            search_from = index + len(marker)

    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[1])[0]


def _extract_lettered_requirements(
    section_body: str,
    *,
    key_prefix: str,
    label_prefix: str,
    stop_phrase: str = "la entidad",
) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    region = section_body
    stop_idx = region.lower().find(stop_phrase)
    if stop_idx >= 0:
        region = region[:stop_idx]

    for match in re.finditer(
        r"\b([a-f])\.\s+(.+?)(?=\s+[a-f]\.\s+|\Z)",
        region,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        letter = match.group(1).lower()
        text = _clean_requirement_text(match.group(2), max_len=420)
        if len(text) < 20:
            continue
        items.append(
            (
                f"{key_prefix}_{letter}",
                f"{label_prefix} ({letter.upper()})",
                text,
            )
        )
    return items


def _extract_subsection_by_marker(
    section_body: str,
    marker: str,
    stop_markers: tuple[str, ...],
) -> str:
    search_from = 0
    while True:
        index = section_body.lower().find(marker.lower(), search_from)
        if index < 0:
            return ""
        after = section_body[index + len(marker) : index + len(marker) + 10]
        if re.match(r"\s*\.{4,}", after):
            search_from = index + len(marker)
            continue
        fragment = section_body[index + len(marker) :]
        end = len(fragment)
        for stop in stop_markers:
            stop_idx = fragment.lower().find(stop.lower())
            if stop_idx >= 0:
                end = min(end, stop_idx)
        body = _clean_pliego_section_body(fragment[:end], max_len=1_200)
        if len(body) > 40:
            return body
        search_from = index + len(marker)
    return ""


def _concise_legal_bullet(text: str, max_len: int = 160) -> str:
    cleaned = _clean_requirement_text(text, max_len=900)
    for delimiter in (". ", "; "):
        if delimiter in cleaned:
            first = cleaned.split(delimiter, 1)[0].strip()
            if len(first) >= 24:
                cleaned = first
                break
    if len(cleaned) > max_len:
        trimmed = cleaned[: max_len - 3].rsplit(" ", 1)[0]
        cleaned = f"{trimmed}..."
    return cleaned


def _append_legal_section_item(
    items: list[RequirementItem],
    seen_keys: set[str],
    *,
    key: str,
    label: str,
    display_value: str,
    source_document: str,
    source_document_id: Optional[UUID],
    evidence: str = "",
    confidence: float = 0.9,
) -> None:
    if key in seen_keys or not display_value.strip():
        return
    seen_keys.add(key)
    normalized_evidence = evidence.strip()
    normalized_display = display_value.strip()
    items.append(
        _item(
            key=key,
            label=label,
            value=display_value,
            display_value=display_value,
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=normalized_evidence[:220]
            if normalized_evidence and normalized_evidence != normalized_display
            else "",
            confidence=confidence,
        )
    )


def _extract_requirement_sentences(section_body: str, max_bullets: int = 6) -> list[str]:
    bullets: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", section_body):
        normalized = normalize_text(sentence)
        if len(normalized) < 30:
            continue
        if "modalidades" in normalized and not re.search(r"\bdebe(?:r|n)?\b", normalized):
            continue
        if not re.search(
            r"\bdebe(?:r|n)?\b|acreditar|presentar|certificado|no estar|no debera|informar",
            normalized,
        ):
            continue
        bullet = _concise_legal_bullet(sentence)
        if bullet and bullet not in bullets:
            bullets.append(bullet)
        if len(bullets) >= max_bullets:
            break
    return bullets


def _extract_topic_requirements(
    section_body: str,
    spec: dict[str, Any],
) -> list[tuple[str, str, str]]:
    key_prefix = str(spec["key_prefix"])
    label = str(spec["label"])
    bullets: list[str] = []

    debe_phrase = spec.get("lettered_debe_phrase")
    if debe_phrase:
        debe_idx = section_body.lower().find(str(debe_phrase).lower())
        if debe_idx >= 0:
            letter_region = section_body[debe_idx:]
            stop_idx = letter_region.lower().find("la entidad debe consultar")
            if stop_idx > 0:
                letter_region = letter_region[:stop_idx]
            for match in re.finditer(
                r"\b([a-f])\.\s+(.+?)(?=\s+[a-f]\.\s+|\Z)",
                letter_region,
                flags=re.IGNORECASE | re.DOTALL,
            ):
                bullet = _concise_legal_bullet(match.group(2))
                if len(bullet) >= 20:
                    bullets.append(bullet)

    subsection_markers = spec.get("subsection_markers") or ()
    subsection_stops = tuple(marker for marker, _, _ in subsection_markers) + (
        "capacidad financiera",
        "experiencia general",
    )
    for marker, _sub_key, sub_label in subsection_markers:
        body = _extract_subsection_by_marker(section_body, marker, subsection_stops)
        if body:
            bullets.append(f"{sub_label}: {_concise_legal_bullet(body, max_len=140)}")

    if not bullets:
        bullets.extend(_extract_requirement_sentences(section_body))

    if not bullets and key_prefix == "capacidad_juridica":
        for _key, _label, display in _extract_simple_legal_clauses(section_body):
            if display not in bullets:
                bullets.append(display)

    antecedentes_match = re.search(
        r"la entidad debe consultar los antecedentes.+",
        section_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if antecedentes_match and key_prefix == "capacidad_juridica":
        bullets.append(_concise_legal_bullet(antecedentes_match.group(0), max_len=160))

    if not bullets:
        return []

    unique_bullets: list[str] = []
    seen_bullets: set[str] = set()
    for bullet in bullets:
        normalized = normalize_text(bullet)
        if normalized in seen_bullets:
            continue
        seen_bullets.add(normalized)
        unique_bullets.append(bullet)

    display = "\n".join(f"• {bullet}" for bullet in unique_bullets[:6])
    return [(f"{key_prefix}_resumen", label, display)]


def _extract_simple_legal_clauses(
    section_body: str,
) -> list[tuple[str, str, str]]:
    clauses: list[tuple[str, str, str]] = []
    normalized_body = normalize_text(section_body)

    if re.search(r"registro\s+unico\s+de\s+proponentes|\binscrip\w+\s+en\s+el\s+rup\b|\brup\b", normalized_body):
        match = re.search(
            r"[^.]{0,40}(?:registro\s+unico\s+de\s+proponentes|\brup\b)[^.]{0,180}\.",
            section_body,
            flags=re.IGNORECASE,
        )
        text = _clean_requirement_text(match.group(0) if match else section_body[:200], max_len=280)
        clauses.append(("rup_vigente", "Inscripción vigente en el RUP", text))

    if re.search(r"capacidad\s+juridica|personeria\s+juridica", normalized_body):
        match = re.search(
            r"[^.]{0,20}capacidad\s+juridica[^.]{0,180}\.",
            section_body,
            flags=re.IGNORECASE,
        )
        text = _clean_requirement_text(match.group(0) if match else "Acreditar capacidad jurídica", max_len=280)
        clauses.append(("legal_capacity", "Capacidad jurídica", text))

    license_match = re.search(
        r"licencia\s+de\s+construccion|registro\s+nacional\s+de\s+contratistas|\brnc\b",
        normalized_body,
    )
    if license_match:
        match = re.search(
            r"[^.]{0,20}(?:licencia\s+de\s+construccion|registro\s+nacional\s+de\s+contratistas|\brnc\b)[^.]{0,120}\.",
            section_body,
            flags=re.IGNORECASE,
        )
        text = _clean_requirement_text(match.group(0) if match else license_match.group(0), max_len=280)
        clauses.append(("specific_license", "Habilitación específica para contratar", text))

    return clauses


def _append_rup_validity_if_present(
    items: list[RequirementItem],
    seen_keys: set[str],
    normalized: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> None:
    rup_match = re.search(
        r"(?:certificado|registro\s+unico\s+de\s+proponentes|\brup\b).{0,220}?(\d{1,3})\s*\)?\s*dias",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not rup_match or "rup_certificate_validity" in seen_keys:
        return
    days = int(rup_match.group(1))
    seen_keys.add("rup_certificate_validity")
    items.append(
        _item(
            key="rup_certificate_validity",
            label="Vigencia del certificado RUP",
            value=days,
            display_value=f"Certificado RUP expedido máximo {days} días antes del cierre",
            source_document=source_document,
            source_document_id=source_document_id,
            evidence=_snippet(normalized, rup_match.start(), rup_match.end() + 60),
            confidence=0.9,
        )
    )


_LEGAL_ITEM_ORDER: tuple[str, ...] = (
    "rup_certificate_validity",
    "rup_vigente",
    "capacidad_juridica_resumen",
    "existencia_representacion_resumen",
    "seguridad_social_resumen",
    "requisitos_legales_resumen",
    "legal_capacity",
    "specific_license",
)


def _dedupe_legal_requirement_items(items: list[RequirementItem]) -> list[RequirementItem]:
    filtered = [
        item
        for item in items
        if not re.search(r"_(a|b|c|d|e|f)$", item["key"])
        and not item["key"].endswith("_antecedentes")
    ]
    by_key = {item["key"]: item for item in filtered}
    if by_key.get("rup_certificate_validity"):
        by_key.pop("rup_vigente", None)

    ordered = [by_key[key] for key in _LEGAL_ITEM_ORDER if key in by_key]
    for key, item in by_key.items():
        if key not in _LEGAL_ITEM_ORDER:
            ordered.append(item)
    return ordered[:5]


def extract_requisitos_legales(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    seen_keys: set[str] = set()
    normalized = normalize_text(text)

    for spec in _LEGAL_TOPIC_SPECS:
        section_body = _find_topic_section(
            normalized,
            tuple(spec["start_markers"]),
            tuple(spec["stop_markers"]),
            prefer_phrases=tuple(spec.get("prefer_phrases", ())),
        )
        if not section_body:
            continue

        for key, label, display in _extract_topic_requirements(section_body, spec):
            _append_legal_section_item(
                items,
                seen_keys,
                key=key,
                label=label,
                display_value=display,
                source_document=source_document,
                source_document_id=source_document_id,
            )

    if not items:
        fallback_body = _find_topic_section(
            normalized,
            ("requisitos legales", "habilitacion", "capacidad juridica"),
            _LEGAL_TOPIC_STOP_MARKERS,
        )
        if fallback_body:
            for key, label, display in _extract_simple_legal_clauses(fallback_body):
                _append_legal_section_item(
                    items,
                    seen_keys,
                    key=key,
                    label=label,
                    display_value=display,
                    source_document=source_document,
                    source_document_id=source_document_id,
                )
            if not items:
                summary = _clean_pliego_section_body(fallback_body, max_len=420)
                _append_legal_section_item(
                    items,
                    seen_keys,
                    key="requisitos_legales_resumen",
                    label="Requisitos legales y habilitación",
                    display_value=summary,
                    source_document=source_document,
                    source_document_id=source_document_id,
                )

    _append_rup_validity_if_present(
        items,
        seen_keys,
        normalized,
        source_document,
        source_document_id,
    )

    return _dedupe_legal_requirement_items(items)


from app.services.tender_requirements.scoring_extraction import extract_sistema_puntos  # noqa: E402


EXTRACTORS = {
    "experiencia_general": extract_experiencia_general,
    "experiencia_especifica": extract_experiencia_especifica,
    "indicadores_financieros": extract_indicadores_financieros,
    "requisitos_legales": extract_requisitos_legales,
    "sistema_puntos": extract_sistema_puntos,
}
