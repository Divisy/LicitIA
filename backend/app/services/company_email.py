"""Reject consumer inboxes so signup is company email only."""
from __future__ import annotations

PERSONAL_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.es",
        "hotmail.co.uk",
        "outlook.com",
        "outlook.es",
        "live.com",
        "live.com.mx",
        "msn.com",
        "yahoo.com",
        "yahoo.es",
        "yahoo.com.mx",
        "ymail.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "gmx.com",
        "gmx.es",
        "mail.com",
        "zoho.com",
        "yopmail.com",
        "tutanota.com",
        "tuta.com",
    }
)

COMPANY_EMAIL_REQUIRED_MESSAGE = "Usa el correo de tu empresa"


def email_domain(email: str) -> str:
    if "@" not in (email or ""):
        return ""
    return email.strip().lower().rsplit("@", 1)[-1]


def is_personal_email(email: str) -> bool:
    return email_domain(email) in PERSONAL_EMAIL_DOMAINS


def is_company_email(email: str) -> bool:
    domain = email_domain(email)
    return bool(domain) and domain not in PERSONAL_EMAIL_DOMAINS
