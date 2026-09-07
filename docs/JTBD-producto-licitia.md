# JTBD de producto — LicitIA

Documento de referencia para alinear desarrollo de UX/producto alrededor de las preguntas reales del licitador, no de la estructura del pliego.

**Última actualización:** septiembre 2026  
**Estado:** Marco activo para Fase 1 (UX sobre MVP técnico)

---

## WHY del producto

LicitIA existe para ayudar a **empresas de construcción, ingeniería e interventoría** a:

1. **Encontrar licitaciones relevantes mucho más rápido** que buscando manualmente en SECOP.
2. **Acceder a más oportunidades** — hoy vía radar y match con su experiencia; **próximamente** vía identificación de **socios para consorcios y uniones temporales**.

El motor técnico (SECOP + pliegos + extracción + match) es el **cómo**. El **por qué** es tiempo ahorrado y más procesos donde pueden competir — solos o en alianza.

| Pilar | Promesa | Estado |
|-------|---------|--------|
| **Velocidad** | Ver solo licitaciones que encajan con tu empresa, no un listado genérico | MVP: match % + filtros |
| **Sector** | Construcción, ingeniería, interventoría (obra pública) | Copy + datos SECOP |
| **Alianzas** | Encontrar socios para presentarse juntas | Roadmap (no MVP) |

---

## Contexto

### Qué es el MVP técnico hoy

LicitIA ya resuelve el **motor de valor**:

| Capa | Capacidad |
|------|-----------|
| **Datos** | Conexión SECOP → licitaciones de estudios/diseños, interventoría, estudios+diseños+obra y ejecución de obra |
| **Documentos** | Descarga pliego, anexo, presupuesto; carga manual |
| **Extracción** | Lectura de PDFs/XLSX → experiencia, financiera, jurídica, puntaje, capacidad residual (obra), variables del contrato (POE, plazo, anticipo…) |
| **Presentación** | Requisitos y variables mostrados en el detalle de cada licitación |

Eso responde: *«¿Qué exige este pliego para participar?»* — una vez que el usuario **ya abrió** el proceso.

### Qué no es (aún) producto

La pantalla **Inicio** (`/dashboard`) se construyó principalmente para **validar** que los datos de SECOP llegaban bien: tabla larga, filtros básicos, metadatos. Funciona como explorador, pero **no como primera impresión de producto**.

El usuario no entra a LicitIA para ver *otro listado SECOP*; entra para **encontrar oportunidades relevantes más rápido** y **ampliar su capacidad de participar** (hoy con match, mañana con socios).

### Cambio de mentalidad

| Hoy (orientado al pliego) | Objetivo (orientado al JTBD) |
|---------------------------|------------------------------|
| Lista → abrir → scroll por secciones del documento base | Inicio con prioridades → triaje → decisión rápida → habilitación |
| Misma jerarquía que el PDF | Dos capas: *¿me interesa?* y *¿puedo ser hábil?* |
| Valor visible solo al profundizar | Valor visible en los primeros 30 segundos |

---

## Usuario nuevo: Pregunta 0 y JTBD 0

Antes del JTBD 1 existe un momento **solo para quien entra por primera vez** (o vuelve sin haber configurado el producto). Son dos capas **relacionadas pero distintas**:

| | **Pregunta 0** | **JTBD 0** |
|---|----------------|------------|
| **Qué es** | Pregunta de **comprensión y confianza** | **Trabajo** que el usuario debe **completar** |
| **Formulación** | *«¿Cómo encuentro licitaciones relevantes mucho más rápido — y esto es para mi sector?»* | *«Enséñale a LicitIA en qué es buena mi empresa»* |
| **Tipo** | Entender **por qué** quedarse (WHY) | **Activar** el radar personalizado |
| **Tiempo** | **&lt; 30 segundos** | Varios minutos (subir Excel de experiencias) |
| **Éxito** | *«Ah, esto es para construcción/ingeniería/interventoría, me ahorra tiempo vs SECOP y puedo subir mi portafolio»* | Portafolio cargado → match IA operativo |

### Cómo se conectan

```text
WHY del producto                    Pregunta 0 (30 seg)           JTBD 0 (minutos)              JTBD 1 (recurrente)
────────────────                    ───────────────────           ────────────────              ─────────────────
Más rápido + más oportunidades  →   «¿Es para mí?»         →    «Subo mi experiencia»   →    «¿Qué hay para mí hoy?»
(socios: roadmap)                         POR QUÉ                      CÓMO                         VALOR REAL
```

La **respuesta** a la Pregunta 0 explica **por qué** hace falta el JTBD 0:

> *«SECOP lista todo y te hace perder horas. LicitIA filtra licitaciones de obra pública que encajan con **tu** experiencia en construcción, ingeniería o interventoría — mucho más rápido. Para eso, sube tu portafolio. Próximamente también te ayudaremos a encontrar socios para consorcios.»*

- Sin Pregunta 0 respondida → el usuario no entiende por qué subir experiencias.
- Sin JTBD 0 cumplido → el WHY de velocidad no se cumple (solo ve un listado SECOP).

### Pregunta 0 — Qué debe mostrar el producto en &lt; 30 segundos

Una sola idea clara en pantalla (bienvenida / onboarding / home vacía):

> **«LicitIA ayuda a empresas de construcción, ingeniería e interventoría a encontrar licitaciones relevantes mucho más rápido — cruzando cada proceso con tu experiencia, no con un listado genérico SECOP.»**

En UI:

1. **Promesa en una línea** — sector + velocidad (no tabla de 32 filas como primer elemento).
2. **Diferencial visible** — radar personalizado + visión de alianzas (*próximamente*).
3. **Un solo CTA** — *«Sube tu portafolio de experiencias»* (puente a JTBD 0).

**Implementación:** `WelcomeStep`, `FirstSessionHome`, `PortfolioBanner` — ver `OnboardingWizard`.

**US:** `US 1.10` — Primera sesión: WHY, Pregunta 0 y JTBD 0 (`docs/US-1.10-primera-sesion-portafolio.md`).

### JTBD 0 — Enséñale a LicitIA en qué es buena tu empresa

**Pregunta:** *¿Cómo activo el radar para que LicitIA me muestre licitaciones relevantes para mi empresa?*

**Situación:** Usuario convencido por la Pregunta 0; necesita el input mínimo (Excel de experiencias en obra pública) para que el match funcione.

**Éxito:**

- Al menos un archivo de experiencias subido (o camino claro para hacerlo).
- Entiende que el **match %** viene de **su** portafolio en construcción/ingeniería/interventoría.
- Ve una señal de personalización (`MatchPreviewStep`: top 3 con match, o estado vacío guiado).

**Solución de producto:**

- `ExperiencesStep` en onboarding (upload Excel, plantilla).
- Tras subir: `MatchPreviewStep` — preview de match, no tabla genérica.
- Si omite: `FirstSessionHome` + `PortfolioBanner` persistente.

**US:** `US 1.10` — misma US que Pregunta 0 (`docs/US-1.10-primera-sesion-portafolio.md`).

---

## Los JTBD 1–5 (Fase 1)

Ordenados como los vive el licitador **una vez el producto puede personalizar** (JTBD 0 cumplido o usuario recurrente) hasta decidir si estudia un proceso en serio.

### JTBD 1 — Orientarme

**Pregunta:** *¿Qué hay relevante para mí hoy? ¿Valió la pena entrar?*

**Situación:** Vuelta diaria (o primera sesión **después** de JTBD 0). Tiene 30–60 segundos para percibir valor distinto a SECOP.

**Prerrequisito:** experiencias cargadas; sin ellas, este JTBD se degrada a listado genérico.

**Éxito:** Ve un resumen accionable: novedades, procesos que cierran pronto, favoritas pendientes, señal de match con su experiencia.

**Solución de producto (objetivo):**

- Pantalla de **Inicio** con hero/resumen del día (no tabla como primer elemento).
- Mensaje claro si no hay experiencias cargadas: *«Sube tu portafolio para ver oportunidades para ti»*.
- Contador o frase tipo: *«4 oportunidades cierran en 7 días · 2 con alto match»*.

**US / backlog:** `1.9.1` — Inicio: resumen y oportunidades prioritarias

---

### JTBD 2 — Priorizar

**Pregunta:** *¿En qué debo enfocarme primero?*

**Situación:** Tiene poco tiempo; no puede abrir 32–200 procesos uno a uno.

**Éxito:** Un bloque acotado (5–10 ítems) con lo más urgente y relevante: cierre próximo + match + monto + tipo.

**Solución de producto (objetivo):**

- Sección **«Oportunidades para ti»** con cards (no filas de tabla).
- Criterios MVP: match de experiencia alto, cierre en ventana configurable (ej. 7–14 días), opcionalmente monto mínimo.
- Orden por urgencia de cierre, no solo por fecha de publicación.

**US / backlog:** `1.9.1` (cards) + `1.9.3` (urgencia en datos)

---

### JTBD 3 — Filtrar ruido

**Pregunta:** *¿Cuáles descarto sin abrir? ¿Cómo encuentro más si necesito?*

**Situación:** Quiere interventoría en Bogotá, no obra en otro departamento; o solo procesos con buen match.

**Éxito:** Filtra rápido por tipo, ubicación, match y urgencia; el explorador completo queda disponible pero no es la home.

**Solución de producto (objetivo):**

- Chips de tipo de contrato (ya existen) + **filtros rápidos**: «Cierra esta semana», «Alto match (>60%)».
- **Tipo de proceso visible en cada fila** del explorador.
- Ruta o sección **«Explorar todas»** = tabla actual del dashboard (reubicada, no eliminada).

**US / backlog:** `1.9.2` — Explorador: filtros rápidos y tipo en tabla

---

### JTBD 4 — Decidir si profundizo

**Pregunta:** *¿Vale la pena estudiar esta licitación en serio?*

**Situación:** Hizo clic en una oportunidad. Antes de leer requisitos y pliego, necesita la foto del proceso.

**Éxito:** En segundos ve: días al cierre, monto, tipo, POE/anticipo/plazo (y CRPC si es obra).

**Solución de producto:**

| Estado | Entregable |
|--------|------------|
| ✅ Implementado | **US 1.9** — Barra sticky «Resumen para decidir» en `TenderDetailPanel` |
| Pendiente | Señales de urgencia/tipo en fila del explorador (refuerzo desde JTBD 3) |
| Pendiente | Reducir duplicación en detalle (monto/cierre repetidos bajo el sticky) |

**US / backlog:** `1.9` (hecho) · mejoras menores en detalle

---

### JTBD 5 — Entender qué debo cumplir

**Pregunta:** *¿Qué exige el proceso para poder ofertar?*

**Situación:** Decidió que el proceso interesa. Necesita requisitos claros, no párrafos del PDF.

**Éxito:** Ve experiencia, financiera, jurídica, puntaje y K (obra) de forma escaneable, separada por capacidad.

**Solución de producto:**

| Estado | Entregable |
|--------|------------|
| ✅ MVP motor | Extracción y UI US 1.4, 1.5, 1.8 (regex + LLM híbrido) |
| Pendiente | **US 1.11** — Panel «¿Puedo ser hábil?» (resumen 5 capacidades + K) |
| Pendiente | **US 1.12** — Tabs por capacidad + documentos |
| Pendiente | **US 1.13** — Checklists experiencia/financiera |
| Pendiente | **US 1.14** — Hero numérico financiera (CTd, umbrales) |
| Futuro | **US 1.15 / 1.5.3** — Encaje y gap analysis vs perfil empresa |

**Nota:** El motor ya extrae; falta **reorganizar la UX** alrededor de la pregunta del usuario.

---

## Mapa del recorrido (Fase 1)

```text
Usuario entra a LicitIA (primera vez)
        │
        ├─ Pregunta 0: ¿Es para mi sector? ¿Más rápido que SECOP?  → Welcome / FirstSessionHome
        └─ JTBD 0: Enséñale en qué es buena tu empresa           → Subir experiencias (onboarding)

Usuario recurrente (o tras JTBD 0)
        │
        ├─ JTBD 1: Orientarme          → Inicio: resumen del día
        ├─ JTBD 2: Priorizar           → Bloque «Oportunidades para ti»
        ├─ JTBD 3: Filtrar ruido       → Explorar todas (tabla + filtros rápidos)
        │
        Abre una licitación
        │
        ├─ JTBD 4: ¿Vale la pena?       → Sticky resumen (US 1.9)
        └─ JTBD 5: ¿Qué debo cumplir?  → Requisitos (MVP + US 1.11–1.14)
```

### Fase 2 (fuera del alcance inmediato de Fase 1)

Preguntas posteriores que requieren perfil de empresa o comparación:

- *¿Cumplo con todo?* → semáforo habilitantes (US 1.5.3)
- *¿Me conviene ofertar económicamente?* → encaje / fit score (US 1.14)
- *¿Qué documentos me faltan?* → gap documental + Formatos

---

## Pantalla de inicio propuesta (visión)

La **home** no debe ser la tabla SECOP. Depende del estado del usuario:

### Usuario nuevo (sin experiencias)

```text
┌─ Pregunta 0: WHY en < 30 s ──────────────────────────────┐
│  Encuentra licitaciones relevantes para tu empresa en solo segundos. │
│  Construcción · Ingeniería · Interventoría.              │
│  Próximamente: socios para consorcios.                    │
│  [ Subir portafolio de experiencias ]  (CTA → JTBD 0)    │
└──────────────────────────────────────────────────────────┘
```

### Usuario recurrente (con experiencias)

```text
┌─ Bienvenida / resumen del día ───────────────────────────┐
│  X oportunidades cierran en 7 días · Y con alto match   │
└────────────────────────────────────────────────────────┘

┌─ Oportunidades para ti (5–8 cards) ────────────────────┐
│  Cierra en 3d · Interventoría · $242M · Match 78%      │
│  Cierra en 5d · Obra · $1.2B · Match 65%               │
└────────────────────────────────────────────────────────┘

┌─ Acciones rápidas ─────────────────────────────────────┐
│  Favoritas · Actualizar experiencias · Explorar todas  │
└────────────────────────────────────────────────────────┘

┌─ Explorar todas las licitaciones ──────────────────────┐
│  (tabla actual del dashboard, filtros, paginación)    │
└────────────────────────────────────────────────────────┘
```

### Principios de diseño (Fase 1)

1. **Personalizada** — sin experiencias, guiar a cargar portafolio antes de mostrar tabla vacía de sentido.
2. **Orientada a decisión** — cada elemento responde *¿mire esto o no?*
3. **Limitada arriba, completa abajo** — pocos ítems prioritarios; explorador para el resto.
4. **Urgencia visible** — el cierre pesa tanto como el monto.
5. **Diferencial visible** — radar personalizado y match IA; alianzas como visión de producto.

### Navegación (concepto)

| Ruta actual | Propuesta |
|-------------|-----------|
| `/dashboard` = tabla completa | `/dashboard` o `/inicio` = resumen + oportunidades prioritarias |
| — | `/explorar` o sección «Todas» = tabla actual |
| `/favorites` | Sin cambio |
| `/experiences` | Sin cambio (alimenta JTBD 2 y match) |

---

## Relación JTBD ↔ User Stories

| ID | Pregunta / job | US | Fase | Estado |
|----|----------------|-----|------|--------|
| **Pregunta 0** | ¿Cómo encuentro licitaciones relevantes más rápido (mi sector)? | US 1.10 welcome + FirstSessionHome | 0 | ✅ Implementado |
| **JTBD 0** | Enséñale en qué es buena tu empresa | US 1.10 portafolio + MatchPreview | 0 | ✅ Implementado |
| **JTBD 1** | ¿Qué hay para mí hoy? | 1.9.1 Inicio: resumen y prioridades | 1 | Pendiente |
| **JTBD 2** | ¿En qué me enfoco? | 1.9.1 (cards) + 1.9.3 (urgencia) | 1 | Pendiente |
| **JTBD 3** | ¿Cómo filtro ruido? | 1.9.2 Explorador: filtros y tipo en fila | 1 | Pendiente |
| **JTBD 4** | ¿Vale la pena estudiarla? | 1.9 Sticky resumen en detalle | 1 | ✅ Hecho |
| **JTBD 5** | ¿Qué debo cumplir? | 1.11, 1.12, 1.13, 1.14 | 1–2 | Parcial (motor 1.5–1.8) |
| — | ¿Cumplo / me conviene? | 1.15, 1.5.3 | 2 | Futuro |
| — | ¿Con quién me asocio? | TBD (alianzas / socios) | 2+ | Roadmap |

### Orden de implementación sugerido

1. **US 1.10** — Pregunta 0 + JTBD 0: WHY, welcome, experiencias, FirstSessionHome, preview match ✅
2. **1.9.3** — Urgencia de cierre en explorador (columna/badge, orden por cierre)
3. **1.9.2** — Filtros rápidos + tipo visible en fila
4. **1.9.1** — Nueva home recurrente: resumen + oportunidades prioritarias
5. **1.11** — Panel «¿Puedo ser hábil?»
6. **1.12** — Tabs por capacidad

---

## Qué NO es Fase 1

- Semáforo cumple / no cumple vs datos de la empresa (requiere perfil y gap analysis).
- Backend nuevo de extracción (salvo bugs o mejoras puntuales).
- Sincronización multi-dispositivo, notificaciones push, export Excel (evaluar después).
- Reemplazar SECOP; la tabla de exploración sigue existiendo.

---

## Frase guía para el equipo

> **MVP:** LicitIA ingesta SECOP, lee pliegos y muestra requisitos habilitantes estructurados.  
> **WHY:** Ayudar a construcción, ingeniería e interventoría a encontrar licitaciones relevantes más rápido y, a futuro, socios para más oportunidades.  
> **Usuario nuevo (&lt; 30 s):** Responder Pregunta 0 (sector + velocidad) y llevar a JTBD 0 (subir portafolio).  
> **Usuario recurrente (Fase 1):** Reorganizar la UX para *«qué licito y por dónde empiezo»*, no solo *«qué pide este pliego»* al abrir cada proceso.

---

## Referencias

- `docs/US-1.10-primera-sesion-portafolio.md` — WHY, Pregunta 0 + JTBD 0
- `docs/US-1.9-resumen-para-decidir.md` — JTBD 4 en detalle
- `FEATURES_MVP_MAXIMO_VALOR.md` — ideas de dashboard (match, prioritarias, filtros rápidos)
- Conversación de producto: separación *¿vale la pena licitar?* vs *¿puedo ser hábil?*
