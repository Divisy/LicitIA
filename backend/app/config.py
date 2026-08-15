"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/licitia"
    
    # SECOP API (Socrata)
    SECOP_BASE_URL: str = "https://www.datos.gov.co/resource"
    SECOP_DATASET_ID: str = ""
    SECOP_APP_TOKEN: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    
    # WhatsApp Cloud API
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_ID: Optional[str] = None
    
    # Email (SMTP)
    NOTIFICATION_FROM_EMAIL: str = "noreply@licitia.com"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    
    # API Security (optional for MVP)
    API_KEY: Optional[str] = None
    
    # Scheduler
    FETCH_INTERVAL_HOURS: int = 2

    # SECOP ingestion window (days) for MVP daily sync
    SECOP_FETCH_LOOKBACK_DAYS: int = 1
    
    class Config:
        env_file = [".env", "../.env"]  # Check backend/.env and root/.env
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env that aren't in the model


settings = Settings()

