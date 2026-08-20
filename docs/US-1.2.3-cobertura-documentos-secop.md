# US 1.2.3 — Mejorar cobertura de documentos clave SECOP

## USER STORY

Ampliar la detección y extracción de documentos clave (pliego de condiciones, anexo técnico, presupuesto) cuando SECOP los publica con nombres no estándar o en formatos que hoy no procesamos, y comunicar con claridad al usuario por qué una licitación no tiene documentos archivados.

**As a** sistema de LicitIA  
**Quiero** clasificar mejor los archivos de SECOP y reprocesar licitaciones que quedaron sin documentos por reglas demasiado estrictas  
**Para** maximizar la cobertura real del histórico archivado en R2 y reducir falsos negativos en el dashboard

---

## BACKGROUND

Tras cerrar **US 1.2.2** (backfill histórico + R2), la validación manual con 3 licitaciones reveló que el pipeline técnico funciona, pero la **cobertura efectiva** queda limitada por:

| Limitación | Ejemplo real (prod) |
|------------|---------------------|
| **SECOP incompleto** | `CVC LP 008 2026`: pliego y anexo sí; presupuesto no publicado en `dmgg-8hin` |
| **Archivos empaquetados** | `El Agrado`: pliego/anexo probablemente dentro de `.rar`; solo se archivó presupuesto |
| **Clasificador literal** | `SPL-LP-004-2026`: existe `PROYECTO DE PLIEGOS.pdf` pero se clasifica como `otro` → 0 docs en UI |
| **UX ambigua** | Mensaje genérico: *"pendiente de extracción o no disponible en SECOP"* sin distinguir causa |

Estado actual en producción (referencia):

- ~215 licitaciones en `tenders`
- ~209 con al menos un documento tras backfill
- ~6 sin documentos (mezcla de: sin archivos en SECOP, sin clasificar, o dentro de comprimidos)
- Clasificación en `secop_document_filters.py` por keywords exactos en nombre/descripción

---

## SOLUCIÓN

### Fase A — Ampliar clasificador (prioridad alta)

Extender `_KEYWORD_RULES` en `secop_document_filters.py` con variantes frecuentes en SECOP Colombia:

**Pliego de condiciones**

- `proyecto de pliego`, `proyecto de pliegos`, `proyecto pliego`
- `pliegos definitivos`, `prepliego`, `documento base`
- `estudio previo` (opcional: solo si no compite con anexo; evaluar en tests)

**Anexo técnico**

- `anexos de proyecto`, `anexo de proyecto`
- `analisis del sector`, `análisis del sector`
- `especificaciones tecnicas`, `especificaciones generales`

**Presupuesto**

- `ppto`, `presupuesto oficial`, `formulario presupuesto`, `formul1 presupuesto`
- `analisis de precios`, `apu` (ya parcialmente cubierto)

Reglas:

- Mantener orden de prioridad (pliego > anexo > presupuesto) para evitar doble clasificación incorrecta.
- Añadir tests unitarios por cada keyword nueva con casos reales de las 3 licitaciones de prueba.
- Documentar keywords en README o en docstring del módulo.

### Fase B — Reprocesar licitaciones “sin docs”

Tras desplegar el clasificador mejorado:

1. Script `scripts/reset_document_extraction_attempts.py`:
   - Resetea `documents_extraction_attempted_at = NULL` en licitaciones **sin filas en `tender_documents`**.
   - Opción `--external-id` / `--reference` para casos puntuales.
   - `--dry-run` con conteo previo.

2. Ejecutar backfill acelerado existente (`backfill_documents.py`) para re-extraer hacia R2.

2b. Ejecutar re-sincronización incremental (`resync_documents.py`) sobre licitaciones **ya procesadas** para añadir documentos que el clasificador anterior omitió sin borrar filas existentes.

3. Registrar métricas antes/después: licitaciones con docs, docs por tipo, errores.

### Fase C — Mejorar UX en frontend

En `TenderDetailPanel`, distinguir estados:

| Estado | Condición | Mensaje sugerido |
|--------|-----------|------------------|
| **Con documentos** | `documents.length > 0` | Listado actual |
| **Procesada sin docs** | `attempted_at` set, 0 docs | *"No se encontraron documentos clave en SECOP para esta licitación."* |
| **Pendiente** | `attempted_at` null, 0 docs | *"Extracción de documentos pendiente."* |

Requiere exponer `documents_extraction_attempted_at` (o un enum `document_extraction_status`) en `TenderResponse` del API.

### Fase D — Fuera de alcance de esta US

Ver **[US 1.2.4 — Extracción ZIP/RAR](US-1.2.4-extraccion-documentos-zip-rar.md)** (descompresión e inspección de contenido interno).

- Re-ingesta SECOP (US 1.1).
- Extracción de texto / análisis de PDFs (US 1.2.5).

---

## CRITERIOS DE ACEPTACIÓN

**GIVEN** que R2 y el backfill histórico están operativos (US 1.2.1 + 1.2.2)  
**WHEN** se despliega el clasificador ampliado y se ejecuta el reproceso  
**THEN**

1. `SPL-LP-004-2026` (Corpoamazonia) archiva al menos el pliego (`PROYECTO DE PLIEGOS.pdf`) y se puede descargar desde el frontend.
2. Las keywords nuevas tienen tests en `test_secop_document_filters.py` (≥ 10 casos incluyendo las 3 licitaciones de prueba).
3. El script de reset + backfill documentado en README reprocesa licitaciones sin docs sin duplicar filas (`uq_tender_document`).
4. El panel de detalle muestra mensaje diferenciado para *pendiente* vs *procesada sin docs*.
5. Casos donde SECOP genuinamente no publica el archivo (ej. presupuesto Palmira) siguen mostrando *procesada sin docs* — no error del sistema.
6. Re-ejecutar extracción sobre licitación ya archivada es idempotente (sin duplicados en BD ni R2).

---

## DEFINICIÓN DE HECHO (DoD)

- [ ] Keywords ampliadas en `secop_document_filters.py` con tests verdes
- [ ] Script `reset_document_extraction_attempts.py` + README
- [ ] Reproceso ejecutado en prod y métricas antes/después registradas
- [ ] Campo de estado de extracción expuesto en API y consumido en frontend
- [ ] Validación manual de las 3 licitaciones de prueba documentada
- [ ] `SPL-LP-004-2026` con ≥ 1 documento descargable

---

## DEPENDENCIAS

| US | Relación |
|----|----------|
| 1.2 | Pipeline de extracción y clasificación |
| 1.2.1 | Almacenamiento R2 |
| 1.2.2 | Backfill histórico y `documents_extraction_attempted_at` |
| 1.3 | UI de documentos (mensajes a mejorar) |

---

## NOTAS OPERATIVAS

**Reproceso sugerido en prod:**

```bash
cd backend
PYTHONPATH=. python scripts/reset_document_extraction_attempts.py --dry-run
PYTHONPATH=. python scripts/reset_document_extraction_attempts.py
PYTHONPATH=. python scripts/backfill_documents.py --batch-size 25
PYTHONPATH=. python scripts/resync_documents.py --dry-run
PYTHONPATH=. python scripts/resync_documents.py --batch-size 25
```

**Impacto estimado:** +5–15 % licitaciones con al menos un documento (principalmente las clasificadas como `otro` con nombres alternativos). No resuelve archivos dentro de `.rar`/`.zip` (US 1.2.4).

**Riesgos:**

- Falsos positivos (ej. `estudio previo` clasificado como pliego cuando es otro tipo de estudio).
- Mitigación: tests con casos reales + orden de reglas + revisión manual de muestra post-deploy.

---

**Siguiente en roadmap:** [US 1.2.4 — Extracción ZIP/RAR](US-1.2.4-extraccion-documentos-zip-rar.md)
