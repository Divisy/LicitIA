# US 1.2.4 — Extracción de documentos en archivos comprimidos (ZIP/RAR)

## USER STORY

Procesar archivos `.zip` y `.rar` publicados en SECOP para extraer y archivar documentos clave (pliego de condiciones, anexo técnico, presupuesto) que las entidades publican empaquetados en lugar de como archivos sueltos.

**As a** sistema de LicitIA  
**Quiero** descomprimir archivos comprimidos descargados desde SECOP y clasificar su contenido interno  
**Para** extraer pliego, anexo y presupuesto cuando no están disponibles como PDF/Excel individuales en el dataset `dmgg-8hin`

---

## BACKGROUND

Tras la **US 1.2.3** (clasificador ampliado), muchas licitaciones seguirán sin documentos clave porque la entidad los publica **dentro de comprimidos**, no como archivos sueltos en SECOP.

### Caso validado en producción

| Licitación | Entidad | Qué muestra LicitIA hoy | Qué hay en SECOP (`CO1.BDOS.10654605`) |
|------------|---------|-------------------------|----------------------------------------|
| `LP No. DHMA-LOP-SPOP-001 DE 2026` | Alcaldía de El Agrado | 2 filas de presupuesto (1 `.xlsx` + 1 `.rar` sin abrir) | `26. CCE-EICP-FM-14 Formul1 Presupuesto....xlsx`, `1.2. PRESUPUESTO.rar`, `8 - 21. FORMATOS.rar`, `OTROS DOCUMENTOS.rar` — pliego/anexo presumiblemente dentro de los `.rar` de formatos/otros |

### Comportamiento actual del pipeline (US 1.2 + 1.2.3)

| Situación | Comportamiento hoy | Problema |
|-----------|-------------------|----------|
| `.zip`/`.rar` con nombre que matchea presupuesto/anexo | Se descarga y archiva **el contenedor** en R2 | El usuario ve un `.rar`/`.zip` no utilizable como documento ofimático |
| `.zip`/`.rar` clasificado como `otro` (`OTROS DOCUMENTOS.rar`, `FORMATOS.rar`) | **Ignorado** por completo | Pliego/anexo internos nunca se inspeccionan |
| Archivos sueltos PDF/XLSX/DOCX | Extracción normal ✅ | Sin cambio |

**Referencia prod (ago 2026):** ~17 comprimidos ya almacenados en R2 como filas en `tender_documents` sin contenido extraído.

### Estado técnico previo a esta US

| Componente | Estado |
|------------|--------|
| Almacenamiento Cloudflare R2 (US 1.2.1) | ✅ |
| Backfill histórico + `documents_extraction_attempted_at` (US 1.2.2) | ✅ |
| Clasificador por nombre (US 1.2.3) | ✅ prerequisito |
| Re-sync incremental (US 1.2.3+) | ✅ `resync_documents.py` |
| Descompresión ZIP/RAR | ❌ no implementado |
| Binario `unrar` en imagen Docker/Railway | ❌ pendiente |

---

## SOLUCIÓN

### Fase A — Detectar archivos comprimidos candidatos

Tras listar documentos de SECOP para un `portfolio_id` (`fetch_documents_for_portfolio` ampliado o paso dedicado):

**Incluir como candidato a descompresión** si cumple **ambas** condiciones:

1. Extensión `.zip`, `.rar` (v1; `.7z` fuera de alcance).
2. Cualquiera de:
   - Clasificado ya como documento clave por nombre (US 1.2.3), **o**
   - Clasificado como `otro` **y** el nombre normalizado contiene alguna keyword de contenedor:

```text
anexo, anexos, pliego, pliegos, presupuesto, ppto, formato, formatos,
documento, documentos, otros documentos, apu, aiu, condiciones
```

**Excluir explícitamente** (no descomprimir):

- Nombres que contengan `plano`, `planos`, `cad`, `bim`, `dwg` (packs de ingeniería).
- Archivos mayores que `ARCHIVE_MAX_DOWNLOAD_BYTES` (config, default 100 MB).
- Comprimidos protegidos con contraseña (error registrado, continuar lote).

### Fase B — Descargar y descomprimir en staging temporal

1. Descargar el comprimido a staging bajo `DOCUMENTS_STORAGE_PATH` (directorio temporal por licitación).
2. Descomprimir con límites de seguridad (anti zip-bomb):

| Límite | Valor default (config) |
|--------|------------------------|
| Tamaño máximo descomprimido total por comprimido | `ARCHIVE_MAX_UNCOMPRESSED_BYTES` = 500 MB |
| Máximo de archivos internos extraídos | `ARCHIVE_MAX_FILES` = 200 |
| Profundidad máxima | `ARCHIVE_MAX_DEPTH` = 1 (sin zip dentro de zip en v1) |
| Extensiones internas permitidas | `.pdf`, `.xlsx`, `.xls`, `.xlsm`, `.docx`, `.doc` |

3. **ZIP:** librería estándar `zipfile` (Python).
4. **RAR:** librería `rarfile` + binario del sistema `unrar` (instalado en Dockerfile Railway).
5. Borrar staging tras subir hijos a R2 (`DOCUMENT_STORAGE_WRITE_LOCAL=false` en prod).

### Fase C — Clasificar y persistir contenido interno

1. Aplicar `classify_document()` de US 1.2.3 a **cada archivo interno** (solo nombre; contenido PDF queda para US 1.2.5).
2. Persistir **solo** documentos clave (`pliego_condiciones`, `anexo_tecnico`, `presupuesto`).
3. Subir a R2 con convención existente:

```text
{external_id}/{tipo}/{external_document_id}_{nombre_seguro}.pdf
```

4. Registrar en `tender_documents` (idempotente vía `uq_tender_document`).

#### Identificador de archivos internos (`external_document_id`)

Los hijos extraídos **no tienen** `id_documento` propio en SECOP. Usar identificador sintético estable:

```text
{secop_archive_id}:{ruta_interna_normalizada}
```

Ejemplo: `839783410:OTROS DOCUMENTOS/pliego condiciones.pdf`

- Misma ruta interna + mismo comprimido SECOP → mismo id → upsert idempotente.
- `download_url`: URL del archivo **padre** en SECOP (referencia) o vacío; la descarga en UI sirve el blob del hijo en R2.

#### Metadatos opcionales (recomendado en implementación)

| Campo | Valor |
|-------|-------|
| `source_archive_id` | `id_documento` SECOP del `.zip`/`.rar` padre |
| `classification_source` | `archive_extract` |

*(Si no se añade migración en v1, documentar el padre solo en logs.)*

#### Política sobre el comprimido original

| Decisión v1 | Detalle |
|-------------|---------|
| **No exponer** contenedores `.zip`/`.rar` en API/UI (US 1.3) | El frontend lista solo PDF/XLSX/DOCX descargables |
| **No conservar** blob del contenedor en R2 tras extracción exitosa con ≥1 hijo clave | Reduce ruido y duplicación |
| **Excepción:** si la extracción falla pero el contenedor ya estaba en R2 | Mantener fila existente hasta reproceso; marcar en logs |

### Fase D — Script de reproceso

`scripts/extract_compressed_documents.py`:

```bash
cd backend
PYTHONPATH=. python scripts/extract_compressed_documents.py --dry-run
PYTHONPATH=. python scripts/extract_compressed_documents.py --batch-size 25
PYTHONPATH=. python scripts/extract_compressed_documents.py --external-id CO1.REQ.10837635
PYTHONPATH=. python scripts/extract_compressed_documents.py --reference "LP No. DHMA-LOP-SPOP-001"
```

**Alcance del script:**

- Licitaciones con comprimidos candidatos en SECOP y/o filas `tender_documents` con extensión `.zip`/`.rar`.
- Prioridad: licitaciones **sin pliego** o **sin anexo** pese a tener comprimidos.

**Salida:** comprimidos procesados, archivos internos inspeccionados, docs clave guardados, errores, duración.

**Complemento:** tras desplegar, ejecutar también `resync_documents.py` no sustituye este script (resync no descomprime).

### Fase E — Integración con el job existente

Flag `ARCHIVE_EXTRACTION_ENABLED` (default `true` tras estabilizar).

Flujo por licitación en `extract_documents_for_tender`:

```text
1. Extraer archivos sueltos key (flujo actual US 1.2.3)
2. Si ARCHIVE_EXTRACTION_ENABLED → procesar comprimidos candidatos (Fase A–C)
3. Marcar documents_extraction_attempted_at (US 1.2.2)
```

El job diario (`extract_documents_for_pending_tenders`) y `resync_documents.py` heredan el paso 2 automáticamente.

**Rollback:** `ARCHIVE_EXTRACTION_ENABLED=false` restaura comportamiento actual (solo sueltos + contenedores key sin abrir).

### Fase F — Infraestructura Railway

Añadir al Dockerfile del backend:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends unrar-free \
    && rm -rf /var/lib/apt/lists/*
```

Dependencia Python: `rarfile` en `requirements.txt`.

---

## CRITERIOS DE ACEPTACIÓN

**GIVEN** que R2 está configurado (US 1.2.1), el clasificador ampliado desplegado (US 1.2.3) y una licitación con archivos `.rar`/`.zip` en SECOP  
**WHEN** se ejecuta la extracción de documentos comprimidos (`ARCHIVE_EXTRACTION_ENABLED=true`)  
**THEN**

1. Para **`LP No. DHMA-LOP-SPOP-001 DE 2026` (El Agrado)**, se archivan en R2 **al menos pliego y/o anexo técnico** extraídos del comprimido (si existen dentro de `OTROS DOCUMENTOS.rar` o `FORMATOS.rar`).
2. Los archivos internos clasificados como clave quedan en R2 y en `tender_documents` con metadatos correctos (`file_name` del hijo, no del contenedor).
3. El comprimido original **no aparece** en el listado del frontend (US 1.3); solo los hijos descargables.
4. El proceso respeta límites de tamaño/cantidad/profundidad y **no** persiste extensiones no permitidas (CAD, imágenes sueltas, etc.).
5. Re-ejecutar sobre la misma licitación **no crea duplicados** (`uq_tender_document` con id sintético) ni blobs redundantes en R2.
6. Errores de descompresión (corrupto, contraseña, RAR no soportado) se registran en logs **sin tumbar** el lote completo.
7. Tras extracción, **no quedan residuos** de staging en Volume Railway (`/data` temporal limpio).

### Validación manual (muestra)

| Licitación | Resultado esperado |
|------------|-------------------|
| El Agrado `LP No. DHMA-LOP-SPOP-001 DE 2026` | Pliego y/o anexo descargables; presupuesto XLSX suelto sigue disponible |
| Licitación con `5. Presupuesto Oficial.zip` ya en R2 | Hijos XLSX/PDF extraídos; contenedor oculto en UI |
| Licitación solo con `planos_obra.rar` | No descomprimido (excluido por política) |

### Métricas globales (cierre)

| Métrica | Objetivo |
|---------|----------|
| Licitaciones con ≥1 pliego **o** anexo tras reproceso | Incremento vs baseline post-1.2.3 |
| Filas `tender_documents` con extensión `.zip`/`.rar` visibles en API | → 0 (contenedores ocultos o eliminados) |
| `orphan_metadata_rows` | 0 tras `reconcile_documents.py` |
| Comprimidos procesados con error | Documentado en logs; < 5 % del lote |

---

## FUERA DE ALCANCE

- Extracción de texto o clasificación por **contenido** PDF (US 1.2.5).
- Descompresión de `.7z`, formatos propietarios o archivos **con contraseña** (solo log + skip).
- Descarga masiva de planos CAD, imágenes, BIM dentro de comprimidos.
- OCR de PDFs escaneados dentro del comprimido.
- Re-ingesta de licitaciones desde SECOP (US 1.1).
- Mejora del clasificador por nombre (US 1.2.3 — prerequisito, no se repite aquí).
- Frontend de progreso / barra de extracción de comprimidos.
- Zip dentro de zip (profundidad > 1) en v1.

---

## DEFINICIÓN DE HECHO (DoD)

- [ ] US 1.2.3 desplegada en producción.
- [ ] Módulo `archive_extraction.py` (o equivalente) con límites de seguridad documentados y tests.
- [ ] `unrar` en Dockerfile + `rarfile` en `requirements.txt`.
- [ ] Integración en `extract_documents_for_tender` tras archivos sueltos.
- [ ] Flag `ARCHIVE_EXTRACTION_ENABLED` en `config.py`.
- [ ] Script `extract_compressed_documents.py` + documentación en README.
- [ ] Tests unitarios: detección de candidatos, clasificación de internos, límites tamaño/cantidad, idempotencia de id sintético.
- [ ] Caso **El Agrado** validado: pliego y/o anexo descargables desde frontend.
- [ ] Reproceso ejecutado en prod (métricas antes/después registradas).
- [ ] Staging temporal sin residuos en Volume Railway tras extracción.
- [ ] API/UI no lista contenedores `.zip`/`.rar` como documentos clave.

---

## DEPENDENCIAS

| US | Relación |
|----|----------|
| 1.2 | Pipeline de extracción y descarga SECOP |
| 1.2.1 | Almacenamiento R2 (**bloqueante**) |
| 1.2.2 | Backfill histórico y `documents_extraction_attempted_at` |
| 1.2.3 | Clasificador por nombre (**bloqueante** — archivos internos usan las mismas reglas) |
| 1.3 | UI de descarga de documentos (ocultar contenedores) |
| 1.2.5 | Clasificación por contenido PDF (complementaria; no sustituye extracción de comprimidos) |

---

## NOTAS OPERATIVAS

### Reproceso sugerido en prod (post-deploy)

```bash
cd backend
PYTHONPATH=. python scripts/extract_compressed_documents.py --dry-run
PYTHONPATH=. python scripts/extract_compressed_documents.py --batch-size 10
PYTHONPATH=. python scripts/reconcile_documents.py --fix
```

### Variables de entorno (propuesta)

```env
ARCHIVE_EXTRACTION_ENABLED=true
ARCHIVE_MAX_DOWNLOAD_BYTES=104857600      # 100 MB
ARCHIVE_MAX_UNCOMPRESSED_BYTES=524288000  # 500 MB
ARCHIVE_MAX_FILES=200
ARCHIVE_MAX_DEPTH=1
```

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Zip-bomb / comprimido enorme | Límites de bytes y conteo de archivos |
| Falsos positivos en keywords de contenedor | Lista acotada + exclusión de `planos_*` |
| `unrar` ausente en Railway | Verificar en CI/deploy; fallo explícito en logs |
| Hijos con nombre genérico (`ANEXO 2.pdf`) no clasificados | US 1.2.5 posterior; no bloquea cierre de 1.2.4 |
| Duplicados hijo vs archivo suelto mismo nombre | `uq_tender_document` por id distinto (SECOP id vs sintético) |

### Impacto estimado

- **El Agrado** y licitaciones similares: de 0 pliegos → ≥1 pliego/anexo.
- **Prod (~17 comprimidos ya almacenados):** conversión a documentos ofimáticos utilizables.
- No resuelve nombres internos ambiguos sin keyword (→ US 1.2.5).

---

## SECUENCIA RECOMENDADA EN ROADMAP

```text
1.2.3 (nombre) → 1.2.4 (comprimidos) → resync / extract_compressed → 1.2.5 (contenido PDF sueltos)
```
