from app.services.rup_contract_kind import (
    RupExperienceKind,
    classify_rup_experience_kind,
    extract_unspsc_codes,
    kind_payload_for_experience,
    unspsc_codes_from_stored,
)


def test_classify_obra_from_unspsc_72():
    kind = classify_rup_experience_kind(unspsc_codes=["72103300"])
    assert kind == RupExperienceKind.EJECUCION_OBRA


def test_classify_estudios_from_unspsc_8110():
    kind = classify_rup_experience_kind(unspsc_codes=["81101500"])
    assert kind == RupExperienceKind.ESTUDIOS_DISENOS


def test_classify_estudios_disenos_y_obra_when_both_signals():
    kind = classify_rup_experience_kind(
        object_text="Estudios, diseños y construcción del acueducto",
        unspsc_codes=["72141100", "81101500"],
    )
    assert kind == RupExperienceKind.ESTUDIOS_DISENOS_Y_OBRA


def test_classify_interventoria_wins_over_unspsc_obra():
    kind = classify_rup_experience_kind(
        object_text="Interventoría técnica de obras de pavimentación",
        unspsc_codes=["72103300"],
    )
    assert kind == RupExperienceKind.INTERVENTORIA


def test_classify_construction_related_flag():
    kind = classify_rup_experience_kind(
        extra_text="CONTRATO RELACIONADO CON LA CONSTRUCCIÓN (LEY 1537 DE 2012) (SI O NO): SI"
    )
    assert kind == RupExperienceKind.EJECUCION_OBRA


def test_extract_unspsc_from_ccb_table_and_spaced_pdf_text():
    piped = extract_unspsc_codes("|SEGM|FAMI|CLAS|PROD|\n| 72 | 10 | 33 | 00 |\n| 81 | 10 | 15 | 00 |")
    assert piped == ["72103300", "81101500"]
    spaced = extract_unspsc_codes("CLASIFICADOR SEGM FAMI CLAS PROD 72 10 33 00 72 15 15 00")
    assert "72103300" in spaced
    assert "72151500" in spaced
    assert "08032019" not in extract_unspsc_codes("Fecha terminacion: 08 03 2019")
    assert extract_unspsc_codes("Contrato IDU-1257-2017 objeto 72103300 SERVICIOS") == []
    assert unspsc_codes_from_stored(
        stored_json=None,
        category="72103300 SERVICIOS DE MANTENIMIENTO",
        description="72103300 SERVICIOS",
    ) == []
    assert unspsc_codes_from_stored(stored_json='["72103300", "81101500"]') == [
        "72103300",
        "81101500",
    ]


def test_extract_unspsc_when_pdf_splits_clasificador_and_glues_code():
    stacked = extract_unspsc_codes(
        """
        CONTRATO EJECUTADO IDENTIFICADO CON EL
        CLASIFICADOR DE BIENES Y SERVICIOS EN EL TERCER NIVEL:
        CONTRATO RELACIONADO CON LA CONSTRUCCIÓN (LEY 1537 DE 2012) (SI O NO): SI
        SEGM
        FAMI
        CLAS
        PROD
        72
        10
        33
        00
        """
    )
    assert stacked == ["72103300"]
    glued = extract_unspsc_codes(
        "CLASIFICACION CONTRATO 72103300SERVICIOS DE MANTENIMIENTO Y REPARACIÓN"
    )
    assert glued == ["72103300"]


def test_kind_payload_reclassifies_legacy_rows():
    kind, label = kind_payload_for_experience(
        engineering_area=None,
        project_description="72103300 SERVICIOS DE MANTENIMIENTO Y REPARACIÓN DE INFRAESTRUCTURA",
        category="72103300 SERVICIOS DE MANTENIMIENTO",
        contract_number="IDU-1257-2017",
    )
    assert kind == "ejecucion_obra"
    assert label == "Ejecución de obra"


def test_kind_payload_uses_acta_objeto_over_stored_rup_kind():
    kind, label = kind_payload_for_experience(
        engineering_area="ejecucion_obra",
        project_description="72103300 SERVICIOS DE MANTENIMIENTO",
        category="72103300",
        contract_number="RUP-1",
        specific_experience=(
            "Interventoría técnica y administrativa de las obras de pavimentación "
            "en el municipio de Santa Isabel."
        ),
    )
    assert kind == "interventoria"
    assert label == "Interventoría"


def test_kind_payload_classifies_all_four_kinds_from_objeto():
    cases = [
        (
            "Elaboración de estudios y diseños definitivos para el acueducto veredal.",
            "estudios_disenos",
            "Estudios y diseños",
        ),
        (
            "Interventoría integral al contrato de obra del sistema vial.",
            "interventoria",
            "Interventoría",
        ),
        (
            "Estudios, diseños y construcción del sistema de acueducto de Santa Isabel.",
            "estudios_disenos_y_obra",
            "Estudios, diseños y obra",
        ),
        (
            "Construcción y pavimentación de la malla vial urbana en Paipa.",
            "ejecucion_obra",
            "Ejecución de obra",
        ),
    ]
    for objeto, expected_kind, expected_label in cases:
        kind, label = kind_payload_for_experience(
            engineering_area="desconocido",
            project_description="",
            category="",
            contract_number="RUP-12",
            specific_experience=objeto,
        )
        assert kind == expected_kind
        assert label == expected_label


def test_estudios_para_mejoramiento_is_not_obra():
    kind, _ = kind_payload_for_experience(
        engineering_area="ejecucion_obra",
        project_description="obra",
        category="",
        contract_number="RUP-2",
        specific_experience=(
            "Elaboración de estudios y diseños para el mejoramiento de la malla vial."
        ),
    )
    assert kind == "estudios_disenos"
