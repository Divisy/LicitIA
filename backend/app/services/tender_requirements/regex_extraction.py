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
    ("indicadores_financieros", "Indicadores financieros y solvencia", "pliego_condiciones"),
    ("requisitos_legales", "Requisitos legales y habilitación", "pliego_condiciones"),
    ("otros", "Otros requisitos relevantes", "pliego_condiciones"),
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
    match = re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _clean_requirement_text(match.group(1))


def _merge_items(existing: list[RequirementItem], new_items: list[RequirementItem]) -> list[RequirementItem]:
    merged = list(existing)
    seen = {item["key"] for item in merged}
    for item in new_items:
        if item["key"] in seen:
            continue
        merged.append(item)
        seen.add(item["key"])
    return merged


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
        r"3\.8\.1.{0,4000}?(?=3\.8\.2|3\.9|capitulo|capítulo|\Z)",
        normalized,
        flags=re.DOTALL,
    )
    section_region = section_region_match.group(0) if section_region_match else normalized

    hundred_match = re.search(
        r"cien\s+por\s+ciento\s*\(\s*100\s*%|100\s*%[^.\n]{0,80}"
        r"(?:presupuesto\s+oficial|proceso\s+de\s+contratacion)",
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
        percent_match = re.search(
            r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|por ciento)[^.\n]{0,80}"
            r"(?:del\s+)?(?:presupuesto|valor|contrato)",
            region,
        )
        if percent_match and not any(item["key"] == "min_percentage_budget" for item in items):
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

    return items


def extract_experiencia_especifica(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)

    specific_block = _extract_labeled_block(
        normalized,
        "experiencia especifica",
        ("a. la experiencia", "b. el proponente", "requisitos de experiencia"),
    )
    if specific_block:
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

    code_matches = re.findall(
        r"(?:codigo(?:s)?|c[oó]digo(?:s)?\s+unspsc|unspsc)"
        r"[^.\n]{0,40}?(\d{6,8}(?:\s*[,/]\s*\d{6,8})*)",
        normalized,
    )
    if code_matches:
        raw_codes = [code for code in re.findall(r"\d{6,8}", code_matches[0]) if not code.startswith(("19", "20"))]
        if raw_codes:
            items.append(
                _item(
                    key="activity_codes",
                    label="Códigos de actividad",
                    value=raw_codes,
                    display_value=", ".join(raw_codes),
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=code_matches[0][:180],
                    confidence=0.75,
                )
            )

    return items


def _parse_threshold(raw: str) -> Optional[float]:
    cleaned = raw.strip().rstrip(".")
    if not cleaned:
        return None
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None


def extract_indicadores_financieros(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)
    indicator_patterns: tuple[tuple[str, str, str], ...] = (
        (r"liquidez\s+corriente", "liquidez_corriente", "Índice de liquidez corriente"),
        (r"capital\s+de\s+trabajo", "capital_trabajo", "Capital de trabajo"),
        (r"endeudamiento", "endeudamiento", "Índice de endeudamiento"),
        (r"razon\s+corriente", "razon_corriente", "Razón corriente"),
        (r"solvencia", "solvencia", "Solvencia"),
    )

    for pattern, key, label in indicator_patterns:
        for match in re.finditer(pattern, normalized):
            region = normalized[max(0, match.start() - 40) : match.end() + 120]
            threshold_match = re.search(
                r"(?:>=?|mayor\s+o\s+igual\s+a|superior\s+a|minimo|mínimo)\s*([\d.,]+)",
                region,
            )
            if threshold_match:
                threshold = _parse_threshold(threshold_match.group(1))
                if threshold is None:
                    display = label
                    value = {"indicator": key}
                else:
                    display = f"{label} ≥ {threshold:g}"
                    value = {"indicator": key, "operator": ">=", "threshold": threshold}
            else:
                display = label
                value = {"indicator": key}

            if any(item["key"] == key for item in items):
                continue

            items.append(
                _item(
                    key=key,
                    label=label,
                    value=value,
                    display_value=display,
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(normalized, match.start(), match.end() + 100),
                    confidence=0.8 if threshold_match else 0.7,
                )
            )

    score_match = re.search(
        r"(?:puntaje|puntuaci[oó]n|calificaci[oó]n)[^.\n]{0,80}"
        r"(\d{1,3}(?:[.,]\d+)?)\s*(?:puntos?|%|por ciento)",
        normalized,
    )
    if score_match:
        score = float(score_match.group(1).replace(",", "."))
        items.append(
            _item(
                key="qualification_score",
                label="Puntaje / calificación",
                value=score,
                display_value=f"{score:g}",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, score_match.start(), score_match.end() + 40),
                confidence=0.72,
            )
        )

    return items


def extract_requisitos_legales(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)

    if re.search(r"registro\s+unico\s+de\s+proponentes|\brup\b", normalized):
        match = re.search(r"registro\s+unico\s+de\s+proponentes|\brup\b", normalized)
        items.append(
            _item(
                key="rup_vigente",
                label="Inscripción vigente en el RUP",
                value=True,
                display_value="Requerido",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, match.start(), match.end() + 80) if match else "",
                confidence=0.9,
            )
        )

    if re.search(r"capacidad\s+juridica|personeria\s+juridica", normalized):
        match = re.search(r"capacidad\s+juridica|personeria\s+juridica", normalized)
        items.append(
            _item(
                key="legal_capacity",
                label="Capacidad jurídica",
                value=True,
                display_value="Requerido",
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, match.start(), match.end() + 80) if match else "",
                confidence=0.85,
            )
        )

    license_match = re.search(
        r"(licencia\s+de\s+construccion|registro\s+nacional\s+de\s+contratistas|\brnc\b)",
        normalized,
    )
    if license_match:
        items.append(
            _item(
                key="specific_license",
                label="Habilitación específica para contratar",
                value=license_match.group(1),
                display_value=license_match.group(1).title(),
                source_document=source_document,
                source_document_id=source_document_id,
                evidence=_snippet(normalized, license_match.start(), license_match.end() + 60),
                confidence=0.82,
            )
        )

    return items


def extract_otros_requisitos(
    text: str,
    source_document: str,
    source_document_id: Optional[UUID],
) -> list[RequirementItem]:
    if not text.strip():
        return []

    items: list[RequirementItem] = []
    normalized = normalize_text(text)
    special_patterns: tuple[tuple[str, str, str], ...] = (
        (
            r"calidad\s+de\s+mipyme|certificado.{0,40}mipyme|micro,?\s*pequena\s+y\s+mediana\s+empresa",
            "pyme",
            "Beneficio / condición MiPyme",
        ),
        (
            r"empresa\s+de\s+mujeres|empresas\s+de\s+mujeres|formato\s*13",
            "mujer",
            "Emprendimiento / empresa de mujeres",
        ),
        (r"\bmocho\b", "mocho", "Requisito especial (mocho)"),
        (
            r"emprendimiento\s+y\s+empresa\s+de\s+mujeres|empresa\s+emergente",
            "emprendimiento",
            "Emprendimiento / empresa emergente",
        ),
    )

    for pattern, key, label in special_patterns:
        match = re.search(pattern, normalized)
        if match:
            items.append(
                _item(
                    key=key,
                    label=label,
                    value=True,
                    display_value="Mencionado en pliego",
                    source_document=source_document,
                    source_document_id=source_document_id,
                    evidence=_snippet(normalized, match.start(), match.end() + 80),
                    confidence=0.75,
                )
            )

    return items


EXTRACTORS = {
    "experiencia_general": extract_experiencia_general,
    "experiencia_especifica": extract_experiencia_especifica,
    "indicadores_financieros": extract_indicadores_financieros,
    "requisitos_legales": extract_requisitos_legales,
    "otros": extract_otros_requisitos,
}
