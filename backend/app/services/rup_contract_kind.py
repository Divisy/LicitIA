"""Classify RUP experiences into the same contract kinds used on the dashboard."""
from __future__ import annotations

import enum
import re
import unicodedata
from typing import Iterable, Optional


class RupExperienceKind(str, enum.Enum):
    EJECUCION_OBRA = "ejecucion_obra"
    INTERVENTORIA = "interventoria"
    ESTUDIOS_DISENOS = "estudios_disenos"
    ESTUDIOS_DISENOS_Y_OBRA = "estudios_disenos_y_obra"
    DESCONOCIDO = "desconocido"


_KIND_LABELS = {
    RupExperienceKind.EJECUCION_OBRA: "Ejecución de obra",
    RupExperienceKind.INTERVENTORIA: "Interventoría",
    RupExperienceKind.ESTUDIOS_DISENOS: "Estudios y diseños",
    RupExperienceKind.ESTUDIOS_DISENOS_Y_OBRA: "Estudios, diseños y obra",
    RupExperienceKind.DESCONOCIDO: "No identificado",
}

_KIND_VALUES = {kind.value for kind in RupExperienceKind}

_INTERVENTORIA = (
    "interventoria",
    "interventor",
    "supervision de obra",
    "supervision tecnica",
    "control de obra",
    "fiscalizacion",
)
_ESTUDIOS = (
    "estudios y dise",
    "estudio y dise",
    "estudios, dise",
    "estudio, dise",
    "elaboracion de estudios",
    "actualizacion de estudios",
    "disenos complementarios",
    "disenos definitivos",
    "estudios de factibilidad",
    "prefactibilidad",
    "consultoria",
    "ingenieria de detalle",
    "ingenieria civil y arquitectura",
)
_OBRA = (
    "ejecucion de obra",
    "construccion",
    "obra publica",
    "obras civiles",
    "paviment",
    "edificacion",
    "remodelacion",
    "mantenimiento de infraestructura",
    "mantenimiento y reparacion",
)

_OBRA_UNSPSC_PREFIXES = ("72",)
_ESTUDIOS_UNSPSC_PREFIXES = ("8110", "8111")


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return f" {text.strip()} "


def _contains_any(haystack: str, tokens: tuple[str, ...]) -> bool:
    return any(token in haystack for token in tokens)


def extract_unspsc_codes(*parts: Optional[str]) -> list[str]:
    """UNSPSC 8-digit codes from a RUP clasificador snippet only (not free text)."""
    return extract_rup_clasificador_unspsc(" ".join(part or "" for part in parts))


def extract_rup_clasificador_unspsc(block: str) -> list[str]:
    """Codes listed under the CCB clasificador table of one executed contract."""
    if not (block or "").strip():
        return []
    marker = re.search(
        r"CLASIFICADOR DE BIENES Y SERVICIOS|IDENTIFICADO CON EL CLASIFICADOR|"
        r"SEGM\s*[\| ]\s*FAMI",
        block,
        re.IGNORECASE,
    )
    section = block[marker.start() :] if marker else ""
    if not section:
        return []
    stop = re.search(
        r"NUMERO CONSECUTIVO|CERTIFICA:|CONTRATOS ADJUDICADOS|ENTIDAD CONTRATANTE:"
        r"|FECHA DE INSCRIPCION|CONTRATO RELACIONADO CON LA CONSTRUCCI",
        section[40:],
        re.IGNORECASE,
    )
    if stop:
        section = section[: 40 + stop.start()]

    codes: list[str] = []
    seen: set[str] = set()

    def add(code: str) -> None:
        if code and code not in seen and len(code) == 8 and code.isdigit():
            seen.add(code)
            codes.append(code)

    for match in re.finditer(
        r"\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|",
        section,
    ):
        add("".join(match.groups()))
    for match in re.finditer(
        r"(?<!\d)(\d{2})(?:\s+)(\d{2})(?:\s+)(\d{2})(?:\s+)(\d{2})(?!\d)",
        section,
    ):
        groups = match.groups()
        if _unspsc_groups_look_like_date(groups):
            continue
        add("".join(groups))
    # 8-digit UNSPSC next to the clasificador, not contract numbers elsewhere.
    for match in re.finditer(r"\b(\d{8})\b", section):
        add(match.group(1))
    return codes


def unspsc_codes_from_stored(
    *,
    stored_json: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> list[str]:
    """Only codes saved from the user's RUP clasificador. Never invent from other text."""
    import json

    if not stored_json:
        return []
    try:
        parsed = json.loads(stored_json)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    unique: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        digits = re.sub(r"\D", "", str(item))
        if len(digits) == 8 and digits not in seen:
            seen.add(digits)
            unique.append(digits)
    return unique


def _unspsc_groups_look_like_date(groups: tuple[str, str, str, str]) -> bool:
    day, month, year = int(groups[0]), int(groups[1]), int(groups[2] + groups[3])
    if 1 <= day <= 31 and 1 <= month <= 12 and 1990 <= year <= 2035:
        return True
    year_first = int(groups[0] + groups[1])
    month2, day2 = int(groups[2]), int(groups[3])
    return 1990 <= year_first <= 2035 and 1 <= month2 <= 12 and 1 <= day2 <= 31


def parse_stored_contract_kind(value: Optional[str]) -> Optional[RupExperienceKind]:
    raw = (value or "").strip().lower()
    if raw in _KIND_VALUES:
        return RupExperienceKind(raw)
    return None


def classify_rup_experience_kind(
    *,
    object_text: str = "",
    category: str = "",
    contract_number: str = "",
    extra_text: str = "",
    unspsc_codes: Optional[Iterable[str]] = None,
) -> RupExperienceKind:
    codes = [re.sub(r"\D", "", code) for code in (unspsc_codes or []) if code]
    codes.extend(extract_unspsc_codes(object_text, category, extra_text, contract_number))
    # Preserve order, drop empties
    unique_codes: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code and code not in seen:
            seen.add(code)
            unique_codes.append(code)

    haystack = _normalize(
        " ".join(
            part
            for part in (object_text, category, contract_number, extra_text, " ".join(unique_codes))
            if part
        )
    )
    related_construction = bool(
        re.search(r"\(si o no\)\s*:\s*si\b", haystack)
        or re.search(r"relacionado con la construccion.{0,40}:\s*si\b", haystack)
    )
    codes_obra = any(code.startswith(_OBRA_UNSPSC_PREFIXES) for code in unique_codes)
    codes_estudios = any(
        any(code.startswith(prefix) for prefix in _ESTUDIOS_UNSPSC_PREFIXES)
        for code in unique_codes
    )
    has_interventoria = _contains_any(haystack, _INTERVENTORIA)
    has_estudios = _contains_any(haystack, _ESTUDIOS) or codes_estudios
    has_obra = _contains_any(haystack, _OBRA) or codes_obra or related_construction

    if has_interventoria:
        return RupExperienceKind.INTERVENTORIA
    if has_estudios and has_obra:
        return RupExperienceKind.ESTUDIOS_DISENOS_Y_OBRA
    if has_estudios:
        return RupExperienceKind.ESTUDIOS_DISENOS
    if has_obra:
        return RupExperienceKind.EJECUCION_OBRA
    return RupExperienceKind.DESCONOCIDO


def kind_payload_for_experience(
    *,
    engineering_area: Optional[str],
    project_description: Optional[str],
    category: Optional[str],
    contract_number: Optional[str],
) -> tuple[str, str]:
    stored = parse_stored_contract_kind(engineering_area)
    kind = stored or classify_rup_experience_kind(
        object_text=project_description or "",
        category=category or "",
        contract_number=contract_number or "",
        extra_text=engineering_area or "",
    )
    return kind.value, _KIND_LABELS[kind]
