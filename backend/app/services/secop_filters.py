"""SECOP II filter configuration for MVP user story 1.1."""

# Modalidades de contratación (valores exactos en dataset SECOP II p6dx-8zbt)
MODALITY_CONCURSO_MERITOS_ABIERTO = "Concurso de méritos abierto"
MODALITY_LICITACION_OBRA_PUBLICA = "Licitación pública Obra Publica"

# Estado del procedimiento requerido por el MVP
ESTADO_PUBLICADO = "Publicado"

# UNSPSC solo aplica a Concurso de méritos abierto (estudios, diseños, interventoría, obras)
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
