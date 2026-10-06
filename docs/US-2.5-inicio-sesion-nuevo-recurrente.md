# US 2.5 — Inicio de sesión: usuario nuevo vs recurrente

**Jira:** `2.5 [Backend+Frontend] Alta vs vuelta — inicio de sesión para usuario nuevo y recurrente`

## USER STORY

**As a** personal de licitaciones que entra a LicitIA  
**Quiero** un camino claro si soy nuevo y otro si ya tengo cuenta  
**Para** configurar el radar la primera vez (empresa, RUP, contacto) y, cuando vuelvo, entrar a mi portafolio sin repetir el asistente ni sentir que el producto no me reconoce.

---

## BACKGROUND

Hoy **no hay cuenta con contraseña**. La identidad es el email en `leads` más `localStorage`. `/dashboard` no está cerrado.

Hay dos puertas que se pisan:

| Superficie | Qué hace hoy | Qué entiende el usuario |
|------------|----------------|-------------------------|
| Landing `/` CTA **Log in** | **Alta**: razón social + email → `POST /leads` → flags de onboarding → dashboard + **asistente** (welcome → RUP → contacto) | Cree que ya tiene cuenta |
| Landing “¿Ya tienes cuenta?” | Link a `/login` | Correcto, pero choca con el CTA |
| `/login` | Solo email; si está en `leads` entra; si no, error | Recurrente |
| “Saltar y ver el dashboard” | Navega a `/` (la misma landing) | Roto |

Problemas de producto:

- El botón de **alta dice Log in**.
- Si el mismo email entra otra vez **por la landing**, se trata como nuevo y **puede reabrir el asistente**.
- El recurrente **no prueba** que el correo es suyo: quien conozca el email entra (RUP incluido).
- Al hacer logout se borra `licitia_onboarding_completed`. Si no hay RUP, el recurrente **ve FirstSessionHome** otra vez (parece usuario nuevo).
- Logout **no limpia** ciudad, teléfono, sectores ni `licitia_portfolio_skipped`.
- `CompanyNameStep` ya no está en el asistente: la empresa sale de la landing. Bien; hay que no volver a pedirla en la vuelta.

**Épica 2:** 2.0 perfil → 2.1 acta → 2.3 entidad → 2.4 tipología → **2.5 quién entra y cómo**.

**Asistente** = overlay de configuración (`OnboardingWizard`): bienvenida → cargar RUP → nombre / celular / ciudad / sectores. No es una tecnología aparte.

---

## OBJETIVO

1. **Separar alta y vuelta** en copy, rutas y comportamiento.
2. Usuario **nuevo**: formulario de crear cuenta → asistente una sola vez → radar.
3. Usuario **recurrente**: “Ya tengo cuenta” → email + **código de un solo uso** → dashboard según portafolio (con RUP = radar; sin RUP = FirstSessionHome, **sin** asistente completo).
4. No reabrir el asistente si el lead ya existe o la empresa ya tiene experiencias.

### Alcance MVP (BACKEND + FRONTEND)

| Incluye | No incluye |
|---------|------------|
| Copy: **Empezar / Crear cuenta** vs **Ya tengo cuenta** | Contraseña, “olvidé mi clave”, Google / Microsoft |
| Landing = solo alta; si el email **ya está** en `leads` → no crear otra vez; ir a login | Identity Provider / JWT de largo plazo (se puede añadir token de sesión corto) |
| `/login` = solo vuelta; si el email **no está** → ir a alta (no solo un error muerto) | Cerrar el dashboard a invitados (el skip a radar sin cuenta puede seguir) |
| Código OTP por correo para recurrentes (y opcionalmente al confirmar el email nuevo) | SMS / WhatsApp OTP en esta US |
| Al entrar: si `GET /experiences` tiene filas → radar; si no → FirstSessionHome + banner RUP | Rediseñar el contenido del asistente (pasos 1–3 se mantienen) |
| No disparar `licitia_start_onboarding` en login ni en alta de email ya existente | Perfil de varios usuarios por la misma empresa |
| Arreglar “Saltar y ver el dashboard” → `/dashboard` | Facturación / trial Pro+ |
| Logout borra identidad **y** skip/sectores/ciudad/teléfono de esa sesión de navegador | Migrar leads históricos a “password” |

---

## SOLUCIÓN

### A. Producto — Dos modos, no dos productos

**Landing (`/`)** — usuario nuevo

- Campos: **Razón social** + **Correo empresarial**.
- CTA: **Empezar** o **Crear cuenta** (nunca “Log in” / “Iniciar sesión”).
- Link único: **¿Ya tienes cuenta? Entra aquí** → `/login`.
- Skip: **Ver el radar sin cuenta** → `/dashboard` de verdad (invitado; sin asistente).

Si el email **ya existe** en `leads`:

- No setear `licitia_start_onboarding`.
- Mensaje: *Esta cuenta ya está. Entra con tu correo.*
- CTA del mensaje → `/login` con el email precargado.

Si el email **no existe**:

- `POST /leads` (como hoy).
- Marcar alta de esta sesión (`licitia_start_onboarding` **solo aquí**).
- Ir a `/dashboard` y abrir el **asistente una vez**.

**Login (`/login`)** — usuario recurrente

- Título: **Bienvenido de nuevo**.
- Campo: correo.
- CTA: **Enviar código** (no “Iniciar sesión” a ciegas).
- Si no existe: *No hay cuenta con este correo.* Link **Crear cuenta** → landing con email precargado.
- Si existe: enviar código de 6 dígitos (TTL ~10 min, un uso). Segunda pantalla: código + **Entrar**.
- **No** abrir el asistente.
- Restaurar del lead: nombre, empresa, teléfono, ciudad, sectores (como hoy el GET check).

### B. Producto — Qué ve al entrar

| Condición | Pantalla |
|-----------|----------|
| Alta nueva, sin RUP | Asistente (welcome → RUP → contacto) |
| Alta nueva, saltó welcome | Radar + portafolio saltado (igual que hoy) |
| Recurrente con experiencias RUP en backend | Radar listo (US 1.11+) |
| Recurrente sin experiencias | **FirstSessionHome** + banner “Cargar RUP” — **no** welcome del asistente |
| Invitado (skip landing) | Radar sin identidad; banner opcional de crear cuenta |

El asistente **solo** arranca si `licitia_start_onboarding=true` **y** no hay experiencias para esa empresa **y** el lead no está marcado como onboarding cerrado.

### C. Backend — identidad mínima

Reutilizar `leads`. Añadir lo necesario para OTP (tabla o columnas), p. ej.:

- `POST /api/v1/auth/request-code` `{ email }` → 200 genérico (no revelar si existe, **o** en MVP sí revelar para el copy de “crea cuenta”; preferir revelar en login para no bloquear alta).
- `POST /api/v1/auth/verify-code` `{ email, code }` → ok + payload del lead.
- Código: 6 dígitos, hash en servidor, expiración, invalidar al usar, rate limit (p. ej. 3 envíos / 15 min).
- Email: plantilla corta *Tu código LicitIA es ######. Caduca en 10 minutos.*

Alta nueva: el `POST /leads` sigue; el OTP del recurrente es obligatorio en `/login`. En alta, el MVP **no exige** OTP antes del asistente (menos fricción el día 0); fase 2.5.2 puede pedir código también al registrarse.

Marca de onboarding en servidor (recomendado): `leads.onboarding_completed_at` al terminar o saltar el asistente, para que otro navegador no reabra el welcome. Si no da tiempo, MVP = “hay experiencias ⇒ no wizard” + flag local.

### D. Frontend — flags y logout

Dejar de usar la landing como segundo login.

Al **logout**: borrar email, nombre, empresa, industria, rol, teléfono, ciudad, sectores, `licitia_new_user`, `licitia_start_onboarding`, `licitia_onboarding_*`, `licitia_portfolio_skipped`. Ir a `/` (landing), no a `/landing` huérfano.

Favoritas siguen keyed por email en `localStorage` (fuera de esta US cambiarlas de sitio).

### E. Relación con otras US

| US | Relación |
|----|----------|
| 1.11 RUP | Decide radar vs FirstSessionHome en la vuelta |
| 2.0 perfil / contacto del asistente | Se pide **una vez** en el alta; en la vuelta se hidrata del lead |
| 2.1–2.4 | No cambian; el usuario recurrente con RUP debe ver tipología/entidad igual |

---

## CRITERIOS DE ACEPTACIÓN

### MVP (fase 2.5.1)

**GIVEN** un visitante en la landing que no tiene lead  
**WHEN** completa razón social + email y pulsa **Empezar** / **Crear cuenta**  
**THEN**

- Se crea el lead (`POST /leads`).
- El CTA **no** dice Log in ni Iniciar sesión.
- Va al dashboard y se abre el asistente (welcome → RUP → contacto).
- `licitia_start_onboarding` se usa **solo** en este camino.

**GIVEN** un visitante cuyo email **ya está** en `leads`  
**WHEN** intenta “Crear cuenta” en la landing  
**THEN**

- No se abre el asistente.
- Ve que la cuenta existe y un enlace/botón a `/login` (email precargado).

**GIVEN** un visitante en `/login` con email **inexistente**  
**WHEN** pide entrar  
**THEN**

- No entra al dashboard como si fuera cuenta.
- Ve copy para **crear cuenta** y puede ir a la landing (email precargado).

**GIVEN** un lead existente  
**WHEN** en `/login` pide código, lo recibe y lo confirma  
**THEN**

- Entra al dashboard.
- El asistente **no** se abre.
- Si la empresa tiene RUP / experiencias: ve el radar.
- Si no tiene: ve FirstSessionHome / banner RUP (puede abrir el paso RUP, no el welcome completo).

**GIVEN** un código OTP  
**WHEN** está vencido, mal escrito o reutilizado  
**THEN** no entra; puede pedir otro código (con rate limit).

**GIVEN** el enlace **Ver el radar sin cuenta** (o copy equivalente)  
**WHEN** lo pulsa  
**THEN** llega a `/dashboard` (no se queda en la landing).

**GIVEN** un usuario que ya terminó o saltó el asistente  
**WHEN** vuelve a abrir la app en el mismo navegador o hace login  
**THEN** no se monta el overlay de welcome otra vez.

**GIVEN** logout  
**WHEN** cierra sesión  
**THEN**

- No queda email/empresa/onboarding/skip/sectores en `localStorage`.
- La siguiente visita a `/` es landing de alta, no un dashboard a nombre de otro.

**GIVEN** copy y rutas  
**WHEN** se recorre la landing  
**THEN**

- Un solo mensaje **Ya tengo cuenta** → `/login`.
- No hay dos CTAs que parezcan login.

**GIVEN** tests  
**WHEN** corre el suite  
**THEN** hay cobertura de: alta nueva abre asistente; email existente en landing no abre asistente; login inexistente no entra; verify-code ok / fail; dashboard con experiencias no abre wizard.

### Validación manual (muestra — gate de cierre MVP)

| Caso | Resultado esperado |
|------|-------------------|
| Email nuevo + Empezar | Asistente; lead creado |
| Mismo email otra vez por landing | “Ya tienes cuenta” → login |
| Login email desconocido | Ir a crear cuenta; no dashboard |
| Login + código correcto, empresa con RUP | Radar, sin welcome |
| Login + código, empresa sin RUP | FirstSessionHome, sin welcome |
| Código malo / vencido | Error claro; reenviar |
| Skip radar sin cuenta | `/dashboard` |
| Logout y otro email en el mismo Chrome | No mezcla empresa/RUP/onboarding |

### Fases posteriores (no bloquean cierre MVP)

| Fase | Criterio adicional |
|------|-------------------|
| 2.5.2 | OTP también en el alta (confirmar el correo el día 0) |
| 2.5.3 | Cookie / token de sesión (no solo `localStorage`) y cerrar rutas de app si no hay sesión, excepto invitado explícito |
| 2.5.4 | Varios usuarios por la misma empresa (roles) |

---

## FUERA DE ALCANCE (MVP)

- Contraseña persistente y recuperación de clave.
- OAuth (Google, Microsoft).
- WhatsApp / SMS como canal del código.
- Facturación, trial 30 días, planes Pro+.
- Cambiar los pasos internos del asistente (texto de welcome, parser RUP, campos de ciudad).
- Autorización por API key en todos los endpoints (el RUP sigue asociado a `company_name` como hoy).
- Multi-tenant con NIT como unique login.

---

## DEFINICIÓN DE HECHO (DoD)

### Fase 2.5.1 (MVP)

- [ ] Landing: CTA de **alta**; copy **Ya tengo cuenta** → `/login`.
- [ ] Email existente en landing: no wizard; redirección a login.
- [ ] `/login`: request + verify código; email inexistente → alta.
- [ ] Asistente solo en alta nueva.
- [ ] Recurrente con RUP → radar; sin RUP → FirstSessionHome.
- [ ] Skip landing → `/dashboard`.
- [ ] Logout limpia identidad y flags de onboarding/skip/sectores.
- [ ] Tests de los caminos de la tabla GIVEN/WHEN/THEN.
- [ ] Validación manual de la muestra documentada en el ticket de cierre.

### Épica completa (2.5.1 → 2.5.4)

- [ ] Confirmar email en el alta.
- [ ] Sesión server-side y gate de rutas.
- [ ] Varios usuarios por empresa.

---

## DEPENDENCIAS

| US / componente | Relación |
|-----------------|----------|
| `leads` + `POST /leads` + `GET /leads/check` | Identidad actual; check se sustituye/complementa con OTP |
| SMTP / `notifications.py` | Envío del código |
| `OnboardingWizard` / `useOnboarding` | Solo flag de alta nueva |
| `usePortfolioStatus` / `GET /experiences` | Rama radar vs FirstSessionHome |
| `AppLayout` logout | Limpieza de storage |
| Landing + `Login.tsx` | Superficies |

---

## NOTAS OPERATIVAS

- **No hay contraseña en el MVP.** El código de un solo uso es la prueba de posesión del correo.
- Respuesta de “email no existe” en login es deliberada (UX de alta). No enumerar leads en un `GET` admin público más de lo que ya existe.
- El nombre comercial de empresa en el RUP debe seguir alineado con la razón social del lead (US 1.11).
- Invitado sin cuenta: no mezclar su `localStorage` con el de un login posterior (logout / cambio de email limpia).

### Título sugerido en Jira

`2.5 [Backend+Frontend] Alta vs vuelta — inicio de sesión para usuario nuevo y recurrente`
