"""SECOP document API client and file download helpers (user story 1.2)."""
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote

import requests
from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger
from app.services.secop_document_filters import DocumentType, classify_document, is_key_document

logger = get_logger(__name__)

_CHUNK_SIZE = 64 * 1024


class SecopDocumentDTO(BaseModel):
    """DTO for a SECOP downloadable document."""
    external_document_id: str
    portfolio_id: str
    file_name: str
    download_url: str
    file_size: Optional[int] = None
    extension: Optional[str] = None
    description: Optional[str] = None
    document_type: DocumentType


def _extract_url(value) -> str:
    if isinstance(value, dict):
        return str(value.get("url") or "")
    return str(value or "")


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\- ]+", "_", name).strip("._ ")
    return cleaned or "documento"


def fetch_documents_for_portfolio(portfolio_id: str) -> List[SecopDocumentDTO]:
    """Fetch document metadata from SECOP Archivos Descarga dataset."""
    if not portfolio_id or not settings.SECOP_DOCUMENTS_DATASET_ID:
        return []

    base_url = f"{settings.SECOP_BASE_URL}/{settings.SECOP_DOCUMENTS_DATASET_ID}.json"
    safe_portfolio_id = portfolio_id.replace("'", "''")
    params = {
        "$limit": 500,
        "$where": f"proceso='{safe_portfolio_id}'",
    }

    headers = {}
    if settings.SECOP_APP_TOKEN:
        headers["X-App-Token"] = settings.SECOP_APP_TOKEN

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        raw_items = response.json()
    except requests.RequestException as exc:
        logger.error("Error fetching SECOP documents for %s: %s", portfolio_id, exc)
        return []

    documents: List[SecopDocumentDTO] = []
    seen_ids: set[str] = set()

    for item in raw_items:
        external_id = str(item.get("id_documento") or "").strip()
        if not external_id or external_id in seen_ids:
            continue
        seen_ids.add(external_id)

        file_name = str(item.get("nombre_archivo") or item.get("descripci_n") or "documento").strip()
        description = item.get("descripci_n")
        doc_type = classify_document(file_name, str(description) if description else None)

        if not is_key_document(doc_type):
            continue

        download_url = _extract_url(item.get("url_descarga_documento"))
        if not download_url:
            continue

        file_size = None
        if item.get("tamanno_archivo"):
            try:
                file_size = int(item["tamanno_archivo"])
            except (TypeError, ValueError):
                file_size = None

        documents.append(
            SecopDocumentDTO(
                external_document_id=external_id,
                portfolio_id=portfolio_id,
                file_name=file_name,
                download_url=download_url,
                file_size=file_size,
                extension=item.get("extensi_n"),
                description=str(description) if description else None,
                document_type=doc_type,
            )
        )

    logger.info(
        "Found %s key documents for portfolio %s",
        len(documents),
        portfolio_id,
    )
    return documents


def build_document_storage_path(
    external_id: str,
    document_type: DocumentType,
    file_name: str,
    external_document_id: str,
) -> Path:
    """Build local storage path: {base}/{external_id}/{type}/{id}_{filename}."""
    root = Path(settings.DOCUMENTS_STORAGE_PATH)
    folder_name = _safe_filename(external_id)
    type_folder = document_type.value
    safe_name = _safe_filename(unquote(file_name))
    return root / folder_name / type_folder / f"{external_document_id}_{safe_name}"


def download_document_file(document: SecopDocumentDTO, destination: Path) -> bool:
    """Download a SECOP document to the given path."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and destination.stat().st_size > 0:
        logger.debug("Document already exists at %s", destination)
        return True

    headers = {}
    if settings.SECOP_APP_TOKEN:
        headers["X-App-Token"] = settings.SECOP_APP_TOKEN

    try:
        with requests.get(
            document.download_url,
            headers=headers,
            timeout=120,
            stream=True,
        ) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    if chunk:
                        handle.write(chunk)
        return True
    except requests.RequestException as exc:
        logger.error(
            "Failed to download document %s (%s): %s",
            document.external_document_id,
            document.file_name,
            exc,
        )
        if destination.exists():
            destination.unlink(missing_ok=True)
        return False
