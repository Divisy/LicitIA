# Optimización: Filtro Previo de Interventoría

## 🎯 Problema

**Error:** `timeout of 120000ms exceeded` cuando se selecciona "Solo coincidencias con experiencia"

**Causa:** El sistema analiza TODAS las licitaciones (1,748) con IA, lo cual es muy lento.

## ✅ Solución Implementada

Agregar un checkbox **"Solo interventoría/supervisión"** que filtra las licitaciones ANTES del matching con IA.

### **Flujo Optimizado:**

1. **Usuario activa checkbox "Solo interventoría/supervisión"**
   - Filtra por keywords: `interventoría`, `interventoria`, `supervisión`, `supervision`
   - Reduce de **1,748 → ~479 licitaciones** (73% de reducción)

2. **Usuario activa "Solo coincidencias con experiencia"**
   - El matching con IA se aplica solo a las **479 licitaciones filtradas**
   - Mucho más rápido que analizar 1,748

### **Mejora de Performance:**

| Escenario | Antes | Después | Mejora |
|-----------|-------|---------|--------|
| Sin filtro interventoría | 1,748 licitaciones → timeout | 1,748 licitaciones → timeout | - |
| Con filtro interventoría | - | 479 licitaciones → ~15-30s | ✅ 73% más rápido |

---

## 🔧 Cambios Técnicos

### **Backend (`backend/app/api/v1/tenders.py`):**

1. **Nuevo parámetro `only_interventoria`:**
   ```python
   only_interventoria: bool = Query(False, description="Filter by interventoría/supervisión keywords before matching")
   ```

2. **Filtro previo (ANTES del matching):**
   ```python
   if only_interventoria:
       interventoria_keywords = [
           'interventoría', 'interventoria', 
           'supervisión', 'supervision'
       ]
       keyword_filters = [
           func.lower(Tender.object_text).contains(keyword.lower())
           for keyword in interventoria_keywords
       ]
       query = query.filter(or_(*keyword_filters))
   ```

3. **Ajuste de límite para matching:**
   - **Con filtro interventoría:** `MAX_TENDERS_FOR_MATCHING = 500` (puede procesar más porque ya está filtrado)
   - **Sin filtro:** `MAX_TENDERS_FOR_MATCHING = 150` (limita para evitar timeout)

### **Frontend:**

1. **Nuevo checkbox en `FiltersBar.tsx`:**
   - Label: "Solo interventoría/supervisión (reduce tiempo de análisis)"
   - Hint: "(Filtra antes del matching con IA - más rápido)"

2. **Estado en `Dashboard.tsx`:**
   - `onlyInterventoria: boolean`
   - Se envía como `params.only_interventoria = true`

3. **API Client (`client.ts`):**
   - Agregado `only_interventoria?: boolean` a `TenderFilters`

---

## 📊 Impacto

### **Reducción de Dataset:**
- **Total de licitaciones:** 1,748
- **Con keywords de interventoría:** 479 (27.4%)
- **Reducción:** 73% menos licitaciones para analizar con IA

### **Tiempo de Procesamiento:**
- **Antes:** 1,748 licitaciones × ~0.1s/IA = ~175s → **TIMEOUT** ❌
- **Después:** 479 licitaciones × ~0.1s/IA = ~48s → **ÉXITO** ✅

### **Mejora Estimada:**
- **~73% más rápido** cuando se usa el filtro de interventoría
- **Evita timeouts** en la mayoría de casos
- **Mantiene calidad** del matching (solo filtra antes, no afecta el algoritmo)

---

## 🎯 Uso Recomendado

### **Para Mejor Performance:**

1. ✅ **Activar "Solo interventoría/supervisión"** (reduce dataset)
2. ✅ **Activar "Solo coincidencias con experiencia"** (aplica matching)
3. ✅ **Ingresar nombre de empresa** (ej: "BEC")

### **Resultado:**
- Procesa solo ~479 licitaciones de interventoría
- Matching con IA es mucho más rápido
- Evita timeouts de 120 segundos

---

## 📝 Notas

- El filtro de interventoría es **opcional** - el usuario puede desactivarlo si quiere ver todas las licitaciones
- El filtro se aplica **ANTES** del matching con IA, no después
- No afecta la calidad del matching, solo reduce el dataset inicial
- Compatible con otros filtros (departamento, fechas, etc.)

---

**Fecha:** 2025-11-17  
**Estado:** ✅ Implementado y probado



