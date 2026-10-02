# US 2.0 — Perfil de empresa: razón social, contacto y sector (Épica 2)

**Jira:** `2.0 [Frontend+Backend] Perfil de empresa en landing y onboarding — sector estudios / interventoría / obra`

## USER STORY

**As a** responsable de licitaciones que entra a LicitIA por primera vez  
**Quiero** entrar con la razón social y el correo de la empresa, y en el onboarding decir quién soy, un teléfono y si hacemos estudios y diseños, interventoría y/o obra  
**Para** que LicitIA sepa de entrada **qué tipo de procesos busca mi empresa**, sin rellenar un formulario de marketing (tamaño, cargo, industria genérica).

---

## BACKGROUND

Hoy el primer contacto está invertido y es ruido:

**Landing (login / registro):** email + nombre (opcional) + empresa (opcional). La razón social no es obligatoria. El copy del input es «Tu email», no correo empresarial.

**Onboarding — paso actual `MarketingInfoStep`:** título *«Cuéntanos sobre ti»*. Campos:

| Campo hoy | Problema |
|-----------|----------|
| Nombre de tu empresa * | Duplica la landing; si ya se pidió razón social, sobra |
| Tu nombre completo | OK, pero es de la **empresa/contacto**, no un perfil personal |
| Industria o sector (construcción, ingeniería, consultoría…) | No calza con los filtros del dashboard (`estudios_disenos`, `interventoria`, `ejecucion_obra`) |
| Tamaño de empresa | No se usa para el radar |
| Cargo o rol | No se usa para el radar |

El usuario de la captura (oct 2026) está en el paso 3 del onboarding con *«Cuéntanos sobre ti»* y esos campos. **Esta US no quita el onboarding**; lo deja y recorta ese paso.

**Épica 2** arranca aquí: dejar de tratar al usuario como lead de marketing y tratarlo como **empresa del sector** (estudios, interventoría, obra), alineado con el WHY y con los tabs del dashboard.

---

## OBJETIVO

1. **Landing / login inicial:** solo **Razón social** + **Correo empresarial**. Ambos obligatorios. CTA de entrar (Log in / Continuar).
2. **Onboarding — sección *Cuéntanos sobre tu empresa* (no *sobre ti*):** solo  
   - Nombre de contacto  
   - Teléfono  
   - Sector: **Estudios y diseños**, **Interventoría**, **Obra** (la empresa puede marcar **uno o varios**).
3. Persistir esos datos en el lead / perfil de empresa para personalizar el radar (filtro por tipo de contrato).

El resto del onboarding (Welcome, RUP / portafolio, preview de match) **se mantiene**.

---

## ALCANCE

| Incluye | No incluye |
|---------|------------|
| Landing: 2 campos (razón social, correo empresarial), ambos required | Auth JWT, magic link, contraseña, Google login |
| Validar correo con formato email (dominio libre; copy dice *empresarial*) | Verificar que el dominio no sea gmail/hotmail (fase posterior si se pide) |
| Renombrar el paso a *Cuéntanos sobre tu empresa* | Quitar Welcome / cargar RUP / MatchPreview |
| 3 campos en ese paso: contacto, teléfono, sector (multi) | Tamaño de empresa, cargo, industria genérica |
| Quitar razón social de este paso (ya viene de landing) | Implementar US 1.11 RUP |
| Guardar `phone` + `sectors[]` en lead | Nuevo modelo de usuario / multi-empresa |
| Default del filtro *Tipo de contrato* según sectores marcados | Forzar el radar a un solo tipo si marca varios |

---

## SOLUCIÓN

### A. Landing — Log in inicial

Solo dos inputs + CTA:

| Campo | Obligatorio | Copy |
|-------|-------------|------|
| Razón social | Sí | *Razón social* |
| Correo empresarial | Sí | *Correo empresarial* |
| CTA | — | *Log in* / *Continuar* (mismo flujo actual a dashboard + onboarding) |

Quitar: *Tu nombre (opcional)*, *Empresa (opcional)*, placeholder *Tu email*.

Flujo: `POST /api/v1/leads` con `company` (razón social) + `email`. Guardar `licitia_user_company` y `licitia_user_email` como hoy. Si falta alguno, no entra.

### B. Onboarding — *Cuéntanos sobre tu empresa*

Sustituye el contenido de `MarketingInfoStep`. El wizard sigue: Welcome → (RUP / portafolio) → **este paso** → preview. Si el orden actual pone el marketing al final, **no se cambia el orden de los pasos**; solo el contenido y el título.

**Título:** Cuéntanos sobre tu empresa  
**Subtítulo:** Para personalizar el radar. La razón social ya la diste al entrar.

| Campo | Obligatorio | UI |
|-------|-------------|----|
| Nombre de contacto | Sí | Texto. Prellenar si ya había `licitia_user_name` |
| Teléfono | Sí | Texto; dígitos / `+57`; mín. 7 dígitos |
| Sector | Sí (≥ 1) | Checkboxes (no un select de uno solo): **Estudios y diseños**, **Interventoría**, **Obra** |

Quitar del paso: nombre de empresa, industria, tamaño, cargo, *Omitir y continuar* (este paso sí califica a la empresa; Atrás se mantiene).

Valores persistidos (alineados a `contract_kind` del dashboard):

| Checkbox | Valor |
|----------|--------|
| Estudios y diseños | `estudios_disenos` |
| Interventoría | `interventoria` |
| Obra | `ejecucion_obra` |

Si marca varios, el dashboard abre en **Todas** con esos tipos disponibles; si marca uno solo, el tab por defecto es ese.

### C. Backend

`leads`:

- `company` deja de ser opcional en el alta desde landing.
- `name` = nombre de contacto (se llena en onboarding, no en landing).
- Nuevo: `phone` (string).
- Nuevo: `sectors` (JSON o string CSV: `estudios_disenos`, `interventoria`, `ejecucion_obra`).
- Dejar de pedir `industry` / `company_size` / `role` en UI. Columnas viejas pueden quedar nulas (no migrar datos de marketing).

`POST /api/v1/leads` acepta `phone` y `sectors`. El onboarding hace update del lead por email, igual que hoy.

---

## CRITERIOS DE ACEPTACIÓN

**GIVEN** un visitante en la landing  
**WHEN** ve el formulario de entrada  
**THEN** solo hay Razón social, Correo empresarial y el CTA. No hay nombre ni empresa opcional.

**GIVEN** envía el form sin razón social o sin correo  
**WHEN** intenta entrar  
**THEN** no navega al dashboard; error en el campo vacío.

**GIVEN** razón social + correo válidos  
**WHEN** hace Log in  
**THEN** se crea/actualiza el lead, guarda email y razón social, y entra al onboarding existente.

**GIVEN** el paso de datos de empresa  
**WHEN** se muestra  
**THEN** el título es *Cuéntanos sobre tu empresa* y solo aparecen Nombre de contacto, Teléfono y Sector (tres checks). No aparece *Cuéntanos sobre ti*, ni industria, ni tamaño, ni cargo, ni otra vez la razón social.

**GIVEN** no marca ningún sector o deja teléfono / contacto vacío  
**WHEN** pulsa Continuar  
**THEN** no avanza; pide completar.

**GIVEN** marca Interventoría (solo)  
**WHEN** termina onboarding y llega al dashboard  
**THEN** el filtro *Tipo de contrato* arranca en Interventoría.

**GIVEN** marca Estudios y diseños + Obra  
**WHEN** llega al dashboard  
**THEN** no se fuerza un solo tab; queda en Todas (o equivalente) y el perfil guarda ambos sectores.

**GIVEN** un lead ya existente con el mismo correo  
**WHEN** completa este paso  
**THEN** se actualizan nombre de contacto, teléfono y sectores; no se duplica el lead.

---

## TÍTULO JIRA

`2.0 [Frontend+Backend] Perfil de empresa: landing (razón social + correo) y onboarding (contacto, teléfono, sector)`
