# US 1.12 — Bug: faltan interventorías y estudios/diseños (concurso de méritos)

**Jira:** `[BUG][BACKEND] US 1.12 Cobertura concurso de méritos — interventoría y estudios/diseños`

## USER STORY

**As a** personal de licitaciones que usa el radar de LicitIA  
**Quiero** ver **todas** las interventorías y los estudios/diseños abiertos en SECOP (concurso de méritos abierto), no un subconjunto  
**Para** no perder procesos que sí aparecen en SECOP II y en los que mi empresa puede ofertar.

---

## BACKGROUND

En producción el dashboard muestra, en la práctica, **~1 proceso de estudios y diseños en 60 días** y **~5 interventorías en toda Colombia**. Contra SECOP II hay muchos más concursos de méritos abiertos de interventoría y consultoría (estudios/diseños).

### Causa raíz (medida en datos.gov.co, dataset `p6dx-8zbt`, 1 oct 2026)

La ingesta MVP (`fetch_mvp_secop_tenders` en `secop_client.py`) **no trae todo concurso de méritos**. Para CMA exige **a la vez**:

1. `modalidad_de_contratacion = Concurso de méritos abierto`
2. `estado_del_procedimiento = Publicado` y `estado_de_apertura_del_proceso = Abierto`
3. `codigo_principal_de_categoria` **LIKE** uno de 10 UNSPSC de obra (`UNSPSC_CODES_CONCURSO_MERITOS` en `secop_filters.py`: `81101500`, `72110000`, `72140000`, `95110000`, …)

Licitación pública de obra **no** usa esa lista UNSPSC; por eso el radar de obra se ve poblado y el de CMA no.

**Conteo SECOP, últimos 60 días, Publicado + Abierto:**

| Filtro | Procesos |
|--------|---------:|
| CMA (todas las categorías) | **110** |
| CMA + tipo Interventoría | **61** |
| CMA + tipo Consultoría | **48** |
| CMA que pegan la whitelist UNSPSC actual | **3** |

De los 109 Interventoría+Consultoría, **94 tienen `codigo_principal_de_categoria = UNSPECIFIED`**. El código que sí aparece más (además de 81101500) es `V1.80101600` (gestión de proyectos), **que no está en la lista**. Hijos UNSPSC (`81101515`) tampoco matchean `LIKE '%81101500%'`.

Conclusión: **no es que SECOP no tenga procesos; LicitIA los descarta en la query.** El síntoma ~1 estudios / ~5 interventorías es coherente con ingestas viejas + 3 hits UNSPSC.

### Otros factores (secundarios, validar al arreglar)

| Factor | Efecto |
|--------|--------|
| `SECOP_FETCH_LOOKBACK_DAYS` default **7** | Un catch-up de 60 días hace falta después de cambiar el filtro |
| Solo `codigo_principal`; no `categorias_adicionales` | Procesos clasificados en categoría secundaria no entran |
| Dashboard = solo Publicado + Abierto | SECOP muestra también cerrados / en evaluación; **esta US no pide traer cerrados** |
| Tipo Consultoría incluye no-infra (p. ej. TI `43222500`) | No tragar *todo* CMA a ciegas |

**Nota de numeración:** el panel *¿Puedo ser hábil?* queda como **US 1.13**. Esta 1.12 es el bug de cobertura.

---

## OBJETIVO

Que el radar de **concurso de méritos abierto** cubra interventoría y estudios/diseños **como en SECOP** (mismos procesos abiertos), no solo los 10 UNSPSC de construcción.

### Alcance MVP

| Incluye | No incluye |
|---------|------------|
| Cambiar criterio de ingesta CMA: dejar de exigir UNSPSC de obra como *AND* | Traer contratación directa, mínima cuantía, ni CMA de papelería/TI genérica |
| Incluir CMA `tipo_de_contrato = Interventoría` | Cambiar clasificación US 1.4 (`contract_kind`) salvo ajustes puntuales |
| Incluir CMA `tipo_de_contrato = Consultoría` cuando el objeto/UNSPSC sea estudios, diseños, ingeniería o infra | Consultoría jurídica, software, vigilancia, etc. |
| Mantener UNSPSC actuales como **inclusión extra** (OR) | Ampliar licitación pública de obra |
| Catch-up (lookback 60 días) + tests de filtro | Rediseño de UI del dashboard |
| Comparar conteo vs SECOP (misma ventana y estados) | Procesos no Publicado / no Abierto |

---

## SOLUCIÓN

### A. Nuevo criterio CMA (reemplaza AND UNSPSC)

Ingerir un concurso de méritos abierto **Publicado + Abierto** si cumple **cualquiera**:

1. `tipo_de_contrato = Interventoría`, o
2. `tipo_de_contrato = Consultoría` **y** el proceso es de estudios/diseños/ingeniería/infra (objeto y/o UNSPSC; ver lista de inclusión/exclusión abajo), o
3. `codigo_principal_de_categoria` o categorías adicionales matchean UNSPSC de obra/infra (lista actual **más** familias usadas en CMA: p. ej. `80101600`, `80101510`, `811015xx`, `81102200`). Match por **prefijo** (6–8 dígitos), no igualdad exacta a `81101500`.

**Exclusión Consultoría (MVP):** objeto o UNSPSC claramente ajenos (TI `4323xxxx` / `4322xxxx`, seguros, vigilancia, papelería) → no ingest.

Centralizar el criterio en `secop_filters.py` + tests. `fetch_mvp_secop_tenders` deja de hacer 10 round-trips UNSPSC-only; una o dos queries CMA (p. ej. por `tipo_de_contrato`) + filtro en memoria para Consultoría.

### B. Catch-up

Tras desplegar: `sync_secop_ingestion.py --lookback-days 60` (o lookback de producto acordado) para llenar el hueco histórico.

### C. Verificación vs SECOP

Misma definición: modalidad CMA, Publicado, Abierto, ventana 60 días.

- Interventorías en LicitIA ≈ conteo SECOP tipo Interventoría (± holgura por exclusión de basura).
- Estudios y diseños en UI (`contract_kind = estudios_disenos`) en el mismo orden de magnitud que CMA Consultoría de infra, no “1 proceso”.

### D. Relación con otras US

| US | Relación |
|----|----------|
| 1.1 Radar / filtros SECOP | Esta US corrige el filtro CMA de esa base |
| 1.4 `contract_kind` | Interventoría vs estudios/diseños se sigue derivando del objeto/tipo |
| 1.10 / 1.11 | Primera sesión y RUP no cambian; solo hay más procesos que matchear |

---

## ACCEPTANCE CRITERIA

**GIVEN** el dataset SECOP II `p6dx-8zbt`  
**WHEN** se cuentan CMA Publicado + Abierto, tipo Interventoría, últimos 60 días  
**THEN** LicitIA tiene ingestados (y visibles si siguen Abiertos) **el mismo conjunto**, no un dígito de procesos.

**GIVEN** CMA Publicado + Abierto, tipo Consultoría de estudios/diseños/ingeniería, últimos 60 días  
**WHEN** el usuario filtra o ve “Estudios y diseños” en el dashboard  
**THEN** ve **varios** procesos (orden de magnitud del SECOP), no ~1.

**GIVEN** un CMA de interventoría con `codigo_principal_de_categoria = UNSPECIFIED` o `V1.80101600`  
**WHEN** corre la ingesta  
**THEN** el proceso **sí** se guarda (hoy se descarta).

**GIVEN** un CMA de consultoría de software / no infra  
**WHEN** corre la ingesta  
**THEN** **no** entra al radar (el producto sigue siendo obra / ingeniería / interventoría).

**GIVEN** licitaciones públicas de obra que ya se veían  
**WHEN** se despliega el fix  
**THEN** no hay regresión de cobertura de obra.

**GIVEN** tests de `secop_filters` / cliente SECOP  
**WHEN** CI corre  
**THEN** hay casos: Interventoría sin UNSPSC de obra → incluido; Consultoría TI → excluido; UNSPSC hijo `81101515` → incluido si aplica la rama UNSPSC.

---

## TÍTULO JIRA

`1.12 [BUG][Backend] Concurso de méritos: no se traen todas las interventorías ni estudios/diseños`
