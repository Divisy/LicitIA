"""Ask OpenAI whether a tender object matches acta objects of the same contract type."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE: dict[tuple[str, str], bool] = {}
_BATCH = 6
_OBJECT_CHARS = 700


def _digest(text: str) -> str:
    folded = " ".join((text or "").split()).lower()
    return hashlib.sha256(folded.encode("utf-8")).hexdigest()


def parse_object_match_payload(payload: Any, allowed: dict[str, set[str]]) -> dict[str, set[str]]:
    """Keep only ids the prompt was allowed to return."""
    found: dict[str, set[str]] = {tender_id: set() for tender_id in allowed}
    if not isinstance(payload, dict):
        return found
    rows = payload.get("tenders")
    if not isinstance(rows, list):
        return found
    for row in rows:
        if not isinstance(row, dict):
            continue
        tender_id = str(row.get("tender_id") or "")
        if tender_id not in allowed:
            continue
        raw_ids = row.get("experience_ids") or []
        if not isinstance(raw_ids, list):
            continue
        found[tender_id] = {str(item) for item in raw_ids if str(item) in allowed[tender_id]}
    return found


def _clip(text: str) -> str:
    return " ".join((text or "").split())[:_OBJECT_CHARS]


def _prompt(tenders: list[dict], experiences: list[dict]) -> str:
    tender_lines = [
        {"tender_id": item["id"], "objeto": _clip(item["object"])} for item in tenders
    ]
    experience_lines = [
        {"experience_id": item["experience_id"], "objeto": _clip(item["object_text"])}
        for item in experiences
    ]
    return (
        "Compara el objeto de cada licitación con los objetos de contratos ya ejecutados. "
        "Hay match solo cuando el trabajo es el mismo, aunque la redacción cambie "
        "(por ejemplo, interventoría de pavimentación e interventoría de mejoramiento vial). "
        "No basta con que ambos digan interventoría, obra o estudios. "
        "Si la especialidad es distinta, no hay match. Si dudas, no lo incluyas. "
        "Usa únicamente los ids entregados. "
        'Devuelve JSON: {"tenders":[{"tender_id":"...","experience_ids":["..."]}]}.\n\n'
        f"Licitaciones:\n{json.dumps(tender_lines, ensure_ascii=False)}\n\n"
        f"Contratos:\n{json.dumps(experience_lines, ensure_ascii=False)}"
    )


def _call_openai(client, tenders: list[dict], experiences: list[dict]) -> dict[str, set[str]]:
    allowed = {
        item["id"]: {row["experience_id"] for row in experiences} for item in tenders
    }
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL_NAME or "gpt-4o-mini",
        temperature=0,
        max_tokens=800,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Comparas objetos contractuales colombianos. Responde únicamente JSON válido.",
            },
            {"role": "user", "content": _prompt(tenders, experiences)},
        ],
    )
    payload = json.loads(response.choices[0].message.content or "{}")
    return parse_object_match_payload(payload, allowed)


def judge_object_matches(
    tenders: list[dict],
    experiences: list[dict],
    client: Optional[Any] = None,
) -> tuple[dict[str, set[str]], set[str]]:
    """Return (matches by tender id, tender ids whose comparison failed).

    tenders items: id, kind, object.
    experiences items: experience_id, contract_kind, object_text, has_acta.
    """
    matches: dict[str, set[str]] = {}
    failed: set[str] = set()
    if client is None:
        if not settings.OPENAI_API_KEY:
            return matches, {item["id"] for item in tenders}
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

    grouped: dict[str, list[dict]] = {}
    for tender in tenders:
        grouped.setdefault(tender["kind"], []).append(tender)

    experiences_by_kind: dict[str, list[dict]] = {}
    for row in experiences:
        if not row.get("has_acta") or not (row.get("object_text") or "").strip():
            continue
        kind = (row.get("contract_kind") or "").strip().lower()
        experiences_by_kind.setdefault(kind, []).append(row)

    jobs: list[tuple[list[dict], list[dict]]] = []
    for kind, kind_tenders in grouped.items():
        candidates = experiences_by_kind.get(kind) or []
        if not candidates:
            continue
        kind_tenders = [item for item in kind_tenders if (item.get("object") or "").strip()]
        pending: list[dict] = []
        for tender in kind_tenders:
            tender_key = _digest(tender["object"])
            resolved: set[str] = set()
            missing = False
            for row in candidates:
                cache_key = (tender_key, _digest(f"{row['experience_id']}|{row['object_text']}"))
                if cache_key not in _CACHE:
                    missing = True
                    break
                if _CACHE[cache_key]:
                    resolved.add(str(row["experience_id"]))
            if missing:
                pending.append(tender)
            else:
                matches[tender["id"]] = resolved
        for start in range(0, len(pending), _BATCH):
            jobs.append((pending[start : start + _BATCH], candidates))

    def _run(job):
        batch, candidates = job
        try:
            return batch, candidates, _call_openai(client, batch, candidates)
        except Exception as exc:
            logger.warning("Object match failed: %s", exc)
            return batch, candidates, None

    if not jobs:
        return matches, failed

    workers = min(4, len(jobs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for batch, candidates, result in pool.map(_run, jobs):
            if result is None:
                failed.update(item["id"] for item in batch)
                continue
            for tender in batch:
                tender_key = _digest(tender["object"])
                chosen = result.get(tender["id"], set())
                matches[tender["id"]] = chosen
                for row in candidates:
                    cache_key = (tender_key, _digest(f"{row['experience_id']}|{row['object_text']}"))
                    _CACHE[cache_key] = str(row["experience_id"]) in chosen
    return matches, failed
