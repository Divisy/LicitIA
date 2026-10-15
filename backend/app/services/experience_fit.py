"""Decide if a company can bid from the same contract type, the object match and the pliego minimum.

OpenAI compares objects before this function runs. The SMMLV sum, the date
window and the contract count use the general-experience section already
stored for the tender. Acta line items do not decide this result.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

PUEDE_APLICAR = "puede_aplicar"
NO_APLICA = "no_aplica"
NO_SE_PUEDE_AFIRMAR = "no_se_puede_afirmar"

_REAL_KINDS = {
    "ejecucion_obra",
    "interventoria",
    "estudios_disenos",
    "estudios_disenos_y_obra",
}

# The year's salary was stored in the SMMLV column of six old rows.
_SALARY_COPIED_AS_SMMLV = 81510.0


@dataclass
class FitContract:
    experience_id: str
    contract_number: Optional[str]
    contracting_entity: Optional[str]
    amount_smmlv: Optional[float]
    in_general_sum: bool
    specific_met: bool
    matched_activity: Optional[str] = None
    object_text: Optional[str] = None


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
                    "object_text": row.object_text,
                }
                for row in self.contracts
            ],
        }


def _candidates(experiences: list[dict], kind: str) -> list[dict]:
    rows = []
    for row in experiences:
        contract_kind = (row.get("contract_kind") or "").strip().lower()
        if contract_kind != kind:
            continue
        if not row.get("has_acta") or not (row.get("object_text") or "").strip():
            continue
        rows.append(row)
    return rows


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def _general_items(requirements: Optional[dict]) -> Optional[list[dict]]:
    """Items already stored for general experience. None means the pliego is still unread."""
    if not requirements:
        return None
    section = next(
        (
            item
            for item in requirements.get("sections") or []
            if item.get("key") == "experiencia_general"
        ),
        None,
    )
    if section is None:
        return None
    version = str(requirements.get("extraction_version") or "")
    if requirements.get("general_experience_extracted") or (version and not version.startswith("general-")):
        return list(section.get("items") or [])
    if section.get("items"):
        return list(section.get("items") or [])
    return None


def _item_value(items: list[dict], key: str) -> Any:
    for item in items:
        if item.get("key") == key:
            return item.get("value")
    return None


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


def _usable_smmlv(value: Any) -> Optional[float]:
    amount = _number(value)
    if amount is None:
        return None
    if abs(amount - _SALARY_COPIED_AS_SMMLV) < 1 or abs(amount - 81.51) < 0.02:
        return None
    return amount


def _count_bounds(value: Any) -> tuple[Optional[int], Optional[int]]:
    if isinstance(value, dict):
        low = _number(value.get("minimum"))
        high = _number(value.get("maximum"))
        return (int(low) if low else None, int(high) if high else None)
    number = _number(value)
    if number and number > 0:
        return int(number), None
    return None, None


def _tiers(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [tier for tier in value if isinstance(tier, dict)]


def _tier_percentage(tiers: list[dict], count: int) -> Optional[float]:
    for tier in tiers:
        bounds = str(tier.get("contract_range") or "")
        if "-" not in bounds:
            continue
        low_text, high_text = bounds.split("-", 1)
        low = _number(low_text)
        high = _number(high_text)
        percentage = _number(tier.get("percentage"))
        if low is None or high is None or percentage is None:
            continue
        if int(low) <= count <= int(high):
            return percentage
    return None


def _budget_smmlv(tender_amount: Optional[float], publication_date) -> Optional[float]:
    day = _as_date(publication_date)
    amount = _number(tender_amount)
    if day is None or amount is None or amount <= 0:
        return None
    from app.services.rup_parser import _SMMLV_BY_YEAR

    year_smmlv = _SMMLV_BY_YEAR.get(day.year)
    if not year_smmlv:
        return None
    return amount / year_smmlv


def _minimum_for_count(
    *,
    count: int,
    percentage: Optional[float],
    direct_smmlv: Optional[float],
    tiers: list[dict],
    budget_smmlv: Optional[float],
) -> Optional[float]:
    if tiers:
        tier_percentage = _tier_percentage(tiers, count)
        if tier_percentage is None or budget_smmlv is None:
            return None
        return budget_smmlv * tier_percentage / 100
    if percentage is not None:
        if budget_smmlv is None:
            return None
        return budget_smmlv * percentage / 100
    return direct_smmlv


def _smmlv_display(amount: float) -> str:
    text = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} SMMLV"


def present_general_experience_smmlv(
    payload: dict,
    *,
    tender_amount: Optional[float],
    publication_date,
) -> dict:
    """Show the SMMLV amount the general-experience section itself states.

    A percentage of the official budget is converted with that year's SMMLV.
    A figure stored beside that percentage is left out of the response.
    """
    shown = deepcopy(payload)
    for section in shown.get("sections") or []:
        if section.get("key") != "experiencia_general":
            continue
        items = list(section.get("items") or [])
        percentage = _number(_item_value(items, "min_percentage_budget"))
        tiers = _tiers(_item_value(items, "experience_value_tiers"))
        if tiers or percentage is None:
            if tiers:
                section["items"] = [item for item in items if item.get("key") != "min_amount_smmlv"]
            continue
        budget = _budget_smmlv(tender_amount, publication_date)
        if budget is None:
            section["items"] = [item for item in items if item.get("key") != "min_amount_smmlv"]
            continue
        amount = round(budget * percentage / 100, 2)
        target = next((item for item in items if item.get("key") == "min_amount_smmlv"), None)
        if target is None:
            source = next((item for item in items if item.get("key") == "min_percentage_budget"), {})
            target = {
                "key": "min_amount_smmlv",
                "label": "Monto mínimo en SMMLV",
                "confidence": source.get("confidence", 0.9),
                "source_document": source.get("source_document") or "pliego_condiciones",
                "source_document_id": source.get("source_document_id"),
            }
            items.append(target)
        percentage_text = f"{percentage:g}".replace(".", ",")
        target["value"] = amount
        target["display_value"] = _smmlv_display(amount)
        target["evidence"] = f"{percentage_text}% del presupuesto oficial expresado en SMMLV"
        section["items"] = items
    return shown


def _fit_contract(row: dict, *, in_sum: bool, amount: Optional[float]) -> FitContract:
    return FitContract(
        experience_id=str(row.get("experience_id")),
        contract_number=row.get("contract_number"),
        contracting_entity=row.get("contracting_entity"),
        amount_smmlv=amount,
        in_general_sum=in_sum,
        specific_met=False,
        object_text=(row.get("object_text") or "").strip() or None,
    )


def evaluate_experience_fit(
    *,
    tender_kind: Optional[str],
    tender_object: str,
    experiences: list[dict],
    matched_experience_ids: Optional[set[str]] = None,
    comparison_available: bool = False,
    tender_amount: Optional[float] = None,
    publication_date=None,
    requirements: Optional[dict] = None,
) -> ExperienceFitResult:
    """Require the same contract type, an object match, and the stored general-experience minimum."""
    kind = (tender_kind or "").strip().lower()
    if kind not in _REAL_KINDS:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="La licitación no tiene tipo de contrato",
        )
    if not (tender_object or "").strip():
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="La licitación no tiene objeto",
        )

    candidates = _candidates(experiences, kind)
    if not candidates:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Sin actas con objeto para este tipo de contrato",
        )
    if not comparison_available:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="No se pudo comparar los objetos",
        )

    matched = {str(item) for item in (matched_experience_ids or set())}
    matched_rows = [row for row in candidates if str(row.get("experience_id")) in matched]
    if not matched_rows:
        return ExperienceFitResult(
            status=NO_APLICA,
            reason="Ningún objeto de acta de este tipo coincide con la licitación",
            contracts=[],
        )

    items = _general_items(requirements)
    if items is None:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="La experiencia general del pliego todavía no está leída",
        )

    percentage = _number(_item_value(items, "min_percentage_budget"))
    direct = _number(_item_value(items, "min_amount_smmlv"))
    tiers = _tiers(_item_value(items, "experience_value_tiers"))
    low_count, high_count = _count_bounds(_item_value(items, "contracts_minimum"))
    window_years = _number(_item_value(items, "time_window_years"))
    published = _as_date(publication_date)
    cutoff = _years_before(published, int(window_years)) if published and window_years else None
    budget = _budget_smmlv(tender_amount, publication_date)

    if percentage is None and direct is None and not tiers:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="El pliego no dejó un mínimo de experiencia general utilizable",
        )
    if (percentage is not None or tiers) and budget is None and direct is None:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Falta el presupuesto para convertir el porcentaje del pliego a SMMLV",
        )

    eligible: list[tuple[dict, float]] = []
    uncertain = False
    for row in matched_rows:
        amount = _usable_smmlv(row.get("amount_smmlv"))
        raw_amount = _number(row.get("amount_smmlv"))
        completion = _as_date(row.get("completion_date"))
        if cutoff is not None:
            if completion is None:
                uncertain = True
                continue
            if completion < cutoff:
                continue
        if amount is None:
            if raw_amount is None:
                uncertain = True
            continue
        eligible.append((row, amount))

    eligible.sort(key=lambda item: item[1], reverse=True)
    count_low = low_count or 1
    count_high = high_count or len(eligible)
    if count_high < count_low:
        count_high = count_low

    best: Optional[tuple[float, float, list[tuple[dict, float]]]] = None
    for count in range(count_low, min(count_high, len(eligible)) + 1):
        minimum = _minimum_for_count(
            count=count,
            percentage=percentage,
            direct_smmlv=direct,
            tiers=tiers,
            budget_smmlv=budget,
        )
        if minimum is None:
            continue
        chosen = eligible[:count]
        total = sum(amount for _, amount in chosen)
        if total + 1e-6 >= minimum and (best is None or total > best[0]):
            best = (total, minimum, chosen)

    if best is not None:
        total, minimum, chosen = best
        return ExperienceFitResult(
            status=PUEDE_APLICAR,
            reason="La suma de SMMLV cubre el mínimo de la experiencia general",
            general_sum_smmlv=round(total, 2),
            general_minimum_smmlv=round(minimum, 2),
            contracts=[_fit_contract(row, in_sum=True, amount=amount) for row, amount in chosen],
        )

    judged = eligible[: min(count_high, len(eligible))]
    total = sum(amount for _, amount in judged)
    sample_count = count_low if len(eligible) < count_low else min(count_high, len(eligible))
    minimum = _minimum_for_count(
        count=max(sample_count, 1),
        percentage=percentage,
        direct_smmlv=direct,
        tiers=tiers,
        budget_smmlv=budget,
    )
    if uncertain or minimum is None:
        return ExperienceFitResult(
            status=NO_SE_PUEDE_AFIRMAR,
            reason="Falta la fecha o el SMMLV de un contrato que podría cubrir el mínimo",
        )
    return ExperienceFitResult(
        status=NO_APLICA,
        reason="La suma de SMMLV no alcanza el mínimo de la experiencia general",
        general_sum_smmlv=round(total, 2),
        general_minimum_smmlv=round(minimum, 2),
        contracts=[_fit_contract(row, in_sum=True, amount=amount) for row, amount in judged],
    )
