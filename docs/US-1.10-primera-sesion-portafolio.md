# US 1.10 — Primera sesión: WHY, Pregunta 0 y JTBD 0

## USER STORY

**As a** responsable de licitaciones en una empresa de construcción, ingeniería o interventoría que entra por primera vez a LicitIA  
**Quiero** entender en segundos para qué sirve el producto y subir el portafolio de experiencias de mi empresa  
**Para** encontrar licitaciones relevantes mucho más rápido que en SECOP y, a futuro, identificar socios para presentarnos juntas a más procesos.

---

## BACKGROUND

**WHY del producto:** LicitIA existe para que empresas de **construcción, ingeniería e interventoría** (1) **encuentren licitaciones relevantes mucho más rápido** y (2) **descubran socios para presentarse en consorcio** y así acceder a más oportunidades.

El usuario nuevo no pregunta *«¿qué dice el pliego?»* — eso llega después. Pregunta:

> **Pregunta 0:** *«¿Cómo encuentro licitaciones relevantes para mi empresa mucho más rápido — y esto es para el sector mío?»*

La respuesta en **< 30 s** debe comunicar el WHY (velocidad + sector + visión de alianzas), no solo el mecanismo técnico (match vs SECOP).

**JTBD 0** es el trabajo inmediato que desbloquea el valor:

> *«Enséñale a LicitIA en qué es buena mi empresa»* → subir portafolio → radar y match % operativos.

Sin JTBD 0, el usuario solo ve un listado SECOP y el WHY no se cumple.

**Estado previo:** onboarding skippable, tabla como hero, `ExperiencesStep` desconectado. **Esta US** implementa welcome + experiencias + `FirstSessionHome` + `MatchPreviewStep` + `usePortfolioStatus`.

**Nota de numeración:** el panel «¿Puedo ser hábil?» en detalle de licitación es **US 1.11** en el mapa JTBD (no confundir con esta US).

---

## SOLUCIÓN

### A. Pregunta 0 — Bienvenida (< 30 s)

`WelcomeStep`: copy centrado en **WHY** (sector + velocidad + alianzas en roadmap).

**Mensaje principal:**

> *LicitIA ayuda a empresas de construcción, ingeniería e interventoría a encontrar licitaciones relevantes mucho más rápido — cruzando cada proceso con tu experiencia, no con un listado genérico SECOP.*

**Tiles:**

| Tile | Mensaje |
|------|---------|
| Encuentra más rápido | Licitaciones filtradas por tu portafolio en obra pública |
| Para tu sector | Construcción, ingeniería e interventoría |
| Más oportunidades | Próximamente: socios para consorcios y UT |

**CTA principal:** *Comenzar* → `ExperiencesStep`.  
**Secundario:** *Explorar sin personalizar* → dashboard con `FirstSessionHome` / banner.

### B. JTBD 0 — Activar portafolio

Flujo: `WelcomeStep` → `ExperiencesStep` → `MatchPreviewStep` → `MarketingInfoStep` (opcional).

- Upload Excel (≥ 1 experiencia) = portafolio activo.
- `MatchPreviewStep`: top 3 match % como prueba de personalización.
- CTA *Ir a mis oportunidades* → dashboard con columna match visible.

### C. Home sin portafolio

`usePortfolioStatus` (`empty` | `ready`). Si `empty`: `FirstSessionHome` + `PortfolioBanner`; tabla vía enlace.

### D. Sin cambios de backend

---

## ACCEPTANCE CRITERIA

**GIVEN** usuario nuevo en `WelcomeStep`  
**WHEN** lee la pantalla  
**THEN** entiende en < 30 s sector (construcción/ingeniería/interventoría), velocidad vs SECOP y necesidad de subir portafolio; CTA principal va a experiencias.

**GIVEN** upload Excel válido (≥ 1 experiencia)  
**WHEN** completa onboarding  
**THEN** preview top 3 match % y dashboard con match visible.

**GIVEN** sin experiencias  
**WHEN** entra al dashboard  
**THEN** `FirstSessionHome` + banner; tabla por enlace.

**GIVEN** *Explorar sin personalizar*  
**THEN** tabla con match vacío y banner persistente.

**GIVEN** ≥ 1 experiencia previa  
**THEN** dashboard normal sin onboarding ni `FirstSessionHome`.

---

## TÍTULO JIRA

`1.10 [Frontend] Primera sesión — WHY, Pregunta 0 y activación de portafolio (JTBD 0)`
