# US 1.8 — Capacidad residual (obra pública)

## USER STORY

**As a** constructor o licitador de obra pública  
**Quiero** ver en el detalle de la licitación el requisito de capacidad residual (K de contratación), la CRPC del proceso y cómo acreditarla  
**Para** saber si mi empresa tiene cupo para asumir el contrato junto con los demás en ejecución, sin confundirlo con los indicadores financieros de la Matriz 2.

---

## BACKGROUND

En Colombia, la **capacidad residual** (también **K de contratación**) es un habilitante **adicional** a liquidez, endeudamiento, ROE, etc. Está regulada en el **Decreto 1082 de 2015** (arts. 2.2.1.1.1.3.1 y 2.2.1.1.1.6.4) y en la **Guía CCE GI-22** (*Capacidad residual del proponente en procesos de contratación de obra pública*).

| Concepto | Definición breve |
|----------|------------------|
| **CRPC** | Capacidad residual **del proceso** (lo que exige la entidad) |
| **CRP** | Capacidad residual **del proponente** (lo que debe demostrar el oferente) |
| **Regla** | El proponente es hábil si **CRP ≥ CRPC** |

**Fórmulas documento base obra (§3.11):**

- Plazo ≤ 12 meses: `CRPC = POE − Anticipo`
- Plazo > 12 meses: `CRPC = (POE − Anticipo) / Plazo_estimado × 12`
- Proponente: `CRP = CO × [(E + CT + CF) / 100] − SCE`

Factores del puntaje máximo (ej. Villa María III):

| Factor | Máx. pts | Fuente en pliego |
|--------|----------|------------------|
| Experiencia (E) | 120 | Formato 5, contratos segmento 72 |
| Capacidad financiera (CF) | 40 | Índice de liquidez (reutiliza §3.6) |
| Capacidad técnica (CT) | 40 | Profesionales vinculados (Formato 5) |
| Capacidad de organización (CO) | factor multiplicador | Metodología CCE |
| SCE | resta | Contratos en ejecución (Formato 5) |

**Acreditación:** Formato 5 – Capacidad residual (+ RUP cuando aplica).

### Qué NO es capacidad residual

- No es un índice de la Matriz 2 (liquidez, ROE, ROA).
- No aplica a interventoría, consultoría pura ni suministros.
- No sustituye capital de trabajo (§3.7); son requisitos distintos.

### Estado actual en LicitIA

- `indicadores_financieros` extrae §3.6–3.9 y Matriz 2 (v1.9.7 incluye ROE/ROA en documento base obra).
- **No hay** extracción ni UI de §3.11 / Formato 5.
- `ContractKind` ya distingue `ejecucion_obra` y `estudios_disenos_y_obra` (`contract_kind.py`).

---

## ALCANCE DE TIPO DE PROCESO

La extracción y visualización de capacidad residual **solo** se activa cuando:

```text
detect_contract_kind(tender) ∈ { ejecucion_obra, estudios_disenos_y_obra }
```

Equivalente operativo en SECOP: modalidad **«Licitación pública Obra Pública»**, excluyendo interventoría en el objeto.

| Tipo LicitIA | ¿Capacidad residual? |
|--------------|----------------------|
| `ejecucion_obra` | **Sí** |
| `estudios_disenos_y_obra` | **Sí** |
| `interventoria` | No |
| `estudios_disenos` | No |
| `desconocido` | No |

---

## OBJETIVO

Mostrar en el panel de detalle una subsección **«Capacidad residual»** (o ítems dentro de requisitos) con:

1. CRPC calculada o citada del pliego (POE, anticipo, plazo).
2. Fórmula CRP y factores E / CF / CT / CO / SCE con puntajes máximos.
3. Formato 5 y reglas de proponente plural.
4. Evidencia textual (§3.11) y estado `no_encontrado` si el pliego no es documento base obra.

### Fuera de alcance (fase inicial)

- Calcular CRP de la empresa del usuario (gap analysis).
- Descargar o validar Formato 5 diligenciado.
- Aplicativo Excel CCE integrado.

---

## SOLUCIÓN PROPUESTA

### Fase 1.8.1 — Extracción regex (MVP)

#### A. Gate por tipo de contrato

En `build_tender_requirements()` o extractor dedicado:

```python
if detect_contract_kind(tender) not in (
    ContractKind.EJECUCION_OBRA,
    ContractKind.ESTUDIOS_DISENOS_Y_OBRA,
):
    return []  # no sección capacidad_residual
```

#### B. Nueva sección o extensión de requisitos

**Opción recomendada:** clave `capacidad_residual` en `SECTION_DEFINITIONS` (título: «Capacidad residual (K)»), separada de `indicadores_financieros` para no mezclar Matriz 2 con §3.11.

Ítems estructurados sugeridos:

| key | label | value |
|-----|-------|-------|
| `crpc_formula` | CRPC del proceso | fórmula + POE/anticipo/plazo si están en pliego o US 1.4 |
| `crp_formula` | CRP del proponente | `CO × [(E+CT+CF)/100] − SCE` |
| `factor_experiencia` | Experiencia (E) | puntaje máx. 120, referencia Formato 5 |
| `factor_capacidad_financiera` | CF | puntaje máx. 40, liquidez |
| `factor_capacidad_tecnica` | CT | puntaje máx. 40, profesionales |
| `factor_organizacion` | CO | descripción breve |
| `sce` | Contratos en ejecución | resta SCE, Formato 5 |
| `proponente_plural` | Proponente plural | suma CRP miembros, regla miembro negativo |
| `accreditation_formato_5` | Cómo acreditar | Formato 5 + firmas |
| `habilitante_rule` | Regla de habilitación | CRP ≥ CRPC |

#### C. Localización en el pliego

Marcadores (documento base CCE obra):

```text
3.11 capacidad residual
3.11.1 calculo de la capacidad residual del proceso
3.11.2 calculo de la capacidad residual del proponente
formato 5 capacidad residual
crp >= crpc
```

Archivo nuevo sugerido: `backend/app/services/tender_requirements/residual_capacity_extraction.py`.

Reutilizar:

- `normalize_text`, `_snippet`, `_item` de `regex_extraction.py`
- POE y anticipo de `tender_summary` / US 1.4 cuando existan para **pre-calcular CRPC** en display.
- Plazo de ejecución de US 1.4 para elegir fórmula ≤12 vs >12 meses.

#### D. Enriquecimiento LLM (opcional, fase 1.8.2)

Solo si regex devuelve sección vacía o incompleta:

- Excerpt §3.11 (~3.000 caracteres).
- Prompt scoring-only style: no inventar CRPC; citar evidencia.
- Validar que mencione CRP y CRPC.

Costo: 1 llamada condicional (~misma magnitud que fallback de puntaje).

#### E. Frontend

`TenderDetailPanel.tsx`:

- Mostrar sección `capacidad_residual` **solo** si `contractKind` es `ejecucion_obra` o `estudios_disenos_y_obra`.
- Tarjetas: regla CRP ≥ CRPC, CRPC estimada (si hay POE), tabla de factores E/CF/CT, enlace a Formato 5.
- No mostrar en filtros de interventoría / estudios puros.

#### F. Versión y caché

- `EXTRACTION_VERSION` bump al implementar.
- Invalidar caché si obra pública sin ítems `capacidad_residual` pero pliego contiene `3.11 capacidad residual`.

---

## CRITERIOS DE ACEPTACIÓN (fase 1.8.1)

1. **LP-009 / Villa María III:** extrae §3.11, factores 120/40/40, Formato 5, regla CRP ≥ CRPC.
2. **Interventoría (ej. CCE):** no aparece sección capacidad residual.
3. **Estudios y diseños** (concurso méritos sin obra pública): no aparece.
4. **Estudios, diseños y obra** (modalidad obra pública): sí aparece.
5. Tests unitarios con fragmento `OBRA_DOCUMENTO_BASE_RESIDUAL_SAMPLE`.
6. CRPC display usa POE de US 1.4 cuando el pliego no repite el valor numérico.

---

## PLAN DE IMPLEMENTACIÓN

| Paso | Tarea | Estimación |
|------|-------|------------|
| 1 | `residual_capacity_extraction.py` + tests con Villa María §3.11 | 1 día |
| 2 | Registrar sección en `SECTION_DEFINITIONS` + `service.py` con gate `ContractKind` | 0.5 día |
| 3 | Merge POE/anticipo/plazo desde `tender` / summary para CRPC display | 0.5 día |
| 4 | UI `TenderDetailPanel` + orden de ítems | 0.5 día |
| 5 | LLM fallback opcional (1.8.2) | 0.5 día |
| 6 | QA manual LP-009 + una obra sin estudios + una interventoría | 0.5 día |

**Total MVP regex:** ~3 días.

---

## REFERENCIAS NORMATIVAS

- Decreto 1082 de 2015: arts. 2.2.1.1.1.3.1, 2.2.1.1.1.6.4.
- [Guía CCE — Capacidad residual (GI-22)](https://www.colombiacompra.gov.co/manuales-guias-y-pliegos-tipo/manuales-y-guias).
- Documento base — Licitación de obra pública de infraestructura social (§3.11, Formato 5).

---

## RELACIÓN CON OTRAS US

| US | Relación |
|----|----------|
| 1.4 Variables licitación | POE, anticipo, plazo → CRPC |
| 1.5 Indicadores financieros | CF en CRP reutiliza liquidez de §3.6; no duplicar Matriz 2 |
| 1.5.3 Gap analysis (futuro) | CRP empresa vs CRPC proceso |
