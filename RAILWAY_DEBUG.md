# 🔍 Debug: Railway "Dockerfile does not exist"

## ✅ Lo que sabemos:
1. Railway **SÍ está leyendo** `backend/railway.json` (confirmado en la UI)
2. El archivo `backend/Dockerfile` **existe** en el repo
3. El `railway.json` tiene `dockerfilePath: "Dockerfile"`

## ❌ El problema:
Railway no encuentra el Dockerfile durante el build, aunque la configuración parece correcta.

## 🔧 Soluciones a probar:

### Solución 1: Verificar Root Directory en Railway UI
1. Ve a **Settings → Source**
2. Verifica que **Root Directory** sea exactamente: `backend` (sin `/` al inicio)
3. Si está vacío o incorrecto, configúralo como `backend`

### Solución 2: Cambiar a Nixpacks temporalmente
Si el Dockerfile sigue fallando, usa Nixpacks que es más confiable:

**En Railway UI:**
1. **Settings → Build → Builder:** Cambia a **"Nixpacks"**
2. **Settings → Deploy → Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Railway detectará `requirements.txt` automáticamente

**O modifica `backend/railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Solución 3: Eliminar railway.json y configurar en UI
1. Elimina `backend/railway.json` del repo
2. Configura todo directamente en Railway UI:
   - Root Directory: `backend`
   - Builder: `Dockerfile`
   - Dockerfile Path: (dejar vacío o `Dockerfile`)
   - Start Command: `./init_railway.sh`

### Solución 4: Verificar que el Dockerfile esté en el commit correcto
```bash
# Verifica que el Dockerfile esté en el último commit
git log --oneline -5 -- backend/Dockerfile
git show HEAD:backend/Dockerfile | head -5
```

---

## 🎯 Recomendación Inmediata:

**Usa Nixpacks** (Solución 2) porque:
- Es más confiable en Railway
- Detecta automáticamente `requirements.txt`
- No depende de rutas de Dockerfile
- Es más rápido para iterar

Luego, una vez que funcione, puedes volver a Dockerfile si lo necesitas.

