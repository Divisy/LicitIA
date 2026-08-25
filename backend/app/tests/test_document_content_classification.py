"""Tests for presupuesto content classification (US 1.2.5 MVP)."""
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from openpyxl import Workbook

from app.models.tender import Tender, TenderSource
from app.services.document_content_classification import (
    classify_presupuesto_candidate,
    content_has_presupuesto_anchor,
    extract_presupuesto_by_content_for_tender,
    fetch_otro_presupuesto_candidates,
    is_excluded_presupuesto_filename,
    looks_like_presupuesto_workbook,
)
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import SecopDocumentDTO


def _build_presupuesto_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "FORMULARIO 1 - PRESUPUESTO OFICIAL"
    sheet["A2"] = "Valor total del presupuesto"
    sheet["B2"] = 1_250_000_000
    workbook.save(path)


def _build_matrix_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "Matriz 1 - Experiencia"
    sheet["A2"] = "Valor total de contratos"
    sheet["B2"] = 5_000_000_000
    workbook.save(path)


def test_excluded_filenames_block_false_positives():
    assert is_excluded_presupuesto_filename("4. Matriz 1-Experiencia INTERV.xlsx") is True
    assert is_excluded_presupuesto_filename("CERTIFICADO_PDA 2026.pdf") is True
    assert is_excluded_presupuesto_filename("Autorizacion de vigencias futuras obra.pdf") is True
    assert is_excluded_presupuesto_filename("Formato 9 - Puntaje.pdf") is True


def test_content_anchor_requires_strong_phrase():
    assert content_has_presupuesto_anchor("FORMULARIO 1 PRESUPUESTO OFICIAL") is True
    assert content_has_presupuesto_anchor("solo presupuesto y subtotal") is False


def test_looks_like_presupuesto_workbook(tmp_path: Path):
    presupuesto = tmp_path / "presupuesto.xlsx"
    matrix = tmp_path / "matrix.xlsx"
    _build_presupuesto_xlsx(presupuesto)
    _build_matrix_xlsx(matrix)

    assert looks_like_presupuesto_workbook(presupuesto) is True
    assert looks_like_presupuesto_workbook(matrix) is False


def test_classify_presupuesto_candidate_rejects_matrix_by_filename(tmp_path: Path):
    matrix = tmp_path / "matrix.xlsx"
    _build_matrix_xlsx(matrix)
    text = "FORMULARIO 1 presupuesto oficial valor total"
    assert classify_presupuesto_candidate(
        "Matriz 1 - Experiencia.xlsx",
        text,
        matrix,
        ".xlsx",
    ) is False


def test_classify_presupuesto_candidate_accepts_real_formulario_1(tmp_path: Path):
    presupuesto = tmp_path / "presupuesto.xlsx"
    _build_presupuesto_xlsx(presupuesto)
    text = "FORMULARIO 1 PRESUPUESTO OFICIAL"
    assert classify_presupuesto_candidate(
        "DOCUMENTO ECONOMICO.xlsx",
        text,
        presupuesto,
        ".xlsx",
    ) is True


@patch("app.services.document_content_classification.fetch_all_documents_for_portfolio")
def test_fetch_otro_presupuesto_candidates_skips_excluded_names(mock_fetch):
    mock_fetch.return_value = [
        SecopDocumentDTO(
            external_document_id="1",
            portfolio_id="portfolio-1",
            file_name="DOCUMENTO.pdf",
            download_url="https://example.com/1",
            document_type=DocumentType.OTRO,
        ),
        SecopDocumentDTO(
            external_document_id="2",
            portfolio_id="portfolio-1",
            file_name="Matriz 1 Experiencia.xlsx",
            download_url="https://example.com/2",
            document_type=DocumentType.OTRO,
        ),
    ]

    candidates = fetch_otro_presupuesto_candidates("portfolio-1")
    assert len(candidates) == 1
    assert candidates[0].file_name == "DOCUMENTO.pdf"


@patch("app.services.document_content_classification.settings")
@patch("app.services.document_content_classification.extract_candidate_text", return_value="FORMULARIO 1 PRESUPUESTO OFICIAL")
@patch("app.services.document_content_classification.download_document_file", return_value=True)
@patch("app.services.document_content_classification.classify_presupuesto_candidate", return_value=True)
@patch("app.services.document_content_classification.fetch_otro_presupuesto_candidates")
def test_extract_presupuesto_by_content_persists_first_match(
    mock_candidates,
    mock_classify,
    mock_download,
    mock_extract_text,
    mock_settings,
    tmp_path: Path,
):
    mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_ENABLED = True
    mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_PAGES = 2
    mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_CHARS = 4000

    candidate = SecopDocumentDTO(
        external_document_id="99",
        portfolio_id="portfolio-1",
        file_name="DOCUMENTO ECONOMICO.xlsx",
        download_url="https://example.com/99",
        document_type=DocumentType.OTRO,
        extension="xlsx",
    )
    mock_candidates.return_value = [candidate]

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.99",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Object",
        state="Publicado",
        process_url="https://example.com",
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    storage = MagicMock()
    saved_documents: list[SecopDocumentDTO] = []

    def fake_upsert(db_session, tender_obj, document, object_key):
        saved_documents.append(document)
        return MagicMock(), True

    def fake_download(document, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake")
        return True

    mock_download.side_effect = fake_download

    result = extract_presupuesto_by_content_for_tender(
        db,
        tender,
        "portfolio-1",
        storage,
        fake_upsert,
    )

    assert result.documents_saved == 1
    assert result.documents_added == 1
    assert saved_documents[0].document_type == DocumentType.PRESUPUESTO
