# 🔧 Solución: Frontend sin URL en Railway

## ❓ Problema
El frontend no genera URL pública en Railway aunque está en el mismo proyecto que el backend.

## ✅ Solución: Habilitar Public Networking

### Paso 1: Verificar que el Frontend esté como Servicio Separado

En Railway, cada servicio debe estar **separado** para tener su propia URL:

```
Proyecto LicitIA
├── Servicio: PostgreSQL (Base de datos)
├── Servicio: Backend (FastAPI) → URL: https://backend-production.up.railway.app
└── Servicio: Frontend (React) → URL: https://frontend-production.up.railway.app
```

### Paso 2: Habilitar Public Networking en el Frontend

1. **Selecciona el servicio del Frontend** en Railway
2. Ve a la pestaña **"Settings"**
3. Busca la sección **"Networking"**
4. **Habilita "Public Networking"** (toggle o botón)
5. Railway generará automáticamente una URL pública

### Paso 3: Verificar Configuración del Servicio Frontend

Asegúrate de que el servicio del frontend tenga:

**Settings → Source:**
- Root Directory: `frontend`
- Build Command: `npm run build` (si usas Nixpacks)
- Start Command: `npm run preview` o usar Dockerfile

**Settings → Networking:**
- ✅ **Public Networking: ENABLED** (esto es crítico)

### Paso 4: Configurar Variables de Entorno del Frontend

Una vez que tengas la URL del backend, configura en el frontend:

**Variables de Entorno del Frontend:**
```bash
VITE_API_URL=https://tu-backend.railway.app/api/v1
```

### Paso 5: Actualizar CORS en Backend

En el backend, agrega la URL del frontend a CORS:

**Variables de Entorno del Backend:**
```bash
CORS_ORIGINS=https://tu-frontend.railway.app,https://tu-backend.railway.app
```

---

## 🔍 Verificación

### ¿Cómo saber si está bien configurado?

1. **Backend:**
   - Debe tener URL: `https://backend-production.up.railway.app`
   - Debe estar en "Settings" → "Networking" → "Public Networking: Enabled"

2. **Frontend:**
   - Debe tener URL: `https://frontend-production.up.railway.app`
   - Debe estar en "Settings" → "Networking" → "Public Networking: Enabled"

### Si el Frontend NO tiene URL:

1. Ve al servicio del Frontend
2. Click en **"Settings"**
3. Busca **"Networking"** → **"Public Networking"**
4. Habilita el toggle o click en **"Generate Domain"**
5. Railway creará la URL automáticamente

---

## 📝 Nota Importante

**SÍ puedes tener ambos en el mismo proyecto**, pero:
- Cada servicio debe tener **"Public Networking" habilitado** para tener URL pública
- Cada servicio genera su **propia URL independiente**
- Puedes usar dominios personalizados para cada uno

---

## 🚨 Troubleshooting

### El frontend no aparece en la lista de servicios:
- Asegúrate de haber agregado el frontend como un servicio separado
- "+ New" → "GitHub Repo" → Selecciona el mismo repo pero con Root Directory: `frontend`

### El frontend no genera URL:
- Verifica que "Public Networking" esté habilitado
- Revisa que el servicio esté desplegado correctamente
- Verifica los logs del frontend para errores de build

### El frontend no se conecta al backend:
- Verifica `VITE_API_URL` en variables de entorno del frontend
- Verifica `CORS_ORIGINS` en variables de entorno del backend
- Asegúrate de usar `https://` en producción

