# US 1.4 — Extracción de variables generales de licitación

## Objetivo

Mostrar en el detalle de cada licitación la información general acordada, con fuentes trazables y reglas de aplicabilidad por tipo de contrato.

## Mapa de campos

| Prioridad | Campo | Fuente |
|-----------|-------|--------|
| P0 | Fecha presentación oferta | SECOP (`closing_date`) |
| P0 | Trabajo a realizar | SECOP (`object_text`) |
| P0 | Ubicación administrativa | SECOP (`department`, `municipality`) |
| P0 | Costo total | SECOP (`amount`) o presupuesto XLSX si hay total oficial |
| P0 | % AIU | Presupuesto XLSX — **solo ejecución de obra** |
| P1 | Duración | Pliego PDF |
| P1 | % anticipo | Pliego PDF |
| P1 | Forma de pago | Pliego PDF |
| P1 | Ubicación exacta | SECOP (administrativa en MVP) |
| P2 | Precios con ajuste | Pliego PDF |
| P2 | Grupos o lotes | Pliego PDF |
| P2 | Relación contrato vs presupuesto | Pliego + presupuesto |
| P2 | Costo mensual | Calculado (`costo_total ÷ duración en meses`) |
| P3 | Fecha adjudicación | Pliego PDF (SECOP cuando exista) |

## Regla AIU

- **Ejecución de obra**: extraer % AIU del Formulario 1 / presupuesto XLSX.
- **Interventoría** y **estudios y diseños**: mostrar **“No aplica”** (no es error de extracción).

## API

- `GET /api/v1/tenders/{id}/summary` — devuelve campos estructurados; persiste caché en `tender_summaries`.
- Query `?refresh=true` fuerza recomputo.

## Implementación

- Backend: `app/services/tender_summary/`
- Modelo: `tender_summaries`
- UI: sección **Información general** en `TenderDetailPanel`
