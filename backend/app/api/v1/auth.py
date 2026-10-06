"""Email one-time-code login for returning users."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/auth/request-code")
async def request_code(payload: EmailPayload, db: Session = Depends(get_db)):
    try:
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
        email_sent = await asyncio.to_thread(send_login_code_email, email, code)

        body = {
            "exists": True,
            "ttl_minutes": settings.AUTH_OTP_TTL_MINUTES,
            "email_sent": email_sent,
        }
        if not email_sent or settings.AUTH_OTP_DEBUG:
            body["debug_code"] = code
        return body
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("request-code failed for %s", payload.email)
        raise HTTPException(status_code=500, detail=f"No se pudo enviar el código: {exc}") from exc


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
