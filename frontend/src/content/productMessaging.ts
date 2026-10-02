/**
 * Copy alineado al WHY de LicitIA y a Pregunta 0 / JTBD 0.
 * North star: más oportunidades vía socios para consorcios / UT.
 * Ver docs/JTBD-producto-licitia.md y docs/US-1.10-primera-sesion-portafolio.md
 */

export const PRODUCT_WHY = {
  audience: 'empresas de construcción, ingeniería e interventoría',
  pillarFast: 'encontrar licitaciones relevantes mucho más rápido',
  pillarPartners: 'encontrar socios para presentarse juntas y acceder a más oportunidades',
} as const

/** Respuesta a Pregunta 0 — comprensión en < 30 s */
export const PREGUNTA_0_HEADLINE =
  'Encuentra licitaciones relevantes para tu empresa en solo segundos.'

export const PREGUNTA_0_PROMISE =
  'LicitIA ayuda a empresas de construcción, ingeniería e interventoría a descubrir oportunidades de obra pública que encajan con su experiencia — sin perder horas en SECOP.'

/** Versión escaneable para onboarding (menos carga cognitiva) */
export const PREGUNTA_0_LEAD_SHORT =
  'Oportunidades de obra pública filtradas por tu experiencia — sin perder horas en SECOP.'

export const PREGUNTA_0_PROMISE_EXTENDED =
  'Próximamente podrás identificar socios para armar consorcios y presentarte a procesos que solas no alcanzarías.'

export const PREGUNTA_0_VALUE_POINTS = [
  {
    id: 'experience',
    label: 'Filtrado por tu experiencia general, específica e indicadores financieros.',
  },
  {
    id: 'updates',
    label: 'Actualización diaria de licitaciones para el sector de la construcción.',
  },
  {
    id: 'partners',
    label: 'Socios para consorcios',
  },
] as const

/** JTBD 0 — activar portafolio */
export const JTBD_0_TITLE = 'Primero, cuéntale a LicitIA en qué es buena tu empresa'

export const JTBD_0_DESCRIPTION =
  'Sube tu RUP. Con eso sabemos qué puedes aportar a un consorcio, tu match % en cada licitación y en cuáles te falta un socio.'

export const WELCOME_CTA_LABEL = 'Continuar — cargar RUP'

export const PORTFOLIO_BANNER_TITLE = 'Tu perfil aún no está activo'

export const PORTFOLIO_BANNER_TEXT =
  'Sube tu RUP para ver en qué licitaciones puedes ir sola y en cuáles necesitas un socio para participar.'

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
