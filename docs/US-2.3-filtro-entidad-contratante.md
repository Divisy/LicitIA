# US 2.3 — Filtro de entidad contratante

**Jira:** `2.3 [Frontend+Backend] Filtro de entidad contratante en el listado de licitaciones`

## USER STORY

**As a** responsable de licitaciones que mira el radar  
**Quiero** filtrar las licitaciones por **entidad contratante** (no por el nombre de mi empresa)  
**Para** ver solo procesos de INVÍAS, un municipio, FONADE u otra entidad, igual que en SECOP.

---

## BACKGROUND

En el dashboard de licitaciones el licitador ya filtra por **tipo de contrato**, **fecha de cierre** y **ubicación**.

Históricamente el filtro de texto extra era **nombre de empresa**. Eso no sirve en este listado:

- El nombre de la empresa del usuario **no es un atributo de la licitación**. Se usa (o se usará) para match / RUP, no para recortar el radar.
- Lo que el usuario busca es la **entidad que convoca**: *Instituto Nacional de Vías*, *Alcaldía de Paipa*, *FONADE*, *IDU*, etc. Esa columna ya existe en la tabla (`entity_name`) y en el detalle.

Hoy:

| Qué hay | Problema |
|---------|----------|
| `FiltersBar` recibe `companyName` / `onCompanyNameChange` | El campo no debe filtrar por la empresa del usuario |
| `GET /tenders?company_name=` | Es el nombre de la **empresa LicitIA** para matching de experiencia, no un filtro de entidad |
| Tabla: columna entidad (`tender.entity_name`) | No hay forma de filtrar el listado por ese valor |
| Ubicación (`department` / municipio) | Se mantiene; no sustituye a la entidad |

**Épica 2:** 2.0 perfil de empresa → 2.1 acta/objeto → **2.3 filtrar el radar por quién contrata**.

---

## OBJETIVO

Sustituir el filtro de **nombre de empresa** en la barra de licitaciones por un filtro de **entidad contratante**.

El usuario escribe (o elige) parte del nombre de la entidad. El listado muestra solo licitaciones cuyo `entity_name` coincide (búsqueda parcial, sin importar mayúsculas).

El `company_name` del usuario **sigue existiendo** para RUP / match; **deja de usarse como filtro de UI** del radar.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye |
|---------|------------|
| Campo **Entidad contratante** en `FiltersBar` (reemplaza nombre de empresa) | Autocompletar con catálogo oficial de entidades SECOP |
| Query `entity` / `entity_name` en `GET /api/v1/tenders` (ILIKE sobre `tenders.entity_name`) | Filtrar experiencias del RUP por entidad (eso ya está en la tabla de contratos) |
| Combinar con tipo de contrato, fechas de cierre y ubicación | Filtro múltiple (varias entidades a la vez) |
| Placeholder y copy claros (*INVÍAS, municipio, IDU…*) | Cambiar el matching `company_name` |
| Vacío = no filtra por entidad | Nuevo índice obligatorio si el ILIKE actual basta |

---

## SOLUCIÓN

### A. Producto — barra de filtros

En el dashboard (`FiltersBar`), la fila de filtros avanzados queda:

| Campo | Sigue / cambia |
|-------|----------------|
| Tipo de contrato | Igual |
| Cierre desde / Cierre hasta | Igual |
| Ubicación | Igual (departamento o municipio) |
| **Entidad contratante** | **Nuevo.** Sustituye nombre de empresa |
| Buscar | Igual |

**Label:** Entidad contratante  
**Placeholder:** *INVÍAS, municipio, IDU…*  
**Comportamiento:** texto libre; se aplica al pulsar **Buscar** (mismo submit que fechas y ubicación).

No mostrar “Nombre de empresa”, “Mi empresa” ni un input ligado a `licitia_user_company`.

### B. Backend

`GET /api/v1/tenders`:

| Parámetro | Rol |
|-----------|-----|
| `entity` (nuevo) o `entity_name` | Filtro opcional. `Tender.entity_name ILIKE %valor%` |
| `company_name` | **No** se usa para este filtro. Sigue siendo el identificador de la empresa para match (pausado), no se muestra en la barra |

Si `entity` viene vacío o no se envía, no se restringe por entidad.

El filtro es **aditivo** con los demás (`contract_kind`, `date_from` / `date_to`, `department`).

### C. Frontend

- Estado del dashboard: `entity` (string), no reutilizar `companyName` del lead.
- `getTenders({ entity })` cuando el campo tiene texto.
- Quitar props `companyName` / `onCompanyNameChange` del `FiltersBar` si solo servían a este input.
- Resultados: la columna de entidad de la tabla coincide con el texto buscado (parcial).

### D. Relación con otras US

| US | Relación |
|----|----------|
| Listado / radar | Superficie de esta US |
| 2.0 Perfil empresa | La razón social del usuario no es este filtro |
| 1.11 / 2.1 Experiencia | Entidad contratante del **contrato ejecutado** es otro dato; no se mezcla aquí |
| Match experiencia | Sigue usando `company_name` internamente; no se toca el score |

---

## ACCEPTANCE CRITERIA

**GIVEN** un usuario en el dashboard de licitaciones  
**WHEN** mira los filtros  
**THEN** ve el campo **Entidad contratante**. No ve filtro de nombre de empresa / razón social del usuario.

**GIVEN** escribe `INVÍAS` (o `invias`) y pulsa Buscar  
**WHEN** carga el listado  
**THEN** solo aparecen licitaciones cuya entidad contiene ese texto. Tipo, fechas y ubicación, si estaban puestos, se mantienen.

**GIVEN** escribe `Paipa`  
**WHEN** hay procesos del municipio de Paipa y de otras entidades  
**THEN** solo entran los de entidades cuyo nombre incluye Paipa (no se usa como sustituto del filtro de ubicación).

**GIVEN** deja el campo vacío y busca  
**WHEN** no hay otros filtros restrictivos  
**THEN** el listado no se recorta por entidad.

**GIVEN** combina entidad + tipo Interventoría + un rango de cierre  
**WHEN** busca  
**THEN** las tres condiciones se aplican a la vez.

**GIVEN** un `company_name` guardado en sesión (lead / RUP)  
**WHEN** abre el dashboard  
**THEN** ese valor no se pega en el filtro de entidad ni filtra el radar por la empresa del usuario.

---

## FUERA DE ALCANCE

- Typeahead / lista oficial de entidades SECOP.
- Filtrar por NIT de la entidad.
- Varias entidades en un mismo filtro (OR).
- Cambiar el algoritmo de match % o el parámetro `company_name` de matching.

---

## TÍTULO JIRA

`2.3 [Frontend+Backend] Filtro de entidad contratante — reemplaza nombre de empresa en el radar`
