"""Tests for SECOP MVP filters and mapping."""
from datetime import datetime

from app.services.secop_client import build_location
from app.services.secop_filters import (
    ESTADO_APERTURA_ABIERTO,
    ESTADO_PUBLICADO,
    MODALITY_CONCURSO_MERITOS_ABIERTO,
    MODALITY_LICITACION_OBRA_PUBLICA,
    UNSPSC_CODES_CONCURSO_MERITOS,
    is_dashboard_active_tender,
)


def test_unspsc_codes_count():
    assert len(UNSPSC_CODES_CONCURSO_MERITOS) == 10


def test_unspsc_codes_include_civil_engineering():
    assert "81101500" in UNSPSC_CODES_CONCURSO_MERITOS
    assert "95110000" in UNSPSC_CODES_CONCURSO_MERITOS


def test_modalities_match_secop_dataset_values():
    assert MODALITY_CONCURSO_MERITOS_ABIERTO == "Concurso de méritos abierto"
    assert MODALITY_LICITACION_OBRA_PUBLICA == "Licitación pública Obra Publica"


def test_estado_publicado_value():
    assert ESTADO_PUBLICADO == "Publicado"


def test_is_dashboard_active_tender():
    assert is_dashboard_active_tender(state="Publicado", apertura_estado="Abierto")
    assert not is_dashboard_active_tender(state="Publicado", apertura_estado="Cerrado")
    assert not is_dashboard_active_tender(state="Evaluación", apertura_estado="Abierto")
    assert not is_dashboard_active_tender(state="Publicado", apertura_estado=None)


def test_build_location_combines_department_and_municipality():
    assert build_location("Cundinamarca", "Bogotá") == "Cundinamarca, Bogotá"


def test_build_location_handles_missing_parts():
    assert build_location("Antioquia", None) == "Antioquia"
    assert build_location(None, None) is None
