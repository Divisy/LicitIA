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
    SYNC_ADMIN_TOKEN: Optional[str] = None
    
    # Scheduler
    FETCH_INTERVAL_HOURS: int = 2

    # SECOP ingestion window (days). Overlap avoids missing tenders if a job is skipped.
    SECOP_FETCH_LOOKBACK_DAYS: int = 7
    SECOP_STATE_REFRESH_ENABLED: bool = True
    SECOP_STATE_REFRESH_BATCH_SIZE: int = 50
    INACTIVE_TENDER_PURGE_BATCH_SIZE: int = 100

    # SECOP documents dataset (Archivos Descarga desde 2025)
    SECOP_DOCUMENTS_DATASET_ID: str = "dmgg-8hin"
    DOCUMENTS_STORAGE_PATH: str = "storage/documents"
    DOCUMENT_EXTRACTION_ENABLED: bool = True
    DOCUMENT_EXTRACTION_BATCH_SIZE: int = 25

    # Archive extraction (US 1.2.4)
    ARCHIVE_EXTRACTION_ENABLED: bool = True
    ARCHIVE_MAX_DOWNLOAD_BYTES: int = 104_857_600  # 100 MB
    ARCHIVE_MAX_UNCOMPRESSED_BYTES: int = 524_288_000  # 500 MB
    ARCHIVE_MAX_FILES: int = 200
    ARCHIVE_MAX_DEPTH: int = 1

    # Tender summary extraction (US 1.4)
    TENDER_SUMMARY_EXTRACTION_ENABLED: bool = True

    # Tender requirements extraction (US 1.5)
    TENDER_REQUIREMENTS_EXTRACTION_ENABLED: bool = True
    TENDER_REQUIREMENTS_USE_LLM: bool = True
    TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE: float = 0.70
    TENDER_REQUIREMENTS_LLM_MAX_CHARS: int = 8_000
    TENDER_REQUIREMENTS_MAX_CHARS: int = 250_000

    # Presupuesto content classification (US 1.2.5 MVP)
    PRESUPUESTO_CONTENT_CLASSIFICATION_ENABLED: bool = True
    PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_PAGES: int = 2
    PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_CHARS: int = 4000

    # Manual key document upload (US 1.2.6 MVP)
    MANUAL_DOCUMENT_UPLOAD_ENABLED: bool = True
    MANUAL_DOCUMENT_UPLOAD_MAX_BYTES: int = 52_428_800  # 50 MB

    # Document storage backend: local (Railway Volume) or r2 (Cloudflare R2)
    DOCUMENT_STORAGE_BACKEND: str = "local"
    # When using R2, keep a copy on the local volume (default: false to save disk)
    DOCUMENT_STORAGE_WRITE_LOCAL: bool = False

    # Cloudflare R2 (S3-compatible)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_PREFIX: str = ""
    R2_REGION: str = "auto"

    @property
    def r2_endpoint_url(self) -> Optional[str]:
        if not self.R2_ACCOUNT_ID:
            return None
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    
    class Config:
        env_file = [".env", "../.env"]  # Check backend/.env and root/.env
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env that aren't in the model


settings = Settings()

