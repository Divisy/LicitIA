# US 2.1 — Cargar acta o certificado de obra (experiencia específica y objeto)

**Jira:** `2.1 [Backend+Frontend] Cargar acta o certificado de obra — experiencia específica y objeto del contrato`

## USER STORY

**As a** responsable de licitaciones que ya cargó el RUP  
**Quiero** adjuntar el acta de recibo o el certificado de obra de cada contrato  
**Para** que LicitIA tenga la **experiencia específica** y el **objeto del contrato**, y pueda usarlos después en el match contra lo que pide el pliego.

---

## BACKGROUND

La **US 1.11** activa el perfil con el certificado RUP: lista de contratos ejecutados, contratista, entidad, valor (SMMLV), fechas, códigos UNSPSC del clasificador e indicadores de capacidad.

Eso **no alcanza** para experiencia específica. El RUP de Cámara de Comercio **no trae el objeto contractual** de cada contrato (o lo trae truncado / por clasificador, no el texto del acta). En pliego, la experiencia específica se evalúa contra el **objeto**: *construcción de malla vial*, *interventoría de acueducto*, *estudios y diseños de puente*, etc.

Hoy el licitador ya tiene esos PDFs (acta de recibo a satisfacción, acta de liquidación, certificado de la entidad). Sin cargarlos, el match posterior solo puede cruzar UNSPSC, montos y un tipo de contrato inferido del RUP — insuficiente frente a la Matriz 1.

**Épica 2** (después del perfil de empresa, US 2.0): completar el lado empresa del JTBD 0 con el dato que el RUP no da.

**Lo que no existe sin esta US:**

- Upload por contrato de acta / certificado PDF.
- Campo persistido de experiencia específica / objeto.
- Columna de objeto en la tabla de experiencia.
- Recalificar **tipo de contrato** con el objeto real (no solo con el RUP).

El **cálculo de match % usando el objeto** no es esta US: aquí se captura y se deja listo el insumo.

---

## OBJETIVO

Por cada fila de `company_experiences` proveniente del RUP, permitir **cargar un PDF** (acta o certificado de obra). Al cargarlo:

1. Guardar el archivo (evidencia).
2. Extraer el **objeto del contrato**.
3. Tratar ese objeto como **experiencia específica** de ese contrato.
4. Clasificar **tipo de contrato** en uno de cuatro valores, según el objeto.
5. Dejar el objeto disponible para el match futuro.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye (fuera de esta US) |
|---------|-------------------------------|
| Upload PDF por contrato (acta de recibo, liquidación o certificado de la entidad) | Rediseñar el algoritmo de match % (US posterior) |
| Extraer objeto (texto nativo del PDF; OCR/visión si el acta está escaneada) | Exigir acta para activar el portafolio / onboarding |
| Mostrar columnas **Acta** y **Objeto del contrato** | Edición manual del objeto (texto libre) |
| Recalificar tipo: Estudios y diseños / Interventoría / Estudios, diseños y obra / Ejecución de obra | Carga masiva de un ZIP con todas las actas |
| Reemplazar el PDF de un contrato | Parsear múltiples contratos desde un solo compilado y repartirlos a varias filas |
| Persistencia en R2 + `specific_experience` | Certificados que no son PDF |
| Re-extraer objeto al recargar Experiencia si el PDF ya está y el objeto quedó vacío | Semáforo de habilitación vs pliego (US 1.12+) |

---

## SOLUCIÓN

### A. Artefacto de entrada

Por cada contrato del RUP, el usuario sube **un PDF**:

- Acta de recibo / finalización / liquidación, **o**
- Certificado de experiencia / certificado de la entidad contratante.

| Regla | Valor |
|-------|--------|
| Extensión | `.pdf` |
| Tamaño máx. | Alinear con RUP (25 MB) |
| Relación | 1 PDF ↔ 1 fila `company_experiences` |
| Obligatorio | No. El RUP sigue siendo suficiente para listar contratos; el acta **completa** experiencia específica |

Rechazar no-PDF con: *«Sube el certificado o el acta de finalización en PDF.»*

### B. Flujo de producto

Después de US 1.11, en **Experiencia / RUP** (`ExperienceList`):

1. El usuario ve la tabla de contratos extraídos del RUP.
2. En la columna **Acta**, pulsa *Cargar acta* y elige el PDF de ese contrato.
3. El archivo se guarda aunque el objeto aún no se lea.
4. Si se extrae el objeto, aparece en **Objeto del contrato** y se actualiza **Tipo de contrato**.
5. Si el PDF es escaneado o el objeto no salió, al **volver a abrir** la página de experiencia el sistema reintenta la extracción sobre el PDF ya guardado (sin pedirlo otra vez).
6. *Reemplazar* cambia el PDF de esa fila.

Copy de ayuda (junto a la tabla):

> El RUP no incluye el objeto de cada contrato. Carga el acta en PDF; si se lee el objeto, aparece en la columna Objeto del contrato.

Contador: `N contratos · M sin acta` (sin objeto extraído).

### C. Extracción (backend)

Pipeline:

1. Guardar PDF en almacenamiento (R2) con clave por experiencia, p. ej. `rup/{slug}/experiences/{id}/acta.pdf`.
2. Extraer texto nativo del PDF (página a página).
3. Localizar el objeto con reglas (p. ej. *Objeto del contrato:*, objeto en la línea siguiente, *tiene por objeto*, *cuyo objeto fue*).
4. Si no hay objeto usable (PDF escaneado, capa de texto basura, redacción distinta): OCR/visión sobre páginas del acta (prioridad a páginas que mencionen objeto / acta / consorcio).
5. Si hay texto largo pero las reglas fallan: LLM sobre el texto para devolver solo el objeto (no inventar).
6. Persistir `specific_experience` = objeto (máx. ~2000 caracteres, recortado antes de valor / plazo / firmas).
7. Regenerar `keywords` a partir del objeto (`extract_keywords`) para el match futuro.
8. Clasificar tipo de contrato **solo con el objeto** (no mezclar UNSPSC del RUP si el objeto ya clasifica).

**Tipo de contrato (obligatorio, uno de cuatro):**

| Valor | Etiqueta |
|-------|----------|
| `estudios_disenos` | Estudios y diseños |
| `interventoria` | Interventoría |
| `estudios_disenos_y_obra` | Estudios, diseños y obra |
| `ejecucion_obra` | Ejecución de obra |

Reglas de clasificación (objeto):

- Interventoría / interventor / supervisión de obra gana sobre obra.
- Estudios/diseños **y** ejecución/construcción → Estudios, diseños y obra.
- Solo estudios/diseños/consultoría de diseño → Estudios y diseños (p. ej. *estudios y diseños para el mejoramiento…* no es obra).
- Construcción / pavimentación / ejecución de obra → Ejecución de obra.

Si el objeto no clasifica, se mantiene el tipo inferido del RUP.

Guardar el tipo en `engineering_area` cuando la clasificación desde el objeto es uno de los cuatro.

### D. Datos y API

Campos en `company_experiences` (crear si no existen):

| Campo | Uso |
|-------|-----|
| `specific_experience` | Objeto extraído (experiencia específica) |
| `specific_evidence_filename` | Nombre original del PDF |
| `specific_evidence_key` | Clave en R2 / storage |
| `engineering_area` | Tipo de contrato (se actualiza desde el objeto) |
| `keywords` | Tokens del objeto para match posterior |

| Método | Ruta | Rol |
|--------|------|-----|
| `POST` | `/api/v1/experiences/{id}/specific-evidence` | Multipart PDF → guarda, extrae, clasifica, responde la experiencia actualizada |
| `GET` | `/api/v1/experiences?hydrate_rup=true` | En la página de experiencia: rellena UNSPSC/SMMLV del RUP **y** reintenta objeto si hay acta guardada y el objeto está vacío |

El listado ya incluye `specific_experience`, `specific_evidence_filename`, `contract_kind`, `contract_kind_label`.

Commit del archivo **antes** de terminar el OCR: si la visión tarda o falla, el usuario no pierde el adjunto.

Al reimportar RUP (US 1.11), **conservar** acta + objeto de cada `contract_number` que se vuelva a crear.

### E. Frontend

Tabla `ExperienceList`:

| Columna | Contenido |
|---------|-----------|
| Tipo de contrato | Tag de uno de los cuatro tipos (icono + etiqueta). Se actualiza cuando hay objeto |
| Acta | Nombre del PDF + *Cargar acta* / *Reemplazar* |
| Objeto del contrato | Texto extraído (3 líneas, tooltip con el resto) o **—** si aún no hay objeto |

Sin objeto: se muestra el filename si el PDF está y el CTA sigue siendo *Cargar acta* (o *Reemplazar* cuando ya hay objeto).

Estados: subiendo → éxito (objeto y tipo) → PDF guardado sin objeto (guion + reintento al recargar). Error de formato/tamaño inline.

### F. Relación con otras US

| US | Relación |
|----|----------|
| 1.11 Cargar RUP | Fuente de las filas; esta US las completa |
| 2.0 Perfil empresa | Sectores del radar; el tipo por contrato sale del objeto |
| Match `experience_matching.py` | Consumirá `specific_experience` / keywords; **no se cambia el score en esta US** |
| 1.5 Requisitos del pliego | El pliego pide experiencia específica; el objeto es el lado empresa |
| 1.12 Semáforo hábil | Podrá comparar objeto vs experiencia exigida más adelante |

---

## ACCEPTANCE CRITERIA

**GIVEN** una empresa con RUP cargado y contratos en la tabla  
**WHEN** abre Experiencia  
**THEN** ve *Cargar acta* por contrato y las columnas Acta y Objeto del contrato. No se pide Excel.

**GIVEN** un acta o certificado PDF con objeto legible  
**WHEN** lo sube en un contrato  
**THEN** el archivo queda asociado a esa fila, el objeto aparece en **Objeto del contrato**, y ese texto es la experiencia específica persistida.

**GIVEN** el objeto extraído habla de interventoría, de estudios y diseños, de estudios+obra, o de construcción/ejecución  
**WHEN** termina la extracción  
**THEN** **Tipo de contrato** queda en exactamente uno de: Estudios y diseños; Interventoría; Estudios, diseños y obra; Ejecución de obra.

**GIVEN** el RUP había marcado otro tipo  
**WHEN** el objeto clasifica con claridad  
**THEN** gana el objeto, no el RUP.

**GIVEN** un PDF escaneado o con capa de texto basura  
**WHEN** se sube  
**THEN** se intenta OCR/visión; si sale el objeto, se muestra igual que en un PDF de texto.

**GIVEN** el PDF se guardó pero el objeto quedó vacío  
**WHEN** el usuario recarga Experiencia (`hydrate_rup`)  
**THEN** el sistema relee el PDF almacenado y, si ahora extrae objeto, llena la columna sin pedir el archivo otra vez.

**GIVEN** un archivo que no es PDF o supera el tamaño  
**WHEN** lo selecciona  
**THEN** no se adjunta; mensaje claro.

**GIVEN** el usuario reemplaza el PDF  
**WHEN** el nuevo archivo extrae objeto  
**THEN** se actualizan evidencia, objeto, keywords y tipo.

**GIVEN** el usuario vuelve a cargar el RUP  
**WHEN** se regeneran las filas  
**THEN** actas y objetos ya adjuntos se conservan por número de contrato.

**GIVEN** contratos sin acta  
**WHEN** usa el dashboard / match actual  
**THEN** el match existente no se rompe; la falta de objeto no bloquea el radar.

---

## FUERA DE ALCANCE

- Recalcular match % con el objeto (siguiente US de matching).
- Comparar objeto vs experiencia específica exigida en el pliego (habilitación).
- Un PDF que contiene actas de varios contratos y asignar cada una a su fila.
- Editar el objeto a mano en la tabla.
- Obligar acta en el onboarding antes de ver licitaciones.

---

## TÍTULO JIRA

`2.1 [Backend+Frontend] Cargar acta o certificado de obra — experiencia específica y objeto del contrato`
