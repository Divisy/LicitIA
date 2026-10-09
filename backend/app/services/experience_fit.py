"""Decide if a company can bid a tender from stored actas and pliego requirements.

Two steps, no embeddings:
1. Acta object against the tender object, then SMMLV sum against the general minimum.
2. Specific activities named in the pliego against the acta line items.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from app.services.project_typology import classify_project_typologies
from app.services.rup_parser import DEFAULT_SMMLV_COP, _SMMLV_BY_YEAR

PUEDE_APLICAR = "puede_aplicar"
NO_APLICA = "no_aplica"
NO_SE_PUEDE_AFIRMAR = "no_se_puede_afirmar"

_REAL_KINDS = {
    "ejecucion_obra",
    "interventoria",
    "estudios_disenos",
    "estudios_disenos_y_obra",
}
_WEAK_TYPOLOGIES = {"otro", "construccion"}

_GENERIC = {
    "interventoria",
    "construccion",
    "reconstruccion",
    "mejoramiento",
    "ejecucion",
    "estudios",
    "disenos",
    "diseno",
    "obra",
    "obras",
    "experiencia",
    "especifica",
    "general",
    "contrato",
    "contratos",
    "proponente",
    "presupuesto",
    "oficial",
    "valor",
    "smmlv",
    "porcentaje",
    "ciento",
    "menos",
    "proceso",
    "contratacion",
    "presente",
    "valido",
    "validos",
    "aportado",
    "aportados",
    "correspondiente",
    "respecto",
    "total",
    "establecido",
    "para",
    "por",
    "del",
    "los",
    "las",
    "una",
    "uno",
    "con",
    "que",
    "como",
    "sus",
    "este",
    "esta",
    "entre",
    "sobre",
    "desde",
    "hasta",
    "mediante",
    "segun",
    "cada",
    "todo",
    "toda",
    "anos",
    "ultimo",
    "ultimos",
}

_SYNONYMS = {
    "pavimento asfaltico": (
        "pavimento asfaltico",
        "carpeta asfaltica",
        "mezcla asfaltica",
        "concreto asfaltico",
    ),
    "concreto hidraulico": (
        "concreto hidraulico",
        "pavimento rigido",
    ),
    "via primaria": ("via primaria", "vias primarias"),
    "vias primarias": ("via primaria", "vias primarias"),
}


@dataclass
class FitContract:
    experience_id: str
    contract_number: Optional[str]
    contracting_entity: Optional[str]
    amount_smmlv: Optional[float]
    in_general_sum: bool
    specific_met: bool
    matched_activity: Optional[str] = None


@dataclass
class ExperienceFitResult:
    status: str
    reason: str
    general_sum_smmlv: Optional[float] = None
    general_minimum_smmlv: Optional[float] = None
    contracts: list[FitContract] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "general_sum_smmlv": self.general_sum_smmlv,
            "general_minimum_smmlv": self.general_minimum_smmlv,
            "contracts": [
                {
                    "experience_id": row.experience_id,
                    "contract_number": row.contract_number,
                    "contracting_entity": row.contracting_entity,
                    "amount_smmlv": row.amount_smmlv,
                    "in_general_sum": row.in_general_sum,
                    "specific_met": row.specific_met,
                    "matched_activity": row.matched_activity,
                }
                for row in self.contracts
            ],
        }


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text or "")
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return f" {raw.strip()} "


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _section_items(requirements: Optional[dict], key: str) -> list[dict]:
    for section in (requirements or {}).get("sections") or []:
        if section.get("key") == key:
            return list(section.get("items") or [])
    return []


def _item_value(items: list[dict], key: str) -> Any:
    for item in items:
        if item.get("key") == key:
            return item.get("value")
    return None


def parse_specific_activities(scope: str) -> tuple[str, list[str]]:
    """Return ('or'|'and', phrases). Empty phrases means the scope is not searchable."""
    folded = _fold(scope).strip()
    folded = re.sub(r"\d+(?:[.,]\d+)?\s*(?:%|por ciento)", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    if not folded:
        return "or", []
    mode = "or" if re.search(r"\bo\b", folded) else "and"
    splitter = r"\s+\bo\b\s+" if mode == "or" else r"\s+\by\b\s+"
    phrases: list[str] = []
    seen: set[str] = set()
    for part in re.split(splitter, folded):
        words = [word for word in part.split() if word not in _GENERIC and len(word) > 2]
        if len(words) < 2 and not (len(words) == 1 and len(words[0]) >= 8):
            continue
        phrase = " ".join(words)
        if phrase not in seen:
            seen.add(phrase)
            phrases.append(phrase)
    if len(phrases) <= 1:
        mode = "or"
    return mode, phrases


def _phrase_in_partidas(phrase: str, partidas: str) -> bool:
    folded = _fold(partidas)
    options = [phrase]
    rest = ""
    for key, alts in _SYNONYMS.items():
        if phrase == key or phrase.startswith(key + " "):
            options = list(alts)
            rest = phrase[len(key) :].strip()
            break
    rest_words = [word for word in rest.split() if word]
    return any(
        f" {option} " in folded and all(f" {word} " in folded for word in rest_words)
        for option in options
    )


def _activities_met(mode: str, phrases: list[str], partidas: str) -> Optional[str]:
    hits = [phrase for phrase in phrases if _phrase_in_partidas(phrase, partidas)]
    if mode == "and":
        if len(hits) == len(phrases):
            return ", ".join(hits)
        return None
    return hits[0] if hits else None


def _smmlv_cop(year: Optional[int]) -> Optional[float]:
    if year is None:
        return None
    value = _SMMLV_BY_YEAR.get(year)
    return float(value) if value else None


def _budget_smmlv(amount_cop: Optional[float], year: Optional[int]) -> Optional[float]:
    if amount_cop is None or amount_cop <= 0:
        return None
    wage = _smmlv_cop(year) or (DEFAULT_SMMLV_COP if year and year >= 2026 else None)
    if not wage:
        return None
    return float(amount_cop) / wage


def _specific_typologies(text: str) -> set[str]:
    return set(classify_project_typologies(text)) - _WEAK_TYPOLOGIES


def evaluate_experience_fit(
    *,
    tender_kind: Optional[str],
    tender_object: str,
    tender_amount: Optional[float],
    publication_date: Optional[date],
    requirements: Optional[dict],
    experiences: list[dict],
) -> ExperienceFitResult:
    """experiences entries use the stored fields. Missing inputs never become puede_aplicar."""
    general_items = _section_items(requirements, "experiencia_general")
    specific_items = _section_items(requirements, "experiencia_especifica")
    if not general_items and not specific_items:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Sin pliego leído",
        )

    percentage = _number(_item_value(general_items, "min_percentage_budget"))
    direct_smmlv = _number(_item_value(general_items, "min_amount_smmlv"))
    year = publication_date.year if publication_date else None
    budget_smmlv = _budget_smmlv(tender_amount, year)
    if percentage is not None and budget_smmlv is not None:
        minimum = budget_smmlv * (percentage / 100.0)
    elif direct_smmlv is not None:
        minimum = direct_smmlv
    else:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Sin mínimo de experiencia general en SMMLV",
        )

    count_rule = _item_value(general_items, "contracts_minimum") or _item_value(
        specific_items, "contracts_minimum"
    )
    minimum_count = maximum_count = None
    if isinstance(count_rule, dict):
        minimum_count = _number(count_rule.get("minimum"))
        maximum_count = _number(count_rule.get("maximum"))

    window_years = _number(_item_value(general_items, "time_window_years"))
    window_start = None
    if window_years is not None and publication_date is not None:
        try:
            window_start = publication_date.replace(year=publication_date.year - int(window_years))
        except ValueError:
            window_start = date(publication_date.year - int(window_years), 3, 1)

    kind = (tender_kind or "").strip().lower()
    if kind not in _REAL_KINDS:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="La licitación no tiene tipo de contrato",
            general_minimum_smmlv=round(minimum, 2),
        )

    tender_types = _specific_typologies(tender_object or "")
    if not tender_types:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="El objeto de la licitación no define el tipo de obra",
            general_minimum_smmlv=round(minimum, 2),
        )

    scope = _item_value(specific_items, "specific_scope") or ""
    mode, phrases = parse_specific_activities(str(scope) if scope else "")
    specific_pct = _number(_item_value(specific_items, "specific_min_percentage"))
    specific_floor = None
    if specific_pct is not None and budget_smmlv is not None:
        specific_floor = budget_smmlv * (specific_pct / 100.0)

    if not phrases:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="La experiencia específica del pliego no tiene actividades buscables",
            general_minimum_smmlv=round(minimum, 2),
        )

    any_acta = False
    entered: list[FitContract] = []
    for row in experiences:
        if row.get("has_acta") and (row.get("object_text") or "").strip():
            any_acta = True
        contract_kind = (row.get("contract_kind") or "").strip().lower()
        if contract_kind not in _REAL_KINDS or contract_kind != kind:
            continue
        if not row.get("has_acta") or not (row.get("object_text") or "").strip():
            continue
        if row.get("amount_smmlv") is None:
            continue
        completed = row.get("completion_date")
        if window_start is not None and (completed is None or completed < window_start):
            continue
        object_types = _specific_typologies(row.get("object_text") or "")
        if not tender_types.intersection(object_types):
            continue
        entered.append(
            FitContract(
                experience_id=str(row.get("experience_id")),
                contract_number=row.get("contract_number"),
                contracting_entity=row.get("contracting_entity"),
                amount_smmlv=float(row["amount_smmlv"]),
                in_general_sum=True,
                specific_met=False,
            )
        )

    if not entered:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR if not any_acta else NO_APLICA,
            reason="Sin actas para comparar" if not any_acta else "Ningún contrato coincide en tipo y objeto",
            general_minimum_smmlv=round(minimum, 2),
            general_sum_smmlv=0.0,
        )

    by_id = {str(row.get("experience_id")): row for row in experiences}
    if not any((by_id[item.experience_id].get("partidas") or "").strip() for item in entered):
        total = sum(item.amount_smmlv or 0 for item in entered)
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Sin partidas en el acta",
            general_sum_smmlv=round(total, 2),
            general_minimum_smmlv=round(minimum, 2),
            contracts=entered,
        )

    total = 0.0
    specific_ok = False
    for item in entered:
        source = by_id[item.experience_id]
        total += item.amount_smmlv or 0
        partidas = (source.get("partidas") or "").strip()
        if not partidas:
            continue
        activity = _activities_met(mode, phrases, partidas)
        if not activity:
            continue
        if specific_floor is not None and (item.amount_smmlv or 0) < specific_floor:
            continue
        item.specific_met = True
        item.matched_activity = activity
        specific_ok = True

    count = len(entered)
    count_ok = True
    if minimum_count is not None and count < minimum_count:
        count_ok = False
    if maximum_count is not None and count > maximum_count:
        count_ok = False
    general_ok = total + 1e-6 >= minimum and count_ok

    result = ExperienceFitResult(
        status=NO_APLICA,
        reason="",
        general_sum_smmlv=round(total, 2),
        general_minimum_smmlv=round(minimum, 2),
        contracts=entered,
    )
    if general_ok and specific_ok:
        result.status = PUEDE_APLICAR
        result.reason = "La suma de SMMLV y las partidas cubren el pliego"
        return result
    if not general_ok and not specific_ok:
        result.reason = "No alcanza la experiencia general ni la específica"
    elif not general_ok:
        result.reason = "La suma de SMMLV no cubre la experiencia general"
    else:
        result.reason = "Las partidas no acreditan la experiencia específica"
    return result


def publication_as_date(value: Optional[datetime | date]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value
