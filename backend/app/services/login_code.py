"""Issue and verify one-time login codes."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.lead import Lead
from app.models.login_code import LoginCode


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def hash_code(email: str, code: str) -> str:
    payload = f"{normalize_email(email)}:{code}:{settings.AUTH_OTP_SECRET}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def ensure_auth_tables(db: Session) -> None:
    for stmt in (
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone VARCHAR(50)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS sectors VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS industry VARCHAR(100)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS company_size VARCHAR(50)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS role VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMP",
    ):
        db.execute(text(stmt))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS login_codes (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                code_hash VARCHAR(64) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                consumed_at TIMESTAMP,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_login_codes_email ON login_codes (email)"))
    db.commit()


def find_lead_by_email(db: Session, email: str) -> Optional[Lead]:
    normalized = normalize_email(email)
    if not normalized:
        return None
    return (
        db.query(Lead)
        .filter(func.lower(Lead.email) == normalized)
        .first()
    )


def recent_send_count(db: Session, email: str) -> int:
    window = datetime.utcnow() - timedelta(minutes=settings.AUTH_OTP_WINDOW_MINUTES)
    return (
        db.query(LoginCode)
        .filter(
            LoginCode.email == normalize_email(email),
            LoginCode.created_at >= window,
        )
        .count()
    )


def issue_code(db: Session, email: str) -> str:
    normalized = normalize_email(email)
    now = datetime.utcnow()
    db.query(LoginCode).filter(
        LoginCode.email == normalized,
        LoginCode.consumed_at.is_(None),
    ).update({"consumed_at": now}, synchronize_session=False)

    code = generate_code()
    row = LoginCode(
        email=normalized,
        code_hash=hash_code(normalized, code),
        expires_at=now + timedelta(minutes=settings.AUTH_OTP_TTL_MINUTES),
        created_at=now,
        attempt_count=0,
    )
    db.add(row)
    db.commit()
    return code


class VerifyResult:
    def __init__(self, ok: bool, reason: str = "") -> None:
        self.ok = ok
        self.reason = reason


def verify_code(db: Session, email: str, code: str) -> VerifyResult:
    normalized = normalize_email(email)
    submitted = (code or "").strip()
    if len(submitted) != 6 or not submitted.isdigit():
        return VerifyResult(False, "invalid")

    now = datetime.utcnow()
    row = (
        db.query(LoginCode)
        .filter(
            LoginCode.email == normalized,
            LoginCode.consumed_at.is_(None),
        )
        .order_by(LoginCode.created_at.desc())
        .first()
    )
    if row is None:
        return VerifyResult(False, "invalid")
    if row.expires_at < now:
        row.consumed_at = now
        db.commit()
        return VerifyResult(False, "expired")
    if row.attempt_count >= settings.AUTH_OTP_MAX_ATTEMPTS:
        row.consumed_at = now
        db.commit()
        return VerifyResult(False, "locked")

    row.attempt_count = (row.attempt_count or 0) + 1
    if row.code_hash != hash_code(normalized, submitted):
        db.commit()
        return VerifyResult(False, "invalid")

    row.consumed_at = now
    db.commit()
    return VerifyResult(True)
