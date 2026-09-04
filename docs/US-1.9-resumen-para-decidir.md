# US 1.9 — Resumen para decidir en detalle de licitación

## USER STORY

**As a** personal de licitaciones  
**Quiero** ver al abrir una licitación un resumen fijo con lo esencial del proceso (cierre, monto, tipo, variables clave)  
**Para** decidir en segundos si vale la pena estudiarla en serio, sin hacer scroll por todo el panel de detalle.

---

## BACKGROUND

Hoy LicitIA permite:

- Listar licitaciones activas en el **dashboard** (`/dashboard`) y abrir el **detalle** (`TenderDetailPanel`).
- Ver información general del proceso (US 1.4): entidad, objeto, fechas, monto SECOP, POE, anticipo, plazo y tipo de contrato.
- Consultar documentos (US 1.3) y requisitos extraídos (US 1.5), incluida capacidad residual para obra (US 1.8).
- Marcar licitaciones como favoritas (US 1.7) desde la cabecera del detalle.

**Lo que no existe:**

- Ninguna **barra de decisión** que agrupe en un solo vistazo cierre, monto, tipo de proceso y variables clave de US 1.4.
- El usuario debe leer el bloque inicial del modal y bajar a "Información general" y "Requisitos" para armar mentalmente la foto del proceso.
- La CRPC estimada (US 1.8) solo aparece al hacer scroll hasta la sección de capacidad residual; no está visible al abrir el detalle.
- No hay jerarquía visual entre *"¿me interesa?"* y *"¿puedo ser hábil?"* — ambas preguntas compiten en el mismo scroll largo.

**Flujo operativo del licitador:**

1. Filtra en el dashboard por departamento, tipo o match de experiencia.
2. Abre una licitación prometedora y mira de inmediato: *¿cuánto queda para cerrar? ¿cuánto vale? ¿es obra o interventoría?*
3. Si el proceso parece viable, baja a pliego, requisitos y documentos.
4. Hoy esos datos existen pero **dispersos**; pierde tiempo en scroll antes de decidir si sigue investigando.

**Relación con otras US:**

| US | Relación |
|----|----------|
| 1.4 Variables licitación | Fuente de POE, anticipo, plazo y `contract_kind_label` en la barra |
| 1.7 Favoritas | Botón favorita visible junto al resumen (cabecera del modal) |
| 1.8 Capacidad residual | CRPC estimada en la barra solo si `ejecucion_obra` / `estudios_disenos_y_obra` |
| 1.10 (futura) | Panel *"¿Puedo ser hábil?"* — esta US no lo implementa |
| 1.11 (futura) | Tabs por capacidad — esta US no los implementa |
| 1.14 (futura) | Encaje / fit score — fuera de alcance |

---

## OBJETIVO

Añadir una **barra de resumen sticky** en el modal de detalle que responda en segundos: *¿vale la pena mirar esta licitación en serio?*

### Alcance MVP (etiqueta Jira: FRONTEND)

| Incluye | No incluye (futuro) |
|---------|---------------------|
| Barra sticky bajo cabecera del modal | Tabs de requisitos (US 1.11) |
| Días hasta cierre + fecha de cierre | Semáforo cumple / no cumple requisitos |
| Monto SECOP + tipo de proceso (`contract_kind_label`) | Encaje / fit score (US 1.14) |
| POE, anticipo %, plazo (si US 1.4 los tiene) | Cambios de backend o extracción |
| CRPC estimada si obra y hay datos para calcularla | Panel *"¿Puedo ser hábil?"* (US 1.10) |
| Acceso rápido: favorita + enlace SECOP | Página dedicada `/tenders/:id` |
| Reutilizar lógica existente (`computeCrpcEstimated`, summary US 1.4) | Gap analysis vs perfil empresa (US 1.5.3) |

---

## SOLUCIÓN

### A. Ubicación y comportamiento

`TenderDetailPanel` → dentro de `ComposedModal`, **después** de la cabecera (favorita + SECOP) y **antes** del objeto largo / bloques de requisitos.

- `position: sticky; top: 0` (o offset bajo cabecera fija del modal) al hacer scroll en el cuerpo del modal.
- Fondo sólido (`background`) + borde inferior para separar del contenido que pasa por debajo.
- En viewports estrechos: grid de 2 filas o wrap; sin scroll horizontal.

### B. Contenido de la barra

| Campo | Fuente | Fallback / regla |
|-------|--------|------------------|
| Días hasta cierre | `tender.closing_date` — cálculo en frontend | Ocultar chip si no hay fecha |
| Fecha de cierre | `tender.closing_date` formateada | *"Sin fecha de cierre"* |
| Monto | `tender.amount` | *"Monto no informado"* |
| Tipo de proceso | `summary.contract_kind_label` | Ocultar si no hay summary |
| POE | `summary` / campo POE de US 1.4 | Si no hay POE, mostrar monto SECOP como referencia |
| Anticipo | `summary.fields.advance_payment_percentage` | Ocultar si ausente |
| Plazo ejecución | `summary.fields.execution_duration` | Ocultar si ausente |
| CRPC estimada | `computeCrpcEstimated` (misma lógica que US 1.8) | Solo si `contract_kind` es obra; ocultar si no calculable |

**Formato visual:** chips o pares etiqueta-valor compactos (Carbon `Tag` / texto secundario). Sin párrafos largos ni citas a documentos.

### C. Wireframe

```
┌─ Detalle de licitación — CM-011-2026 ─────────────────────┐
│ [★ Favorita]                              Ver en SECOP ↗  │
├─ RESUMEN (sticky) ────────────────────────────────────────┤
│ Cierra en 12 días · 15/03/2026  │  $ 45.000 M  │  Obra   │
│ POE $ 45.000 M · Anticipo 20% · Plazo 18 meses           │
│ CRPC estimada $ 1.674 M          (solo si obra)            │
└───────────────────────────────────────────────────────────┘
│ … objeto, información general, requisitos (sin cambios) …  │
```

### D. Componente

`DecisionSummaryBar` (interno en `TenderDetailPanel.tsx` o archivo colindante):

```typescript
type DecisionSummaryBarProps = {
  tender: Tender
  summary: TenderSummary | null
}
```

- Props mínimas: `tender` + `summary` (ya cargados en el panel).
- No fetch adicional; no estado global nuevo.
- Reutilizar helpers existentes para CRPC y formateo de montos/fechas.

### E. API (MVP)

**Sin cambios de backend.** Solo consumo de datos ya disponibles en el panel:

- `tender` del listado / detalle.
- `summary` de US 1.4 (si ya se carga en `TenderDetailPanel`).
- Cálculo CRPC en cliente (misma función que sección residual US 1.8).

### F. Archivos a tocar (estimación)

| Archivo | Cambio |
|---------|--------|
| `components/TenderDetailPanel.tsx` | Componente `DecisionSummaryBar` + integración en layout del modal |
| `components/TenderDetailPanel.scss` | Estilos sticky, grid compacto, responsive |

---

## CRITERIOS DE ACEPTACIÓN

### MVP

**GIVEN** una licitación con fecha de cierre futura  
**WHEN** el usuario abre el detalle  
**THEN**

- Ve en la barra sticky los días restantes y la fecha de cierre sin hacer scroll.
- El chip de días usa lenguaje claro (*"Cierra en N días"* o *"Cierra hoy"* / *"Cerrada"* si aplica).

**GIVEN** que US 1.4 extrajo anticipo y plazo  
**WHEN** el usuario abre el detalle  
**THEN**

- Ve POE (o monto SECOP si no hay POE), anticipo y plazo en la misma barra.
- Los campos ausentes no muestran placeholder vacío ruidoso (se omiten).

**GIVEN** una licitación de **ejecución de obra** con POE y anticipo suficientes  
**WHEN** el usuario abre el detalle  
**THEN**

- Ve la CRPC estimada en la barra sticky (mismo valor que en sección residual US 1.8).

**GIVEN** una licitación de **interventoría** (u otro tipo distinto de obra)  
**WHEN** el usuario abre el detalle  
**THEN**

- La barra no muestra CRPC estimada.

**GIVEN** que el usuario hace scroll en el modal  
**WHEN** baja a requisitos, documentos o capacidad residual  
**THEN**

- La barra de resumen permanece visible (sticky) y no tapa contenido crítico del modal.

**GIVEN** que el usuario está en el detalle  
**WHEN** mira la cabecera del modal  
**THEN**

- Sigue viendo el botón favorita (US 1.7) y el enlace *"Ver en SECOP"* sin duplicar acciones en la barra sticky.

### Validación manual (gate de cierre)

| Paso | Resultado esperado |
|------|-------------------|
| Abrir licitación de **obra** con summary completo | Barra muestra cierre, monto, tipo, POE, anticipo, plazo y CRPC |
| Abrir licitación de **interventoría** | Barra sin CRPC; resto de campos según summary |
| Abrir licitación **sin summary** US 1.4 | Barra muestra al menos cierre y monto SECOP; sin error en consola |
| Scroll hasta requisitos | Barra sticky sigue visible |
| Viewport móvil (~375px) | Barra legible sin overflow horizontal |

---

## FUERA DE ALCANCE (MVP)

- Tabs por capacidad, checklists adicionales, panel *"¿Puedo ser hábil?"* (US 1.10, 1.11, 1.12).
- Backend nuevo o cambios en extracción / `EXTRACTION_VERSION`.
- Comparación con datos de la empresa o semáforos de cumplimiento.
- Página de detalle dedicada fuera del modal.
- Hero numérico financiero (CTd, umbrales) — US 1.13.

---

## DEFINICIÓN DE HECHO

- [ ] `DecisionSummaryBar` integrada en `TenderDetailPanel` con comportamiento sticky.
- [ ] Campos: cierre, días restantes, monto, tipo, POE/anticipo/plazo cuando existan en summary.
- [ ] CRPC en barra solo para obra (`ejecucion_obra` / `estudios_disenos_y_obra`) con datos suficientes.
- [ ] Sin fetch ni estado nuevo; reutiliza `tender`, `summary` y `computeCrpcEstimated`.
- [ ] Estilos responsive en `TenderDetailPanel.scss`.
- [ ] Validación manual según tabla anterior (obra, interventoría, sin summary).

---

## ESTIMACIÓN

| Ítem | Esfuerzo |
|------|----------|
| Componente `DecisionSummaryBar` + layout sticky | 0,5 d |
| Integración summary / tender / CRPC | 0,25 d |
| Estilos Carbon + responsive | 0,25 d |
| QA manual (3 escenarios) | 0,25 d |
| **Total MVP** | **~1 día** |

---

## TÍTULO JIRA SUGERIDO

`1.9 [Frontend] Resumen para decidir — sticky bar en detalle de licitación (cierre, monto, tipo, POE, CRPC obra)`
