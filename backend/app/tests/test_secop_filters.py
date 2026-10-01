"""Tests for SECOP MVP filters and mapping."""
from app.services.secop_client import build_location
from app.services.secop_filters import (
    ESTADO_APERTURA_ABIERTO,
    ESTADO_PUBLICADO,
    MODALITY_CONCURSO_MERITOS_ABIERTO,
    MODALITY_LICITACION_OBRA_PUBLICA,
    UNSPSC_CODES_CONCURSO_MERITOS,
    is_dashboard_active_tender,
    should_ingest_concurso_meritos,
    unspsc_matches_concurso_meritos,
)


def test_unspsc_codes_count():
    assert len(UNSPSC_CODES_CONCURSO_MERITOS) == 10


def test_unspsc_codes_include_civil_engineering():
    assert "81101500" in UNSPSC_CODES_CONCURSO_MERITOS
    assert "95110000" in UNSPSC_CODES_CONCURSO_MERITOS


def test_unspsc_matches_child_code_and_prefix():
    assert unspsc_matches_concurso_meritos("V1.81101500")
    assert unspsc_matches_concurso_meritos("81101515")
    assert unspsc_matches_concurso_meritos("V1.80101600")
    assert not unspsc_matches_concurso_meritos("UNSPECIFIED")
    assert not unspsc_matches_concurso_meritos("V1.43222500")


def test_modalities_match_secop_dataset_values():
    assert MODALITY_CONCURSO_MERITOS_ABIERTO == "Concurso de méritos abierto"
    assert MODALITY_LICITACION_OBRA_PUBLICA == "Licitación pública Obra Publica"


def test_estado_publicado_value():
    assert ESTADO_PUBLICADO == "Publicado"
    assert ESTADO_APERTURA_ABIERTO == "Abierto"


def test_is_dashboard_active_tender():
    assert is_dashboard_active_tender(state="Publicado", apertura_estado="Abierto")
    assert not is_dashboard_active_tender(state="Publicado", apertura_estado="Cerrado")
    assert not is_dashboard_active_tender(state="Evaluación", apertura_estado="Abierto")
    assert not is_dashboard_active_tender(state="Publicado", apertura_estado=None)


def test_ingest_interventoria_without_unspsc():
    """datos.gov.co often publishes Interventoría as UNSPECIFIED (FDLCB-CMA-001-2026)."""
    assert should_ingest_concurso_meritos(
        contract_type="Interventoría",
        object_text=(
            "REALIZAR LA INTERVENTORÍA TÉCNICA, ADMINISTRATIVA, FINANCIERA "
            "DEL CONTRATO DE MALLA VIAL DE CIUDAD BOLÍVAR"
        ),
        unspsc_code="UNSPECIFIED",
    )


def test_ingest_interventoria_project_management_unspsc():
    assert should_ingest_concurso_meritos(
        contract_type="Interventoría",
        object_text="Interventoría a la ampliación del puente Simón Bolívar",
        unspsc_code="V1.80101600",
    )


def test_ingest_consultoria_estudios_disenos():
    assert should_ingest_concurso_meritos(
        contract_type="Consultoría",
        object_text=(
            "ESTUDIOS Y DISEÑOS PARA LA CONSTRUCCIÓN DE LA PLANTA DE "
            "TRATAMIENTO DE AGUAS RESIDUALES PTAR"
        ),
        unspsc_code="UNSPECIFIED",
    )


def test_reject_consultoria_software():
    assert not should_ingest_concurso_meritos(
        contract_type="Consultoría",
        object_text="Desarrollo de software y servicios de telecomunicaciones WAN-LAN",
        unspsc_code="V1.43222500",
    )


def test_reject_consultoria_it_unspsc_even_with_generic_object():
    assert not should_ingest_concurso_meritos(
        contract_type="Consultoría",
        object_text="Prestación de servicios de consultoría",
        unspsc_code="43222500",
    )


def test_unspsc_only_still_includes_obra_family():
    assert should_ingest_concurso_meritos(
        contract_type="No Especificado",
        object_text="Mejoramiento de vías terciarias",
        unspsc_code="95110000",
    )


def test_build_location_combines_department_and_municipality():
    assert build_location("Cundinamarca", "Bogotá") == "Cundinamarca, Bogotá"


def test_build_location_handles_missing_parts():
    assert build_location("Antioquia", None) == "Antioquia"
    assert build_location(None, None) is None
