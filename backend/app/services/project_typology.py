"""Classify project typologies from a contract or tender object."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Iterable, Optional

CATALOG: dict[str, str] = {
    "construccion": "Construcción",
    "edificacion": "Edificación",
    "vias": "Vías",
    "geotecnica": "Geotécnica",
    "espacio_publico": "Espacio público",
    "bicicarril": "Bicicarril",
    "senalizacion": "Señalización",
    "acueducto_alcantarillado": "Acueducto y alcantarillado",
    "parques": "Parques",
    "puentes": "Puentes",
    "otro": "Otra",
}

_SPECIFIC_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "vias",
        (
            "malla vial",
            "paviment",
            "carreteable",
            "doble calzada",
            "via terciaria",
            "vias terciarias",
            "via urbana",
            "vias urbanas",
            "mejoramiento vial",
            "rehabilitacion vial",
            "carretera",
            "afirmado",
            "terciaria",
            " vias ",
            " via ",
            " vial ",
        ),
    ),
    (
        "edificacion",
        (
            "edificacion",
            "edificio",
            "colegio",
            "hospital",
            "vivienda",
            "aulas",
            "centro de salud",
            "institucion educativa",
        ),
    ),
    (
        "geotecnica",
        (
            "geotecn",
            "talud",
            "estabilidad de ladera",
            "cimentacion profunda",
            "muros de contencion",
        ),
    ),
    (
        "espacio_publico",
        (
            "espacio publico",
            "andenes",
            "alameda",
            "plazas",
            "espacio peaton",
        ),
    ),
    (
        "bicicarril",
        ("ciclorruta", "ciclo ruta", "ciclovia", "ciclo via", "bicicarril", "cicloinfra"),
    ),
    ("senalizacion", ("senaliz", "semafor")),
    (
        "acueducto_alcantarillado",
        (
            "acueducto",
            "alcantarill",
            "ptap",
            "ptar",
            "redes hidraulicas",
            "acueduct y alcant",
        ),
    ),
    ("parques", ("parques", "parque ", "zonas verdes", "zona verde")),
    ("puentes", ("puente", "viaducto", "ponton")),
)

_CONSTRUCCION = (
    "construccion",
    "obras civiles",
    "obra civil",
    "ejecucion de obra",
    "ejecucion de las obras",
)

_CATALOG_VALUES = set(CATALOG)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return f" {text.strip()} "


def typology_label(value: str) -> str:
    return CATALOG.get(value, value)


def parse_typology_params(raw: Optional[Iterable[str]]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        for part in str(item).split(","):
            key = part.strip().lower()
            if key in _CATALOG_VALUES and key not in seen:
                seen.add(key)
                values.append(key)
    return values


def typologies_from_stored(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        parsed = [part.strip() for part in str(raw).split(",") if part.strip()]
    if not isinstance(parsed, list):
        return []
    return parse_typology_params(str(item) for item in parsed)


def classify_project_typologies(*parts: Optional[str]) -> list[str]:
    """Return catalog values for a contract/tender object. Empty if there is no usable text."""
    haystack = _normalize(" ".join(part or "" for part in parts))
    letters = sum(1 for ch in haystack if ch.isalpha())
    if letters < 12:
        return []

    found: list[str] = []
    for key, tokens in _SPECIFIC_SIGNALS:
        if any(token in haystack for token in tokens):
            found.append(key)

    if found:
        return found

    if any(token in haystack for token in _CONSTRUCCION):
        return ["construccion"]
    return ["otro"]


def typologies_intersect(object_text: str, selected: Iterable[str]) -> bool:
    wanted = set(parse_typology_params(selected))
    if not wanted:
        return True
    return bool(wanted.intersection(classify_project_typologies(object_text)))


def apply_project_typologies(experience) -> list[str]:
    objeto = (getattr(experience, "specific_experience", None) or "").strip()
    description = (getattr(experience, "project_description", None) or "").strip()
    values = classify_project_typologies(objeto or description)
    dumped = json.dumps(values, ensure_ascii=False) if values else None
    if hasattr(experience, "project_typologies"):
        experience.project_typologies = dumped
    return values


def union_typologies(experiences: Iterable) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for experience in experiences:
        stored = typologies_from_stored(getattr(experience, "project_typologies", None))
        values = stored or classify_project_typologies(
            getattr(experience, "specific_experience", None),
            getattr(experience, "project_description", None)
            if not (getattr(experience, "specific_experience", None) or "").strip()
            else "",
        )
        for key in values:
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return ordered
