# Mejoras para Matching con Experiencia - Mayor Precisión

## 🎯 Objetivo
Mejorar la precisión del algoritmo de matching para que identifique mejor las licitaciones que realmente encajan con la experiencia de la empresa.

---

## 📊 Análisis de Limitaciones Actuales

### **1. Keywords Matching (50% del peso)**

**Problemas actuales:**
- ❌ Solo cuenta coincidencias exactas de palabras
- ❌ No considera sinónimos (ej: "vial" vs "carretera" vs "vías")
- ❌ No pondera keywords importantes vs. secundarios
- ❌ No entiende contexto semántico
- ❌ No considera orden/posición de keywords
- ❌ Lista de keywords limitada y estática

**Ejemplo de problema:**
- Experiencia: "Interventoría de carretera en Cundinamarca"
- Licitación: "Supervisión de vías en Cundinamarca"
- **Resultado actual:** Bajo match porque "carretera" ≠ "vías"
- **Debería ser:** Alto match porque son sinónimos

---

### **2. Amount Matching (25% del peso)**

**Problemas actuales:**
- ❌ No considera inflación (experiencias de 2000 vs 2024)
- ❌ Rangos fijos (0.5x-2x) pueden ser muy amplios o muy restrictivos
- ❌ No considera tipo de proyecto (interventoría vs construcción)
- ❌ No diferencia entre proyectos grandes/pequeños
- ❌ Score neutral (0.5) cuando falta monto puede ser engañoso

**Ejemplo de problema:**
- Experiencia: $100M en 2000 (con inflación ≈ $500M en 2024)
- Licitación: $400M en 2024
- **Resultado actual:** Bajo match (ratio 4x)
- **Debería ser:** Alto match (considerando inflación)

---

### **3. Entity Matching (15% del peso)**

**Problemas actuales:**
- ❌ Muy básico, solo busca palabras comunes
- ❌ No normaliza nombres (INVIAS vs "Instituto Nacional de Vías")
- ❌ No considera entidades relacionadas
- ❌ No usa fuzzy matching para nombres similares
- ❌ No diferencia entre entidades principales y secundarias

**Ejemplo de problema:**
- Experiencia: "INVIAS"
- Licitación: "Instituto Nacional de Vías"
- **Resultado actual:** Bajo match (0.0)
- **Debería ser:** Alto match (1.0) - misma entidad

---

### **4. Category Matching (10% del peso)**

**Problemas actuales:**
- ❌ Muy limitado, solo busca palabras clave
- ❌ No hay taxonomía de categorías
- ❌ No considera subcategorías
- ❌ Score neutral (0.5) cuando no hay match puede sesgar resultados
- ❌ No diferencia entre tipos de interventoría (vial, ambiental, etc.)

---

### **5. Factores Faltantes (0% del peso actual)**

**Factores importantes que NO se consideran:**
- ❌ **Ubicación geográfica** (departamento/municipio) - Muy importante
- ❌ **Fecha de experiencia** (experiencias recientes más relevantes)
- ❌ **Éxito del proyecto** (proyectos ganados vs perdidos)
- ❌ **Complejidad del proyecto** (similar complejidad = mejor match)
- ❌ **Duración del proyecto** (proyectos de duración similar)

---

## 🚀 Mejoras Propuestas (Priorizadas)

### **Mejora #1: Keywords Matching Mejorado** 🔥 (Alta Prioridad)

#### **1.1. Sinónimos y Variaciones**
```python
# Diccionario de sinónimos
SYNONYMS = {
    "vial": ["vías", "vias", "carretera", "malla vial", "infraestructura vial"],
    "interventoría": ["interventoria", "supervisión", "supervision", "control"],
    "obra": ["obras", "construcción", "construccion", "proyecto"],
    "mantenimiento": ["conservación", "conservacion", "rehabilitación", "rehabilitacion"],
    # ... más sinónimos
}

# Al buscar keywords, también buscar sinónimos
def find_keyword_with_synonyms(keyword, text):
    if keyword in text:
        return True
    if keyword in SYNONYMS:
        for synonym in SYNONYMS[keyword]:
            if synonym in text:
                return True
    return False
```

**Impacto:** Alto - Mejora significativamente la precisión

---

#### **1.2. Ponderación de Keywords**
```python
# Keywords más importantes tienen más peso
KEYWORD_WEIGHTS = {
    "interventoría": 2.0,  # Muy importante
    "vial": 1.5,
    "carretera": 1.5,
    "supervisión": 1.5,
    "obra": 1.0,
    "mantenimiento": 1.0,
    # ... otros keywords con peso 1.0 por defecto
}

# Calcular score ponderado
def calculate_weighted_keyword_score(matches):
    total_weight = sum(KEYWORD_WEIGHTS.get(kw, 1.0) for kw in matches)
    max_possible_weight = sum(KEYWORD_WEIGHTS.get(kw, 1.0) for kw in all_keywords)
    return total_weight / max_possible_weight
```

**Impacto:** Alto - Prioriza keywords más relevantes

---

#### **1.3. Extracción Mejorada de Keywords**
```python
# Usar NLP para extraer keywords más relevantes
import nltk
from collections import Counter

def extract_keywords_advanced(text):
    # 1. Tokenizar y limpiar
    tokens = nltk.word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalpha() and len(t) > 3]
    
    # 2. Remover stop words
    stop_words = set(nltk.corpus.stopwords.words('spanish'))
    tokens = [t for t in tokens if t not in stop_words]
    
    # 3. Extraer bigramas y trigramas importantes
    bigrams = list(nltk.bigrams(tokens))
    trigrams = list(nltk.trigrams(tokens))
    
    # 4. Filtrar por frecuencia y relevancia
    # 5. Combinar con keywords técnicos conocidos
    
    return relevant_keywords
```

**Impacto:** Medio - Requiere librerías adicionales pero mejora calidad

---

#### **1.4. Similaridad Semántica (Opcional - Avanzado)**
```python
# Usar embeddings para similaridad semántica
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def calculate_semantic_similarity(text1, text2):
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return similarity
```

**Impacto:** Alto - Pero requiere modelo de ML, más complejo

---

### **Mejora #2: Amount Matching Mejorado** 🔥 (Alta Prioridad)

#### **2.1. Ajuste por Inflación**
```python
import pandas as pd

# Datos de inflación histórica (IPC Colombia)
INFLATION_RATES = {
    2000: 5.7, 2001: 7.6, 2002: 6.2,  # ... más años
    2020: 1.6, 2021: 5.6, 2022: 13.1, 2023: 11.8
}

def adjust_for_inflation(amount, year_from, year_to):
    """Ajustar monto por inflación entre dos años."""
    if year_from >= year_to:
        return amount
    
    # Calcular factor de inflación acumulado
    factor = 1.0
    for year in range(year_from + 1, year_to + 1):
        if year in INFLATION_RATES:
            factor *= (1 + INFLATION_RATES[year] / 100)
    
    return amount * factor

def calculate_amount_score_improved(tender_amount, tender_year, 
                                   experience_amount, experience_year):
    # Ajustar experiencia a año actual
    adjusted_experience = adjust_for_inflation(
        experience_amount, 
        experience_year, 
        tender_year or datetime.now().year
    )
    
    # Calcular ratio con monto ajustado
    ratio = tender_amount / adjusted_experience if adjusted_experience > 0 else 0
    
    # Rangos más precisos
    if 0.8 <= ratio <= 1.2:  # Muy similar (±20%)
        return 1.0
    elif 0.6 <= ratio <= 1.5:  # Similar (±50%)
        return 0.9
    elif 0.4 <= ratio <= 2.0:  # Aceptable (2x)
        return 0.7
    elif 0.2 <= ratio <= 3.0:  # Amplio (3x)
        return 0.5
    else:
        return 0.2
```

**Impacto:** Alto - Mejora significativamente matching de experiencias antiguas

---

#### **2.2. Rangos por Tipo de Proyecto**
```python
# Rangos diferentes según tipo de proyecto
AMOUNT_RANGES_BY_TYPE = {
    "interventoría": {
        "tight": (0.8, 1.2),    # ±20%
        "good": (0.6, 1.5),     # ±50%
        "acceptable": (0.4, 2.0) # 2x
    },
    "construcción": {
        "tight": (0.7, 1.3),
        "good": (0.5, 2.0),
        "acceptable": (0.3, 3.0)
    },
    # ... más tipos
}
```

**Impacto:** Medio - Mejora precisión por tipo de proyecto

---

### **Mejora #3: Entity Matching Mejorado** 🔥 (Alta Prioridad)

#### **3.1. Normalización de Nombres**
```python
# Diccionario de normalizaciones comunes
ENTITY_NORMALIZATIONS = {
    "invias": ["instituto nacional de vías", "instituto nacional de vias"],
    "idrd": ["instituto distrital de recreación y deporte"],
    "idu": ["instituto de desarrollo urbano"],
    # ... más normalizaciones
}

def normalize_entity_name(entity_name):
    """Normalizar nombre de entidad para matching."""
    name_lower = entity_name.lower().strip()
    
    # Buscar en normalizaciones
    for normalized, variants in ENTITY_NORMALIZATIONS.items():
        if name_lower == normalized or name_lower in variants:
            return normalized
        if any(variant in name_lower for variant in variants):
            return normalized
    
    return name_lower

def calculate_entity_score_improved(tender_entity, experience_entity):
    if not experience_entity:
        return 0.5
    
    tender_norm = normalize_entity_name(tender_entity)
    experience_norm = normalize_entity_name(experience_entity)
    
    # Exact match después de normalización
    if tender_norm == experience_norm:
        return 1.0
    
    # Fuzzy matching para nombres similares
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, tender_norm, experience_norm).ratio()
    
    if similarity >= 0.9:  # Muy similar
        return 0.95
    elif similarity >= 0.7:  # Similar
        return 0.7
    elif similarity >= 0.5:  # Parcial
        return 0.4
    
    return 0.0
```

**Impacto:** Alto - Resuelve problema de nombres diferentes de misma entidad

---

#### **3.2. Fuzzy Matching Avanzado**
```python
from fuzzywuzzy import fuzz

def calculate_entity_fuzzy_score(entity1, entity2):
    # Ratio de similitud
    ratio = fuzz.ratio(entity1.lower(), entity2.lower())
    
    # Partial ratio (una contiene a la otra)
    partial = fuzz.partial_ratio(entity1.lower(), entity2.lower())
    
    # Token sort ratio (ignora orden)
    token_sort = fuzz.token_sort_ratio(entity1.lower(), entity2.lower())
    
    # Usar el mejor score
    best_score = max(ratio, partial, token_sort)
    
    # Normalizar a 0-1
    return best_score / 100.0
```

**Impacto:** Alto - Mejora matching de nombres similares

---

### **Mejora #4: Agregar Factor de Ubicación** 🔥 (Alta Prioridad)

#### **4.1. Matching Geográfico**
```python
def calculate_location_score(tender_dept, tender_municipality,
                            experience_dept, experience_municipality):
    """Calcular score basado en ubicación geográfica."""
    
    # Mismo municipio = match perfecto
    if tender_municipality and experience_municipality:
        if normalize_location(tender_municipality) == normalize_location(experience_municipality):
            return 1.0
    
    # Mismo departamento = buen match
    if tender_dept and experience_dept:
        if normalize_location(tender_dept) == normalize_location(experience_dept):
            return 0.8
    
    # Departamentos vecinos = match parcial
    if are_neighboring_departments(tender_dept, experience_dept):
        return 0.5
    
    # Sin match geográfico
    return 0.3  # No es 0 porque puede ser match válido

def normalize_location(location):
    """Normalizar nombres de ubicaciones."""
    # Remover acentos, convertir a minúsculas
    # "Cundinamarca" = "cundinamarca"
    # "Bogotá" = "bogota"
    return location.lower().strip()
```

**Impacto:** Muy Alto - La ubicación es muy importante para matching

**Nuevo peso sugerido:** 20% (agregar a los pesos existentes)

---

### **Mejora #5: Factor de Fecha de Experiencia** (Media Prioridad)

#### **5.1. Ponderación por Antigüedad**
```python
def calculate_recency_weight(experience_date):
    """Calcular peso según antigüedad de la experiencia."""
    if not experience_date:
        return 0.8  # Sin fecha, peso medio
    
    years_ago = (datetime.now().date() - experience_date).days / 365.25
    
    if years_ago <= 2:  # Muy reciente (últimos 2 años)
        return 1.0
    elif years_ago <= 5:  # Reciente (2-5 años)
        return 0.9
    elif years_ago <= 10:  # Moderado (5-10 años)
        return 0.7
    else:  # Antiguo (>10 años)
        return 0.5

# Aplicar peso a todos los scores
def apply_recency_weight(base_score, recency_weight):
    return base_score * recency_weight
```

**Impacto:** Medio - Experiencias recientes son más relevantes

---

### **Mejora #6: Factor de Éxito del Proyecto** (Media Prioridad)

#### **6.1. Ponderación por Éxito**
```python
# Agregar campo "was_successful" a CompanyExperience
# Si el proyecto fue ganado/completado exitosamente = más relevante

def calculate_success_weight(was_successful):
    """Calcular peso según éxito del proyecto."""
    if was_successful is None:
        return 0.8  # Sin información, peso medio
    
    if was_successful:
        return 1.0  # Proyecto exitoso = más relevante
    else:
        return 0.6  # Proyecto no exitoso = menos relevante
```

**Impacto:** Medio - Requiere agregar campo a modelo

---

### **Mejora #7: Category Matching Mejorado** (Media Prioridad)

#### **7.1. Taxonomía de Categorías**
```python
# Taxonomía jerárquica de categorías
CATEGORY_TAXONOMY = {
    "interventoría": {
        "vial": ["carretera", "vías", "malla vial", "infraestructura vial"],
        "ambiental": ["medio ambiente", "ambiental", "sostenibilidad"],
        "construcción": ["obra", "construcción", "edificación"],
        # ... más subcategorías
    },
    "supervisión": {
        "técnica": ["técnica", "ingeniería"],
        "administrativa": ["administrativa", "gestión"],
        # ... más
    }
}

def calculate_category_score_improved(tender, experience):
    """Matching mejorado de categorías usando taxonomía."""
    if not experience.category:
        return 0.5
    
    tender_text = (tender.object_text or "").lower()
    exp_category = experience.category.lower()
    
    # Buscar en taxonomía
    for main_cat, subcats in CATEGORY_TAXONOMY.items():
        if main_cat in exp_category:
            # Buscar subcategorías en texto de licitación
            for subcat, keywords in subcats.items():
                if any(kw in tender_text for kw in keywords):
                    return 1.0  # Match perfecto
    
    # Fallback a matching básico
    return calculate_category_score(tender, experience)
```

**Impacto:** Medio - Mejora precisión de categorías

---

## 📊 Nuevos Pesos Sugeridos

### **Opción 1: Agregar Ubicación (Recomendado)**
```python
WEIGHTS_IMPROVED = {
    "keyword": 0.40,    # Reducido de 0.50
    "amount": 0.20,     # Reducido de 0.25
    "entity": 0.15,     # Mantiene
    "category": 0.10,   # Mantiene
    "location": 0.15,   # NUEVO - Muy importante
}
```

### **Opción 2: Agregar Ubicación + Fecha**
```python
WEIGHTS_IMPROVED = {
    "keyword": 0.35,
    "amount": 0.20,
    "entity": 0.15,
    "category": 0.10,
    "location": 0.15,   # NUEVO
    "recency": 0.05,    # NUEVO - Peso menor pero importante
}
```

---

## 🎯 Plan de Implementación Recomendado

### **Fase 1: Mejoras Rápidas (1-2 semanas)**
1. ✅ **Sinónimos y variaciones** en keywords
2. ✅ **Normalización de entidades**
3. ✅ **Factor de ubicación geográfica**
4. ✅ **Ajuste por inflación** en amounts

**Impacto esperado:** +30-40% de precisión

---

### **Fase 2: Mejoras Intermedias (2-3 semanas)**
5. ✅ **Ponderación de keywords**
6. ✅ **Fuzzy matching** de entidades
7. ✅ **Factor de fecha** (recency)
8. ✅ **Rangos por tipo de proyecto**

**Impacto esperado:** +20-30% adicional de precisión

---

### **Fase 3: Mejoras Avanzadas (3-4 semanas)**
9. ✅ **NLP para extracción de keywords**
10. ✅ **Taxonomía de categorías**
11. ✅ **Factor de éxito** (requiere datos)
12. ✅ **Similaridad semántica** (opcional, requiere ML)

**Impacto esperado:** +10-20% adicional de precisión

---

## 📈 Métricas de Éxito

### **Cómo medir mejoras:**
1. **Precisión (Precision):** % de licitaciones con match alto que realmente son relevantes
2. **Recall:** % de licitaciones relevantes que se identifican correctamente
3. **F1-Score:** Balance entre precisión y recall
4. **Feedback del usuario:** Marcar licitaciones como "Relevante" / "No relevante"

### **Objetivo:**
- **Precisión actual estimada:** ~60-70%
- **Objetivo después de mejoras:** ~85-90%

---

## 💡 Recomendación Final

**Empezar con Fase 1 (Mejoras Rápidas):**
1. Sinónimos en keywords
2. Normalización de entidades
3. Factor de ubicación
4. Ajuste por inflación

Estas 4 mejoras son **rápidas de implementar** y tienen **alto impacto** en la precisión.

---

**Fecha de creación:** 2025-11-17  
**Versión:** 1.0

