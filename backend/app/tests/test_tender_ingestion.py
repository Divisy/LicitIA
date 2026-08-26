"""Tests for SECOP tender ingestion and state refresh."""
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.secop_client import SecopTenderDTO
from app.services.tender_ingestion import refresh_stale_tender_states


def _sample_dto(
    external_id: str,
    *,
    state: str = "Publicado",
    apertura_estado: str | None = "Abierto",
) -> SecopTenderDTO:
    return SecopTenderDTO(
        external_id=external_id,
        reference="LP-TEST",
        portfolio_id="portfolio-1",
        entity_name="Entidad Test",
        object_text="Interventoría vial",
        state=state,
        apertura_estado=apertura_estado,
        process_url="https://example.com",
        source="SECOP_II",
    )


@patch("app.services.tender_ingestion.fetch_tenders_by_external_ids")
@patch("app.services.tender_ingestion.settings")
def test_refresh_stale_tender_states_purges_inactive(mock_settings, mock_fetch):
    mock_settings.SECOP_STATE_REFRESH_ENABLED = True
    mock_settings.SECOP_STATE_REFRESH_BATCH_SIZE = 10

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.123",
        source=TenderSource.SECOP_II,
        entity_name="Old Entity",
        object_text="Old object",
        state="Publicado",
        apertura_estado="Abierto",
        process_url="https://example.com",
        updated_at=datetime(2026, 8, 1),
    )

    class FakeQuery:
        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return [tender]

    class FakeSession:
        def query(self, _model):
            return FakeQuery()

        def commit(self):
            return None

        def delete(self, _obj):
            return None

    mock_fetch.return_value = [
        _sample_dto("CO1.REQ.123", state="Adjudicado", apertura_estado="Cerrado")
    ]

    with patch("app.services.tender_ingestion.purge_tender") as mock_purge:
        stats = refresh_stale_tender_states(FakeSession())

    assert stats["purged"] == 1
    assert stats["refreshed"] == 0
    mock_purge.assert_called_once()


@patch("app.services.tender_ingestion.settings")
def test_refresh_stale_tender_states_disabled(mock_settings):
    mock_settings.SECOP_STATE_REFRESH_ENABLED = False
    stats = refresh_stale_tender_states(object())  # type: ignore[arg-type]
    assert stats == {"candidates": 0, "refreshed": 0, "state_changes": 0}
