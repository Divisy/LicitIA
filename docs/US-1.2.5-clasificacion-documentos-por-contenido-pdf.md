# US 1.2.5 — Clasificación de documentos SECOP por contenido PDF

## USER STORY

Clasificar documentos clave de licitaciones (pliego de condiciones, anexo técnico, presupuesto) analizando el **contenido** del archivo cuando el nombre en SECOP no es suficiente para el clasificador por filename (US 1.2.3).

**As a** sistema de LicitIA  
**Quiero** extraer texto de las primeras páginas de cada PDF candidato y determinar su tipo documental con keywords o LLM  
**Para** archivar pliego, anexo y presupuesto aunque la entidad use nombres no estándar en SECOP (`PROYECTO DE-PLIEGO`, `ANEXO 2`, etc.)

---

## BACKGROUND

Tras US 1.2.3 (keywords en nombre de archivo) y US 1.2.4 (ZIP/RAR), seguirán existiendo licitaciones con documentos publicados en SECOP que **no se clasifican por nombre**:

| Caso real | Archivo en SECOP | Problema del clasificador por nombre |
|-----------|------------------|--------------------------------------|
| Tibasosa `PC-MT-LP-003-2026` | `PROYECTO DE-PLIEGO.pdf` | Guión atípico (`DE-PLIEGO`) u omisión de keywords |
| Tibasosa | `ANEXO 2.pdf` | Solo número de anexo, sin "técnico" |
| Varias entidades | `ESTUDIO PREVIO.pdf`, `VIABILIDAD.pdf` | Nombre genérico; el contenido sí dice "pliego" o "condiciones" |

En `dmgg-8hin`, el campo `descripci_n` suele repetir el nombre del archivo — **no aporta metadatos extra**. La señal fiable está dentro del PDF.

Estado actual:

- Pipeline descarga y guarda en R2 solo archivos ya clasificados como clave (US 1.2 + 1.2.1).
- Archivos clasificados como `otro` se **descartan** aunque sean pliego/anexo/presupuesto.
- OpenAI ya integrado en el backend (`classification.py`) para relevancia de licitaciones.

---

## SOLUCIÓN

### Fase A — Extracción de texto (PDF)

- Tras listar documentos SECOP para un `portfolio_id`, para cada archivo **no clasificado** por nombre (tipo `otro`) con extensión PDF (y opcionalmente DOCX/XLSX en fase posterior):
  - Descargar a staging temporal.
  - Extraer texto de las **primeras 1–2 páginas** (librería: `pypdf`, `pdfplumber` o similar).
  - Limitar tamaño de texto enviado a clasificador (ej. 4.000 caracteres).

### Fase B — Clasificación por contenido

**Modo 1 — Keywords en contenido (default, sin costo LLM):**

- Aplicar reglas similares a US 1.2.3 sobre el texto extraído (`pliego de condiciones`, `anexo técnico`, `presupuesto oficial`, `análisis del sector`, etc.).
- Umbral: al menos N coincidencias o frase ancla en primera página.

**Modo 2 — LLM (fallback o configurable):**

- Si keywords en contenido no clasifican, llamar OpenAI con schema JSON:
  ```json
  { "document_type": "pliego_condiciones|anexo_tecnico|presupuesto|otro", "confidence": 0.0-1.0, "evidence": "fragmento citado" }
  ```
- Solo persistir si `confidence >= umbral` (ej. 0.75).

### Fase C — Integración con pipeline de extracción

- Flujo por licitación:
  1. Clasificar por **nombre** (US 1.2.3) → descargar y subir a R2 los key docs.
  2. Para archivos `otro` en PDF: clasificar por **contenido** → si es key doc, descargar y subir.
  3. Marcar `documents_extraction_attempted_at` (US 1.2.2).
- Guardar en `tender_documents` (o campo opcional `classification_source`: `filename` | `content_keywords` | `content_llm`).

### Fase D — Job y reproceso

- Flag `DOCUMENT_CONTENT_CLASSIFICATION_ENABLED` (default `false` en primer deploy).
- Script `scripts/reclassify_documents_by_content.py`:
  - `--dry-run`, `--limit`, `--reference`
  - Procesa licitaciones con docs faltantes o reprocesa candidatos `otro` desde SECOP.
- Métricas: candidatos analizados, nuevos key docs, costo LLM estimado.

---

## CRITERIOS DE ACEPTACIÓN

**GIVEN** que R2 está configurado (US 1.2.1), el backfill completado (US 1.2.2) y el clasificador por nombre desplegado (US 1.2.3)  
**AND** existen licitaciones con archivos PDF en SECOP clasificados como `otro` por nombre pero que son documentos clave por contenido  
**WHEN** se habilita la clasificación por contenido y se ejecuta extracción o reproceso  
**THEN**

- Los PDF cuyo texto en las primeras 1–2 páginas indique pliego, anexo técnico o presupuesto se archivan en R2 y aparecen en `tender_documents`.
- Caso de validación: `PC-MT-LP-003-2026` (Tibasosa) — `PROYECTO DE-PLIEGO.pdf` se clasifica y descarga aunque el nombre no matchee keywords actuales.
- El pipeline **no descarga** archivos que sigan siendo `otro` tras análisis de contenido (formularios, CDP, avisos).
- Toda fila en `tender_documents` sigue teniendo blob en R2; reproceso idempotente (`uq_tender_document`).
- Con `DOCUMENT_CONTENT_CLASSIFICATION_ENABLED=false`, el comportamiento es idéntico al actual (solo clasificación por nombre).
- Logs registran fuente de clasificación (`filename` / `content_keywords` / `content_llm`) y confianza cuando aplique.
- Límite de costo: modo LLM opcional; batch documentado con estimación de tokens por licitación.

### Validación manual (muestra — no único gate de cierre)

| Licitación | Resultado esperado |
|------------|-------------------|
| `PC-MT-LP-003-2026` (Tibasosa) | Pliego extraído por contenido si no lo cubre nombre |
| `SPL-LP-004-2026` (Corpoamazonia) | Pliego por contenido o nombre |
| Licitación con solo `CDP.pdf` | Sigue sin archivarse |

### Métricas globales (cierre)

- Aumento medible de `tenders_with_documents` y `document_rows` tras reproceso vs baseline post-1.2.3.
- `orphan_metadata_rows = 0` tras reconciliación.
- Muestra aleatoria ≥ 3 licitaciones preexistentes sin regresión en descargas.

---

## FUERA DE ALCANCE

- OCR de PDFs escaneados sin capa de texto (US futura).
- Clasificación de contenido dentro de ZIP/RAR sin extraer (US 1.2.4 prerequisito).
- Extracción de variables de negocio del PDF (valor, plazo, AIU — US 1.4).
- Clasificación en tiempo real al abrir el modal en frontend (solo job/script batch).
- 100 % de precisión sin revisión; campos con baja confianza pueden quedar sin archivar.

---

## DEFINICIÓN DE HECHO (DoD)

- [ ] US 1.2.3 y 1.2.4 desplegadas (o 1.2.4 explícitamente no bloqueante si se acota a PDF sueltos).
- [ ] Servicio `document_content_classification.py` con extracción de texto PDF (1–2 páginas).
- [ ] Clasificación por keywords en contenido + fallback LLM opcional con schema JSON.
- [ ] Integración en `extract_documents_for_tender` detrás de feature flag.
- [ ] Script `reclassify_documents_by_content.py` documentado en README.
- [ ] Tests unitarios con PDFs de fixture (texto conocido) ≥ 8 casos.
- [ ] Reproceso en prod con métricas antes/después documentadas.
- [ ] Validación manual de muestra (≥ 3 licitaciones) documentada en ticket de cierre.

---

## DEPENDENCIAS

| US | Relación |
|----|----------|
| 1.2 | Pipeline de descarga SECOP |
| 1.2.1 | Almacenamiento R2 |
| 1.2.2 | Tracking `documents_extraction_attempted_at` |
| 1.2.3 | Clasificador por nombre (se ejecuta antes que contenido) |
| 1.2.4 | ZIP/RAR (complementaria; no sustituye contenido PDF suelto) |
| 1.3 | UI de descarga de documentos |
| 1.4 | Extracción de variables (épica distinta; usa PDFs ya archivados) |

---

## NOTAS OPERATIVAS

**Variables de entorno sugeridas:**

```bash
DOCUMENT_CONTENT_CLASSIFICATION_ENABLED=true
DOCUMENT_CONTENT_CLASSIFICATION_USE_LLM=false   # true para fallback LLM
DOCUMENT_CONTENT_CLASSIFICATION_LLM_MIN_CONFIDENCE=0.75
DOCUMENT_CONTENT_CLASSIFICATION_MAX_PAGES=2
```

**Reproceso sugerido:**

```bash
cd backend
PYTHONPATH=. python scripts/reclassify_documents_by_content.py --dry-run
PYTHONPATH=. python scripts/reset_document_extraction_attempts.py   # solo sin docs, si aplica
PYTHONPATH=. python scripts/reclassify_documents_by_content.py --limit 50
```

**Impacto estimado:** +10–25 % licitaciones con los 3 tipos de documento (según muestra); mayor ganancia en entidades con nombres atípicos.

**Coste LLM (si habilitado):** ~1 llamada por PDF candidato `otro`; acotar con keywords-first para minimizar tokens.

**Riesgos:**

| Riesgo | Mitigación |
|--------|------------|
| PDF sin texto (escaneado) | Skip + log; OCR en US futura |
| Falso positivo (CDP clasificado como pliego) | Exclusiones en contenido + umbral confianza |
| Tiempo de job largo | Lote + flag + script offline |
| Costo OpenAI | Keywords primero; LLM solo fallback |

**Título sugerido en Jira:** `1.2.5 [Backend] Clasificación de documentos SECOP por contenido PDF`
