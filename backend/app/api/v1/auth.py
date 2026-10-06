"""Email one-time-code login for returning users."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.api.v1.leads import ensure_lead_city_column, to_lead_response
from app.services.login_code import (
    ensure_auth_tables,
    find_lead_by_email,
    issue_code,
    normalize_email,
    recent_send_count,
    verify_code,
)
from app.services.notifications import send_login_code_email

router = APIRouter()
logger = get_logger(__name__)


class EmailPayload(BaseModel):
    email: EmailStr


class VerifyPayload(BaseModel):
    email: EmailStr
    code: str


def _send_login_code_safe(email: str, code: str) -> None:
    try:
        send_login_code_email(email, code)
    except Exception:
        logger.exception("Failed to email login code to %s", email)


@router.post("/auth/request-code")
async def request_code(
    payload: EmailPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    ensure_lead_city_column(db)
    ensure_auth_tables(db)
    email = normalize_email(payload.email)
    lead = find_lead_by_email(db, email)
    if lead is None:
        return {"exists": False}

    if recent_send_count(db, email) >= settings.AUTH_OTP_MAX_SENDS:
        raise HTTPException(
            status_code=429,
            detail="Demasiados códigos. Espera unos minutos e inténtalo de nuevo.",
        )

    code = issue_code(db, email)
    smtp_ready = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
    if smtp_ready:
        background_tasks.add_task(_send_login_code_safe, email, code)

    body = {
        "exists": True,
        "ttl_minutes": settings.AUTH_OTP_TTL_MINUTES,
    }
    if settings.AUTH_OTP_DEBUG or not smtp_ready:
        body["debug_code"] = code
    return body


@router.post("/auth/verify-code")
async def verify_login_code(payload: VerifyPayload, db: Session = Depends(get_db)):
    ensure_lead_city_column(db)
    ensure_auth_tables(db)
    email = normalize_email(payload.email)
    lead = find_lead_by_email(db, email)
    if lead is None:
        return {"ok": False, "exists": False}

    result = verify_code(db, email, payload.code)
    if not result.ok:
        detail = {
            "expired": "El código ya venció. Pide uno nuevo.",
            "locked": "Demasiados intentos. Pide un código nuevo.",
        }.get(result.reason, "Código incorrecto.")
        raise HTTPException(status_code=401, detail=detail)

    return {"ok": True, "exists": True, "lead": to_lead_response(lead)}
