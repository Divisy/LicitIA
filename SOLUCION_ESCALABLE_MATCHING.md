# Solución Escalable para Matching con IA

## 🎯 Problema Actual

- **Licitaciones de interventoría:** ~400
- **Límite actual:** Solo 8 licitaciones procesadas
- **Tiempo por licitación:** ~11 segundos (procesa contra 11 experiencias)
- **Problema:** No escalable, solo procesa 8 de 400 licitaciones

---

## 🔍 Análisis del Cuello de Botella

### **Problema Principal:**
Cada licitación procesa contra **11 experiencias**, y cada comparación llama a la IA:
- **11 experiencias** × **1.0-1.5s por comparación** = **~11-16s por licitación**
- **400 licitaciones** × **11s** = **~4,400 segundos (73 minutos)** ❌

### **Causa Raíz:**
1. **Embeddings de experiencias se calculan cada vez** (no hay caché)
2. **Procesamiento secuencial** (una comparación a la vez)
3. **No hay batch processing real** (procesa 2 textos a la vez, no más)

---

## ✅ Solución Propuesta: Híbrida Multi-Nivel

### **Nivel 1: Caché de Embeddings de Experiencias** ⭐ (Más Impacto)

**Problema:** Las experiencias no cambian frecuentemente, pero calculamos sus embeddings cada vez.

**Solución:**
- Cachear embeddings de experiencias en memoria
- Recalcular solo cuando se actualiza una experiencia
- **Ahorro:** De 11 llamadas a IA → 1 llamada por licitación

**Impacto:**
- **Antes:** 11 experiencias × 1.5s = 16.5s por licitación
- **Después:** 1 licitación × 1.5s = 1.5s por licitación
- **Mejora:** **91% más rápido** (de 11s a ~1.5s)

**Escalabilidad:**
- **400 licitaciones** × **1.5s** = **~600 segundos (10 minutos)**
- Con early exit: **~2-3 minutos** para encontrar suficientes matches

---

### **Nivel 2: Batch Processing Real de Embeddings**

**Problema:** Procesa 2 textos a la vez (licitación + experiencia).

**Solución:**
- Procesar múltiples licitaciones en un solo batch
- Ejemplo: 10 licitaciones + 11 experiencias = 21 textos en un batch
- **Ahorro:** Reducción adicional de ~20-30%

**Impacto:**
- **Antes:** 1.5s por licitación (con caché)
- **Después:** ~1.0-1.2s por licitación (con batch)
- **Mejora:** **20-30% más rápido**

**Escalabilidad:**
- **400 licitaciones** × **1.0s** = **~400 segundos (6.7 minutos)**
- Con early exit: **~1-2 minutos**

---

### **Nivel 3: Procesamiento Asíncrono (Opcional)**

**Problema:** Bloquea la request HTTP por varios minutos.

**Solución:**
- Procesar matching en background (Celery, RQ, o thread pool)
- Mostrar resultados progresivamente
- Cachear resultados en Redis/DB

**Impacto:**
- No bloquea la request
- Usuario ve resultados mientras se procesan
- Puede procesar todas las 400 licitaciones sin timeout

---

## 🚀 Implementación Recomendada

### **Fase 1: Caché de Embeddings (Implementar Primero)** ⭐

**Prioridad:** ALTA  
**Complejidad:** Media  
**Impacto:** 91% más rápido

**Implementación:**
1. Cachear embeddings de experiencias en memoria (dict global)
2. Invalidar caché cuando se actualiza una experiencia
3. Calcular embeddings de experiencias una vez al inicio

**Código:**
```python
# Global cache for experience embeddings
_experience_embeddings_cache = {}
_experience_cache_timestamp = {}

def get_experience_embeddings(experiences):
    """Get cached embeddings for experiences."""
    # Check cache and return if valid
    # Calculate if missing or outdated
    pass
```

---

### **Fase 2: Batch Processing Real**

**Prioridad:** MEDIA  
**Complejidad:** Media  
**Impacto:** 20-30% más rápido

**Implementación:**
1. Agrupar múltiples licitaciones en un batch
2. Procesar todas las licitaciones + experiencias en un solo encode()
3. Calcular similitudes en batch usando matriz de similitud

**Código:**
```python
# Process multiple tenders at once
tender_texts = [t.object_text for t in tenders]
experience_texts = [e.project_description for e in experiences]

# Single batch encode
all_embeddings = model.encode(
    tender_texts + experience_texts,
    batch_size=32,
    show_progress_bar=False
)

# Calculate similarity matrix
similarity_matrix = cosine_similarity(
    tender_embeddings,
    experience_embeddings
)
```

---

### **Fase 3: Procesamiento Asíncrono (Si es Necesario)**

**Prioridad:** BAJA (solo si Fase 1 y 2 no son suficientes)  
**Complejidad:** Alta  
**Impacto:** No bloquea requests

**Implementación:**
1. Usar Celery o RQ para procesamiento en background
2. Guardar resultados en Redis o DB
3. API endpoint para consultar estado y resultados

---

## 📊 Comparación de Soluciones

| Solución | Tiempo (400 licitaciones) | Escalabilidad | Complejidad |
|----------|---------------------------|----------------|-------------|
| **Actual (8 licitaciones)** | ~88s (solo 8) | ❌ No escalable | Baja |
| **Fase 1: Caché** | ~10 min (400) | ✅ Escalable | Media |
| **Fase 1 + 2: Batch** | ~6-7 min (400) | ✅✅ Muy escalable | Media |
| **Fase 1 + 2 + 3: Async** | ~6-7 min (no bloquea) | ✅✅✅ Óptimo | Alta |

---

## 🎯 Recomendación Final

### **Implementar Fase 1 (Caché) Inmediatamente:**

1. **Impacto máximo** (91% más rápido)
2. **Complejidad media** (fácil de implementar)
3. **Escalabilidad:** De 8 → ~400 licitaciones procesables

### **Resultado Esperado:**
- **400 licitaciones** × **1.5s** = **~10 minutos**
- Con early exit: **~2-3 minutos** para encontrar matches
- **Escalable** y **funcional**

### **Si Fase 1 no es suficiente:**
- Implementar Fase 2 (Batch Processing)
- Reducir a **~6-7 minutos** total

### **Si aún hay problemas:**
- Implementar Fase 3 (Async)
- No bloquea requests, procesa en background

---

## 💡 Alternativa Rápida (Temporal)

Si necesitas una solución **inmediata** mientras implementamos Fase 1:

**Opción:** Reducir peso de IA semántica y aumentar peso de matching basado en reglas

- **Semántica:** 30% (reducido de 50%)
- **Keywords:** 30% (aumentado de 15%)
- **Monto:** 20%
- **Entidad:** 10%
- **Ubicación:** 10%

**Impacto:**
- Menos llamadas a IA
- Más rápido pero menos preciso
- **Solución temporal** hasta implementar caché

---

**¿Procedo con la implementación de Fase 1 (Caché de Embeddings)?**



