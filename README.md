# LicitIA

Plataforma para detectar y gestionar licitaciones públicas de Colombia (SECOP II), enfocada en consultoría, interventoría y obra pública.

**Repositorio:** [github.com/Divisy/LicitIA](https://github.com/Divisy/LicitIA)

## Estado del MVP

| Componente | Estado |
|------------|--------|
| User Story 1.1 — Conexión SECOP + filtros MVP | Implementado |
| Backend en Railway | [vigilant-joy-production.up.railway.app](https://vigilant-joy-production.up.railway.app) |
| Ingesta automática SECOP | Cada 2 horas (APScheduler) |
| Frontend conectado a producción | Pendiente |

## Qué hace LicitIA

```text
SECOP II (API datos.gov.co)
        ↓  job cada 2 h
Backend FastAPI (Railway)
        ↓
PostgreSQL (Railway)
        ↓
API REST /api/v1/tenders
```

1. Consulta el dataset público de SECOP II vía API Socrata.
2. Filtra licitaciones según reglas del MVP (modalidad, estado, UNSPSC).
3. Persiste los resultados en PostgreSQL.
4. Expone los datos vía API REST (Swagger en `/docs`).

## User Story 1.1 — Filtros SECOP

La ingesta MVP (`fetch_mvp_secop_tenders`) aplica dos flujos:

| Modalidad | Filtro UNSPSC | Estado |
|-----------|---------------|--------|
| Concurso de méritos abierto | 10 códigos (ver `backend/app/services/secop_filters.py`) | Publicado |
| Licitación pública Obra Publica | No aplica | Publicado |

### Campos guardados por licitación

| Campo SECOP | Columna en BD / API |
|-------------|---------------------|
| Entidad | `entity_name` |
| Referencia | `reference` |
| Descripción | `object_text` |
| Fase actual | `current_phase` |
| Fecha presentación oferta | `closing_date` |
| Cuantía | `amount` |
| Estado | `state` |
| Ubicación | `department`, `municipality`, `location` |

Archivos clave:

- `backend/app/services/secop_filters.py` — códigos UNSPSC y modalidades
- `backend/app/services/secop_client.py` — cliente SECOP y mapeo de campos
- `backend/app/services/tender_ingestion.py` — job de ingesta y persistencia

## Producción (Railway)

| Recurso | Valor |
|---------|-------|
| API | https://vigilant-joy-production.up.railway.app |
| Health | https://vigilant-joy-production.up.railway.app/api/v1/health |
| Swagger | https://vigilant-joy-production.up.railway.app/docs |
| Licitaciones | https://vigilant-joy-production.up.railway.app/api/v1/tenders |

### Variables de entorno (backend)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Referencia al Postgres de Railway | `${{Postgres.DATABASE_URL}}` |
| `SECOP_DATASET_ID` | Dataset SECOP II | `p6dx-8zbt` |
| `SECOP_BASE_URL` | Base API Socrata | `https://www.datos.gov.co/resource` |
| `FETCH_INTERVAL_HOURS` | Frecuencia del job | `2` |
| `SECOP_FETCH_LOOKBACK_DAYS` | Ventana de consulta (días) | `1` (operación normal) |
| `CORS_ORIGINS` | Orígenes permitidos del frontend | URLs separadas por coma |

**Carga histórica inicial:** usar `SECOP_FETCH_LOOKBACK_DAYS=60` una vez, luego volver a `1`.

El deploy usa `Dockerfile` y `railway.toml` en la raíz del monorepo. El contenedor ejecuta `backend/init_railway.sh` (migraciones + uvicorn).

## Ver la base de datos (sin frontend)

### Opción A — Swagger

Abrir `/docs` y probar `GET /api/v1/tenders`.

### Opción B — Railway Query

Postgres → Database → Query:

```sql
SELECT COUNT(*) FROM tenders;
```

### Opción C — DBeaver (túnel SSH, recomendado)

1. Instalar [DBeaver](https://dbeaver.io) y Railway CLI (`npm install -g @railway/cli`).
2. Generar llave SSH si no existe: `ssh-keygen -t ed25519`
3. Agregar la llave pública en [railway.app/account/ssh-keys](https://railway.app/account/ssh-keys).
4. Vincular el proyecto y abrir túnel:

```bash
cd /ruta/a/LicitIA-2
railway login
railway link
railway connect Postgres --tunnel-only
```

5. En DBeaver: conexión PostgreSQL a `127.0.0.1` + puerto del túnel, database `railway`, user `postgres`.
6. Navegar: `Schemas → public → Tables → tenders` → View Data.

> El túnel debe permanecer abierto en la terminal. El puerto local cambia en cada sesión.

## Arquitectura

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI + Uvicorn |
| Base de datos | PostgreSQL + SQLAlchemy 2.x |
| Migraciones | Alembic |
| Jobs | APScheduler |
| Frontend | React + Vite + TypeScript |
| Deploy | Railway (Docker) |

## Desarrollo local

### Requisitos

- Python 3.11+
- Node.js 18+ (frontend)
- PostgreSQL local o Docker

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar DATABASE_URL y variables SECOP en backend/.env o .env en la raíz
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Ingesta manual (local o debug)

```bash
cd backend && source venv/bin/activate
python -c "from app.services.tender_ingestion import fetch_and_store_new_tenders; fetch_and_store_new_tenders()"
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose -f docker/docker-compose.yml up --build
```

## API principal

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/tenders` | Listar licitaciones (paginado, filtros) |
| GET | `/api/v1/tenders/{id}` | Detalle de licitación |

## Tests

```bash
cd backend
pytest app/tests/
```

## Estructura del proyecto

```text
LicitIA-2/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── services/       # secop_client, secop_filters, tender_ingestion
│   │   ├── models/
│   │   └── tests/
│   ├── alembic/
│   └── init_railway.sh
├── frontend/
├── Dockerfile              # Build Railway (monorepo)
├── railway.toml
└── README.md
```

## Notas de seguridad

- No commitear `.env` ni credenciales en el repositorio.
- Usar Variables de entorno en Railway para secretos.
- Rotar contraseñas si alguna credencial fue expuesta en logs o chats.

## Próximos pasos

- [ ] Desplegar frontend en Railway y actualizar `CORS_ORIGINS`
- [ ] Dashboard: mostrar `reference`, `current_phase`, `location`
- [ ] Siguientes user stories del MVP acotado

## Licencia

Proyecto MVP — uso interno y desarrollo.
