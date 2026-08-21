"""Tests for duplicate SECOP document handling."""
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.tender_document import TenderDocument
from app.services.document_extraction import deduplicate_visible_documents


def _doc(file_name: str, document_type: str, *, hours_ago: int = 0) -> TenderDocument:
    downloaded_at = datetime.utcnow() - timedelta(hours=hours_ago)
    return TenderDocument(
        id=uuid4(),
        tender_id=uuid4(),
        external_document_id=str(uuid4().int)[:9],
        document_type=document_type,
        file_name=file_name,
        file_path=f"path/{file_name}",
        download_url="https://example.com",
        downloaded_at=downloaded_at,
        created_at=downloaded_at,
    )


def test_deduplicate_visible_documents_keeps_latest_copy():
    older = _doc("Documento Base de Interventoria de obra publica.docx", "pliego_condiciones", hours_ago=2)
    newer = _doc("Documento Base de Interventoria de obra publica.docx", "pliego_condiciones", hours_ago=1)

    result = deduplicate_visible_documents([older, newer])

    assert len(result) == 1
    assert result[0].id == newer.id


def test_deduplicate_visible_documents_normalizes_accents_and_spacing():
    first = _doc("Anexo 1  Anexo Técnico.docx", "anexo_tecnico", hours_ago=2)
    second = _doc("Anexo 1 Anexo Tecnico.docx", "anexo_tecnico", hours_ago=1)

    result = deduplicate_visible_documents([first, second])

    assert len(result) == 1
    assert result[0].id == second.id


def test_deduplicate_visible_documents_keeps_different_types_separate():
    pliego = _doc("Documento Base.pdf", "pliego_condiciones")
    anexo = _doc("Documento Base.pdf", "anexo_tecnico")

    result = deduplicate_visible_documents([pliego, anexo])

    assert len(result) == 2
