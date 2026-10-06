from app.services.project_typology import (
    classify_project_typologies,
    typologies_intersect,
)


def test_classifies_vias_from_pavement_object():
    assert classify_project_typologies(
        "Pavimentación de la malla vial urbana en el municipio de Paipa."
    ) == ["vias"]


def test_classifies_acueducto_not_overwriting_estudios_kind():
    assert classify_project_typologies(
        "Elaboración de estudios y diseños del sistema de acueducto y alcantarillado."
    ) == ["acueducto_alcantarillado"]


def test_classifies_puentes_from_interventoria_object():
    assert classify_project_typologies(
        "Interventoría para la construcción de un puente vehicular sobre el río."
    ) == ["puentes"]


def test_empty_object_has_no_typology():
    assert classify_project_typologies("") == []
    assert classify_project_typologies("n/a") == []


def test_unknown_usable_object_is_otro():
    assert classify_project_typologies(
        "Suministro e instalación de mobiliario de oficina para la secretaría."
    ) == ["otro"]


def test_generic_construction_without_family():
    assert classify_project_typologies(
        "Construcción y ejecución de las obras civiles del contrato."
    ) == ["construccion"]


def test_multiple_typologies():
    result = classify_project_typologies(
        "Construcción de andenes, espacio público y ciclorruta en la avenida."
    )
    assert "espacio_publico" in result
    assert "bicicarril" in result


def test_interventoria_of_roads_is_vias():
    assert classify_project_typologies(
        "Interventoría técnica de las vías urbanas del municipio."
    ) == ["vias"]
    assert typologies_intersect("pavimentación de la malla vial", ["vias", "parques"])
    assert not typologies_intersect("construcción de un parque lineal", ["vias"])
