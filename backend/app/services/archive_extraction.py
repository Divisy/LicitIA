"""Extract key documents from SECOP ZIP/RAR archives (US 1.2.4)."""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService
from app.services.secop_document_filters import DocumentType, classify_document, is_key_document
from app.services.secop_documents import (
    SecopDocumentDTO,
    build_document_object_key,
    build_document_storage_path,
    download_document_file,
    fetch_archive_candidates_for_portfolio,
    is_archive_filename,
)

logger = get_logger(__name__)

ARCHIVE_CONTAINER_KEYWORDS: tuple[str, ...] = (
    "anexo",
    "anexos",
    "pliego",
    "pliegos",
    "presupuesto",
    "ppto",
    "formato",
    "formatos",
    "documento",
    "documentos",
    "otros documentos",
    "apu",
    "aiu",
    "condiciones",
)

ARCHIVE_EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "plano",
    "planos",
    "cad",
    "bim",
    "dwg",
)

ALLOWED_INNER_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".xlsx", ".xls", ".xlsm", ".docx", ".doc"}
)


@dataclass
class ExtractedInnerFile:
    """A file extracted from an archive into staging."""

    relative_path: str
    file_name: str
    local_path: Path
    file_size: int


@dataclass
class ArchiveExtractionResult:
    """Outcome of processing archives for one tender."""

    archives_processed: int = 0
    archives_failed: int = 0
    inner_files_inspected: int = 0
    documents_saved: int = 0
    documents_added: int = 0
    containers_removed: int = 0
    errors: list[str] = field(default_factory=list)


def build_internal_document_id(archive_external_id: str, inner_path: str) -> str:
    """Stable synthetic id for a file inside a SECOP archive."""
    normalized = inner_path.replace("\\", "/").lstrip("/")
    return f"{archive_external_id}:{normalized}"


def is_archive_excluded_by_name(file_name: str) -> bool:
    haystack = file_name.lower()
    return any(keyword in haystack for keyword in ARCHIVE_EXCLUDE_KEYWORDS)


def is_archive_container_candidate(document: SecopDocumentDTO) -> bool:
    """Return True if a SECOP archive should be downloaded and inspected."""
    if not is_archive_filename(document.file_name):
        return False
    if is_archive_excluded_by_name(document.file_name):
        return False
    if document.file_size and document.file_size > settings.ARCHIVE_MAX_DOWNLOAD_BYTES:
        return False
    if is_key_document(document.document_type):
        return True
    if document.document_type != DocumentType.OTRO:
        return False
    haystack = f"{document.file_name} {document.description or ''}".lower()
    return any(keyword in haystack for keyword in ARCHIVE_CONTAINER_KEYWORDS)


def _inner_extension_allowed(file_name: str) -> bool:
    return Path(file_name).suffix.lower() in ALLOWED_INNER_EXTENSIONS


def _iter_zip_members(archive_path: Path) -> Iterator[ExtractedInnerFile]:
    total_uncompressed = 0
    file_count = 0

    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.file_size <= 0:
                continue
            inner_name = Path(info.filename).name
            if not inner_name or not _inner_extension_allowed(inner_name):
                continue

            total_uncompressed += info.file_size
            file_count += 1
            if total_uncompressed > settings.ARCHIVE_MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Archive exceeds maximum uncompressed size")
            if file_count > settings.ARCHIVE_MAX_FILES:
                raise ValueError("Archive exceeds maximum file count")

            with archive.open(info, "r") as source:
                destination = archive_path.parent / f"extract_{file_count}_{inner_name}"
                with destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

            yield ExtractedInnerFile(
                relative_path=info.filename.replace("\\", "/"),
                file_name=inner_name,
                local_path=destination,
                file_size=info.file_size,
            )


def _iter_rar_members(archive_path: Path) -> Iterator[ExtractedInnerFile]:
    try:
        import rarfile
    except ImportError as exc:
        raise RuntimeError("rarfile is not installed") from exc

    unrar_tool = shutil.which("unrar-free") or shutil.which("unrar")
    if unrar_tool:
        rarfile.UNRAR_TOOL = unrar_tool

    total_uncompressed = 0
    file_count = 0

    with rarfile.RarFile(archive_path, "r") as archive:
        for info in archive.infolist():
            if info.isdir():
                continue
            inner_name = Path(info.filename).name
            if not inner_name or not _inner_extension_allowed(inner_name):
                continue

            file_size = info.file_size or info.compress_size or 0
            total_uncompressed += file_size
            file_count += 1
            if total_uncompressed > settings.ARCHIVE_MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Archive exceeds maximum uncompressed size")
            if file_count > settings.ARCHIVE_MAX_FILES:
                raise ValueError("Archive exceeds maximum file count")

            destination = archive_path.parent / f"extract_{file_count}_{inner_name}"
            with archive.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)

            yield ExtractedInnerFile(
                relative_path=info.filename.replace("\\", "/"),
                file_name=inner_name,
                local_path=destination,
                file_size=file_size,
            )


def extract_archive_members(archive_path: Path) -> list[ExtractedInnerFile]:
    """Extract allowed inner files from a ZIP or RAR archive."""
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        return list(_iter_zip_members(archive_path))
    if suffix == ".rar":
        return list(_iter_rar_members(archive_path))
    raise ValueError(f"Unsupported archive format: {suffix}")


def _remove_container_document(
    db: Session,
    tender: Tender,
    archive_external_id: str,
    storage: DocumentStorageService,
) -> bool:
    record = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.tender_id == tender.id,
            TenderDocument.external_document_id == archive_external_id,
        )
        .first()
    )
    if not record:
        return False
    storage.delete_object(record.file_path)
    db.delete(record)
    return True


def _persist_inner_document(
    db: Session,
    tender: Tender,
    archive: SecopDocumentDTO,
    inner: ExtractedInnerFile,
    storage: DocumentStorageService,
    upsert_document_record,
) -> tuple[bool, bool]:
    doc_type = classify_document(inner.file_name)
    if not is_key_document(doc_type):
        return False, False

    synthetic_id = build_internal_document_id(archive.external_document_id, inner.relative_path)
    inner_document = SecopDocumentDTO(
        external_document_id=synthetic_id,
        portfolio_id=archive.portfolio_id,
        file_name=inner.file_name,
        download_url=archive.download_url,
        file_size=inner.file_size,
        extension=Path(inner.file_name).suffix.lstrip(".").lower() or None,
        description=f"Extracted from {archive.file_name}",
        document_type=doc_type,
    )
    object_key = build_document_object_key(
        tender.external_id,
        inner_document.document_type,
        inner_document.file_name,
        inner_document.external_document_id,
    )
    staging_path = build_document_storage_path(
        tender.external_id,
        inner_document.document_type,
        inner_document.file_name,
        inner_document.external_document_id,
    )
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inner.local_path, staging_path)
    storage.persist_local_file(staging_path, object_key)
    _, created = upsert_document_record(db, tender, inner_document, object_key)
    return True, created


def process_archive_document(
    db: Session,
    tender: Tender,
    archive: SecopDocumentDTO,
    storage: DocumentStorageService,
    upsert_document_record,
) -> ArchiveExtractionResult:
    """Download, extract, classify and persist key documents from one archive."""
    result = ArchiveExtractionResult(archives_processed=1)
    staging_dir = Path(tempfile.mkdtemp(prefix="licitia_archive_"))
    archive_path = staging_dir / Path(archive.file_name).name

    try:
        if not download_document_file(archive, archive_path):
            result.archives_failed = 1
            result.errors.append(f"download failed: {archive.file_name}")
            return result

        inner_files = extract_archive_members(archive_path)
        result.inner_files_inspected = len(inner_files)
        key_children_saved = 0

        for inner in inner_files:
            saved, created = _persist_inner_document(
                db,
                tender,
                archive,
                inner,
                storage,
                upsert_document_record,
            )
            if not saved:
                continue
            result.documents_saved += 1
            key_children_saved += 1
            if created:
                result.documents_added += 1

        if key_children_saved > 0 and _remove_container_document(
            db,
            tender,
            archive.external_document_id,
            storage,
        ):
            result.containers_removed = 1

    except Exception as exc:
        result.archives_failed = 1
        result.errors.append(f"{archive.file_name}: {exc}")
        logger.error(
            "Archive extraction failed for tender %s archive %s: %s",
            tender.external_id,
            archive.file_name,
            exc,
            exc_info=True,
        )
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return result


def extract_archives_for_tender(
    db: Session,
    tender: Tender,
    portfolio_id: str,
    storage: DocumentStorageService,
    upsert_document_record,
) -> ArchiveExtractionResult:
    """Process all archive candidates for a tender portfolio."""
    if not settings.ARCHIVE_EXTRACTION_ENABLED:
        return ArchiveExtractionResult()

    totals = ArchiveExtractionResult()
    candidates = [
        document
        for document in fetch_archive_candidates_for_portfolio(portfolio_id)
        if is_archive_container_candidate(document)
    ]

    for archive in candidates:
        result = process_archive_document(
            db,
            tender,
            archive,
            storage,
            upsert_document_record,
        )
        totals.archives_processed += result.archives_processed
        totals.archives_failed += result.archives_failed
        totals.inner_files_inspected += result.inner_files_inspected
        totals.documents_saved += result.documents_saved
        totals.documents_added += result.documents_added
        totals.containers_removed += result.containers_removed
        totals.errors.extend(result.errors)

    if totals.documents_saved:
        logger.info(
            "Archive extraction saved %s documents for tender %s (%s)",
            totals.documents_saved,
            tender.external_id,
            tender.reference,
        )

    return totals
