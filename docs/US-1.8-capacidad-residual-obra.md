# US 1.8 — Capacidad residual en licitaciones de obra pública

## USER STORY

**As a** constructor o personal de licitaciones de obra pública  
**Quiero** ver en el detalle de la licitación el requisito de capacidad residual (K de contratación), la CRPC del proceso y cómo acreditarla  
**Para** saber si mi empresa tiene cupo para asumir el contrato junto con los demás en ejecución, sin confundirlo con los indicadores financieros de la Matriz 2.

---

## BACKGROUND

Hoy LicitIA permite (US 1.5):

- Extraer y mostrar **indicadores financieros y solvencia** desde el pliego y la Matriz 2 (liquidez, endeudamiento, cobertura de intereses, capital de trabajo, ROE, ROA).
- Clasificar el tipo de proceso en el dashboard: **ejecución de obra**, **estudios, diseños y obra**, interventoría, estudios y diseños, etc. (`contract_kind.py`).

**Lo que no existe:**

- Extracción ni visualización de la **capacidad residual** (§3.11 del documento base obra, Formato 5).
- Diferenciación clara entre *índices de la Matriz 2* y *K de contratación* en la UI.

**Marco normativo (Colombia):**

| Concepto | Definición |
|----------|------------|
| **Capacidad residual / K** | Aptitud del oferente para ejecutar el contrato sin que otros compromisos contractuales afecten su cumplimiento (Decreto 1082 de 2015, art. 2.2.1.1.1.3.1) |
| **CRPC** | Capacidad residual **del proceso** (calcula la entidad) |
| **CRP** | Capacidad residual **del proponente** (acredita el oferente) |
| **Regla habilitante** | **CRP ≥ CRPC** |

**Fórmulas documento base obra (§3.11):**

- Plazo ≤ 12 meses: `CRPC = POE − Anticipo`
- Plazo > 12 meses: `CRPC = (POE − Anticipo) / Plazo_estimado × 12`
- Proponente: `CRP = CO × [(E + CT + CF) / 100] − SCE`

**Factores CRP (ej. documento base CCE):**

| Factor | Puntaje máx. | Acreditación |
|--------|--------------|--------------|
| Experiencia (E) | 120 | Formato 5, contratos segmento 72 |
| Capacidad financiera (CF) | 40 | Índice de liquidez (§3.6) |
| Capacidad técnica (CT) | 40 | Profesionales vinculados (Formato 5) |
| Capacidad de organización (CO) | multiplicador | Metodología CCE (Guía GI-22) |
| SCE | resta | Saldos de contratos en ejecución (Formato 5) |

**Alcance normativo:** la capacidad residual **solo aplica a contratos de obra pública** (Guía CCE GI-22). No aplica a interventoría, consultoría pura ni suministros.

**Flujo operativo del licitador (obra):**

1. Revisa indicadores financieros (Matriz 2) en LicitIA.
2. Debe además verificar si tiene **cupo residual** para el nuevo contrato (contratos en ejecución + capacidad técnica/financiera).
3. Hoy debe buscar manualmente el §3.11 y el Formato 5 en el pliego.

**Relación con otras US:**

| US | Relación |
|----|----------|
| 1.4 Variables licitación | POE, anticipo y plazo de ejecución alimentan el cálculo/display de CRPC |
| 1.5 Indicadores financieros | CF en CRP reutiliza liquidez de §3.6; sección separada, no mezclar con Matriz 2 |
| 1.5.3 Gap analysis (futuro) | Comparar CRP de la empresa vs CRPC del proceso |
| 1.7 Favoritas | El usuario puede marcar obras que luego revisa capacidad residual en detalle |

---

## OBJETIVO

Extraer y presentar la **capacidad residual (K)** en el panel de detalle de licitaciones de **obra pública**, con trazabilidad al pliego (§3.11) y estados claros cuando el dato no se encuentre.

### Alcance MVP (etiqueta Jira: BACKEND + FRONTEND)

| Incluye | No incluye (futuro) |
|---------|---------------------|
| Sección **Capacidad residual (K)** en requisitos | Calcular CRP de la empresa del usuario |
| Solo tipos `ejecucion_obra` y `estudios_disenos_y_obra` | Interventoría, estudios y diseños puros, otros procesos |
| Extracción regex de §3.11 (CRPC, CRP, factores E/CF/CT/CO/SCE) | Validar Formato 5 diligenciado |
| Display de CRPC estimada con POE/anticipo/plazo (US 1.4) | Integrar aplicativo Excel CCE |
| Formato 5 y regla CRP ≥ CRPC | Gap analysis / semáforo de cumplimiento |
| Tests unitarios + bump `EXTRACTION_VERSION` | LLM fallback (fase 1.8.2) |

---

## SOLUCIÓN

### A. Gate por tipo de proceso

La sección solo se extrae y muestra cuando:

```text
detect_contract_kind(tender) ∈ { ejecucion_obra, estudios_disenos_y_obra }
```

Equivalente SECOP: modalidad **«Licitación pública Obra Pública»**, excluyendo interventoría en el objeto.

### B. Nueva sección de requisitos

Clave: `capacidad_residual`  
Título UI: **Capacidad residual (K)**  
Separada de `indicadores_financieros` para no confundir Matriz 2 con §3.11.

**Ítems estructurados (MVP):**

| key | label | Contenido |
|-----|-------|-----------|
| `residual_summary` | Resumen | Qué es K y regla CRP ≥ CRPC |
| `crpc_formula` | CRPC del proceso | Fórmula según plazo + valores POE/anticipo si existen |
| `crp_formula` | CRP del proponente | `CO × [(E+CT+CF)/100] − SCE` |
| `factor_experiencia` | Experiencia (E) | Máx. 120 pts, Formato 5 |
| `factor_capacidad_financiera` | Capacidad financiera (CF) | Máx. 40 pts, liquidez |
| `factor_capacidad_tecnica` | Capacidad técnica (CT) | Máx. 40 pts, profesionales |
| `factor_organizacion` | Capacidad de organización (CO) | Rol multiplicador |
| `sce` | Contratos en ejecución (SCE) | Resta al CRP, Formato 5 |
| `proponente_plural` | Proponente plural | Suma CRP de integrantes |
| `accreditation_formato_5` | Cómo acreditar | Formato 5 + firmas |
| `habilitante_rule` | Regla de habilitación | CRP ≥ CRPC |

### C. Extracción (backend)

**Archivo nuevo:** `backend/app/services/tender_requirements/residual_capacity_extraction.py`

**Marcadores en pliego (documento base CCE obra):**

- `3.11 capacidad residual`
- `3.11.1 calculo de la capacidad residual del proceso`
- `3.11.2 calculo de la capacidad residual del proponente`
- `formato 5 capacidad residual`
- `crp` / `crpc`

**Integración:**

- Registrar en `SECTION_DEFINITIONS` y `EXTRACTORS` en `regex_extraction.py` / `service.py`.
- En `build_tender_requirements()`: invocar extractor solo si `ContractKind` es obra.
- Reutilizar POE, anticipo y plazo desde `tender_summary` / US 1.4 para **mostrar CRPC estimada** cuando el pliego no repita cifras.
- `EXTRACTION_VERSION` bump + invalidación de caché si obra pública tiene `3.11` en pliego pero sin ítems extraídos.

### D. Interfaz (frontend)

**Ubicación:** `TenderDetailPanel` → acordeón **Requisitos de participación**, después de *Indicadores financieros y solvencia*.

**Visibilidad:** solo si `contractKind === 'ejecucion_obra' || contractKind === 'estudios_disenos_y_obra'`.

**Presentación:**

- Tarjeta resumen: *“Debes acreditar CRP ≥ CRPC”*.
- CRPC estimada (si hay POE y anticipo de US 1.4).
- Tabla de factores E / CF / CT con puntajes máximos.
- Formato 5 y enlace al documento pliego (US 1.3).
- Estados: `extraido` | `no_encontrado` | `documento_no_disponible`.

### E. Archivos a tocar (estimación)

| Archivo | Cambio |
|---------|--------|
| `residual_capacity_extraction.py` | **Nuevo** — parser §3.11 |
| `regex_extraction.py` / `service.py` | Sección + gate `ContractKind` |
| `test_tender_requirements.py` | Tests con muestra Villa María §3.11 |
| `TenderDetailPanel.tsx` | Sección UI + gate por tipo |
| `client.ts` | Tipos sección `capacidad_residual` (si aplica) |

### F. Fase 1.8.2 (opcional, post-MVP)

- LLM fallback si regex no encuentra §3.11 (1 llamada condicional, mismo patrón que puntaje v1.9.6).
- Solo si excerpt contiene `capacidad residual` y faltan ítems clave.

---

## CRITERIOS DE ACEPTACIÓN

### MVP

**GIVEN** una licitación clasificada como **ejecución de obra** con pliego documento base CCE (ej. LP-009 Villa María III)  
**WHEN** el usuario abre el detalle y la sección de requisitos  
**THEN**

- Ve la sección **Capacidad residual (K)** separada de indicadores financieros.
- Ve la regla **CRP ≥ CRPC**, la fórmula CRPC y los factores E (120), CF (40), CT (40).
- Ve referencia al **Formato 5** y evidencia del §3.11.

**GIVEN** una licitación clasificada como **estudios, diseños y obra** (modalidad obra pública)  
**WHEN** el usuario abre requisitos  
**THEN**

- Ve la misma sección de capacidad residual que en ejecución de obra pura.

**GIVEN** una licitación de **interventoría**  
**WHEN** el usuario abre requisitos  
**THEN**

- **No** aparece la sección Capacidad residual (K).

**GIVEN** una licitación de **estudios y diseños** (concurso de méritos / consultoría, sin obra pública)  
**WHEN** el usuario abre requisitos  
**THEN**

- **No** aparece la sección Capacidad residual (K).

**GIVEN** que US 1.4 tiene POE y anticipo extraídos  
**WHEN** el pliego no repite el valor numérico de CRPC  
**THEN**

- La UI muestra CRPC estimada con la fórmula aplicada (POE − Anticipo, o proporcional si plazo > 12 meses).

**GIVEN** que el pliego de obra no contiene §3.11  
**WHEN** se extraen requisitos  
**THEN**

- La sección queda en estado `no_encontrado` sin inventar datos.

### Validación manual (gate de cierre)

| Paso | Resultado esperado |
|------|-------------------|
| LP-009 / Villa María III | Sección K con §3.11, factores 120/40/40, Formato 5 |
| Obra sin estudios en objeto | Sección K visible |
| Interventoría CCE | Sin sección K |
| Estudios puros (concurso méritos) | Sin sección K |
| Reabrir licitación tras deploy | Re-extracción con nueva `EXTRACTION_VERSION` |

---

## FUERA DE ALCANCE (MVP)

- Cálculo del CRP de la empresa contratista (requiere datos financieros internos).
- Carga o validación del Formato 5 diligenciado.
- Aplicativo Excel de Colombia Compra Eficiente embebido.
- Capacidad residual en procesos que no sean licitación de obra pública.
- Semáforo cumple / no cumple (US 1.5.3).

---

## DEFINICIÓN DE HECHO

- [ ] Extractor `residual_capacity_extraction.py` con tests unitarios.
- [ ] Sección `capacidad_residual` en API `GET /tenders/{id}/requirements`.
- [ ] Gate por `ContractKind` (solo obra y estudios+diseños+obra).
- [ ] UI en `TenderDetailPanel` con sección separada de indicadores financieros.
- [ ] CRPC display reutiliza POE/anticipo/plazo de US 1.4 cuando aplica.
- [ ] `EXTRACTION_VERSION` actualizada e invalidación de caché.
- [ ] Validación manual según tabla anterior.

---

## ESTIMACIÓN

| Ítem | Esfuerzo |
|------|----------|
| Extractor regex + tests (§3.11) | 1 d |
| Integración service + SECTION_DEFINITIONS + gate | 0,5 d |
| Merge POE/anticipo/plazo para CRPC display | 0,5 d |
| UI TenderDetailPanel | 0,5 d |
| QA manual (obra / interventoría / estudios) | 0,5 d |
| **Total MVP** | **~3 días** |

---

## TÍTULO JIRA SUGERIDO

`1.8 [Backend+Frontend] Capacidad residual (K) en licitaciones de obra pública — extracción §3.11 y UI (solo ejecución de obra y estudios, diseños y obra)`
