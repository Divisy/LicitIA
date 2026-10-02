/**
 * Copy alineado al WHY de LicitIA y a Pregunta 0 / JTBD 0.
 * North star: más oportunidades vía socios para consorcios / UT.
 * Ver docs/JTBD-producto-licitia.md y docs/US-1.10-primera-sesion-portafolio.md
 */

export const PRODUCT_WHY = {
  audience: 'empresas de construcción, ingeniería e interventoría',
  pillarPartners:
    'encontrar el socio que te falta para presentarte a más licitaciones',
  pillarProfile: 'conocer tu capacidad y en qué procesos necesitas aliado',
  pillarRadar: 'licitaciones de obra pública filtradas para tu sector',
} as const

/** Respuesta a Pregunta 0 — comprensión en < 30 s */
export const PREGUNTA_0_HEADLINE =
  'Participa en más licitaciones — con el socio que te falta.'

export const PREGUNTA_0_PROMISE =
  'En obra pública, sin el aliado adecuado las oportunidades son pocas. LicitIA conoce tu capacidad y te ayuda a encontrar socios para consorcios y uniones temporales — y a abrir procesos que sola no alcanzarías.'

/** Versión escaneable bajo el titular en onboarding */
export const PREGUNTA_0_LEAD_SHORT =
  'Sube tu portafolio, identifica en qué licitaciones necesitas socio y con quién presentarte.'

export const PREGUNTA_0_PROMISE_EXTENDED =
  'Hoy activamos tu radar y match %. Próximamente, recomendación directa de socios complementarios para cada proceso.'

export const PREGUNTA_0_VALUE_POINTS = [
  {
    id: 'partners',
    label: 'Encuentra socios para consorcios y presentarte a más licitaciones.',
    badge: 'Próximamente',
  },
  {
    id: 'profile',
    label: 'Tu portafolio define qué aportas y dónde necesitas un aliado.',
  },
  {
    id: 'radar',
    label: 'Licitaciones de obra pública actualizadas para construcción e ingeniería.',
  },
] as const

/** JTBD 0 — activar portafolio */
export const JTBD_0_TITLE = 'Primero, cuéntale a LicitIA en qué es buena tu empresa'

export const JTBD_0_DESCRIPTION =
  'Sube tu portafolio de contratos en obra pública. Con eso sabemos qué puedes aportar a un consorcio, tu match % en cada licitación y en cuáles te falta un socio.'

export const WELCOME_CTA_LABEL = 'Continuar — subir portafolio'

export const PORTFOLIO_BANNER_TITLE = 'Tu perfil aún no está activo'

export const PORTFOLIO_BANNER_TEXT =
  'Sube tu portafolio para ver en qué licitaciones puedes ir sola y en cuáles necesitas un socio para participar.'

export const DASHBOARD_SUBTITLE_READY =
  'Licitaciones donde encajas — y dónde podrías necesitar un socio'

export const DASHBOARD_SUBTITLE_EMPTY =
  'Abre más oportunidades de obra pública con el socio correcto'

export const MATCH_PREVIEW_TITLE = 'Tus primeras oportunidades'

export const MATCH_PREVIEW_EMPTY =
  'Tu perfil está activo. En el dashboard verás licitaciones donde encajas y cuáles requieren un aliado.'

/** US 2.0 — perfil de empresa en onboarding */
export const COMPANY_PROFILE_STEP_TITLE = 'Cuéntanos sobre tu empresa'

export const COMPANY_PROFILE_STEP_LEAD =
  'Marca si hacen estudios y diseños, interventoría u obra. El radar de licitaciones te muestra esas licitaciones exclusivas para tu empresa, no el resto de licitaciones de otros sectores del SECOP.'
