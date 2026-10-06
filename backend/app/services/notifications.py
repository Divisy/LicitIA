"""Notification service for email and WhatsApp alerts."""
import smtplib
from email.message import EmailMessage
from typing import Optional
from app.models.tender import Tender
from app.models.subscription import Subscription
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_email_alert(subscription: Subscription, tender: Tender) -> None:
    """
    Send an email alert to a subscription about a new relevant tender.
    
    Args:
        subscription: The subscription to notify
        tender: The tender to notify about
    """
    try:
        # Build email message
        msg = EmailMessage()
        msg["From"] = settings.NOTIFICATION_FROM_EMAIL
        msg["To"] = subscription.contact_email
        msg["Subject"] = f"Nueva licitación de interventoría vial – {tender.entity_name}"
        
        # Build email body
        amount_str = f"${tender.amount:,.2f} COP" if tender.amount else "No especificado"
        pub_date_str = tender.publication_date.strftime('%Y-%m-%d') if tender.publication_date else 'N/A'
        closing_date_str = tender.closing_date.strftime('%Y-%m-%d') if tender.closing_date else 'N/A'
        # relevance_score removed - experience matching is the main approach
        object_preview = tender.object_text[:500] + ('...' if len(tender.object_text) > 500 else '')
        
        body = f"""Hola {subscription.contact_name},

Hemos detectado una nueva licitación que podría ser de tu interés:

Entidad: {tender.entity_name}
Departamento: {tender.department or 'N/A'}
Municipio: {tender.municipality or 'N/A'}
Monto: {amount_str}
Fecha de publicación: {pub_date_str}
Fecha de cierre: {closing_date_str}
Estado: {tender.state}

Objeto del proceso:
{object_preview}

Ver detalles: {tender.process_url}

---
LicitIA - Radar de Oportunidades
"""
        
        msg.set_content(body)
        
        # Send email via SMTP
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured, skipping email send")
            return
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        
        logger.info(f"Email alert sent to {subscription.contact_email} for tender {tender.id}")
    
    except Exception as e:
        logger.error(f"Error sending email alert to {subscription.contact_email}: {e}")


def send_login_code_email(to_email: str, code: str) -> None:
    """Send a one-time login code."""
    msg = EmailMessage()
    msg["From"] = settings.NOTIFICATION_FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Tu código LicitIA"
    ttl = getattr(settings, "AUTH_OTP_TTL_MINUTES", 10)
    msg.set_content(
        f"Tu código LicitIA es {code}. Caduca en {ttl} minutos.\n\n"
        "Si no pediste este código, ignora este correo.\n\n"
        "— LicitIA"
    )

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured; login code for %s was not emailed", to_email)
        return

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
    logger.info("Login code emailed to %s", to_email)


def send_whatsapp_alert(subscription: Subscription, tender: Tender) -> None:
    """
    Send a WhatsApp alert via Cloud API.
    
    Note: This is a placeholder implementation. Configure WhatsApp Cloud API
    credentials in settings to enable.
    
    Args:
        subscription: The subscription to notify
        tender: The tender to notify about
    """
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_ID:
        logger.debug("WhatsApp not configured, skipping")
        return
    
    try:
        import requests
        
        # Build message
        amount_str = f"${tender.amount:,.2f} COP" if tender.amount else "No especificado"
        closing_date_str = tender.closing_date.strftime('%Y-%m-%d') if tender.closing_date else 'N/A'
        
        message = f"""🚧 Nueva licitación de interventoría vial

Entidad: {tender.entity_name}
Departamento: {tender.department or 'N/A'}
Monto: {amount_str}
Fecha cierre: {closing_date_str}

Ver detalles: {tender.process_url}"""
        
        url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": subscription.whatsapp_number,
            "type": "text",
            "text": {"body": message},
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        logger.info(f"WhatsApp alert sent to {subscription.whatsapp_number} for tender {tender.id}")
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp alert to {subscription.whatsapp_number}: {e}")

