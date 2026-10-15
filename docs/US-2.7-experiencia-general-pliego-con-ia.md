# US 2.7 — Experiencia general del pliego leída con IA

**Jira:** `2.7 [Backend] Experiencia general del pliego con IA — párrafo, porcentaje, ventana y número de contratos`

## USER STORY

**As a** personal de licitaciones con el RUP y las actas cargadas  
**Quiero** que el mínimo de experiencia general salga de una lectura fiel del pliego  
**Para** que el match de SMMLV use el porcentaje, la ventana y el número de contratos que el proceso pide de verdad, también cuando el pliego no usa las frases fijas.

---

## BACKGROUND

La US 2.6 ya compara la suma de SMMLV de la empresa contra la experiencia general guardada. Esa sección vive en `tender_requirements.requirements_json`, clave `experiencia_general`, y el radar la lee sin volver a abrir el PDF.

Hoy el proceso de fondo abre el pliego guardado, lee el texto en el servidor y busca la sección con reglas fijas. No llama a OpenAI. Encuentra bien un «100 % del presupuesto oficial» o «últimos 5 años» escritos de forma clara. Si el pliego lo redacta de otra manera, parte el requisito en varios párrafos o no titula la sección «experiencia general», el mínimo no queda guardado y la licitación se queda en **No se puede afirmar**.

El párrafo de esa sección, `requirement_description`, también se guarda en esa lectura. El match de SMMLV no lo usa. Comparar ese párrafo con el objeto de las actas queda fuera de esta US.

Abrir el detalle de una licitación sigue calculando el pliego completo (US 1.5), con indicadores, puntaje y requisitos legales. Esta US no adelanta ese detalle. Solo afina la experiencia general que el radar necesita antes de que alguien abra la licitación.

---

## OBJETIVO

1. En el mismo proceso de fondo, localizar el apartado de experiencia general y enviar esas páginas impresas a OpenAI.
2. Guardar el párrafo copiado tal cual, el porcentaje, el monto en SMMLV, la ventana en años y el número de contratos en la sección `experiencia_general` que el match ya consume.
3. No inventar un número. Si la página no lo escribe, el campo queda vacío y el radar sigue en **No se puede afirmar**.

### Alcance MVP (BACKEND)

| Incluye | No incluye |
|---------|------------|
| Una llamada a `gpt-4o-mini` por pliego, con la página del apartado y las dos siguientes, en imagen | Enviar el pliego completo, los indicadores, el puntaje o los requisitos legales |
| Releer las filas que se guardaron desde el texto del PDF | Volver a llamar al modelo si esa licitación ya tiene la lectura desde las páginas impresas |
| Párrafo copiado tal cual, porcentaje del presupuesto, monto en SMMLV, ventana en años, mínimo y máximo de contratos, y la tabla de porcentajes si cambia según el número de contratos | Comparar el párrafo con el objeto de las actas |
| Proceso de fondo: a los 3 minutos vacía los pliegos ya guardados, uno por uno; cada 3 horas reintenta los que fallaron | Tratar un «cinco (5)» de códigos del RUP como máximo de contratos, o un valor en pesos como SMMLV |
| Si la llamada falla, dejar la fila como está y reintentar | Cambiar la fórmula del match de SMMLV |

---

## SOLUCIÓN

### A. Qué se envía

Para cada licitación activa del radar que ya tiene pliego guardado y todavía no tiene la experiencia general marcada como leída con IA:

1. El texto del PDF solo sirve para encontrar la página que dice «experiencia general».
2. Esa página y las dos siguientes se envían como imagen, en detalle alto.
3. Si el encabezado no aparece, se usa el texto del apartado y esa fila no se vuelve a intentar.
4. Pedir a `gpt-4o-mini` un JSON con estas claves, y nada más:

| Clave | Contenido |
|-------|-----------|
| `requirement_description` | Apartado de experiencia general, copiado tal cual de lo impreso |
| `min_percentage_budget` | Porcentaje del presupuesto oficial, si el pliego lo da |
| `min_amount_smmlv` | Monto directo en SMMLV, solo cuando el pliego escribe un número |
| `time_window_years` | Años de la ventana, si el texto la trae |
| `contracts_minimum` | Mínimo y máximo de contratos, si el texto los dice |
| `experience_value_tiers` | Porcentaje según el número de contratos, si el pliego usa esa tabla |

Si un dato no está impreso en esas páginas, el valor va vacío. El modelo no completa con un porcentaje típico ni con una ventana habitual. El número de contratos sale de la frase que dice cuántos se presentan. Un conteo de códigos del RUP no es el máximo. Un valor en pesos no es un monto en SMMLV.

### B. Dónde se guarda

En la misma fila de `tender_requirements`, dentro de `experiencia_general`. Cada dato conserva valor, texto para mostrar y la cita.

La fila queda marcada como experiencia general leída desde las páginas impresas. Las pasadas siguientes la saltan. Una licitación nueva entra cuando su pliego queda guardado, una sola vez.

Las filas leídas antes desde el texto del PDF se vuelven a leer desde las páginas. Si el encabezado no se encuentra, se guarda la lectura de texto y no se reintenta.

Si la llamada falla, la fila queda como estaba y se reintenta en una pasada posterior.

### C. Qué hace el radar

El match de SMMLV no cambia de fórmula. Sigue usando el porcentaje o el monto, la ventana y el número de contratos guardados en esa sección. Con una lectura más fiel, menos licitaciones se quedan en **No se puede afirmar** por no haber encontrado el mínimo.

### D. Costo

Precio vigente de `gpt-4o-mini`: 0,15 dólares por millón de tokens de entrada y 0,60 por millón de salida.

| Caso | Costo |
|------|--------|
| Un pliego | Cerca de 1,5 centavos de dólar, una sola vez |
| Las 97 licitaciones activas que hoy ya tienen pliego | Cerca de 1,50 dólares en total |
| Una licitación nueva | Cerca de 1,5 centavos de dólar, al guardar su pliego |

El cargo sale de la misma cuenta de API que ya usa LicitIA. Cada página, en detalle alto, pesa unas 25.000 a 37.000 tokens. Tres páginas explican el costo frente a la lectura que solo enviaba texto.

---

## ACCEPTANCE CRITERIA

**GIVEN** un pliego con texto en el que la experiencia general pide el 100 % del presupuesto oficial en los últimos 5 años, con mínimo 1 y máximo 3 contratos  
**WHEN** corre la lectura con IA  
**THEN** `experiencia_general` guarda el párrafo, el porcentaje 100, la ventana 5 y el rango 1 a 3, marcada como leída con IA.

**GIVEN** el mismo pliego redactado sin el título exacto «experiencia general» y con el porcentaje escrito en palabras  
**WHEN** corre la lectura con IA  
**THEN** el porcentaje, la ventana y el número de contratos quedan guardados si el fragmento los contiene.

**GIVEN** el fragmento no trae un porcentaje, un monto en SMMLV ni una ventana  
**WHEN** el modelo responde  
**THEN** esos campos quedan vacíos y no se guarda un número supuesto.

**GIVEN** el apartado está impreso y el texto interno del PDF está dañado  
**WHEN** corre la lectura  
**THEN** el párrafo, el número de contratos y el objeto se copian de las páginas, y un código del RUP no se guarda como máximo de contratos.

**GIVEN** una licitación cuya experiencia general ya fue leída desde las páginas impresas  
**WHEN** corre la pasada siguiente  
**THEN** no se vuelve a enviar el pliego al modelo.

**GIVEN** una licitación nueva cuyo pliego acaba de guardarse  
**WHEN** corre la pasada siguiente del proceso de fondo  
**THEN** se lee una vez y la sección queda disponible para el match de SMMLV.

**GIVEN** la llamada a OpenAI falla y la fila ya tenía una lectura  
**WHEN** termina esa pasada  
**THEN** la fila queda como estaba y la licitación se reintenta después.

**GIVEN** el radar evalúa una licitación con la experiencia general ya leída con IA  
**WHEN** calcula el match  
**THEN** usa el porcentaje, la ventana y el número de contratos guardados, sin abrir el PDF y sin una segunda llamada al modelo.

---

## FUERA DE ALCANCE

- Comparar el párrafo de experiencia general con el objeto de las actas.
- Extraer con IA la experiencia específica, los indicadores, el puntaje o la capacidad jurídica.
- Volver a calcular el pliego completo al abrir el detalle.
- Cambiar la suma de SMMLV, la ventana o el rango de contratos del match.

---

## TÍTULO JIRA

`2.7 [Backend] Experiencia general del pliego con IA — párrafo, porcentaje, ventana y número de contratos`
