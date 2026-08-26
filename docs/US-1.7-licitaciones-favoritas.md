# US 1.7 — Sección de licitaciones favoritas

## USER STORY

**As a** personal de licitaciones  
**Quiero** marcar licitaciones como favoritas después de revisar su detalle y documentos, y consultarlas en una sección aparte  
**Para** organizar las oportunidades que quiero estudiar con más calma antes de decidir si oferto, sin perderlas en el listado general del dashboard.

---

## BACKGROUND

Hoy LicitIA permite:

- Listar licitaciones activas (Publicado + apertura Abierto) en el **dashboard** (`/dashboard`).
- Abrir el **detalle** (`TenderDetailPanel`): información general (US 1.4), documentos (US 1.3), requisitos (US 1.5).
- Filtrar por fecha, departamento, tipo de contrato y matching de experiencia.

**Lo que no existe:**

- Ningún mecanismo de favoritos / guardados / marcadores en frontend ni backend.
- Mencionado como deuda en `Análisis de features actuales y mejoras.md` y `FEATURES_MVP_MAXIMO_VALOR.md`.
- No hay autenticación JWT; la identidad del usuario es el **email en `localStorage`** (`licitia_user_email`), igual que perfil, onboarding y soporte.

**Flujo operativo del licitador:**

1. Explora el dashboard y filtra por match o departamento.
2. Abre licitaciones prometedoras, lee objeto, pliego y anexo.
3. Decide *“esta la reviso después / esta sí la licito”* — hoy no hay forma de guardar esa decisión.
4. Al día siguiente vuelve al dashboard y debe buscar de nuevo entre ~200 procesos.

**Relación con otras US:**

| US | Relación |
|----|----------|
| 1.3 Documentos en UI | El usuario marca favorita **después** de ver anexos/pliego |
| 1.4 / 1.5 Detalle | El panel de detalle es el lugar natural del botón favorito |
| Auth JWT (futura) | MVP usa `localStorage`; migración a API cuando exista usuario autenticado |
| Purge licitaciones inactivas | Favoritos pueden apuntar a licitaciones que dejen de existir en API → estado “no disponible” |

---

## OBJETIVO

Ofrecer una **lista curada de licitaciones favoritas**, separada del explorador general, con marcado/desmarcado persistente en la sesión del usuario (MVP: navegador).

### Alcance MVP (etiqueta Jira: FRONTEND)

| Incluye | No incluye (futuro) |
|---------|---------------------|
| Botón favorito en detalle de licitación | Sincronización multi-dispositivo (requiere backend) |
| Nueva entrada en sidebar: **Favoritas** | Notas o etiquetas por favorita |
| Página `/favorites` con tabla reutilizando `TenderTable` | Favoritos compartidos en equipo |
| Persistencia `localStorage` por email de usuario | Recordatorios / alertas de cierre |
| Indicador visual en fila del dashboard (opcional P1) | Orden manual drag-and-drop |
| Quitar favorito desde lista o detalle | Exportar favoritos a Excel |

---

## SOLUCIÓN

### A. Modelo de datos (MVP — solo cliente)

```typescript
// localStorage key: licitia_favorite_tenders:{email}
type FavoriteTenderRef = {
  tender_id: string          // UUID LicitIA
  external_id: string        // CO1.REQ.xxxxx — para debug y resiliencia
  reference?: string | null  // CM-011-2026 — snapshot al marcar
  marked_at: string          // ISO 8601
}
```

- Al **marcar**: guardar `tender_id` + metadatos mínimos.
- Al **desmarcar**: eliminar por `tender_id`.
- Al **cargar favoritos**: leer IDs → `GET /api/v1/tenders/{id}` por cada una (o endpoint batch futuro).
- Si la API devuelve **404** (licitación purgada/inactiva): mostrar fila atenuada *“Ya no disponible”* con opción de quitar de favoritos.

### B. Hook reutilizable

`useFavoriteTenders()` en `frontend/src/hooks/`:

- `isFavorite(tenderId): boolean`
- `toggleFavorite(tender): void`
- `favoriteIds: string[]`
- `favoriteTenders: Tender[]` (resueltos vía API)
- Escuchar cambios de `licitia_user_email` (misma pestaña vía custom event o re-read al montar).

### C. UI — Marcar / desmarcar

**Ubicación principal:** cabecera de `TenderDetailPanel`, junto a “Ver proceso en SECOP”.

- Icono Carbon: `Star` / `StarFilled`.
- Estados: *“Agregar a favoritas”* / *“Quitar de favoritas”*.
- Feedback: toast o `InlineNotification` breve (2 s).

**Opcional P1:** columna o icono en `TenderTable` del dashboard (sin abrir detalle).

### D. UI — Sección Favoritas

- Ruta: `/favorites`
- Sidebar (`AppLayout`): ítem **Favoritas** con icono `Star` (entre Inicio y Experiencias).
- Página `Favorites.tsx`:
  - Reutiliza `TenderTable` + `TenderDetailPanel` (mismo comportamiento que dashboard).
  - Orden por defecto: `marked_at` descendente (última marcada primero).
  - `EmptyState`: *“Aún no tienes favoritas. Explora el dashboard y marca las licitaciones que quieras estudiar.”*
  - Contador en título: *“Favoritas (3)”*.

### E. API (MVP)

**Sin cambios de backend.** Solo consumo de endpoints existentes:

- `GET /api/v1/tenders/{id}` — hidratar cada favorita.
- Listado general del dashboard no se modifica.

**Fase 2 (cuando exista JWT):** tabla `user_favorite_tenders`, `POST/DELETE/GET /api/v1/favorites`.

### F. Archivos a tocar (estimación)

| Archivo | Cambio |
|---------|--------|
| `hooks/useFavoriteTenders.ts` | **Nuevo** — persistencia y estado |
| `pages/Favorites.tsx` | **Nuevo** — vista favoritas |
| `App.tsx` | Ruta `/favorites` |
| `layouts/AppLayout/AppLayout.tsx` | Ítem navegación |
| `components/TenderDetailPanel.tsx` | Botón favorito |
| `components/TenderTable.tsx` | (P1) columna estrella |
| `api/client.ts` | (opcional) helper `getTenderById` si no existe |

---

## CRITERIOS DE ACEPTACIÓN

### MVP

**GIVEN** que el usuario está en el dashboard y abre el detalle de una licitación activa  
**WHEN** hace clic en *“Agregar a favoritas”*  
**THEN**

- El icono pasa a estado activo (relleno).
- La licitación queda guardada en `localStorage` asociada a su email.
- Si vuelve a abrir el mismo detalle, el estado sigue siendo favorita.

**GIVEN** que el usuario tiene al menos una licitación favorita  
**WHEN** navega a **Favoritas** en el sidebar  
**THEN**

- Ve solo sus licitaciones marcadas en una tabla con las mismas columnas clave que el dashboard.
- Puede abrir el detalle (documentos, resumen, requisitos) desde esa lista.
- Ve el conteo de favoritas en el título de la página.

**GIVEN** que una licitación está en favoritas  
**WHEN** el usuario hace clic en *“Quitar de favoritas”* (desde detalle o desde la lista)  
**THEN**

- Desaparece de la sección Favoritas.
- El icono en detalle vuelve a estado inactivo.

**GIVEN** que una licitación favorita fue purgada del sistema (ya no es Publicado+Abierto)  
**WHEN** el usuario abre Favoritas  
**THEN**

- Ve un aviso de que la oportunidad ya no está disponible (no se muestra como licitable).
- Puede eliminarla de favoritos con un clic.

**GIVEN** que el usuario cierra sesión (`handleLogout` en `AppLayout`)  
**WHEN** inicia sesión con **otro** email  
**THEN**

- Ve las favoritas del nuevo usuario (listas separadas por email), no las del anterior.

### Validación manual (gate de cierre)

| Paso | Resultado esperado |
|------|-------------------|
| Marcar 2 licitaciones desde detalle | Aparecen en `/favorites` |
| Recargar navegador | Favoritas persisten |
| Quitar 1 favorita | Lista queda en 1 |
| Dashboard sin filtro “solo favoritas” | Listado general no se reduce (favoritos es sección aparte) |

---

## FUERA DE ALCANCE (MVP)

- Backend / base de datos de favoritos.
- Filtro “Solo favoritas” en el dashboard principal (evaluar US 1.7.1).
- Notas, prioridad, o carpetas de favoritos.
- Sincronización entre dispositivos.

---

## DEFINICIÓN DE HECHO

- [ ] Hook `useFavoriteTenders` con tests unitarios básicos.
- [ ] Botón favorito en `TenderDetailPanel`.
- [ ] Página `/favorites` + entrada en sidebar.
- [ ] Persistencia por `licitia_user_email`.
- [ ] Manejo de favoritas huérfanas (404).
- [ ] Validación manual según tabla anterior.

---

## ESTIMACIÓN

| Ítem | Esfuerzo |
|------|----------|
| Hook + persistencia | 0,5 d |
| Página Favoritas + navegación | 0,5 d |
| Botón en detalle + estilos Carbon | 0,5 d |
| Casos borde (vacío, 404, logout) | 0,5 d |
| **Total MVP** | **~2 días** |

---

## TÍTULO JIRA SUGERIDO

`1.7 [Frontend] Licitaciones favoritas — marcar, listar y persistir en sección aparte (MVP localStorage)`
