# LicitIA - Radar de Oportunidades

MVP SaaS para detectar y alertar sobre licitaciones públicas de interventoría vial en Colombia.

## 🎯 Descripción

LicitIA es una plataforma que:

- Detecta automáticamente licitaciones públicas del SECOP (últimos 60 días)
- Hace matching inteligente con la experiencia previa de la empresa
- Filtra licitaciones que coinciden con el historial de proyectos (score ≥ 60%)
- Envía alertas por email y WhatsApp a empresas suscritas (opcional)

## 🏗️ Arquitectura

Monorepo con **dos servicios desplegables** en Railway:

| Servicio                      | Root Directory | Stack                                     |
| ----------------------------- | -------------- | ----------------------------------------- |
| `vigilant-joy` (backend)      | `backend/`     | FastAPI, APScheduler, Alembic             |
| `licitia-frontend` (frontend) | `frontend/`    | React + Vite + TypeScript (nginx en prod) |

- **Base de datos**: PostgreSQL (Railway)
- **Documentos SECOP**: **Cloudflare R2** en producción (`DOCUMENT_STORAGE_BACKEND=r2`); Volume Railway `/data` solo como staging temporal si `DOCUMENT_STORAGE_WRITE_LOCAL=true`
- **Desarrollo local**: Docker Compose opcional

### Producción (Railway)

| Componente  | URL                                                   |
| ----------- | ----------------------------------------------------- |
| Frontend    | https://licitia-frontend-production.up.railway.app    |
| Backend API | https://vigilant-joy-production.up.railway.app/api/v1 |
| API Docs    | https://vigilant-joy-production.up.railway.app/docs   |

Variables clave en producción:

- **Backend** (`vigilant-joy`): `DATABASE_URL`, `DOCUMENTS_STORAGE_PATH=/data`, `DOCUMENT_STORAGE_BACKEND=r2`, `R2_*`, `CORS_ORIGINS` (incluye URL del frontend)
- **Frontend** (`licitia-frontend`): `VITE_API_URL=https://vigilant-joy-production.up.railway.app/api/v1`

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

### Frontend contra API de producción (local)

```bash
cd frontend
# Crear frontend/.env.local (gitignored):
# VITE_API_URL=/api/v1
# VITE_PROXY_TARGET=https://vigilant-joy-production.up.railway.app
npm run dev
```

El proxy de Vite evita problemas de CORS en desarrollo local.

## 📊 Base de Datos

### Crear Migración

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Modelos Principales

- **Tender**: Licitaciones detectadas del SECOP
- **TenderDocument**: Metadatos de documentos clave archivados (pliego, anexo técnico, presupuesto)
- **CompanyExperience**: Experiencia de la empresa para matching
- **Subscription**: Empresas suscritas para recibir alertas

## 📄 User Stories (estado)

### US 1.2 — Extracción automática de documentos SECOP ✅

Descarga automática de pliego, anexo técnico y presupuesto desde SECOP (`dmgg-8hin`) tras cada job de ingesta.

### US 1.2.1 — Almacenamiento en Cloudflare R2 ✅

Documentos clave persistidos en **Cloudflare R2** (API S3). En producción: `DOCUMENT_STORAGE_BACKEND=r2`, `DOCUMENT_STORAGE_WRITE_LOCAL=false`. Los 73 archivos existentes fueron migrados desde el Volume Railway; las descargas sirven desde R2 si no hay copia local.

**Variables de entorno (backend):**

```bash
DOCUMENT_STORAGE_BACKEND=r2
DOCUMENT_STORAGE_WRITE_LOCAL=false
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=licitia-documents
R2_PREFIX=prod
```

**Migrar archivos existentes en `/data`:**

```bash
cd backend
PYTHONPATH=. python scripts/migrate_documents_to_r2.py
PYTHONPATH=. python scripts/migrate_documents_to_r2.py --delete-local
```

**Validación en producción:** 73 documentos migrados a R2; descarga verificada desde el frontend (`LP-002-2026`, Sincelejo). Nuevas extracciones suben directo a R2 con `DOCUMENT_STORAGE_WRITE_LOCAL=false`.

### US 1.2.2 — Backfill histórico de documentos ✅

Completa la extracción de documentos clave para licitaciones ya ingestadas. Marca cada licitación con `documents_extraction_attempted_at` para no reintentar indefinidamente las que no tienen docs en SECOP.

**Reconciliar metadatos huérfanos (BD sin archivo en R2):**

```bash
cd backend
PYTHONPATH=. python scripts/reconcile_documents.py          # dry-run
PYTHONPATH=. python scripts/reconcile_documents.py --fix    # borrar huérfanos y reintentar
```

**Backfill acelerado del histórico:**

```bash
PYTHONPATH=. python scripts/backfill_documents.py --dry-run
PYTHONPATH=. python scripts/backfill_documents.py --batch-size 25 --max-batches 10
PYTHONPATH=. python scripts/backfill_documents.py            # hasta vaciar cola
```

El job diario (`extract_documents_for_pending_tenders`, lote de 25) sigue procesando pendientes automáticamente.

### US 1.2.3 — Cobertura ampliada de documentos SECOP ✅

Clasificador ampliado para nombres no estándar en SECOP (`proyecto de pliego`, `anexos de proyecto`, `analisis del sector`, `ppto`, `formulario 1`, etc.), reproceso de licitaciones sin docs y UX con estados claros en el panel de detalle.

**Reprocesar tras mejorar reglas:**

```bash
cd backend
# Licitaciones sin ningún documento archivado
PYTHONPATH=. python scripts/reset_document_extraction_attempts.py --dry-run
PYTHONPATH=. python scripts/reset_document_extraction_attempts.py
PYTHONPATH=. python scripts/backfill_documents.py --batch-size 25

# Re-sincronización incremental masiva (licitaciones ya procesadas)
PYTHONPATH=. python scripts/resync_documents.py --dry-run
PYTHONPATH=. python scripts/resync_documents.py --batch-size 25
PYTHONPATH=. python scripts/resync_documents.py --only-without-pliego --batch-size 25
```

**Estados en UI:** pendiente de extracción · procesada sin docs en SECOP · con documentos archivados.

### US 1.2.4 — Extracción de documentos ZIP/RAR 🔄

Descomprime archivos `.zip`/`.rar` de SECOP, clasifica el contenido interno (mismas reglas US 1.2.3) y archiva solo PDF/XLSX/DOCX clave. Los contenedores no se muestran en la UI.

Spec: [docs/US-1.2.4-extraccion-documentos-zip-rar.md](docs/US-1.2.4-extraccion-documentos-zip-rar.md)

```bash
cd backend
PYTHONPATH=. python scripts/extract_compressed_documents.py --dry-run
PYTHONPATH=. python scripts/extract_compressed_documents.py --batch-size 10
PYTHONPATH=. python scripts/extract_compressed_documents.py --external-id CO1.REQ.10837635
```

Variables: `ARCHIVE_EXTRACTION_ENABLED`, `ARCHIVE_MAX_DOWNLOAD_BYTES`, `ARCHIVE_MAX_UNCOMPRESSED_BYTES`, `ARCHIVE_MAX_FILES`.

### US 1.3 — Documentos en la interfaz ✅

El personal de licitaciones puede ver y descargar documentos desde el dashboard sin SSH ni DBeaver.

**Flujo:** Dashboard → clic en fila de licitación → panel de detalle → documentos agrupados por tipo → Descargar.

**API:**

- `GET /api/v1/tenders/{tender_id}/documents` — listado de metadatos
- `GET /api/v1/tenders/{tender_id}/documents/{document_id}/download` — descarga del archivo

**UI:** componente `TenderDetailPanel` (modal Carbon), integrado en `Dashboard` vía clic en `TenderTable`.

**Validación en producción:** descarga de PDF y Excel desde `licitia-frontend-production` contra licitaciones con documentos archivados (p. ej. `LP-013-2026`, `LP-002-2026`, `ICCU-LP-042-2026`).

## 🔄 Flujo de Trabajo

1. **Job periódico** (cada 24 h en producción, `FETCH_INTERVAL_HOURS`):
   - `fetch_and_store_new_tenders()` obtiene licitaciones del SECOP
   - `extract_documents_for_pending_tenders()` descarga documentos clave (lote de 25)
   - Envía notificaciones a suscripciones activas (si están configuradas)

2. **API REST**:
   - `GET /api/v1/tenders`: Listar licitaciones con filtros y matching de experiencia
   - `GET /api/v1/tenders/{id}`: Detalle de licitación
   - `GET /api/v1/tenders/{id}/documents`: Documentos archivados de la licitación
   - `GET /api/v1/tenders/{id}/documents/{document_id}/download`: Descargar archivo
   - `POST /api/v1/subscriptions`: Crear suscripción
   - `GET /api/v1/experiences`: Experiencias de la empresa

3. **Frontend**:
   - Dashboard con tabla de licitaciones (clic en fila abre detalle)
   - Panel de documentos agrupados por tipo con descarga directa
   - Filtros por fecha, departamento, matching con experiencia
   - Enlace a ficha del proceso en SECOP

## 🧪 Tests

```bash
cd backend
pytest app/tests/
```

## 🔐 Seguridad (MVP)

Para el MVP, la autenticación es opcional. Si configuras `API_KEY` en `.env`, puedes agregar middleware para proteger endpoints de escritura.

## 📝 Notas Importantes

- **SECOP Dataset**: Necesitas encontrar el dataset correcto en datos.gov.co y ajustar los nombres de campos en `secop_client.py` según el esquema real.
- **OpenAI**: Se usa `gpt-4o-mini` por defecto (modelo económico). Ajusta `OPENAI_MODEL_NAME` si prefieres otro.
- **Clasificación**: Si OpenAI falla, se usa un fallback basado en palabras clave.
- **Notificaciones**: Email y WhatsApp son opcionales. Si no configuras credenciales, simplemente se omiten.

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

- [ ] US 1.2.4 — Extracción de documentos dentro de ZIP/RAR 🔄 ([spec](docs/US-1.2.4-extraccion-documentos-zip-rar.md))
- [ ] US 1.2.5 — Clasificación de documentos por contenido PDF ([spec](docs/US-1.2.5-clasificacion-documentos-por-contenido-pdf.md))
- [ ] Columna referencia en tabla de licitaciones (mejor UX)
- [ ] Autenticación completa (JWT)
- [ ] Vista previa embebida de PDF en el navegador

## 📄 Licencia

Este es un proyecto MVP. Úsalo como base para tu desarrollo.
