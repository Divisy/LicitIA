# US 1.11 — Cargar RUP (activar perfil del contratista)

**Jira:** `[BACKEND+FRONTEND] US 1.11 Cargar RUP`

## USER STORY

**As a** responsable de licitaciones en una empresa de construcción, ingeniería o interventoría  
**Quiero** cargar el certificado RUP de mi empresa (no armar un Excel)  
**Para** que LicitIA use la experiencia registrada y la capacidad financiera/organizacional oficiales, active el match % y pueda compararlas con lo que pide cada pliego.

---

## BACKGROUND

**JTBD 0** no cambia: *«Enséñale a LicitIA en qué es buena tu empresa»*. Cambia el artefacto.

Hoy (US 1.10) el usuario debe:

1. Descargar una plantilla Excel.
2. Transcribir a mano contratos de su portafolio.
3. Subir el `.xlsx` a `POST /api/v1/experiences/import`.

Eso **no funciona** en operación real: el dato oficial ya está en el **Registro Único de Proponentes (RUP)** (Ley 1150 de 2007, Decreto 1082 de 2015). El licitador ya paga y descarga ese PDF en la cámara de comercio. Pedirle un Excel es fricción y error (montos desactualizados, contratos omitidos, indicadores que nunca se cargan).

**Lo que el RUP ya trae (y LicitIA necesita):**

| Bloque RUP | Uso en LicitIA |
|------------|----------------|
| Contratos / experiencia inscrita | Filas de `company_experiences` → match % (JTBD 0 / 1) |
| Capacidad financiera (liquidez, endeudamiento, cobertura, capital de trabajo, rentabilidad) | Perfil de la empresa vs Matriz 2 del pliego (US 1.5) |
| Capacidad organizacional | Mismo perfil vs requisitos organizacionales del pliego |
| Identificación (NIT, razón social, cámara, vigencia) | Anclar el perfil; avisar si el RUP está vencido |

**Lo que no existe hoy:**

- Upload ni parser de PDF RUP.
- Tabla de capacidad financiera/organizacional **de la empresa** (solo se extraen umbrales **del pliego**).
- Copy de onboarding habla de «portafolio» / plantilla Excel (`ExperiencesStep`, `productMessaging.ts`).

**Nota de numeración:** en el mapa JTBD anterior, «US 1.11» era el panel *¿Puedo ser hábil?*. Ese panel **pasa a US 1.12**: necesita este perfil RUP para semáforo vs pliego. Esta US no implementa el semáforo.

---

## OBJETIVO

Sustituir la plantilla Excel como camino principal del JTBD 0 por **cargar el certificado RUP**. Extraer y persistir:

1. Experiencias (contratos) del contratista.
2. Indicadores de capacidad financiera y organizacional.

El Excel deja de mostrarse como CTA (descargar plantilla / «sube tu portafolio»). Puede quedar como fallback interno, no en onboarding.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye (fuera de esta US) |
|---------|-------------------------------|
| Upload PDF del certificado RUP (onboarding, FirstSessionHome, perfil) | Semáforo «¿puedo ser hábil?» vs pliego (US 1.12) |
| Extraer contratos → `company_experiences` | Calcular CRP / K de la empresa (US 1.8 es del proceso) |
| Extraer indicadores financieros y organizacionales → perfil empresa | Integración API RUES / consulta en línea a cámaras |
| Guardar archivo fuente (R2) + fecha de expedición / vigencia | RUP de consorcio/UT como persona plural |
| Reemplazar copy: *Cargar RUP* (no plantilla Excel) | Edición manual contrato a contrato |
| Preview post-carga: N contratos + indicadores leídos + MatchPreview | OCR pesado de RUP 100% escaneado (fase 1.11.2 si el PDF no tiene texto) |
| Tests con al menos un RUP de muestra (GV / fixture) | Multi-empresa / auth JWT (sigue `company_name` como hoy) |

---

## SOLUCIÓN

### A. Artefacto de entrada

El usuario sube el **certificado RUP vigente** en PDF (el que expide la cámara: experiencia + capacidad financiera + organizacional).

- Extensiones MVP: `.pdf`
- Tamaño máx.: alinear con documentos SECOP (p. ej. 20–25 MB)
- Rechazar Excel en este paso con mensaje: *«Sube el certificado RUP en PDF, no la plantilla de experiencias.»*

### B. Flujo de producto (reemplaza Excel en US 1.10)

`WelcomeStep` → **`RupUploadStep`** (sustituye `ExperiencesStep` como paso principal) → `MatchPreviewStep`.

Mismos puntos de entrada que el portafolio vacío:

- Onboarding CTA: *Continuar — cargar RUP*
- `FirstSessionHome` + `PortfolioBanner`: *Cargar RUP*
- Perfil: sección *RUP de la empresa* (re-cargar / ver vigencia)

`usePortfolioStatus` = `ready` cuando hay **≥ 1 experiencia persistida** desde el RUP (igual que hoy, cambia la fuente).

### C. Extracción (backend)

Pipeline análogo a requisitos de pliego (US 1.5):

1. Guardar PDF (R2) asociado al `company_name`.
2. Extraer texto (`pdf_text` existente). Si el texto es insuficiente, marcar `rup_text_insufficient` y mensaje *«Este PDF parece escaneado; usa el certificado descargado de la cámara (texto seleccionable).»* — no inventar contratos.
3. Extraer con reglas + LLM (mismo patrón híbrido que scoring/requisitos):

**Contratos / experiencia** → mapear a `CompanyExperience`:

| Campo RUP (típico) | Campo LicitIA |
|--------------------|---------------|
| Número / contrato | `contract_number` |
| Objeto / descripción | `project_description` |
| Entidad contratante | `contracting_entity` |
| Valor (SMMLV o COP; convertir COP si viene en SMMLV × SMMLV del certificado) | `amount` |
| Fecha de terminación / ejecución | `completion_date` |
| Clasificador / códigos | `category` (y keywords vía `extract_keywords`) |
| Departamento / municipio si aparece | `department`, `municipality` |

**Capacidad** → modelo nuevo `CompanyCapacity` (1 fila vigente por `company_name`):

| Indicador | Guardar |
|-----------|---------|
| Índice de liquidez | valor + año / corte del RUP |
| Índice de endeudamiento | idem |
| Cobertura de intereses | idem |
| Rentabilidad del patrimonio / del activo | idem |
| Capital de trabajo | idem |
| Indicadores organizacionales que traiga el certificado | JSON o columnas explícitas de los que aparezcan |
| NIT, razón social, cámara, fecha expedición, fecha vigencia | metadatos |
| `source_document_id` | trazabilidad |

Re-carga de RUP: **reemplaza** experiencias e indicadores de esa empresa (el RUP vigente es la fuente de verdad). Confirmar en UI: *«Esto actualiza la experiencia y los indicadores con este certificado.»*

### D. API

| Método | Ruta | Rol |
|--------|------|-----|
| `POST` | `/api/v1/rup/import?company_name=` | Multipart PDF → extrae, persiste, responde resumen |
| `GET` | `/api/v1/rup/profile?company_name=` | Metadatos RUP + indicadores (sin re-parsear) |

Respuesta de import (mínimo):

```json
{
  "imported_experiences": 12,
  "capacity": { "liquidez": 1.4, "endeudamiento": 0.52 },
  "issued_at": "2026-03-01",
  "valid_until": "2026-12-31",
  "nit": "900…",
  "warnings": []
}
```

El listado `GET /api/v1/experiences` no cambia: el match sigue leyendo `company_experiences`.

`POST /api/v1/experiences/import` (Excel) **no se usa en UI**. Se puede dejar el endpoint por compatibilidad; no es el camino del onboarding.

### E. Frontend

| Superficie | Cambio |
|------------|--------|
| `productMessaging.ts` | CTA y JTBD 0: *cargar RUP*, no *subir portafolio / plantilla* |
| `ExperiencesStep` → `RupUploadStep` (o el mismo componente reescrito) | FileUploader PDF; sin «Descargar plantilla» |
| `FirstSessionHome`, `PortfolioBanner`, `OnboardingJourneyStrip` | Copy RUP |
| Perfil | Estado: RUP cargado · vigencia · N contratos · re-cargar |
| `MatchPreviewStep` | Sin cambio de comportamiento; se alimenta de experiencias ya guardadas |

Estados UI: subiendo → extrayendo → éxito (N contratos + indicadores) → error (PDF ilegible, 0 contratos, archivo que no parece RUP).

### F. Relación con otras US

| US | Relación |
|----|----------|
| 1.10 Primera sesión | Conserva Pregunta 0 y FirstSessionHome; **esta US cambia el input del JTBD 0** |
| 1.5 Requisitos del pliego | Umbrales del proceso; el RUP llena el **lado empresa** |
| 1.8 Capacidad residual | No calcular CRP aquí; el RUP no sustituye Formato 5 |
| 1.12 Cobertura CMA (bug) | Radar de interventoría y estudios/diseños |
| 1.13 (futura) ¿Puedo ser hábil? | Compara perfil RUP vs requisitos extraídos |
| Match `experience_matching.py` | Consume las mismas filas `company_experiences` |

---

## ACCEPTANCE CRITERIA

**GIVEN** un usuario en onboarding o FirstSessionHome  
**WHEN** ve el paso de activar perfil  
**THEN** el CTA es **cargar el RUP en PDF**; no hay «Descargar plantilla» ni se pide Excel.

**GIVEN** un certificado RUP PDF con texto extraíble y ≥ 1 contrato inscrito  
**WHEN** lo sube  
**THEN** se persisten las experiencias, `usePortfolioStatus` pasa a `ready`, ve resumen (N contratos + indicadores leídos) y el `MatchPreviewStep` con top 3 match %.

**GIVEN** el mismo RUP trae indicadores financieros (p. ej. liquidez, endeudamiento)  
**WHEN** la importación termina  
**THEN** `GET /api/v1/rup/profile` devuelve esos valores y quedan asociados a la empresa (no solo en el PDF).

**GIVEN** el usuario vuelve a subir un RUP más reciente  
**WHEN** confirma  
**THEN** experiencias e indicadores se actualizan con el nuevo certificado (fuente de verdad = último RUP).

**GIVEN** un Excel o un PDF que no es RUP / no tiene texto  
**WHEN** lo sube  
**THEN** no se crean experiencias falsas; mensaje claro de qué archivo se espera.

**GIVEN** una empresa que ya tiene experiencias cargadas (Excel legado o RUP)  
**WHEN** entra al dashboard  
**THEN** no ve FirstSessionHome; el match sigue funcionando (sin regresión).

**GIVEN** «Explorar sin personalizar»  
**WHEN** entra al dashboard  
**THEN** banner pide **cargar RUP** (no la plantilla Excel).

---

## TÍTULO JIRA

`1.11 [Backend+Frontend] Cargar RUP — experiencia y capacidad financiera del contratista (JTBD 0)`
