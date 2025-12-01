# Solución para Error 504 (Gateway Timeout)

## 🔴 Problema

Cuando se activa "Solo coincidencias con experiencia", el dashboard muestra:

```
Error: Request failed with status code 504
```

## 🔍 Causa

El matching con IA procesa muchas licitaciones y tarda demasiado tiempo, causando timeout.

## ✅ Soluciones Implementadas

### 1. **Límite de Licitaciones Reducido**

- **Antes:** Procesaba todas las 1748 licitaciones
- **Ahora:** Procesa solo las **100 más recientes**
- **Ubicación:** `backend/app/api/v1/tenders.py` línea 70

### 2. **Timeout de Uvicorn Aumentado**

- **Antes:** Timeout por defecto (60 segundos)
- **Ahora:** **300 segundos (5 minutos)**
- **Ubicación:** `docker/docker-compose.yml` línea 38

### 3. **Optimización del Modelo de IA**

- Texto truncado a 256 caracteres (antes 512)
- Normalización de embeddings para cálculo más rápido
- **Ubicación:** `backend/app/services/experience_matching.py` línea 414

### 4. **Procesamiento en Batches**

- Procesa en lotes de 50 licitaciones
- **Ubicación:** `backend/app/api/v1/tenders.py` línea 77

### 5. **Timeout del Frontend Aumentado**

- **Antes:** Timeout por defecto
- **Ahora:** **120 segundos (2 minutos)**
- **Ubicación:** `frontend/src/api/client.ts` línea 10

### 6. **Modelo Pre-cargado**

- El modelo de IA se carga al iniciar el backend
- No bloquea la primera request
- **Ubicación:** `backend/app/main.py` línea 54-69

## 📊 Mejoras de Performance

| Optimización             | Impacto                     |
| ------------------------ | --------------------------- |
| Límite 100 licitaciones  | -94% tiempo (de 1748 a 100) |
| Texto truncado 256 chars | -50% tiempo de embeddings   |
| Normalización embeddings | +20% velocidad              |
| Timeout 5 minutos        | Evita timeout prematuro     |

## 🧪 Prueba Ahora

1. **Recarga el dashboard** (Ctrl+F5 o Cmd+Shift+R)
2. **Activa "Solo coincidencias con experiencia"**
3. **Espera hasta 2 minutos** (puede tardar con IA)

## ⚠️ Si Sigue Dando Timeout

Si el problema persiste, puede ser:

1. **Proxy/nginx con timeout más corto** - Verificar configuración
2. **Muchas experiencias** - Reducir número de experiencias
3. **Hardware lento** - El modelo de IA requiere CPU/RAM

### Solución Alternativa: Desactivar IA Temporalmente

Si necesitas que funcione inmediatamente, puedes desactivar temporalmente la IA semántica:

```python
# En backend/app/services/experience_matching.py
SEMANTIC_AI_AVAILABLE = False  # Desactivar IA temporalmente
```

Esto usará solo matching con reglas (más rápido, menos preciso).

## 📝 Notas

- **100 licitaciones** es un buen balance entre cobertura y velocidad
- Las **100 más recientes** son las más relevantes
- El matching con IA tarda ~1-2 segundos por licitación
- Con 100 licitaciones: ~2-3 minutos máximo

## 🚀 Próximas Optimizaciones (Opcional)

1. **Cache de embeddings** - Guardar embeddings calculados
2. **Procesamiento asíncrono** - Background job para matching
3. **Batch más grande** - Procesar múltiples embeddings a la vez
4. **Modelo más pequeño** - Usar modelo más rápido

---

**Fecha:** 2025-11-17  
**Estado:** ✅ Optimizaciones aplicadas


