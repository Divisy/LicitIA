# ¿Cómo se Identifican las Licitaciones sobre Interventoría?

## 📋 Proceso Actual (Simplificado)

### 1. **Extracción de SECOP (Filtro Amplio)**

El sistema **NO filtra específicamente por "interventoría"** durante la extracción de SECOP. En su lugar:

**Filtro aplicado:**
- **Código UNSPSC:** `81101500` (Ingeniería Civil y Arquitectura)
- **Rango de fechas:** Últimos 60 días desde la fecha de publicación
- **Sin filtro de keywords:** No se busca "interventoría" o "supervisión" en la extracción

**Ubicación:** `backend/app/services/tender_ingestion.py` líneas 29-35

```python
# Fetch from SECOP with UNSPSC code filter only
# Filter by UNSPSC code 81101500 (Ingeniería Civil y Arquitectura)
secop_tenders = fetch_recent_tenders(
    since_timestamp=since_timestamp,
    unspsc_code="81101500",  # ← Solo este filtro
)
```

**Resultado:** Se extraen **TODAS** las licitaciones de ingeniería civil, no solo interventoría.

---

### 2. **Almacenamiento en Base de Datos**

Todas las licitaciones extraídas se guardan en la base de datos **sin clasificación de relevancia**.

**Campo `is_relevant_interventoria_vial`:**
- Se establece en `False` por defecto
- **Ya no se actualiza** con clasificación de IA (OpenAI fue eliminado)
- Se mantiene en el modelo por compatibilidad, pero no se usa activamente

**Ubicación:** `backend/app/services/tender_ingestion.py` línea 96

```python
is_relevant_interventoria_vial=False,  # Ya no se clasifica con IA
```

---

### 3. **Identificación de Interventoría (Solo para Estadísticas)**

Cuando contamos cuántas licitaciones son sobre interventoría, lo hacemos **después** de extraerlas, buscando keywords en el texto:

**Keywords buscadas:**
- `interventoría`
- `interventoria`
- `supervisión`
- `supervision`

**Ubicación:** Búsqueda en `tender.object_text` usando SQL LIKE

```sql
WHERE LOWER(object_text) LIKE '%interventoría%'
   OR LOWER(object_text) LIKE '%interventoria%'
   OR LOWER(object_text) LIKE '%supervisión%'
   OR LOWER(object_text) LIKE '%supervision%'
```

**Resultado actual:**
- **Total de licitaciones:** 1,748
- **Sobre interventoría/supervisión:** 479 (27.4%)
- **Otras:** 1,269 (72.6%)

---

### 4. **Filtrado Real: Matching con Experiencia**

El sistema **realmente filtra** las licitaciones relevantes usando el **matching con experiencia de la empresa**:

**Proceso:**
1. Usuario sube Excel con experiencias de la empresa
2. Sistema extrae keywords, montos, entidades, ubicaciones de cada experiencia
3. Cuando el usuario activa "Solo coincidencias con experiencia":
   - Se compara cada licitación con todas las experiencias
   - Se calcula un score de matching (0-1) usando:
     - **50%** Semántica (IA con Sentence Transformers)
     - **15%** Keywords
     - **15%** Monto
     - **10%** Entidad
     - **10%** Ubicación
   - Solo se muestran licitaciones con score ≥ 0.55

**Ubicación:** `backend/app/services/experience_matching.py`

---

## 🔄 Cambio de Enfoque

### **Antes (Eliminado):**
- ❌ Filtro de keywords "interventoría" en extracción de SECOP
- ❌ Clasificación con OpenAI para determinar relevancia
- ❌ Campo `is_relevant_interventoria_vial` se actualizaba con IA

### **Ahora (Actual):**
- ✅ Filtro amplio: UNSPSC `81101500` (todas las ingenierías civiles)
- ✅ Matching con experiencia de la empresa (más preciso y personalizado)
- ✅ Cada empresa ve solo licitaciones que coinciden con su experiencia real

---

## 📊 ¿Por Qué Este Enfoque?

### **Ventajas:**
1. **Más preciso:** No todas las empresas hacen el mismo tipo de interventoría
2. **Personalizado:** Cada empresa ve solo lo relevante para su experiencia
3. **Sin falsos positivos:** No se muestran licitaciones de interventoría que no coinciden con la experiencia
4. **Ahorro de costos:** No se usa OpenAI para clasificar (solo para matching semántico)

### **Desventajas:**
1. **Requiere experiencias:** La empresa debe subir su Excel con experiencias
2. **Más lento:** El matching con IA toma tiempo (optimizado a 150 licitaciones más recientes)

---

## 🎯 Resumen

**Pregunta:** ¿Cómo se identifican las licitaciones sobre interventoría?

**Respuesta:**
1. **Extracción:** Se extraen TODAS las licitaciones de ingeniería civil (UNSPSC 81101500)
2. **Almacenamiento:** Se guardan todas sin clasificar
3. **Identificación (estadísticas):** Se buscan keywords "interventoría/supervisión" en el texto
4. **Filtrado (usuario):** Se usa matching con experiencia de la empresa para mostrar solo las relevantes

**El sistema NO identifica específicamente "interventoría" durante la extracción. En su lugar, extrae un conjunto amplio y luego el matching con experiencia determina qué es relevante para cada empresa.**

---

**Fecha:** 2025-11-17  
**Estado:** ✅ Documentación actualizada



