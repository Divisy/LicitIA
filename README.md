# LicitIA - Radar de Oportunidades

MVP SaaS para detectar y alertar sobre licitaciones públicas de interventoría vial en Colombia.

## 🎯 Descripción

LicitIA es una plataforma que:
- Detecta automáticamente licitaciones públicas del SECOP II (filtros MVP por modalidad, UNSPSC y estado)
- Extrae y archiva documentos clave por licitación: pliego de condiciones, anexo técnico y presupuesto
- Hace matching inteligente con la experiencia previa de la empresa
- Filtra licitaciones que coinciden con el historial de proyectos (score ≥ 60%)
- Envía alertas por email y WhatsApp a empresas suscritas (opcional)

## 🏗️ Arquitectura

- **Backend**: FastAPI (Python 3.11+)
- **Base de datos**: PostgreSQL
- **ORM**: SQLAlchemy 2.x + Alembic
- **Jobs en background**: APScheduler
- **Frontend**: React + Vite + TypeScript
- **Containerización**: Docker Compose

## 📋 Requisitos Previos

- Docker y Docker Compose instalados
- Cuenta de OpenAI (para clasificación)
- (Opcional) Token de Socrata para SECOP API
- (Opcional) Credenciales SMTP para emails
- (Opcional) WhatsApp Cloud API credentials

## 🚀 Inicio Rápido

### 1. Configurar Variables de Entorno

Copia el archivo de ejemplo y completa las variables:

```bash
cp .env.example .env
```

Edita `.env` y completa:
- `SECOP_DATASET_ID`: ID del dataset de SECOP en datos.gov.co
- `OPENAI_API_KEY`: Tu clave de API de OpenAI
- `SMTP_USER` y `SMTP_PASSWORD`: Para enviar emails (opcional)
- Otras configuraciones según necesites

### 2. Ejecutar con Docker Compose

```bash
docker-compose -f docker/docker-compose.yml up --build
```

Esto iniciará:
- PostgreSQL en el puerto 5432
- Backend API en http://localhost:8000
- Frontend en http://localhost:3000

### 3. Acceder a la Aplicación

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 📁 Estructura del Proyecto

```
Licitia/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints FastAPI
│   │   ├── core/            # Configuración (DB, logging, scheduler)
│   │   ├── models/          # Modelos SQLAlchemy
│   │   ├── schemas/         # Schemas Pydantic
│   │   ├── services/        # Lógica de negocio
│   │   └── tests/           # Tests
│   ├── alembic/             # Migraciones de base de datos
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Cliente API
│   │   ├── components/     # Componentes React
│   │   └── pages/          # Páginas
│   ├── package.json
│   └── Dockerfile
├── docker/
│   └── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Desarrollo Local (sin Docker)

### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env con DATABASE_URL apuntando a PostgreSQL local

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

## 📊 Base de Datos

### Crear Migración

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Modelos Principales

- **Tender**: Licitaciones detectadas del SECOP (`portfolio_id` para enlazar documentos)
- **TenderDocument**: Metadatos de documentos descargados (tipo, ruta, URL SECOP, tamaño)
- **Subscription**: Empresas suscritas para recibir alertas

## 📄 User Story 1.2 — Extracción de documentos SECOP

Tras cada ingesta de licitaciones, el sistema procesa un lote de licitaciones pendientes y descarga los documentos clave desde el dataset de archivos de SECOP (`dmgg-8hin`), enlazado por `portfolio_id` / `proceso`.

### Tipos de documento

| Tipo | Ejemplos de nombre en SECOP |
|------|----------------------------|
| `pliego_condiciones` | Pliego de condiciones, documento base |
| `anexo_tecnico` | Anexo técnico, especificaciones técnicas |
| `presupuesto` | Presupuesto, oferta económica, APU |

### Almacenamiento

```
{DOCUMENTS_STORAGE_PATH}/{external_id}/{tipo}/{id_documento}_{nombre_archivo}
```

Ejemplo local: `storage/documents/CO1.REQ.10803194/pliego_condiciones/839746559_Documento Base.pdf`

En Railway producción, montar un Volume en `/data` y configurar `DOCUMENTS_STORAGE_PATH=/data`.

### Variables de entorno (documentos)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `SECOP_DOCUMENTS_DATASET_ID` | `dmgg-8hin` | Dataset SECOP de archivos descargables |
| `DOCUMENTS_STORAGE_PATH` | `storage/documents` | Ruta base de almacenamiento |
| `DOCUMENT_EXTRACTION_ENABLED` | `true` | Activa/desactiva la extracción |
| `DOCUMENT_EXTRACTION_BATCH_SIZE` | `25` | Licitaciones por lote sin documentos |
| `FETCH_INTERVAL_HOURS` | `2` | Intervalo del job SECOP (+ extracción) |
| `SECOP_FETCH_LOOKBACK_DAYS` | `1` | Días hacia atrás en cada sincronización |

### Extracción manual (desarrollo o backfill)

```bash
cd backend && source venv/bin/activate
python -c "
from app.core.db import SessionLocal
from app.services.document_extraction import extract_documents_for_pending_tenders
db = SessionLocal()
print(extract_documents_for_pending_tenders(db, limit=25))
db.close()
"
```

## 🔄 Flujo de Trabajo

1. **Job periódico** (`FETCH_INTERVAL_HOURS`, por defecto cada 2 horas):
   - `fetch_and_store_new_tenders()` obtiene licitaciones del SECOP (ventana `SECOP_FETCH_LOOKBACK_DAYS`)
   - Aplica filtros MVP: Concurso de méritos + UNSPSC + Publicado; Licitación pública Obra Pública + Publicado
   - `extract_documents_for_pending_tenders()` descarga documentos clave del lote configurado
   - Envía notificaciones a suscripciones activas (si aplica)

2. **API REST**:
   - `GET /api/v1/tenders`: Listar licitaciones con filtros
   - `GET /api/v1/tenders/{id}`: Detalle de licitación
   - `GET /api/v1/tenders/{id}/documents`: Documentos descargados de una licitación
   - `POST /api/v1/subscriptions`: Crear suscripción
   - `GET /api/v1/subscriptions`: Listar suscripciones

3. **Frontend**:
   - Dashboard con tabla de licitaciones
   - Filtros por fecha, departamento, relevancia
   - Enlaces directos a procesos en SECOP

## 🧪 Tests

```bash
cd backend
pytest app/tests/
```

## 🔐 Seguridad (MVP)

Para el MVP, la autenticación es opcional. Si configuras `API_KEY` en `.env`, puedes agregar middleware para proteger endpoints de escritura.

## 📝 Notas Importantes

- **SECOP licitaciones**: Dataset principal `p6dx-8zbt` (configurable con `SECOP_DATASET_ID`).
- **SECOP documentos**: Dataset `dmgg-8hin` (`SECOP_DOCUMENTS_DATASET_ID`). Los archivos se descargan desde `community.secop.gov.co` con headers de navegador (User-Agent + Referer).
- **OpenAI**: Se usa `gpt-4o-mini` por defecto (modelo económico). Ajusta `OPENAI_MODEL_NAME` si prefieres otro.
- **Clasificación**: Si OpenAI falla, se usa un fallback basado en palabras clave.
- **Notificaciones**: Email y WhatsApp son opcionales. Si no configuras credenciales, simplemente se omiten.
- **Almacenamiento en Railway**: El Volume del servicio backend persiste los PDFs entre redeploys. Para históricos grandes (>500 MB), planear migración a Cloudflare R2 (US 1.3).

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL
- Verifica que PostgreSQL esté corriendo
- Revisa `DATABASE_URL` en `.env`

### Error al obtener datos de SECOP
- Verifica `SECOP_DATASET_ID` en `.env`
- Revisa los nombres de campos en `secop_client.py` - pueden variar según el dataset

### Frontend no se conecta al backend
- Verifica que el backend esté corriendo en puerto 8000
- Revisa la configuración de proxy en `vite.config.ts`

## 📚 Próximos Pasos

- [ ] US 1.3: Almacenamiento persistente de documentos en Cloudflare R2
- [ ] Análisis de contenido de PDFs (extracción de texto)
- [ ] Autenticación completa (JWT)
- [ ] Panel de administración
- [ ] Más filtros y búsqueda avanzada
- [ ] Exportación de datos (CSV, Excel)
- [ ] Dashboard con estadísticas
- [ ] Webhooks para integraciones

## 📄 Licencia

Este es un proyecto MVP. Úsalo como base para tu desarrollo.

