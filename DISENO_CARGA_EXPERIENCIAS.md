# Diseño de Feature: Carga de Experiencias
## Análisis Estratégico y Propuesta de UX/UI

---

## 🎯 CONTEXTO Y OBJETIVO

**Problema Actual:**
- Usuario necesita cargar experiencias para obtener matches relevantes
- Sin experiencias = sin valor del producto
- Fricción alta = menos usuarios completan el proceso

**Objetivo:**
- Reducir fricción al máximo
- Mostrar valor inmediato después de cargar
- Hacer el proceso intuitivo y rápido (<2 minutos)
- Incentivar a cargar más experiencias

---

## 📍 ¿DÓNDE DEBE CARGAR EXPERIENCIAS EL USUARIO?

### **OPCIÓN 1: En el Onboarding (Recomendado para MVP)**
**Ubicación:** Paso 3 del onboarding (después de nombre de empresa)

**Ventajas:**
- ✅ Flujo natural: Nombre → Experiencias → Ver resultados
- ✅ Time-to-Value inmediato: Después de cargar, ve matches
- ✅ Reduce fricción: Todo en un flujo guiado
- ✅ Opción de "Saltar": No bloquea si no tiene Excel

**Desventajas:**
- ⚠️ Puede ser opcional (usuario puede saltar)
- ⚠️ Requiere Excel preparado

**Mejor para:** Nuevos usuarios, primera impresión

---

### **OPCIÓN 2: En el Perfil (Recomendado para usuarios existentes)**
**Ubicación:** Sección "Cargar Experiencias" en Perfil

**Ventajas:**
- ✅ Acceso permanente: Puede cargar cuando quiera
- ✅ Más espacio: Puede mostrar más información
- ✅ Historial: Ve experiencias cargadas

**Desventajas:**
- ⚠️ Menos visible: Usuario puede no encontrarlo
- ⚠️ Requiere navegación adicional

**Mejor para:** Usuarios existentes, actualizaciones

---

### **OPCIÓN 3: Híbrida (RECOMENDADA)**
**Estrategia:**
1. **Onboarding:** Carga inicial (opcional, puede saltar)
2. **Dashboard:** Banner/CTA si no tiene experiencias
3. **Perfil:** Carga permanente y gestión completa

**Ventajas:**
- ✅ Múltiples puntos de entrada
- ✅ No bloquea el flujo inicial
- ✅ Acceso fácil cuando lo necesita

---

## 🎨 DISEÑO IDEAL: Feature de Carga de Experiencias

### **UBICACIÓN PRINCIPAL: Perfil de Empresa**

**Razón:** 
- Es el lugar lógico para "gestionar datos de la empresa"
- Permite espacio para explicación y ayuda
- Accesible desde cualquier momento

---

## 📋 ESTRUCTURA DEL FEATURE

### **SECCIÓN 1: Carga de Experiencias (Principal)**

#### **Header de la Sección:**
```
┌─────────────────────────────────────────┐
│ 📄 Cargar Experiencias                  │
│ ─────────────────────────────────────── │
│ Sube tus proyectos anteriores para      │
│ encontrar licitaciones más relevantes   │
└─────────────────────────────────────────┘
```

#### **Contenido:**

**1. Explicación del Valor (Arriba)**
- **Texto:** "Cuantas más experiencias cargues, mejores matches encontrarás"
- **Estadística:** "Usuarios con 5+ experiencias ven 3x más matches relevantes"
- **Visual:** Progress bar o badge mostrando impacto

**2. Dos Opciones de Carga:**

**A) Carga Masiva (Excel) - Recomendado**
- **Título:** "Carga Rápida desde Excel"
- **Descripción:** "Sube un archivo Excel con todas tus experiencias (2 minutos)"
- **Componentes:**
  - FileUploader de Carbon
  - Botón "Descargar Plantilla" (con ejemplo)
  - Preview del formato esperado
  - Validación en tiempo real

**B) Carga Individual (Manual) - Alternativa**
- **Título:** "Agregar Experiencia Manual"
- **Descripción:** "Agrega una experiencia a la vez (útil para pocas)"
- **Componentes:**
  - Formulario inline o modal
  - Campos: Proyecto, Entidad, Monto, Fecha, Categoría
  - Botón "Agregar Otra" para múltiples

**3. Feedback Inmediato:**
- **Durante carga:** Loading con progreso
- **Después de carga:** 
  - ✅ "X experiencias cargadas exitosamente"
  - ⚠️ "Y experiencias con advertencias (revisar)"
  - ❌ "Z errores (ver detalles)"
- **Siguiente paso:** "Ver matches ahora" (CTA)

---

### **SECCIÓN 2: Gestión de Experiencias (Abajo)**

#### **Lista de Experiencias Cargadas:**
- **Vista:** Tabla o cards con:
  - Descripción del proyecto
  - Entidad contratante
  - Monto
  - Fecha
  - Acciones: Editar | Eliminar | Ver matches relacionados

#### **Estadísticas:**
- **Card destacado:**
  - "X experiencias cargadas"
  - "Y licitaciones encontradas gracias a estas experiencias"
  - "Z% de tus matches vienen de estas experiencias"

---

### **SECCIÓN 3: Ayuda y Guía**

#### **Accordion con:**
1. **"Formato del Excel"**
   - Columnas requeridas
   - Ejemplo visual
   - Descargar plantilla

2. **"¿Por qué cargar experiencias?"**
   - Explicación del matching
   - Ejemplo visual de cómo funciona
   - "Sin experiencias: 0 matches | Con 5 experiencias: 15+ matches"

3. **"Preguntas Frecuentes"**
   - ¿Cuántas experiencias necesito?
   - ¿Qué pasa si no tengo Excel?
   - ¿Puedo editar después?

---

## 🎯 FLUJO DE USUARIO IDEAL

### **Escenario 1: Usuario Nuevo (Onboarding)**
```
1. Completa nombre de empresa
2. Ve pantalla: "Carga tus experiencias (opcional)"
   - Opción A: Subir Excel (recomendado)
   - Opción B: Agregar manualmente
   - Opción C: Saltar por ahora
3. Si carga → Ve feedback inmediato
4. Redirige a Dashboard con matches destacados
```

### **Escenario 2: Usuario Existente (Perfil)**
```
1. Va a Perfil → Sección "Cargar Experiencias"
2. Ve estado actual: "Tienes X experiencias"
3. Opciones:
   - Agregar más desde Excel
   - Agregar manualmente
   - Editar existentes
4. Después de cargar → Ve impacto: "Ahora tienes Y nuevos matches"
```

### **Escenario 3: Usuario sin Experiencias (Dashboard)**
```
1. Entra a Dashboard
2. Ve banner destacado: "Carga experiencias para ver matches personalizados"
3. Click → Va a Perfil → Carga experiencias
4. Vuelve a Dashboard → Ve matches inmediatamente
```

---

## 💡 FEATURES ADICIONALES PARA MAXIMIZAR VALOR

### **1. Preview de Matches Antes de Cargar**
- **Qué:** Mostrar ejemplo: "Con experiencias similares, encontrarías X licitaciones"
- **Valor:** Incentiva a cargar, muestra valor potencial

### **2. Validación Inteligente**
- **Qué:** Al cargar Excel, validar y sugerir correcciones
- **Ejemplo:** "La columna 'Monto' parece estar en formato texto, ¿convertir a número?"
- **Valor:** Reduce errores, mejor calidad de datos

### **3. Importación desde SECOP (Futuro)**
- **Qué:** Conectar con SECOP para importar contratos ganados automáticamente
- **Valor:** Reduce fricción a cero, datos más precisos

### **4. Sugerencias de Mejora**
- **Qué:** Después de cargar, sugerir: "Agrega más detalles sobre [categoría X] para mejores matches"
- **Valor:** Guía al usuario a optimizar sus datos

### **5. Comparación de Impacto**
- **Qué:** "Antes: 5 matches | Después: 18 matches (+260%)"
- **Valor:** Muestra valor tangible de cargar experiencias

---

## 🎨 DISEÑO VISUAL (Carbon Design System)

### **Layout:**
```
┌─────────────────────────────────────────────┐
│ [Header: Cargar Experiencias]              │
│ ────────────────────────────────────────── │
│                                             │
│ [Card: Valor de Cargar Experiencias]       │
│ "5+ experiencias = 3x más matches"        │
│                                             │
│ [Tabs: Excel | Manual]                     │
│                                             │
│ [FileUploader o Formulario]                │
│                                             │
│ [Botón: Cargar]                            │
│                                             │
│ [Feedback: Éxito/Error]                    │
│                                             │
│ [Accordion: Ayuda]                         │
│                                             │
│ [Sección: Experiencias Cargadas]           │
│ [Tabla con acciones]                        │
└─────────────────────────────────────────────┘
```

### **Estados Visuales:**
- **Vacío:** Ilustración + CTA claro
- **Cargando:** Progress bar + mensaje
- **Éxito:** Badge verde + estadísticas
- **Error:** Notificación + sugerencias de corrección
- **Con Datos:** Tabla + estadísticas de impacto

---

## 📊 MÉTRICAS DE ÉXITO

### **KPIs Principales:**
1. **Tasa de Carga:** % usuarios que cargan al menos 1 experiencia
2. **Experiencias por Usuario:** Promedio (objetivo: >5)
3. **Time-to-Carga:** Tiempo desde registro hasta primera carga
4. **Tasa de Re-carga:** % usuarios que agregan más experiencias después
5. **Calidad de Datos:** % experiencias con todos los campos completos

### **Métricas Secundarias:**
- Clicks en "Descargar Plantilla"
- Uso de carga manual vs Excel
- Errores de validación
- Tasa de abandono en el proceso

---

## 🚀 IMPLEMENTACIÓN RECOMENDADA

### **Fase 1: MVP (Semana 1-2)**
- ✅ Carga desde Excel (ya existe, mejorar UX)
- ✅ Carga manual individual (nuevo)
- ✅ Feedback básico (éxito/error)
- ✅ Lista de experiencias cargadas

### **Fase 2: Mejoras (Semana 3-4)**
- ✅ Validación inteligente
- ✅ Preview de matches potenciales
- ✅ Estadísticas de impacto
- ✅ Banner en Dashboard si no tiene experiencias

### **Fase 3: Optimización (Semana 5-6)**
- ✅ Sugerencias de mejora
- ✅ Comparación antes/después
- ✅ Importación desde SECOP (si es posible)

---

## ✅ CONCLUSIÓN

**Ubicación Principal:** Perfil de Empresa
**Ubicación Secundaria:** Onboarding (opcional, puede saltar)
**Ubicación Terciaria:** Banner en Dashboard si no tiene experiencias

**Features Críticas:**
1. Carga desde Excel (rápida, masiva)
2. Carga manual (alternativa, sin fricción)
3. Feedback inmediato con valor (matches encontrados)
4. Gestión de experiencias (editar, eliminar)
5. Ayuda contextual (plantilla, FAQ)

**Principio Clave:** "Cada paso debe mostrar valor o reducir fricción"

