# US 1.5 — Analizador de requisitos de participación (experiencia, indicadores financieros y habilitación)

## USER STORY

**As a** personal de licitaciones  
**Quiero** ver en el detalle de cada licitación los requisitos habilitantes que exige el proceso (experiencia general, experiencia específica, indicadores financieros, requisitos legales y condiciones especiales)  
**Para** saber qué se exige, evaluar si mi empresa cumple y detectar qué me falta para participar.

---

## BACKGROUND

Hoy LicitIA muestra:

- Metadatos SECOP y **información general** del contrato (US 1.4).
- Documentos clave descargables (pliego, anexo, presupuesto — US 1.3).
- **Matching de similitud** entre el objeto de la licitación y el portafolio de experiencias de la empresa.

Eso **no responde** la pregunta operativa del licitador: *¿cumplo los mínimos que el pliego exige para ser habilitado?*

En procesos colombianos de infraestructura, los requisitos suelen estar dispersos en:

| Fuente | Contenido típico |
|--------|------------------|
| **Pliego de condiciones** | Experiencia general, solvencia, habilitación legal, fórmulas de puntaje, requisitos especiales |
| **Anexo técnico** | Experiencia específica, alcance, códigos de actividad / sector, criterios técnicos de acreditación |
| **Matriz 1** (cuando existe) | Detalle de experiencia, % mínimo, contratos de referencia |
| **Matriz 2** (cuando existe) | Indicadores financieros y organizacionales, umbrales numéricos |

Estado actual en el código:

- No hay extracción de requisitos desde pliego/anexo.
- Matrices y formularios habilitantes no son tipo documental archivado (aparecen como `otro` o dentro de ZIP/RAR).
- No hay modelo de datos de requisitos ni API dedicada.
- No hay datos financieros de la empresa para comparar índices (solo `company_experiences`).
- El matching actual compara **similitud semántica**, no **cumplimiento de umbrales**.

**Deuda técnica relacionada:** US 1.2.5 (clasificación por contenido PDF) queda pausada; la carga manual (US 1.2.6) cubre documentos faltantes mientras tanto.

---

## OBJETIVO

Extraer, estructurar y presentar los **requisitos de participación** de cada licitación a partir de sus documentos, con trazabilidad a la fuente y estados claros cuando un dato no se pudo obtener.

### Alcance por fases

| Fase | Entregable | Incluye cumplimiento automático |
|------|------------|----------------------------------|
| **1.5.1 MVP** | Mostrar requisitos extraídos de pliego + anexo | No |
| **1.5.2** | Incluir Matriz 1 / Matriz 2 cuando existan en SECOP | No |
| **1.5.3** | Gap analysis: semáforo cumple / no cumple / revisar | Sí (parcial) |
| **1.5.4** | Requisitos especiales (mocho, mujer, PYME, emprendimiento) | Sí (parcial) |

**Esta US define la épica completa; el cierre de Jira para MVP corresponde a la fase 1.5.1.**

---

## SOLUCIÓN

### Fase 1.5.1 — Extracción y visualización (MVP)

#### A. Fuentes documentales

Prioridad de lectura por licitación:

1. `pliego_condiciones` archivado en R2 (US 1.2).
2. `anexo_tecnico` archivado en R2.
3. Si falta alguno: estado `documento_no_disponible` en la sección afectada (sin inventar datos).

> Matrices y formularios adicionales quedan para fase 1.5.2.

#### B. Extracción de texto

- Reutilizar `tender_summary/pdf_text.py` y patrones de `document_content_classification.py`.
- PDF: texto completo o secciones relevantes (cap a ~40 páginas / 80.000 caracteres por documento).
- Si el PDF no tiene capa de texto: marcar `no_extraible` y sugerir revisión manual.

#### C. Extracción estructurada (híbrida)

**Paso 1 — Segmentación por secciones** (regex / headings):

- `experiencia general`
- `experiencia específica` / `experiencia relacionada`
- `solvencia económica y financiera` / `indicadores financieros`
- `capacidad jurídica` / `requisitos legales`
- `habilitación` / `requisitos de participación`
- `puntaje` / `evaluación` / `fórmula`

**Paso 2 — Parser de campos** (regex para patrones colombianos frecuentes):

- Porcentajes (`30%`, `treinta por ciento`).
- Montos (`$`, `SMMLV`, `salarios mínimos`).
- Plazos (`últimos 5 años`, `desde 2020`).
- Códigos (`código`, `actividad`, `UNSPSC`, referencias RUP sectoriales cuando aparezcan en texto).

**Paso 3 — LLM con schema JSON** (fallback cuando regex no alcanza):

- Modelo: `gpt-4o-mini` (mismo criterio que US 1.4).
- Entrada: texto de sección + metadatos de licitación (`object_text`, `amount`, `contract_kind`).
- Salida: schema validado (ver abajo).
- Solo persistir campos con `confidence >= 0.70` o evidencia textual citada.

#### D. Persistencia y API

- Nueva tabla `tender_requirements` **o** bloque `requirements_json` en extensión de `tender_summaries` (decisión de implementación: preferir tabla dedicada si el JSON crece > 50 KB).
- Endpoint: `GET /api/v1/tenders/{id}/requirements`
- Query `?refresh=true` fuerza recomputo.
- Job batch: `scripts/extract_tender_requirements.py` (`--dry-run`, `--batch-size`, `--reference`).

#### E. Interfaz

Nueva sección en `TenderDetailPanel`: **Requisitos de participación**, debajo de **Información general**.

Agrupación en acordeones o tiles:

1. **Experiencia general**
2. **Experiencia específica** (incluye códigos / actividades cuando existan)
3. **Indicadores financieros y solvencia**
4. **Requisitos legales y habilitación**
5. **Otros requisitos relevantes** (texto libre estructurado)

Cada ítem muestra:

- Valor extraído (texto o número formateado).
- Estado: `extraido` | `no_encontrado` | `revisar` | `documento_no_disponible`.
- Fuente: `pliego` | `anexo` (+ página o fragmento si está disponible).
- Enlace al documento fuente (descarga US 1.3).

En MVP **no** se muestra semáforo de cumplimiento (fase 1.5.3).

---

### Fase 1.5.2 — Matrices SECOP

- Ampliar pipeline documental para archivar **Matriz 1** (experiencia) y **Matriz 2** (indicadores) cuando aparezcan en SECOP o dentro de ZIP/RAR.
- Nuevos tipos: `matriz_experiencia`, `matriz_indicadores` (o reutilizar `otro` con `classification_source`).
- Parser XLSX prioritario para matrices en Excel; PDF como fallback.

### Fase 1.5.3 — Gap analysis (cumplimiento)

- Modelo `company_financials` (índices, activos, pasivos, patrimonio, ingresos — períodos).
- Servicio `requirements_compliance.py`:
  - Compara experiencia específica vs `company_experiences` (monto acumulado, ventana temporal, entidad).
  - Compara indicadores vs `company_financials`.
- UI: badge `Cumple` / `No cumple` / `Revisar` por requisito + texto “Te falta…”.

### Fase 1.5.4 — Requisitos especiales

- Extracción de condiciones de participación preferencial o restrictiva:
  - Emprendimiento / PYME / mipyme
  - Mujer / género
  - “Mocho” y otras restricciones de consorcio/unión temporal
  - Reservas de cupo cuando apliquen

---

## MAPA DE CAMPOS (MVP — fase 1.5.1)

| Prioridad | Grupo | Campo | Fuente principal |
|-----------|-------|-------|------------------|
| P0 | Experiencia general | Descripción del requisito | Pliego |
| P0 | Experiencia general | % mínimo del presupuesto oficial | Pliego |
| P0 | Experiencia general | Monto mínimo absoluto (si aplica) | Pliego |
| P0 | Experiencia general | Ventana temporal (ej. últimos N años) | Pliego |
| P0 | Experiencia general | Cómo se acredita (documentos, matriz) | Pliego |
| P0 | Experiencia específica | Descripción / objeto exigido | Anexo (+ pliego) |
| P0 | Experiencia específica | % o monto mínimo específico | Anexo |
| P0 | Experiencia específica | Códigos de actividad / sector / UNSPSC (si mencionados) | Anexo |
| P0 | Financiero | Indicadores exigidos (liquidez, endeudamiento, capital de trabajo, etc.) | Pliego |
| P0 | Financiero | Umbrales numéricos por indicador | Pliego / Matriz 2 (fase 1.5.2) |
| P0 | Financiero | Fórmula de calificación / puntaje asignado | Pliego |
| P1 | Legal | Inscripción RUP vigente | Pliego |
| P1 | Legal | Capacidad jurídica, representación legal | Pliego |
| P1 | Legal | Certificados y anexos legales exigidos | Pliego |
| P1 | Habilitación | Habilitaciones específicas para contratar (licencias, registros) | Pliego / anexo |
| P2 | Evaluación | Puntaje máximo por criterio habilitante | Pliego |
| P2 | Evaluación | Reglas de asignación de puntaje | Pliego |
| P2 | Otros | Requisitos adicionales detectados | Pliego / anexo |

---

## SCHEMA JSON (extracción LLM — referencia)

```json
{
  "tender_external_id": "CO1.REQ.XXXX",
  "extracted_at": "2026-08-25T12:00:00Z",
  "extraction_version": "1.5.1",
  "sections": {
    "experiencia_general": {
      "status": "extraido",
      "items": [
        {
          "key": "min_percentage_budget",
          "label": "Porcentaje mínimo del presupuesto",
          "value": "30%",
          "numeric_value": 30,
          "unit": "percent",
          "confidence": 0.92,
          "source_document": "pliego_condiciones",
          "evidence": "experiencia general equivalente al treinta por ciento (30%) del presupuesto oficial",
          "page_hint": 45
        }
      ]
    },
    "experiencia_especifica": {
      "status": "extraido",
      "items": [
        {
          "key": "specific_scope",
          "label": "Alcance exigido",
          "value": "Interventoría de obras viales en zonas urbanas",
          "confidence": 0.88,
          "source_document": "anexo_tecnico",
          "evidence": "..."
        },
        {
          "key": "activity_codes",
          "label": "Códigos de actividad",
          "value": ["4321", "7112"],
          "confidence": 0.75,
          "source_document": "anexo_tecnico",
          "evidence": "..."
        }
      ]
    },
    "indicadores_financieros": {
      "status": "revisar",
      "items": [
        {
          "key": "liquidez_corriente",
          "label": "Índice de liquidez corriente",
          "operator": ">=",
          "threshold": 1.0,
          "confidence": 0.81,
          "source_document": "pliego_condiciones",
          "evidence": "..."
        }
      ]
    },
    "requisitos_legales": {
      "status": "extraido",
      "items": [
        {
          "key": "rup_vigente",
          "label": "Inscripción vigente en el RUP",
          "value": true,
          "confidence": 0.95,
          "source_document": "pliego_condiciones",
          "evidence": "..."
        }
      ]
    },
    "otros": {
      "status": "extraido",
      "items": []
    }
  },
  "warnings": ["PDF parcialmente ilegible en páginas 12-14"]
}
```

---

## API

### `GET /api/v1/tenders/{tender_id}/requirements`

**Respuesta 200** — cuerpo alineado con el schema anterior + metadatos de extracción.

**Respuesta 404** — licitación no existe.

**Respuesta 422** — licitación sin pliego ni anexo archivados (mensaje accionable: “Sube los documentos faltantes”).

**Query params:**

| Param | Descripción |
|-------|-------------|
| `refresh=true` | Fuerza recomputo ignorando caché |

### Integración con jobs periódicos

Tras `extract_documents_for_pending_tenders()`, encolar extracción de requisitos para licitaciones con pliego **o** anexo disponibles (flag `TENDER_REQUIREMENTS_EXTRACTION_ENABLED`).

---

## CRITERIOS DE ACEPTACIÓN

### MVP (fase 1.5.1)

**GIVEN** que la licitación tiene al menos pliego o anexo archivado en R2 (US 1.2 / carga manual US 1.2.6)  
**AND** la extracción de requisitos está habilitada  
**WHEN** el personal de licitaciones abre el detalle de la licitación en el dashboard  
**THEN**

- Ve la sección **Requisitos de participación** con los grupos: experiencia general, experiencia específica, indicadores financieros, requisitos legales y otros (si aplica).
- Cada grupo muestra ítems estructurados o el estado `no_encontrado` / `documento_no_disponible` (nunca texto inventado).
- Los ítems extraídos incluyen referencia al documento fuente (pliego o anexo) y fragmento de evidencia cuando la confianza es ≥ 0.70.
- Si falta pliego y anexo, la UI indica qué documentos subir (reutiliza slots de US 1.2.6).
- `GET /api/v1/tenders/{id}/requirements` devuelve el mismo contenido que muestra la UI.
- Reproceso idempotente: segunda ejecución sin `refresh` devuelve caché; con `refresh` actualiza sin duplicar filas.
- Tests unitarios ≥ 10 casos (regex + normalización + integración con fixture de texto).

### Validación manual (muestra — gate de cierre MVP)

| Licitación / fixture | Resultado esperado |
|----------------------|-------------------|
| `verificacion-nivel3/desde-secop-anexo-lp013.pdf` + pliego asociado | Experiencia específica e indicadores visibles con evidencia |
| Licitación con pliego estándar INVIAS/IDU | Experiencia general con % y ventana temporal |
| Licitación solo con presupuesto (sin pliego/anexo) | Sección con estado `documento_no_disponible` |
| Pliego sin capa de texto (escaneado) | `no_extraible` + aviso de revisión manual |

### Fases posteriores (no bloquean cierre MVP)

| Fase | Criterio adicional |
|------|-------------------|
| 1.5.2 | Matriz 1/2 archivada y parseada cuando existe en SECOP |
| 1.5.3 | Semáforo de cumplimiento vs experiencias e indicadores empresa |
| 1.5.4 | Requisitos especiales (PYME, mujer, mocho) visibles cuando el pliego los mencione |

---

## FUERA DE ALCANCE (MVP)

- Semáforo automático de cumplimiento (fase 1.5.3).
- Carga y gestión de estados financieros de la empresa (fase 1.5.3).
- OCR de PDFs escaneados.
- Extracción en tiempo real al abrir el modal (solo job batch + caché; `refresh` bajo demanda).
- 100 % de precisión sin revisión humana en casos ambiguos.
- Interpretación jurídica vinculante (el sistema **informa**, no **certifica** habilitación).
- Sustituir el matching de similitud existente (complementa, no reemplaza).

---

## DEFINICIÓN DE HECHO (DoD)

### Fase 1.5.1 (MVP)

- [ ] Servicio `app/services/tender_requirements/` con extracción híbrida (regex + LLM).
- [ ] Modelo / caché `tender_requirements` (o extensión acordada de `tender_summaries`).
- [ ] Endpoint `GET /api/v1/tenders/{id}/requirements`.
- [ ] Script `scripts/extract_tender_requirements.py` documentado en README.
- [ ] Sección **Requisitos de participación** en `TenderDetailPanel`.
- [ ] Flag `TENDER_REQUIREMENTS_EXTRACTION_ENABLED`.
- [ ] Tests ≥ 10 casos.
- [ ] Validación manual de muestra (≥ 3 licitaciones) documentada en ticket de cierre.

### Épica completa (1.5.1 → 1.5.4)

- [ ] Todas las fases anteriores cerradas.
- [ ] Cobertura documental Matriz 1/2 integrada con US 1.2.x.
- [ ] Gap analysis operativo con datos empresa.

---

## DEPENDENCIAS

| US / componente | Relación |
|-----------------|----------|
| 1.2 / 1.2.1 | Pliego y anexo archivados en R2 |
| 1.2.6 | Carga manual cuando falten documentos |
| 1.3 | Descarga de documentos fuente desde UI |
| 1.4 | Patrón de extracción, caché y sección en `TenderDetailPanel` |
| 1.2.4 | Prerequisito para Matriz 1/2 dentro de ZIP (fase 1.5.2) |
| 1.2.5 | Deuda técnica; no bloquea MVP si hay pliego/anexo por nombre o carga manual |
| Experiencias empresa | Input para fase 1.5.3 (no MVP) |

---

## NOTAS OPERATIVAS

### Variables de entorno sugeridas

```bash
TENDER_REQUIREMENTS_EXTRACTION_ENABLED=true
TENDER_REQUIREMENTS_USE_LLM=true
TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE=0.70
TENDER_REQUIREMENTS_MAX_PDF_PAGES=40
TENDER_REQUIREMENTS_MAX_CHARS=80000
```

### Reproceso sugerido

```bash
cd backend
PYTHONPATH=. python scripts/extract_tender_requirements.py --dry-run
PYTHONPATH=. python scripts/extract_tender_requirements.py --batch-size 25
PYTHONPATH=. python scripts/extract_tender_requirements.py --reference LP-013-2026
```

### Impacto estimado

- **Valor alto** para usuarios: reduce lectura manual del pliego (30–60 min → vista estructurada en segundos).
- **Coste LLM:** ~1–2 llamadas por licitación (pliego + anexo); acotar con regex-first.
- **Riesgo principal:** variabilidad de redacción entre entidades → evidencia obligatoria + estado `revisar`.

### Título sugerido en Jira

`1.5 [Backend+Frontend] Requisitos de participación — experiencia, indicadores y habilitación (MVP 1.5.1)`

---

## DIFERENCIA CON MATCHING DE EXPERIENCIA ACTUAL

| Dimensión | Matching actual | US 1.5 |
|-----------|-----------------|--------|
| Pregunta | ¿Se parece a lo que hacemos? | ¿Qué exige el pliego y cumplo? |
| Fuente | `object_text` SECOP | Pliego + anexo (+ matrices) |
| Salida | Score 0–1 en listado | Requisitos estructurados en detalle |
| Datos empresa | Portafolio de obras | Experiencias + financieros (fase 1.5.3) |

Ambos conviven: el matching prioriza licitaciones relevantes; US 1.5 profundiza en habilitación una vez el usuario abre el detalle.
