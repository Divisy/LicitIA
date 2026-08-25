"""Tests for presupuesto content classification (US 1.2.5 MVP)."""
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from openpyxl import Workbook

from app.models.tender import Tender, TenderSource
from app.services.document_content_classification import (
    classify_presupuesto_by_content,
    extract_candidate_text,
    extract_presupuesto_by_content_for_tender,
    fetch_otro_presupuesto_candidates,
    is_excluded_presupuesto_candidate,
)
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import SecopDocumentDTO


def _build_xlsx_with_text(text: str, path: Path) -> None:
  workbook = Workbook()
  sheet = workbook.active
  sheet["A1"] = text
  sheet["A2"] = "Valor total del presupuesto"
  workbook.save(path)


def test_classify_presupuesto_by_content_anchor_phrase():
  text = "Este documento corresponde al FORMULARIO 1 - PRESUPUESTO OFICIAL de la obra."
  assert classify_presupuesto_by_content(text) is True


def test_classify_presupuesto_by_content_requires_multiple_keywords():
  assert classify_presupuesto_by_content("presupuesto y subtotal") is True
  assert classify_presupuesto_by_content("solo presupuesto") is False


def test_classify_presupuesto_by_content_excludes_cdp():
  text = "CERTIFICADO DE DISPONIBILIDAD PRESUPUESTAL CDP 2026"
  assert classify_presupuesto_by_content(text) is False
  assert is_excluded_presupuesto_candidate("CDP 2026.pdf", text) is True


def test_extract_candidate_text_from_xlsx(tmp_path: Path):
  xlsx_path = tmp_path / "budget.xlsx"
  _build_xlsx_with_text("Analisis de precios unitarios", xlsx_path)

  xlsx_text = extract_candidate_text(xlsx_path, ".xlsx")

  assert "analisis de precios unitarios" in xlsx_text.lower()


@patch("app.services.document_content_classification.fetch_all_documents_for_portfolio")
def test_fetch_otro_presupuesto_candidates_prefers_spreadsheets(mock_fetch):
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
      file_name="FORMATO.xlsx",
      download_url="https://example.com/2",
      document_type=DocumentType.OTRO,
    ),
    SecopDocumentDTO(
      external_document_id="3",
      portfolio_id="portfolio-1",
      file_name="CDP.pdf",
      download_url="https://example.com/3",
      document_type=DocumentType.OTRO,
    ),
  ]

  candidates = fetch_otro_presupuesto_candidates("portfolio-1")

  assert len(candidates) == 2
  assert candidates[0].file_name == "FORMATO.xlsx"


@patch("app.services.document_content_classification.settings")
@patch("app.services.document_content_classification.download_document_file", return_value=True)
@patch("app.services.document_content_classification.extract_candidate_text")
@patch("app.services.document_content_classification.fetch_otro_presupuesto_candidates")
def test_extract_presupuesto_by_content_persists_first_match(
  mock_candidates,
  mock_extract_text,
  mock_download,
  mock_settings,
  tmp_path: Path,
):
  mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_ENABLED = True
  mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_PAGES = 2
  mock_settings.PRESUPUESTO_CONTENT_CLASSIFICATION_MAX_CHARS = 4000

  candidate = SecopDocumentDTO(
    external_document_id="99",
    portfolio_id="portfolio-1",
    file_name="FORMATO ECONOMICO.xlsx",
    download_url="https://example.com/99",
    document_type=DocumentType.OTRO,
    extension="xlsx",
  )
  mock_candidates.return_value = [candidate]
  mock_extract_text.return_value = "Formulario 1 presupuesto oficial propuesta economica"

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
