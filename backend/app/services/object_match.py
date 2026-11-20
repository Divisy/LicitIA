"""Compare tender/pliego texts with acta objects, with optional dual-model consensus."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE: dict[tuple[str, str, str, str], bool] = {}
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


def _specialties(text: str) -> set[str]:
    """Specific work types only. Generic construction does not count as a specialty."""
    from app.services.project_typology import classify_project_typologies

    return {
        item
        for item in classify_project_typologies(text)
        if item not in {"construccion", "otro"}
    }


def specialties_compatible(tender_object: str, acta_object: str) -> bool:
    """False when both texts name a specialty and none is shared."""
    tender = _specialties(tender_object)
    acta = _specialties(acta_object)
    if not tender or not acta:
        return True
    return bool(tender & acta)


def _prompt(tenders: list[dict], experiences: list[dict], purpose: str) -> str:
    tender_lines = [
        {"tender_id": item["id"], "objeto": _clip(item["object"])} for item in tenders
    ]
    experience_lines = [
        {"experience_id": item["experience_id"], "objeto": _clip(item["object_text"])}
        for item in experiences
    ]
    base_purpose = purpose.split(":", 1)[0]
    if base_purpose == "experience":
        intro = (
            "Cada texto es la experiencia que el pliego exige. "
            "Hay match cuando el objeto del acta acredita esa experiencia: el mismo tipo de trabajo, "
            "aunque la redacción cambie. "
            "La interventoría, supervisión o consultoría de una obra acredita la experiencia pedida sobre esa obra. "
        )
    else:
        intro = (
            "Compara el objeto de cada licitación con los objetos de contratos ya ejecutados. "
            "Hay match solo cuando el trabajo es el mismo, aunque la redacción cambie "
            "(por ejemplo, interventoría de pavimentación e interventoría de mejoramiento vial). "
        )
    return (
        intro
        + "No basta con que ambos digan interventoría, obra o estudios. "
        "Si la especialidad es distinta, no hay match. Si dudas, no lo incluyas. "
        "Usa únicamente los ids entregados. "
        'Devuelve JSON: {"tenders":[{"tender_id":"...","experience_ids":["..."]}]}.\n\n'
        f"Licitaciones:\n{json.dumps(tender_lines, ensure_ascii=False)}\n\n"
        f"Contratos:\n{json.dumps(experience_lines, ensure_ascii=False)}"
    )


def _is_claude(model: str) -> bool:
    return model.lower().startswith("claude")


def _has_credentials(model: str) -> bool:
    if _is_claude(model):
        return bool((settings.ANTHROPIC_API_KEY or "").strip())
    return bool((settings.OPENAI_API_KEY or "").strip())


def resolve_match_models() -> tuple[str, str, str]:
    """Return (model_a, model_b, model_c) from the precision design.

    Default: A=gpt-6-luna, B=claude-haiku-5-5, C=gpt-6.1-sol.
    Without Anthropic key, B falls back to gpt-6.1-terra (still a distinct judge).
    """
    primary = (settings.OBJECT_MATCH_MODEL_A or "gpt-6-luna").strip()
    secondary = (settings.OBJECT_MATCH_MODEL_B or "claude-haiku-5-5").strip()
    tiebreak = (settings.OBJECT_MATCH_MODEL_C or "gpt-6.1-sol").strip()
    if _is_claude(secondary) and not (settings.ANTHROPIC_API_KEY or "").strip():
        logger.warning(
            "OBJECT_MATCH_MODEL_B=%s requires ANTHROPIC_API_KEY; using gpt-6.1-terra",
            secondary,
        )
        secondary = "gpt-6.1-terra"
    if _is_claude(tiebreak) and not (settings.ANTHROPIC_API_KEY or "").strip():
        logger.warning(
            "OBJECT_MATCH_MODEL_C=%s requires ANTHROPIC_API_KEY; using gpt-6.1-sol",
            tiebreak,
        )
        tiebreak = "gpt-6.1-sol"
    alternates = ("gpt-6-luna", "claude-haiku-5-5", "gpt-6.1-terra", "gpt-6.1-sol")
    if settings.OBJECT_MATCH_CONSENSUS and secondary == primary:
        secondary = next((item for item in alternates if item != primary), "gpt-6.1-terra")
        if _is_claude(secondary) and not (settings.ANTHROPIC_API_KEY or "").strip():
            secondary = "gpt-6.1-terra"
    if tiebreak == secondary:
        tiebreak = primary if primary != secondary else "gpt-6.1-sol"
    return primary, secondary, tiebreak


def _openai_reasoning_effort(model: str) -> Optional[str]:
    name = model.lower()
    if not name.startswith("gpt-6"):
        return None
    # Sol/Astra reject "none"; Luna/Terra accept it for fast JSON classify.
    if "sol" in name or "astra" in name:
        return "low"
    return "none"


def _call_openai_judge(
    tenders: list[dict],
    experiences: list[dict],
    purpose: str,
    model: str,
    client: Optional[Any] = None,
) -> dict[str, set[str]]:
    from openai import OpenAI

    allowed = {
        item["id"]: {row["experience_id"] for row in experiences} for item in tenders
    }
    openai_client = client if client is not None and hasattr(client, "chat") else OpenAI(
        api_key=settings.OPENAI_API_KEY, timeout=40.0, max_retries=0
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Comparas objetos contractuales colombianos. Responde únicamente JSON válido.",
            },
            {"role": "user", "content": _prompt(tenders, experiences, purpose)},
        ],
    }
    effort = _openai_reasoning_effort(model)
    if effort is None:
        kwargs["max_tokens"] = 800
        kwargs["temperature"] = 0
    else:
        # GPT-6 chat completions reject max_tokens; use max_completion_tokens.
        # Batches of several tenders need headroom so JSON is not truncated.
        kwargs["max_completion_tokens"] = 4096
        kwargs["reasoning_effort"] = effort
        # temperature is only valid when reasoning_effort is none.
        if effort == "none":
            kwargs["temperature"] = 0
    response = openai_client.chat.completions.create(**kwargs)
    payload = json.loads(response.choices[0].message.content or "{}")
    return parse_object_match_payload(payload, allowed)


def _call_anthropic_judge(
    tenders: list[dict],
    experiences: list[dict],
    purpose: str,
    model: str,
) -> dict[str, set[str]]:
    from anthropic import Anthropic

    allowed = {
        item["id"]: {row["experience_id"] for row in experiences} for item in tenders
    }
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=40.0, max_retries=0)
    response = client.messages.create(
        model=model,
        max_tokens=800,
        system=(
            "Comparas objetos contractuales colombianos. "
            "Responde únicamente JSON válido, sin markdown."
        ),
        messages=[
            {"role": "user", "content": _prompt(tenders, experiences, purpose)},
        ],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    payload = json.loads(text or "{}")
    return parse_object_match_payload(payload, allowed)


def _call_openai(
    client,
    tenders: list[dict],
    experiences: list[dict],
    purpose: str = "object",
    model: Optional[str] = None,
) -> dict[str, set[str]]:
    """Dispatch match judge to OpenAI or Anthropic according to model id."""
    model_name = (model or settings.OBJECT_MATCH_MODEL_A or "gpt-6-luna").strip()
    if _is_claude(model_name):
        return _call_anthropic_judge(tenders, experiences, purpose, model_name)
    return _call_openai_judge(
        tenders, experiences, purpose, model_name, client=client
    )


def _allowed_ids(tender: dict, candidates: list[dict]) -> set[str]:
    ids = {str(row["experience_id"]) for row in candidates}
    if tender.get("candidate_ids") is None:
        return ids
    return ids & {str(item) for item in tender["candidate_ids"]}


def _pair_digest(row: dict) -> str:
    return _digest(f"{row['experience_id']}|{row['object_text']}")


def _warm_cache_from_db(
    *,
    purpose: str,
    model: str,
    tenders: list[dict],
    experiences: list[dict],
) -> None:
    from app.services.match_store import load_judgments

    keys: list[tuple[str, str]] = []
    for tender in tenders:
        tender_key = _digest(tender["object"])
        for row in experiences:
            keys.append((tender_key, _pair_digest(row)))
    stored = load_judgments(purpose=purpose, model=model, keys=keys)
    for (tender_digest, experience_digest), matched in stored.items():
        _CACHE[(purpose, model, tender_digest, experience_digest)] = matched


def _persist_cache_rows(
    *,
    purpose: str,
    model: str,
    rows: list[tuple[str, str, bool]],
) -> None:
    if not rows:
        return
    from app.services.match_store import save_judgments

    save_judgments(purpose=purpose, model=model, rows=rows)


def judge_object_matches(
    tenders: list[dict],
    experiences: list[dict],
    client: Optional[Any] = None,
    purpose: str = "object",
    model: Optional[str] = None,
) -> tuple[dict[str, set[str]], set[str]]:
    """Return (matches by tender id, tender ids whose comparison failed).

    tenders items: id, kind, object.
    experiences items: experience_id, contract_kind, object_text, has_acta.
    """
    matches: dict[str, set[str]] = {}
    failed: set[str] = set()
    model_name = (model or settings.OBJECT_MATCH_MODEL_A or "gpt-6-luna").strip()
    if client is None and not _has_credentials(model_name):
        return matches, {item["id"] for item in tenders}

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
        _warm_cache_from_db(
            purpose=purpose, model=model_name, tenders=kind_tenders, experiences=candidates
        )
        allowed_by_tender = {
            tender["id"]: {
                str(item) for item in (tender.get("candidate_ids") or [])
            }
            for tender in kind_tenders
            if tender.get("candidate_ids") is not None
        }
        if allowed_by_tender:
            needed = set().union(*allowed_by_tender.values())
            candidates = [
                row for row in candidates if str(row["experience_id"]) in needed
            ]
        pending: list[dict] = []
        for tender in kind_tenders:
            tender_key = _digest(tender["object"])
            resolved: set[str] = set()
            missing = False
            visible = candidates
            if tender["id"] in allowed_by_tender:
                visible = [
                    row
                    for row in candidates
                    if str(row["experience_id"]) in allowed_by_tender[tender["id"]]
                ]
            for row in visible:
                cache_key = (purpose, model_name, tender_key, _pair_digest(row))
                if cache_key not in _CACHE:
                    missing = True
                    break
                if _CACHE[cache_key] and specialties_compatible(
                    tender["object"], row["object_text"]
                ):
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
            return batch, candidates, _call_openai(
                client, batch, candidates, purpose, model=model_name
            )
        except Exception as exc:
            logger.warning("Object match failed (%s): %s", model_name, exc)
            return batch, candidates, None

    if not jobs:
        return matches, failed

    workers = min(4, len(jobs))
    persist_rows: list[tuple[str, str, bool]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for batch, candidates, result in pool.map(_run, jobs):
            if result is None:
                failed.update(item["id"] for item in batch)
                continue
            objects = {str(row["experience_id"]): row["object_text"] for row in candidates}
            for tender in batch:
                tender_key = _digest(tender["object"])
                allowed = _allowed_ids(tender, candidates)
                chosen = {
                    experience_id
                    for experience_id in result.get(tender["id"], set())
                    if experience_id in allowed
                    and specialties_compatible(tender["object"], objects.get(experience_id, ""))
                }
                matches[tender["id"]] = chosen
                for row in candidates:
                    experience_id = str(row["experience_id"])
                    if experience_id not in allowed:
                        continue
                    experience_digest = _pair_digest(row)
                    matched = experience_id in chosen
                    _CACHE[(purpose, model_name, tender_key, experience_digest)] = matched
                    persist_rows.append((tender_key, experience_digest, matched))
    _persist_cache_rows(purpose=purpose, model=model_name, rows=persist_rows)
    return matches, failed


def judge_object_matches_consensus(
    tenders: list[dict],
    experiences: list[dict],
    client: Optional[Any] = None,
    purpose: str = "object",
) -> tuple[dict[str, set[str]], set[str]]:
    """Require two models to agree; a third model breaks ties on disputed actas."""
    if not settings.OBJECT_MATCH_CONSENSUS:
        model_a, _, _ = resolve_match_models()
        return judge_object_matches(
            tenders, experiences, client=client, purpose=purpose, model=model_a
        )

    model_a, model_b, model_c = resolve_match_models()
    matches_a, failed_a = judge_object_matches(
        tenders, experiences, client=client, purpose=purpose, model=model_a
    )
    matches_b, failed_b = judge_object_matches(
        tenders, experiences, client=client, purpose=purpose, model=model_b
    )
    failed = set(failed_a) | set(failed_b)
    final: dict[str, set[str]] = {}
    disputed_jobs: list[dict] = []

    by_id = {item["id"]: item for item in tenders}
    for tender in tenders:
        tender_id = tender["id"]
        if tender_id in failed:
            continue
        left = set(matches_a.get(tender_id) or set())
        right = set(matches_b.get(tender_id) or set())
        agreed = left & right
        disputed = (left | right) - agreed
        if not disputed:
            final[tender_id] = agreed
            continue
        disputed_jobs.append(
            {
                **tender,
                "id": tender_id,
                "candidate_ids": disputed,
                "_agreed": agreed,
            }
        )

    if not disputed_jobs:
        return final, failed

    # Separate cache namespace so C re-judges even when it shares A's model id.
    matches_c, failed_c = judge_object_matches(
        [
            {
                "id": item["id"],
                "kind": item["kind"],
                "object": item["object"],
                "candidate_ids": item["candidate_ids"],
            }
            for item in disputed_jobs
        ],
        experiences,
        client=client,
        purpose=f"{purpose}:tiebreak",
        model=model_c,
    )
    failed |= failed_c
    for item in disputed_jobs:
        tender_id = item["id"]
        if tender_id in failed_c:
            continue
        agreed = set(item["_agreed"])
        chosen = set(matches_c.get(tender_id) or set()) & set(item["candidate_ids"])
        final[tender_id] = agreed | chosen
        # Keep the original tender entry available for callers that inspect by_id.
        _ = by_id.get(tender_id)
    return final, failed
