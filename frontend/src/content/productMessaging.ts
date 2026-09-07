/**
 * Copy alineado al WHY de LicitIA y a Pregunta 0 / JTBD 0.
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
    badge: 'Próximamente',
  },
] as const

/** JTBD 0 — activar portafolio */
export const JTBD_0_TITLE = 'Cuéntale a LicitIA en qué es buena tu empresa'

export const JTBD_0_DESCRIPTION =
  'Sube tu portafolio de contratos en obra pública. Con eso activamos el radar personalizado y el match % en cada licitación.'
