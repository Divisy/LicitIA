# 🚀 Guía de Despliegue en Railway

## 📋 Opciones de Despliegue

Railway permite desplegar **múltiples servicios en un mismo proyecto**. Tienes dos opciones:

### Opción 1: **Servicios Separados (Recomendado)** ✅
- **Backend** como un servicio
- **Frontend** como otro servicio
- **PostgreSQL** como servicio de base de datos (Railway lo proporciona)
- **Ventajas**: Escalado independiente, mejor organización, más fácil de mantener

### Opción 2: **Monorepo con un solo servicio**
- Todo en un solo servicio
- **Desventajas**: Menos flexible, más difícil de escalar

---

## 🎯 Opción Recomendada: Servicios Separados

### Paso 1: Crear Proyecto en Railway

1. Ve a [railway.app](https://railway.app)
2. Crea una cuenta o inicia sesión
3. Click en **"New Project"**
4. Selecciona **"Empty Project"**

### Paso 2: Agregar Base de Datos PostgreSQL

1. En tu proyecto, click en **"+ New"**
2. Selecciona **"Database"** → **"Add PostgreSQL"**
3. Railway creará automáticamente una base de datos
4. **Copia las variables de entorno** que Railway te proporciona:
   - `DATABASE_URL`
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`

### Paso 3: Desplegar Backend

1. En tu proyecto, click en **"+ New"** → **"GitHub Repo"**
2. Conecta tu repositorio de GitHub
3. Selecciona el directorio `backend/` como **Root Directory**
4. Railway detectará automáticamente el `Dockerfile` o `requirements.txt`

#### Variables de Entorno del Backend:

```bash
# Base de datos (usar la URL de Railway)
DATABASE_URL=postgresql://user:password@host:port/database

# SECOP API
SECOP_DATASET_ID=tu_dataset_id

# OpenAI (si usas)
OPENAI_API_KEY=tu_api_key

# Configuración
FETCH_INTERVAL_HOURS=2

# CORS (URL del frontend en Railway)
CORS_ORIGINS=https://tu-frontend.railway.app
```

#### Configurar el Backend:

1. En el servicio del backend, ve a **"Settings"**
2. En **"Root Directory"**, establece: `backend`
3. En **"Build Command"**, puedes dejar vacío (Railway detecta automáticamente)
4. En **"Start Command"**, establece: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Paso 4: Desplegar Frontend

1. En el mismo proyecto, click en **"+ New"** → **"GitHub Repo"** (mismo repo)
2. Selecciona el directorio `frontend/` como **Root Directory**
3. Railway detectará el `package.json` y construirá automáticamente

#### Variables de Entorno del Frontend:

```bash
# URL del backend (usar la URL pública de Railway)
VITE_API_URL=https://tu-backend.railway.app/api/v1
```

#### Configurar el Frontend:

1. En el servicio del frontend, ve a **"Settings"**
2. En **"Root Directory"**, establece: `frontend`
3. En **"Build Command"**, establece: `npm run build`
4. En **"Start Command"**, establece: `npm run preview` (o usa nginx si tienes Dockerfile)

### Paso 5: Configurar Variables de Entorno

#### Backend:
- Ve a **Settings** → **Variables**
- Agrega todas las variables de entorno necesarias
- **Importante**: Actualiza `CORS_ORIGINS` con la URL del frontend

#### Frontend:
- Ve a **Settings** → **Variables**
- Agrega `VITE_API_URL` con la URL del backend

### Paso 6: Ejecutar Migraciones

Después de desplegar el backend:

1. Ve al servicio del backend
2. Click en **"Deployments"** → **"View Logs"**
3. O usa **"Deploy"** → **"Custom Command"** y ejecuta:
   ```bash
   alembic upgrade head
   ```

---

## 🔧 Configuración Adicional

### Actualizar CORS en Backend

En `backend/app/main.py`, asegúrate de que CORS incluya la URL de Railway:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://tu-frontend.railway.app",  # Agregar URL de Railway
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Actualizar API Client en Frontend

En `frontend/src/api/client.ts`, verifica que use la variable de entorno:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
```

---

## 📝 Archivos Necesarios

### Backend (`backend/railway.json` - Opcional):

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Frontend (`frontend/railway.json` - Opcional):

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npm run preview",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 🚨 Troubleshooting

### Backend no se conecta a la base de datos:
- Verifica que `DATABASE_URL` esté correctamente configurada
- Asegúrate de que la base de datos esté en el mismo proyecto

### Frontend no puede llamar al backend:
- Verifica `CORS_ORIGINS` en el backend
- Verifica `VITE_API_URL` en el frontend
- Asegúrate de usar `https://` en producción

### Migraciones no se ejecutan:
- Ejecuta manualmente: `alembic upgrade head` en el servicio del backend
- O agrega un script de inicio que ejecute las migraciones

---

## ✅ Checklist de Despliegue

- [ ] Proyecto creado en Railway
- [ ] Base de datos PostgreSQL agregada
- [ ] Backend desplegado con variables de entorno
- [ ] Frontend desplegado con variables de entorno
- [ ] CORS configurado correctamente
- [ ] Migraciones ejecutadas
- [ ] URLs públicas configuradas
- [ ] Variables de entorno verificadas
- [ ] Pruebas de conexión realizadas

---

## 🔗 URLs Públicas

Railway generará URLs públicas automáticamente:
- Backend: `https://tu-backend-production.up.railway.app`
- Frontend: `https://tu-frontend-production.up.railway.app`

Puedes configurar dominios personalizados en **Settings** → **Domains**.

