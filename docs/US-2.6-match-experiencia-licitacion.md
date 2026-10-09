# US 2.6 — Match entre experiencia de la empresa y la licitación

**Jira:** `2.6 [Backend+Frontend] Match de experiencia contra la licitación — a qué procesos puede aplicar la empresa`

## USER STORY

**As a** personal de licitaciones con la experiencia de la empresa y actas cargadas  
**Quiero** ver qué licitaciones abiertas puede presentar mi empresa  
**Para** decidir con el objeto del contrato, las partidas del acta y los mínimos del pliego, sin un porcentaje de similitud.

---

## BACKGROUND

La empresa ya tiene sus contratos en experiencia (US 1.11 / carga de la hoja de socios) y, en algunos, el acta en PDF (US 2.1). De cada acta hoy se persiste el **objeto**. El PDF completo queda guardado. El pliego, cuando existe, ya deja en `tender_requirements` la experiencia general (porcentaje del presupuesto oficial en SMMLV, número de contratos, ventana de fechas si el texto la trae) y la experiencia específica (`specific_scope` y, si aplica, el porcentaje de un contrato).

Eso todavía no responde *¿a cuál licitación puede aplicar la empresa?* El match de `experience_matching.py` está apagado a propósito: compara textos parecidos, ignora tipo de contrato, tipología, SMMLV de participación y partidas, y en producción se cortaba a las 100 licitaciones más recientes por timeout.

La acreditación de un contrato ejecutado tiene dos lecturas distintas:

| Qué se compara | Lado licitación | Lado empresa |
|----------------|-----------------|--------------|
| **Paso 1. Objeto** | Objeto del proceso (SECOP) | Objeto del contrato, leído del acta |
| **Paso 2. Experiencia específica** | Actividad que exige el pliego | Partidas ejecutadas del acta: ítems, cantidades y descripción de lo ejecutado |

El objeto del acta dice qué contrato fue. Las partidas dicen qué se ejecutó. Un objeto que dice «mejoramiento de vía» no acredita «pavimento asfáltico» ni «concreto hidráulico» si esa actividad no está en las partidas.

**Épica 2:** 2.1 captura el acta → **2.6 decide si la empresa puede aplicar**.

---

## OBJETIVO

1. Leer cada acta **una vez** y guardar, aparte del objeto, las **partidas ejecutadas**.
2. Al abrir el radar, comparar esa experiencia ya guardada contra cada licitación abierta, en dos pasos, sin volver a abrir PDF y sin modelo de similitud.
3. Marcar la licitación como **Puede aplicar** solo cuando la experiencia general y la específica cumplen lo que el pliego pide. Si falta un dato, **No se puede afirmar**.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye |
|---------|------------|
| Extraer y persistir partidas del acta al subirla y en las actas ya guardadas | Reactivar el % de `experience_matching.py` |
| Paso 1: objeto del acta contra objeto de la licitación, y suma de SMMLV de participación contra el mínimo del pliego | Indicadores financieros del RUP |
| Paso 2: actividad exigida por el pliego contra el texto de partidas | Afirmar específica solo porque el término está en el objeto |
| Estados **Puede aplicar**, **No aplica**, **No se puede afirmar** | Tipología como único criterio para decir que puede aplicar |
| Filtro del radar «Puede aplicar» y contratos que sostienen el resultado | Corregir SMMLV históricos mal cargados en la hoja |
| Ventana de fechas y número de contratos cuando el pliego ya los trae | Carga masiva de actas en ZIP |

---

## SOLUCIÓN

### A. Preparar la experiencia una sola vez

Al subir o reemplazar el acta (`POST /experiences/{id}/specific-evidence`), y en un backfill de las actas ya almacenadas:

1. Seguir guardando el PDF y el **objeto** (US 2.1).
2. Leer el resto del acta y persistir las **partidas**: ítems, cantidades y descripción de lo ejecutado.
3. No comparar contra licitaciones en este momento.

| Campo | Uso |
|-------|-----|
| `specific_experience` | Objeto del contrato (ya existe) |
| `acta_partidas` | Texto de partidas ejecutadas. Vacío si el acta no las trae o no se pudieron leer |
| `amount_smmlv` | SMMLV de la participación, ya guardado |
| `contract_kind` | Tipo elegido o clasificado: obra, interventoría, estudios y diseños, estudios diseños y obra |
| `completion_date` | Fecha de finalización |

Un contrato sin `acta_partidas` puede entrar al paso 1. No puede acreditar el paso 2.

### B. Lo que ya está del lado licitación

No se reextrae el pliego en esta US.

| Dato | Origen |
|------|--------|
| Objeto del proceso | `tender.object_text` |
| Tipo de contrato | El mismo clasificador de cuatro tipos que usa el radar |
| Experiencia general | `min_percentage_budget` o `min_amount_smmlv`, `contracts_minimum`, ventana de fechas si el extractor ya la guardó |
| Experiencia específica | `specific_scope` y, si existe, `specific_min_percentage` |
| Presupuesto | `tender.amount`, para convertir el porcentaje del pliego a SMMLV del año del proceso |

Si el pliego no está leído, o el requisito no tiene número o actividad utilizable, esa licitación queda en **No se puede afirmar**.

### C. Comparar al abrir el radar

Para la empresa de la sesión, sobre las licitaciones activas. Solo se usan campos ya guardados. No se abre el PDF y no se llama al modelo de embeddings.

**Paso 1 — objeto contra objeto (experiencia general).** Un contrato entra a la suma cuando cumple todo esto:

- Tiene acta y objeto.
- Su `contract_kind` es uno de los cuatro y es el mismo de la licitación.
- El objeto del acta y el objeto de la licitación comparten al menos una tipología del catálogo de US 2.4, clasificada con las mismas reglas. Eso define el tipo de obra (vía con vía, puente con puente). La tipología sola no marca la licitación como aplicable.
- Si el pliego trae ventana de fechas, `completion_date` cae dentro. Si no trae ventana, no se inventa una.
- Tiene `amount_smmlv` de participación.

La suma de esos SMMLV se compara con el mínimo del pliego:

- Si el pliego pide un porcentaje del presupuesto oficial en SMMLV, el mínimo es ese porcentaje aplicado al presupuesto de la licitación, expresado en SMMLV.
- Si el pliego pide un número directo de SMMLV, se usa ese número.
- Si pide un mínimo y un máximo de contratos, la cantidad de contratos de la suma tiene que caer en ese rango.

**Paso 2 — experiencia específica del pliego contra las partidas.** Sobre los contratos que entraron al paso 1:

- Se toman las actividades nombradas en `specific_scope` (pavimento asfáltico, concreto hidráulico, vía primaria, y las demás que el pliego deje por escrito).
- Un contrato acredita la específica cuando esas actividades aparecen en `acta_partidas`, ignorando mayúsculas y tildes.
- Si el pliego las une con **o**, basta una. Si las une con **y**, tienen que estar todas.
- Que el término esté solo en el objeto no acredita la específica.
- Si además el pliego pide que uno de esos contratos valga un porcentaje del presupuesto (por ejemplo 70 %), el `amount_smmlv` de un contrato que ya pasó las partidas tiene que alcanzar ese porcentaje.

**Resultado de la licitación:**

| Estado | Cuándo |
|--------|--------|
| **Puede aplicar** | El paso 1 cumple el mínimo y el número de contratos, y el paso 2 acredita la específica |
| **No aplica** | Pliego, actas y partidas alcanzan para calcular, y el paso 1 o el paso 2 no llega |
| **No se puede afirmar** | Falta pliego, presupuesto para convertir el porcentaje, acta, partidas, tipo de contrato, fecha cuando el pliego exige ventana, o la actividad de la específica no quedó en términos buscables |

**Puede aplicar** exige los dos pasos. Un paso cumplido y el otro imposible de calcular deja **No se puede afirmar**.

### D. Ejemplo de aceptación

Pliego de interventoría. Presupuesto oficial equivalente a **300 SMMLV**. Experiencia general: suma ≥ **100 %** (300 SMMLV). Experiencia específica: al menos un contrato ≥ **70 %** (210 SMMLV) y la actividad «pavimento asfáltico» o «concreto hidráulico» de vía primaria.

Contrato **1232 DE 2006**: interventoría, objeto «mejoramiento de la vía Las Margaritas–Cauya», participación **222 SMMLV**, finalización 10/02/2007.

| Comprobación | Resultado |
|--------------|-----------|
| Paso 1, tipo y objeto | Entra: interventoría de vía contra interventoría de vía |
| Paso 1, suma | 222 < 300 → la general no alcanza |
| Paso 2, valor | 222 ≥ 210, el valor de un contrato sí alcanza |
| Paso 2, partidas | Si las partidas no dicen pavimento asfáltico ni concreto hidráulico, la específica no se acredita aunque el objeto diga «vía» |
| Estado | **No aplica** si las partidas se leyeron. **No se puede afirmar** si ese contrato no tiene partidas guardadas |

Si otro contrato de interventoría de vía, con acta, suma los SMMLV que faltan, el paso 1 pasa. El paso 2 sigue en no hasta que las partidas de alguno nombren la actividad exigida.

### E. API y radar

| Método | Cambio |
|--------|--------|
| `POST /experiences/{id}/specific-evidence` | Además del objeto, llena `acta_partidas` |
| `GET /experiences` | Devuelve si la fila tiene partidas (`acta_partidas` presente o un flag) |
| `GET /tenders` | Con la empresa de la sesión, cada ítem trae `experience_fit`: `puede_aplicar`, `no_aplica` o `no_se_puede_afirmar`; la suma de SMMLV; el mínimo pedido; y los contratos que entraron, con número, entidad, SMMLV y si acreditaron partidas |
| `GET /tenders?experience_fit=puede_aplicar` | Solo las que puede aplicar |

El parámetro `match_experience` del match semántico sigue sin efecto.

En el radar, cada fila muestra el estado en palabras, no un porcentaje. **Puede aplicar** abre el detalle de los dos pasos y los contratos. El filtro **Puede aplicar** deja solo ese estado. Las licitaciones en **No se puede afirmar** siguen en el listado general, con el dato que falta (sin pliego, sin partidas, sin presupuesto).

Copy junto al filtro: *Puede aplicar cuando la suma de SMMLV cubre la experiencia general del pliego y las partidas del acta cubren la experiencia específica. Si falta el pliego o las partidas, no se afirma.*

### F. Relación con otras US

| US | Relación |
|----|----------|
| 2.1 Acta | Esta US lee el PDF ya guardado y añade partidas. El objeto sigue siendo el del acta |
| 2.4 Tipología | Solo en el paso 1, para el tipo de obra. No decide **Puede aplicar** |
| 1.5 Requisitos | Usa `tender_requirements` ya extraídos. No vuelve a interpretar el pliego |
| 1.5.3 Semáforo | Esta US cubre experiencia general y específica. La financiera queda fuera |
| `experience_matching.py` | Permanece apagado. Esta US no escribe `experience_match_score` |

---

## ACCEPTANCE CRITERIA

**GIVEN** un acta con objeto y con partidas de obra ejecutada  
**WHEN** se sube en un contrato  
**THEN** el objeto queda en `specific_experience` y las partidas quedan en `acta_partidas`, por separado.

**GIVEN** un acta ya guardada cuyo objeto existe y `acta_partidas` está vacío  
**WHEN** corre el backfill de esta US  
**THEN** las partidas se llenan desde el PDF almacenado, sin pedir el archivo otra vez.

**GIVEN** el usuario abre el radar  
**WHEN** se calcula el match de su empresa  
**THEN** no se invoca el modelo de similitud de `experience_matching.py` y no se muestra un porcentaje de match.

**GIVEN** una licitación de interventoría de vía cuyo pliego pide suma ≥ 300 SMMLV y un contrato ≥ 210 SMMLV con pavimento asfáltico o concreto hidráulico  
**AND** la empresa tiene el contrato 1232 DE 2006 (interventoría, objeto de mejoramiento de vía, 222 SMMLV) con partidas que no mencionan pavimento asfáltico ni concreto hidráulico  
**WHEN** se evalúa  
**THEN** el contrato entra al paso 1, la suma no alcanza 300, la específica no se acredita, y el estado es **No aplica**.

**GIVEN** el mismo pliego  
**AND** las partidas de ese contrato dicen carpeta asfáltica o concreto hidráulico  
**AND** la suma de los contratos que pasaron el paso 1 sigue bajo 300 SMMLV  
**WHEN** se evalúa  
**THEN** el paso 2 acredita la actividad y el valor de ese contrato, el paso 1 no cumple, y el estado sigue **No aplica**.

**GIVEN** el mismo pliego  
**AND** las partidas nombran la actividad exigida  
**AND** la suma de SMMLV de los contratos que pasaron el paso 1 es al menos 300, dentro del número de contratos que pida el pliego  
**WHEN** se evalúa  
**THEN** el estado es **Puede aplicar** y el detalle lista esos contratos con su SMMLV y la actividad encontrada en las partidas.

**GIVEN** la actividad exigida aparece en el objeto del acta y no en las partidas  
**WHEN** se evalúa el paso 2  
**THEN** ese contrato no acredita la experiencia específica.

**GIVEN** el pliego pide pavimento asfáltico **o** concreto hidráulico  
**AND** las partidas traen solo una de las dos  
**WHEN** se evalúa el paso 2  
**THEN** la actividad queda acreditada.

**GIVEN** el pliego pide las dos actividades unidas con **y**  
**AND** las partidas traen solo una  
**WHEN** se evalúa el paso 2  
**THEN** la específica no se acredita.

**GIVEN** el pliego limita los contratos a una ventana de fechas  
**AND** la finalización del contrato cae fuera  
**WHEN** se arma la suma del paso 1  
**THEN** ese contrato no entra a la suma.

**GIVEN** el pliego no trae ventana de fechas  
**WHEN** se arma la suma  
**THEN** no se descarta el contrato por antigüedad.

**GIVEN** la licitación no tiene pliego leído, o no tiene presupuesto para convertir el porcentaje a SMMLV, o ningún contrato candidato tiene partidas  
**WHEN** se evalúa  
**THEN** el estado es **No se puede afirmar** y no aparece al filtrar **Puede aplicar**.

**GIVEN** un contrato sin tipo de contrato, o con tipo distinto al de la licitación  
**WHEN** se arma el paso 1  
**THEN** ese contrato no entra a la suma.

**GIVEN** el filtro **Puede aplicar** está activo  
**WHEN** el radar lista licitaciones  
**THEN** solo muestra las de estado `puede_aplicar`, cada una con los contratos que la sostienen.

**GIVEN** `GET /tenders` de la empresa de la sesión  
**WHEN** responde  
**THEN** cada licitación trae `experience_fit` con uno de `puede_aplicar`, `no_aplica`, `no_se_puede_afirmar`.

---

## FUERA DE ALCANCE

- Porcentaje de similitud y embeddings.
- Indicadores financieros, liquidez, endeudamiento y capital de trabajo.
- Corregir en la hoja los SMMLV que no son la participación del contrato.
- Marcar **Puede aplicar** usando solo tipología, solo objeto o solo el valor, sin las partidas.
- Releer el PDF del acta o del pliego en cada apertura del radar.
- Obligar acta en todos los contratos para ver el listado general de licitaciones.

---

## TÍTULO JIRA

`2.6 [Backend+Frontend] Match de experiencia contra la licitación — a qué procesos puede aplicar la empresa`
