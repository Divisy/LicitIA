"""SECOP II filter configuration for MVP (US 1.1 / US 1.12)."""

from __future__ import annotations

import re
import unicodedata

# Modalidades de contratación (valores exactos en dataset SECOP II p6dx-8zbt)
MODALITY_CONCURSO_MERITOS_ABIERTO = "Concurso de méritos abierto"
MODALITY_LICITACION_OBRA_PUBLICA = "Licitación pública Obra Publica"

# Tipos de contrato (valores exactos en p6dx-8zbt)
CONTRACT_TYPE_INTERVENTORIA = "Interventoría"
CONTRACT_TYPE_CONSULTORIA = "Consultoría"

# Estado del procedimiento requerido por el MVP
ESTADO_PUBLICADO = "Publicado"
ESTADO_APERTURA_ABIERTO = "Abierto"


def is_dashboard_active_tender(*, state: str, apertura_estado: str | None) -> bool:
    """True when the tender is Publicado and still open for offers in SECOP."""
    return state == ESTADO_PUBLICADO and apertura_estado == ESTADO_APERTURA_ABIERTO


# UNSPSC de obra/infra: inclusión extra (OR), no candado.
# datos.gov.co deja codigo_principal_de_categoria = UNSPECIFIED en casi toda interventoría.
UNSPSC_CODES_CONCURSO_MERITOS = [
    "81101500",  # Ingeniería civil y arquitectura
    "72101513",  # Servicios de construcción fuera del sitio (offsite)
    "70102902",  # Servicios de paisajismo
    "72103301",  # Servicios o reparaciones o mantenimiento de calles o parqueaderos
    "72110000",  # Servicios de construcción de edificaciones residenciales
    "72120000",  # Servicios de construcción de edificaciones no residenciales
    "72140000",  # Servicios de construcción pesada
    "95110000",  # Vías
    "95120000",  # Estructuras y edificios permanentes
    "95140000",  # Estructuras y edificio prefabricados
]

# Familias (prefijo) usadas en CMA de interventoría/consultoría de infra
UNSPSC_PREFIXES_CONCURSO_MERITOS = tuple(
    sorted(
        {
            code[:6] for code in UNSPSC_CODES_CONCURSO_MERITOS
        }
        | {
            "811015",  # ingeniería civil (incluye hijos 81101515)
            "811022",
            "811415",  # control de calidad
            "801016",  # gestión / gerencia de proyectos
            "801015",
            "771018",  # gestión ambiental
            "721015",
            "721033",
            "721100",
            "721200",
            "721400",
            "951100",
            "951200",
            "951400",
            "701029",
        }
    )
)

UNSPSC_PREFIXES_EXCLUDED = ("4322", "4323")  # TI / telecomunicaciones

_TI_OBJECT_TOKENS = (
    "telecomunic",
    "software",
    "informatic",
    "wan-lan",
    "wan lan",
    "videoconferenc",
    "seguridad informatic",
    "desarrollo de sistemas",
)

_INFRA_OR_ESTUDIOS_TOKENS = (
    "estudios y dise",
    "estudio y dise",
    "estudios, dise",
    "diseno",
    "diseño",
    "factibilidad",
    "prefactibilidad",
    "consultoria",
    "consultoría",
    "ingenieria",
    "ingeniería",
    "interventor",
    "obra",
    "vial",
    "via ",
    " vías",
    "acueducto",
    "alcantarill",
    "ptar",
    "ptap",
    "paviment",
    "puente",
    "edific",
    "infraestructur",
    "espacio publico",
    "espacio público",
    "malla vial",
    "placa huella",
    "saneamiento",
    "alumbrado",
    "construccion",
    "construcción",
    "mejoramiento",
)


def _normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.lower()).strip()


def _unspsc_digits(code: str | None) -> str:
    raw = (code or "").strip()
    if not raw or raw.upper() in {"UNSPECIFIED", "NO DEFINIDO"}:
        return ""
    if "." in raw:
        raw = raw.split(".")[-1]
    return re.sub(r"\D", "", raw)


def unspsc_matches_concurso_meritos(code: str | None) -> bool:
    digits = _unspsc_digits(code)
    if not digits:
        return False
    if any(digits.startswith(prefix) for prefix in UNSPSC_PREFIXES_EXCLUDED):
        return False
    return any(digits.startswith(prefix) for prefix in UNSPSC_PREFIXES_CONCURSO_MERITOS)


def unspsc_is_excluded_it(code: str | None) -> bool:
    digits = _unspsc_digits(code)
    return bool(digits) and any(digits.startswith(prefix) for prefix in UNSPSC_PREFIXES_EXCLUDED)


def is_interventoria_contract_type(contract_type: str | None) -> bool:
    return "interventor" in _normalize(contract_type)


def is_consultoria_contract_type(contract_type: str | None) -> bool:
    return "consultor" in _normalize(contract_type)


def _haystack(*parts: str | None) -> str:
    return " " + _normalize(" ".join(p or "" for p in parts)) + " "


def _object_looks_like_it(object_text: str | None) -> bool:
    hay = _haystack(object_text)
    return any(token in hay for token in _TI_OBJECT_TOKENS)


def _object_looks_like_infra_or_estudios(object_text: str | None) -> bool:
    hay = _haystack(object_text)
    return any(token in hay for token in _INFRA_OR_ESTUDIOS_TOKENS)


def should_ingest_concurso_meritos(
    *,
    contract_type: str | None,
    object_text: str | None,
    unspsc_code: str | None = None,
    additional_unspsc: str | None = None,
) -> bool:
    """
    US 1.12: CMA entra por tipo de contrato, no por UNSPSC de datos.gov.co.

    datos abiertos deja UNSPSC = UNSPECIFIED aunque la ficha SECOP II sí tenga 81101500.
    """
    if is_interventoria_contract_type(contract_type):
        return True

    if is_consultoria_contract_type(contract_type):
        if unspsc_is_excluded_it(unspsc_code) or unspsc_is_excluded_it(additional_unspsc):
            return False
        if _object_looks_like_it(object_text):
            return False
        if unspsc_matches_concurso_meritos(unspsc_code) or unspsc_matches_concurso_meritos(
            additional_unspsc
        ):
            return True
        return _object_looks_like_infra_or_estudios(object_text)

    return unspsc_matches_concurso_meritos(unspsc_code) or unspsc_matches_concurso_meritos(
        additional_unspsc
    )
