"""Persist object-match judgments and human confirmations for experience fit."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_SCHEMA_READY = False


def _borrow_session(db: Optional[Session]) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    from app.core.db import SessionLocal

    return SessionLocal(), True


def ensure_match_store(db: Optional[Session] = None) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    session, owned = _borrow_session(db)
    try:
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS object_match_judgments (
                    purpose VARCHAR(64) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    tender_digest VARCHAR(64) NOT NULL,
                    experience_digest VARCHAR(64) NOT NULL,
                    matched BOOLEAN NOT NULL,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (purpose, model, tender_digest, experience_digest)
                )
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS experience_fit_confirmations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    owner_email VARCHAR(255) NOT NULL,
                    tender_id UUID NOT NULL,
                    experience_ids TEXT NOT NULL,
                    confirmed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (owner_email, tender_id)
                )
                """
            )
        )
        session.commit()
        _SCHEMA_READY = True
    finally:
        if owned:
            session.close()


def load_judgments(
    db: Optional[Session] = None,
    *,
    purpose: str,
    model: str,
    keys: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], bool]:
    """Return {(tender_digest, experience_digest): matched} for known rows."""
    ensure_match_store(db)
    pairs = list({(t, e) for t, e in keys})
    if not pairs:
        return {}
    session, owned = _borrow_session(db)
    found: dict[tuple[str, str], bool] = {}
    try:
        chunk = 80
        for start in range(0, len(pairs), chunk):
            batch = pairs[start : start + chunk]
            clauses = []
            params: dict = {"purpose": purpose, "model": model}
            for index, (tender_digest, experience_digest) in enumerate(batch):
                clauses.append(
                    f"(tender_digest = :t{index} AND experience_digest = :e{index})"
                )
                params[f"t{index}"] = tender_digest
                params[f"e{index}"] = experience_digest
            rows = session.execute(
                text(
                    f"""
                    SELECT tender_digest, experience_digest, matched
                    FROM object_match_judgments
                    WHERE purpose = :purpose
                      AND model = :model
                      AND ({' OR '.join(clauses)})
                    """
                ),
                params,
            ).fetchall()
            for tender_digest, experience_digest, matched in rows:
                found[(str(tender_digest), str(experience_digest))] = bool(matched)
        return found
    finally:
        if owned:
            session.close()


def save_judgments(
    db: Optional[Session] = None,
    *,
    purpose: str,
    model: str,
    rows: Iterable[tuple[str, str, bool]],
) -> None:
    ensure_match_store(db)
    payload = list(rows)
    if not payload:
        return
    session, owned = _borrow_session(db)
    try:
        for tender_digest, experience_digest, matched in payload:
            session.execute(
                text(
                    """
                    INSERT INTO object_match_judgments (
                        purpose, model, tender_digest, experience_digest, matched, updated_at
                    ) VALUES (
                        :purpose, :model, :tender_digest, :experience_digest, :matched, :updated_at
                    )
                    ON CONFLICT (purpose, model, tender_digest, experience_digest)
                    DO UPDATE SET matched = EXCLUDED.matched, updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "purpose": purpose,
                    "model": model,
                    "tender_digest": tender_digest,
                    "experience_digest": experience_digest,
                    "matched": matched,
                    "updated_at": datetime.utcnow(),
                },
            )
        session.commit()
    finally:
        if owned:
            session.close()


def experience_ids_key(experience_ids: Iterable[str]) -> str:
    return json.dumps(sorted({str(item) for item in experience_ids}), ensure_ascii=False)


def get_confirmation(
    db: Session,
    *,
    owner_email: str,
    tender_id: UUID | str,
) -> Optional[set[str]]:
    ensure_match_store(db)
    email = (owner_email or "").strip().lower()
    if not email:
        return None
    row = db.execute(
        text(
            """
            SELECT experience_ids
            FROM experience_fit_confirmations
            WHERE owner_email = :email AND tender_id = :tender_id
            """
        ),
        {"email": email, "tender_id": str(tender_id)},
    ).first()
    if row is None:
        return None
    try:
        raw = json.loads(row[0] or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, list):
        return None
    return {str(item) for item in raw}


def save_confirmation(
    db: Session,
    *,
    owner_email: str,
    tender_id: UUID | str,
    experience_ids: Iterable[str],
) -> set[str]:
    ensure_match_store(db)
    email = (owner_email or "").strip().lower()
    ids = {str(item) for item in experience_ids}
    payload = experience_ids_key(ids)
    db.execute(
        text(
            """
            INSERT INTO experience_fit_confirmations (
                id, owner_email, tender_id, experience_ids, confirmed_at
            ) VALUES (
                gen_random_uuid(), :email, :tender_id, :experience_ids, :confirmed_at
            )
            ON CONFLICT (owner_email, tender_id)
            DO UPDATE SET experience_ids = EXCLUDED.experience_ids,
                          confirmed_at = EXCLUDED.confirmed_at
            """
        ),
        {
            "email": email,
            "tender_id": str(tender_id),
            "experience_ids": payload,
            "confirmed_at": datetime.utcnow(),
        },
    )
    db.commit()
    return ids


def confirmation_matches(stored: Optional[set[str]], current: Iterable[str]) -> bool:
    if stored is None:
        return False
    return stored == {str(item) for item in current}
