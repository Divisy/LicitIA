# ✅ Corrección: Railway Dockerfile Path

## 🔧 Problema Resuelto

El error `Dockerfile 'Dockerfile' does not exist` se debía a que los archivos `railway.json` tenían rutas incorrectas.

## ✅ Solución Aplicada

### Backend (`backend/railway.json`):
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"  // ✅ Corregido (antes era "backend/Dockerfile")
  }
}
```

**Razón:** Cuando el Root Directory en Railway está configurado como `backend`, Railway ya busca dentro de ese directorio. Por lo tanto, el `dockerfilePath` debe ser relativo a ese directorio, es decir, solo `"Dockerfile"`.

### Frontend (`frontend/railway.json`):
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"  // ✅ Corregido (antes era "frontend/Dockerfile")
  }
}
```

**Razón:** Mismo principio. Si el Root Directory es `frontend`, el Dockerfile se busca como `frontend/Dockerfile` desde la raíz del repo, pero en el `railway.json` debe ser solo `"Dockerfile"` porque Railway ya está dentro del directorio `frontend`.

---

## 📋 Configuración Correcta en Railway

### Backend Service:
- **Root Directory:** `backend` ✅
- **Dockerfile Path (en railway.json):** `Dockerfile` ✅
- **Start Command:** `./init_railway.sh` ✅

### Frontend Service:
- **Root Directory:** `frontend` ✅
- **Dockerfile Path (en railway.json):** `Dockerfile` ✅
- **Start Command:** `nginx -g 'daemon off;'` ✅

---

## 🚀 Próximos Pasos

1. **Haz commit y push de los cambios:**
   ```bash
   git add backend/railway.json frontend/railway.json
   git commit -m "fix: corregir dockerfilePath en railway.json"
   git push
   ```

2. **Railway detectará automáticamente el cambio** y volverá a intentar el despliegue.

3. **Verifica los logs** en Railway para confirmar que el build funciona.

---

## 💡 Nota Importante

Si prefieres **no usar `railway.json`**, puedes configurar todo directamente en la UI de Railway:

- **Settings → Build → Builder:** Selecciona "Dockerfile"
- Railway detectará automáticamente el Dockerfile en el Root Directory configurado.

El archivo `railway.json` es opcional y solo se usa si quieres versionar la configuración.

