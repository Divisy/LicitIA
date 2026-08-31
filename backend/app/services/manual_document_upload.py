"""Manual upload of key tender documents when SECOP extraction is incomplete."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import build_document_object_key, build_document_storage_path

logger = get_logger(__name__)

MANUAL_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        DocumentType.PLIEGO_CONDICIONES.value,
        DocumentType.ANEXO_TECNICO.value,
        DocumentType.PRESUPUESTO.value,
        DocumentType.INDICADORES_FINANCIEROS.value,
    }
)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".xlsx", ".xls", ".xlsm"})

MANUAL_UPLOAD_DESCRIPTION = "Cargado manualmente"


def validate_document_type(document_type: str) -> DocumentType:
    normalized = (document_type or "").strip().lower()
    if normalized not in MANUAL_DOCUMENT_TYPES:
        raise ValueError(
            "document_type must be one of: pliego_condiciones, anexo_tecnico, presupuesto, indicadores_financieros"
        )
    return DocumentType(normalized)


def validate_upload_filename(file_name: str, document_type: DocumentType | None = None) -> str:
    name = Path(file_name or "").name.strip()
    if not name:
        raise ValueError("file name is required")
    extension = Path(name).suffix.lower()
    allowed = set(ALLOWED_EXTENSIONS)
    if document_type == DocumentType.INDICADORES_FINANCIEROS:
        allowed.update({".docx", ".doc"})
    if extension not in allowed:
        raise ValueError("allowed file types: PDF, XLSX, XLS, XLSM" + (
            ", DOCX" if document_type == DocumentType.INDICADORES_FINANCIEROS else ""
        ))
    return name


async def save_manual_tender_document(
    db: Session,
    tender: Tender,
    document_type: DocumentType,
    upload_file: UploadFile,
    storage: DocumentStorageService,
) -> TenderDocument:
    """Persist a user-uploaded key document for a tender."""
    if not settings.MANUAL_DOCUMENT_UPLOAD_ENABLED:
        raise ValueError("manual document upload is disabled")

    file_name = validate_upload_filename(upload_file.filename or "", document_type)
    file_bytes = await upload_file.read()
    if not file_bytes:
        raise ValueError("uploaded file is empty")

    max_bytes = settings.MANUAL_DOCUMENT_UPLOAD_MAX_BYTES
    if len(file_bytes) > max_bytes:
        raise ValueError(f"file exceeds maximum size of {max_bytes // (1024 * 1024)} MB")

    external_document_id = f"manual-{uuid.uuid4().hex[:24]}"
    extension = Path(file_name).suffix.lstrip(".").lower() or None
    document_type_enum = document_type

    object_key = build_document_object_key(
        tender.external_id,
        document_type_enum,
        file_name,
        external_document_id,
    )
    staging_path = build_document_storage_path(
        tender.external_id,
        document_type_enum,
        file_name,
        external_document_id,
    )
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_bytes(file_bytes)
    storage.persist_local_file(staging_path, object_key)

    record = TenderDocument(
        tender_id=tender.id,
        external_document_id=external_document_id,
        document_type=document_type_enum.value,
        file_name=file_name,
        file_path=object_key,
        download_url="manual://upload",
        file_size=len(file_bytes),
        extension=extension,
        description=MANUAL_UPLOAD_DESCRIPTION,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Manual document uploaded for tender %s: type=%s file=%s",
        tender.external_id,
        document_type_enum.value,
        file_name,
    )
    return record
