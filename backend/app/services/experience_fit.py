"""Decide if a company can bid from the same contract type and an object match.

The object comparison is done by OpenAI before this function runs. Typology
keywords, pliego minimums and acta line items do not decide this result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    """Match when the contract type is the same and OpenAI aligned the objects.

    The extra arguments stay so older callers can pass pliego data without
    changing the result.
    """
    del tender_amount, publication_date, requirements
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
    contracts: list[FitContract] = []
    any_match = False
    for row in candidates:
        experience_id = str(row.get("experience_id"))
        is_match = experience_id in matched
        any_match = any_match or is_match
        amount = row.get("amount_smmlv")
        contracts.append(
            FitContract(
                experience_id=experience_id,
                contract_number=row.get("contract_number"),
                contracting_entity=row.get("contracting_entity"),
                amount_smmlv=float(amount) if amount is not None else None,
                in_general_sum=is_match,
                specific_met=False,
            )
        )

    if any_match:
        return ExperienceFitResult(
            status=PUEDE_APLICAR,
            reason="El objeto del acta coincide con el objeto de la licitación",
            contracts=[row for row in contracts if row.in_general_sum],
        )
    return ExperienceFitResult(
        status=NO_APLICA,
        reason="Ningún objeto de acta de este tipo coincide con la licitación",
        contracts=[],
    )
