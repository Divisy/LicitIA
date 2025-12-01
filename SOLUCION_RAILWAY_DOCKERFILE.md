# 🔧 Solución: Error "Dockerfile does not exist" en Railway

## ❌ Problema
Railway muestra el error: `Dockerfile 'Dockerfile' does not exist`

## ✅ Solución

El problema es que Railway está buscando el Dockerfile en el directorio raíz, pero tus Dockerfiles están en `backend/` y `frontend/`.

### Opción 1: Configurar Root Directory en Railway (RECOMENDADO) ✅

**Para el Backend:**
1. En Railway, selecciona el servicio del **Backend**
2. Ve a **"Settings"**
3. En **"Source"** → **"Root Directory"**, establece: `backend`
4. Railway buscará el Dockerfile en `backend/Dockerfile` automáticamente

**Para el Frontend:**
1. En Railway, selecciona el servicio del **Frontend**
2. Ve a **"Settings"**
3. En **"Source"** → **"Root Directory"**, establece: `frontend`
4. Railway buscará el Dockerfile en `frontend/Dockerfile` automáticamente

### Opción 2: Usar Nixpacks (Sin Dockerfile)

Si prefieres no usar Dockerfile, Railway puede detectar automáticamente:

**Backend:**
- Root Directory: `backend`
- Railway detectará `requirements.txt` y usará Nixpacks automáticamente
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Frontend:**
- Root Directory: `frontend`
- Railway detectará `package.json` y usará Nixpacks automáticamente
- Build Command: `npm run build`
- Start Command: `npm run preview` (o usar un servidor estático)

---

## 📝 Configuración Correcta en Railway

### Backend Service Settings:

```
Source:
  Root Directory: backend
  Repository: tu-repo
  Branch: main (o tu branch)

Build:
  Builder: Dockerfile (o Nixpacks)
  Dockerfile Path: Dockerfile (relativo a backend/)

Deploy:
  Start Command: ./init_railway.sh (o uvicorn app.main:app --host 0.0.0.0 --port $PORT)
```

### Frontend Service Settings:

```
Source:
  Root Directory: frontend
  Repository: tu-repo
  Branch: main (o tu branch)

Build:
  Builder: Dockerfile (o Nixpacks)
  Dockerfile Path: Dockerfile (relativo a frontend/)

Deploy:
  Start Command: nginx -g 'daemon off;' (si usas Dockerfile)
  O: npm run preview (si usas Nixpacks)
```

---

## 🚨 Verificación

Después de configurar el Root Directory:

1. **Backend:**
   - Root Directory debe ser: `backend`
   - Railway debe encontrar `backend/Dockerfile`
   - O usar Nixpacks con `backend/requirements.txt`

2. **Frontend:**
   - Root Directory debe ser: `frontend`
   - Railway debe encontrar `frontend/Dockerfile`
   - O usar Nixpacks con `frontend/package.json`

---

## 💡 Recomendación

**Usa Root Directory en lugar de railway.json** porque:
- Es más fácil de configurar en la UI de Railway
- No necesitas archivos de configuración adicionales
- Railway detecta automáticamente el Dockerfile en el directorio raíz del servicio

