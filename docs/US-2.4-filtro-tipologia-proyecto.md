# US 2.4 — Filtro por tipología de proyecto (según el objeto del contrato)

**Jira:** `2.4 [Backend+Frontend] Tipología de proyecto desde el objeto — filtro del radar por experiencia`

## USER STORY

**As a** personal de licitaciones  
**Quiero** colocar en unas palabras la experiencia que tiene mi empresa  
**Para** que se muestren solo las licitaciones asociadas a esa experiencia.

---

## BACKGROUND

Tras **US 1.11** (RUP) y **US 2.1** (acta → objeto del contrato), LicitIA ya sabe:

- Qué contratos ejecutó la empresa.
- El **objeto** de cada contrato (experiencia específica).
- El **tipo de contrato**: estudios y diseños / interventoría / estudios, diseños y obra / ejecución de obra.

Eso **no describe de qué trata la obra**. “Ejecución de obra” cubre vías, acueducto, puentes o parques. El licitador no quiere ver todo SECOP de obra: quiere el radar recortado a **su especialidad**.

Hoy el radar filtra por tipo de contrato, publicación, ubicación y entidad (US 2.3). **No hay tipología de proyecto.** El match % por experiencia sigue pausado; esta US entrega un recorte explícito y entendible: unas palabras = una familia de proyectos.

**Tipología ≠ tipo de contrato**

| Concepto | Ejemplo | De dónde sale |
|----------|---------|----------------|
| Tipo de contrato | Interventoría, ejecución de obra | US 2.1 / RUP |
| **Tipología de proyecto** | Vías, acueducto, puentes, espacio público | **Objeto del contrato** (acta) y, simétrico, objeto SECOP de la licitación |

**Épica 2:** 2.0 perfil → 2.1 acta/objeto → 2.3 entidad → **2.4 tipología para filtrar el radar**.

---

## OBJETIVO

1. Clasificar cada experiencia de la empresa en una o más **tipologías de proyecto**, leyendo el **objeto del contrato** (acta; si no hay acta, el texto que haya del RUP).
2. Mostrar esas tipologías como filtro (chips / palabras) en Experiencia y en el radar.
3. Al marcar una o varias, el listado de licitaciones muestra **solo procesos cuyo objeto encaja** con esas tipologías.

### Catálogo inicial (MVP)

Valores persistidos en snake_case; etiqueta en UI:

| Valor | Etiqueta |
|-------|----------|
| `construccion` | Construcción |
| `edificacion` | Edificación |
| `vias` | Vías |
| `geotecnica` | Geotécnica |
| `espacio_publico` | Espacio público |
| `bicicarril` | Bicicarril |
| `senalizacion` | Señalización |
| `acueducto_alcantarillado` | Acueducto y alcantarillado |
| `parques` | Parques |
| `puentes` | Puentes |
| `otro` | Otra |

Un contrato puede tener **más de una** tipología (p. ej. vías + señalización). “Etc. / Otra” cubre objetos que no caen en la lista; no inventar tipologías libres en el MVP más allá de `otro`.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye |
|---------|------------|
| Clasificar tipología(s) a partir del objeto del contrato (reglas +, si hace falta, LLM) | Recalcular el score de match % |
| Guardar tipologías en `company_experiences` | Taxonomía UNSPSC como única fuente |
| Filtro **Tipología de proyecto** en el radar (multi-select de las que tiene la empresa) | Catálogo abierto editable por el usuario |
| Clasificar el objeto SECOP de cada licitación con el **mismo catálogo** para poder filtrar | Exigir acta para usar el filtro (si no hay objeto, no hay tipología de esa fila) |
| Combinar con tipo de contrato, fechas, ubicación, entidad | Semáforo de habilitación vs pliego |
| Mostrar las tipologías en la tabla de experiencia (junto al objeto) | Deducción desde solo códigos UNSPSC sin texto |

---

## SOLUCIÓN

### A. Producto — Experiencia (después de RUP y acta)

En la tabla de contratos:

- Columna **Tipología** (tags) alimentada cuando hay objeto.
- Si el objeto aún no se extrajo: **—** (igual que el objeto vacío).
- Al extraer o reextraer el objeto (US 2.1), se (re)clasifican las tipologías.

Copy: *La tipología sale del objeto del acta. Sirve para ver en el radar solo licitaciones de esas líneas (vías, acueducto, puentes…).*

### B. Producto — Radar

Nuevo filtro **Tipología de proyecto**, junto a tipo de contrato / publicación / ubicación / entidad.

- Opciones = **unión de tipologías de los contratos de la empresa** (no las 11 de golpe si la empresa solo tiene vías y acueducto).
- Si aún no hay ningún objeto/tipología: el filtro no recorta (o se muestra deshabilitado: *Carga actas para filtrar por tipología*).
- Multi-select. Vacío = no filtra por tipología.
- Se aplica con **Buscar**, junto al resto.

**As a** personal de licitaciones: marca “Vías” y “Acueducto y alcantarillado” → solo licitaciones cuyo objeto hable de esas familias, aunque el tipo de contrato sea obra o interventoría.

### C. Clasificación (backend)

Entrada: texto del objeto (experiencia `specific_experience` o, si no hay, `project_description`).  
Salida: lista de valores del catálogo.

Reglas por palabras clave (normalizar tildes), ejemplos:

| Tipología | Señales en el objeto |
|-----------|----------------------|
| Vías | vía, malla vial, paviment, carreteable, terciaria, doble calzada |
| Edificación | edificacion, colegio, hospital, vivienda, edificio, aulas |
| Geotécnica | geotecn, talud, estabilidad, cimentacion profunda |
| Espacio público | espacio publico, andenes, alameda, plazas |
| Bicicarril | ciclorruta, ciclovia, bicicarril |
| Señalización | senaliz, semafor |
| Acueducto y alcantarillado | acueducto, alcantarill, acueduct y alcant, PTAP, PTAR, redes hidraulicas |
| Parques | parque, zonas verdes |
| Puentes | puente, viaducto, ponton |
| Construcción | construccion / obra civil genérica si no hay otra más específica |
| Otra | objeto usable que no matchea el resto |

Prioridad: las específicas ganan; `construccion` solo si hay ejecución/construcción y ninguna familia más fina. Interventoría de vías → tipología **vías** (el tipo de contrato sigue siendo interventoría).

Si las reglas no alcanzan y hay API de LLM: pedir JSON `{"typologies": ["vias", ...]}` restringido al catálogo; no inventar etiquetas.

Misma función para `tender.object_text`.

### D. Datos y API

`company_experiences.project_typologies` (JSON array de strings).  
Opcional en licitaciones: `tenders.project_typologies` persistido al ingerir/actualizar, o clasificar on the fly en el GET (MVP: on the fly o cache simple; persistir si el GET se vuelve lento).

Al extraer objeto (POST acta / backfill US 2.1): calcular y guardar tipologías.

| Método | Cambio |
|--------|--------|
| `GET /experiences` | Incluye `project_typologies: string[]` |
| `GET /tenders` | Query `typology=` repetible o CSV (`vias,acueducto_alcantarillado`). Filtra licitaciones cuya clasificación intersecta el set |
| `GET /experiences` o perfil | Endpoint o campo agregado `available_typologies` para armar el filtro del radar |

### E. Relación con otras US

| US | Relación |
|----|----------|
| 2.1 Acta / objeto | Fuente del texto a clasificar |
| Tipo de contrato (4 valores) | Sigue aparte; tipología es el “de qué” |
| 2.3 Entidad | Filtro aditivo en el radar |
| Match `experience_matching.py` | Esta US recorta el listado; no sustituye el % de match futuro |

---

## CRITERIOS DE ACEPTACIÓN

### MVP (fase 2.4.1)

**GIVEN** que la empresa tiene RUP cargado (US 1.11)  
**AND** un contrato con objeto extraído del acta (US 2.1), p. ej. *pavimentación de la malla vial urbana*  
**WHEN** el personal de licitaciones abre Experiencia  
**THEN**

- La fila muestra la tipología **Vías** además del tipo de contrato (p. ej. Ejecución de obra).
- `GET /api/v1/experiences` incluye `project_typologies: ["vias"]` (o el set clasificado) para esa fila.
- No se inventa tipología si el objeto está vacío: la columna queda **—**.

**GIVEN** un objeto *estudios y diseños del sistema de acueducto y alcantarillado*  
**WHEN** se clasifica  
**THEN**

- Tipología **Acueducto y alcantarillado**.
- El tipo de contrato puede seguir siendo **Estudios y diseños** (no se pisan).

**GIVEN** un objeto *interventoría para la construcción de un puente vehicular*  
**WHEN** se clasifica  
**THEN**

- Tipología **Puentes**.
- Tipo de contrato **Interventoría**.

**GIVEN** un objeto usable que no encaja en el catálogo (construcción, edificación, vías, geotécnica, espacio público, bicicarril, señalización, acueducto y alcantarillado, parques, puentes)  
**WHEN** se clasifica  
**THEN**

- Queda **Otra** (`otro`).
- No se crea una etiqueta libre fuera del catálogo.

**GIVEN** que el personal de licitaciones reemplaza el acta y el objeto cambia  
**WHEN** termina la extracción  
**THEN**

- Las tipologías de esa fila se recalculan.
- El filtro del radar, al recargar, usa el set nuevo (unión de tipologías vigentes).

**GIVEN** que la empresa tiene al menos una tipología clasificada (p. ej. Vías y Acueducto y alcantarillado)  
**AND** el personal de licitaciones está en el dashboard / radar  
**WHEN** marca **Vías** y pulsa Buscar  
**THEN**

- Solo aparecen licitaciones cuyo `object_text` se clasifica con tipología vías.
- El recorte es independiente del tipo de contrato (puede haber interventoría de vías).
- Tipo de contrato, publicación, ubicación y entidad, si estaban puestos, siguen aplicándose (AND entre filtros; OR entre tipologías marcadas).

**GIVEN** marca Vías **y** Acueducto y alcantarillado  
**WHEN** busca  
**THEN**

- Entran procesos que matchean **al menos una** de las dos (OR).
- `GET /api/v1/tenders?typology=vias&typology=acueducto_alcantarillado` (o CSV equivalente) devuelve el mismo recorte que la UI.

**GIVEN** no marca ninguna tipología  
**WHEN** busca  
**THEN** el radar no se recorta por tipología.

**GIVEN** la empresa no tiene ningún objeto/acta clasificado  
**WHEN** abre el radar  
**THEN**

- No se inventan tipologías ni se muestra el catálogo completo como si fuera experiencia de la empresa.
- El filtro no obliga; copy: cargar actas para filtrar por tipología.

**GIVEN** tests automatizados de clasificación  
**WHEN** corre el suite  
**THEN** hay casos unitarios para vías, acueducto, puentes, interventoría+tipología, objeto vacío y `otro`, más al menos un caso de filtro de listado.

### Validación manual (muestra — gate de cierre MVP)

| Caso | Resultado esperado |
|------|-------------------|
| Acta Santa Isabel (o equivalente) con objeto de acueducto / vías | Tag(s) de tipología correctos en la tabla de experiencia |
| Contrato interventoría + objeto de puente | Tipo Interventoría + tipología Puentes |
| Radar: marcar solo Vías | Listado sin acueductos/parques que no hablen de vías |
| Radar: ninguna tipología marcada | Mismo universo que hoy (salvo otros filtros) |
| Empresa sin actas | Filtro no recorta; no lista tipologías falsas |
| Objeto genérico *construcción de obras varias* | Construcción u Otra; nunca un tag inventado |

### Fases posteriores (no bloquean cierre MVP)

| Fase | Criterio adicional |
|------|-------------------|
| 2.4.2 | Persistir `project_typologies` en `tenders` al ingerir SECOP (no solo on the fly) |
| 2.4.3 | Usar tipología como señal del match % (además del recorte del radar) |
| 2.4.4 | Ampliar catálogo (p. ej. riego, dragados) sin romper valores ya guardados |

---

## FUERA DE ALCANCE (MVP)

- Usuario creando tipologías personalizadas (*mi nicho X*).
- Filtro AND estricto entre tipologías marcadas (debe cumplir todas).
- Usar solo UNSPSC sin leer el objeto.
- Recalcular el score de match % (fase 2.4.3).
- Semáforo de habilitación vs Matriz 1 del pliego.
- Detectar tipología desde el PDF del pliego (solo objeto SECOP + objeto de acta).
- OCR adicional: reutiliza US 2.1; si no hay objeto, no hay tipología.

---

## DEFINICIÓN DE HECHO (DoD)

### Fase 2.4.1 (MVP)

- [ ] Catálogo fijo de tipologías (valores + etiquetas) en backend y frontend.
- [ ] Clasificador de objeto → `project_typologies[]` (reglas; LLM opcional acotado al catálogo).
- [ ] Persistencia en `company_experiences` al extraer/reextraer el objeto (US 2.1).
- [ ] Columna **Tipología** en la tabla de experiencia.
- [ ] `GET /experiences` expone `project_typologies` y el set disponible de la empresa.
- [ ] Filtro **Tipología de proyecto** (multi) en `FiltersBar` / dashboard.
- [ ] `GET /tenders` acepta `typology` y recorta por intersección con el objeto SECOP.
- [ ] Tests de clasificación + al menos un test de filtro.
- [ ] Validación manual de la muestra de la tabla anterior documentada en el ticket de cierre.

### Épica completa (2.4.1 → 2.4.4)

- [ ] Tipologías persistidas en licitaciones (ingesta).
- [ ] Tipología como insumo del match %.
- [ ] Extensión de catálogo versionada.

---

## DEPENDENCIAS

| US / componente | Relación |
|-----------------|----------|
| 1.11 Cargar RUP | Filas de experiencia a clasificar |
| 2.1 Acta / objeto | Texto fuente; sin objeto no hay tipología de esa fila |
| Tipo de contrato (4 valores) | Independiente; no se sustituye |
| 2.3 Entidad contratante | Filtro aditivo en el mismo radar |
| `experience_matching.py` | No se modifica en el MVP |
| Dashboard / `FiltersBar` | Superficie del filtro |

---

## NOTAS OPERATIVAS

- Un contrato puede tener **varias** tipologías; el radar usa la **unión** de las de la empresa como opciones del filtro.
- Entre tipologías marcadas: **OR**. Entre tipología y el resto de filtros del radar: **AND**.
- Normalizar tildes al clasificar (*senalizacion* / *señalización*).
- Si el GET de licitaciones se vuelve lento, pasar a persistir tipología en `tenders` (fase 2.4.2) sin cambiar el contrato de UI.

### Título sugerido en Jira

`2.4 [Backend+Frontend] Tipología de proyecto desde el objeto — filtrar el radar por la experiencia de la empresa`
