import { CompanyExperience } from '../api/client'

export type ExperienceListFilters = {
  contractKind: string
  entity: string
  typology: string
  dateFrom: string
  dateTo: string
  valueMin: string
  valueMax: string
}

export const EMPTY_EXPERIENCE_FILTERS: ExperienceListFilters = {
  contractKind: '',
  entity: '',
  typology: '',
  dateFrom: '',
  dateTo: '',
  valueMin: '',
  valueMax: '',
}

export function hasActiveExperienceFilters(filters: ExperienceListFilters): boolean {
  return Object.values(filters).some((value) => value.trim() !== '')
}

export function experienceValueSmmlv(experience: CompanyExperience): number | null {
  if (experience.amount_smmlv == null || Number.isNaN(experience.amount_smmlv)) {
    return null
  }
  return experience.amount_smmlv
}

function completionDay(experience: CompanyExperience): string {
  return (experience.completion_date || '').slice(0, 10)
}

function experienceKind(experience: CompanyExperience): string {
  const kind = (experience.contract_kind || '').trim()
  if (!kind || kind === 'desconocido') return ''
  return kind
}

function parsedBound(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const number = Number(trimmed)
  return Number.isFinite(number) ? number : null
}

export function filterExperiences(
  experiences: CompanyExperience[],
  filters: ExperienceListFilters
): CompanyExperience[] {
  const min = parsedBound(filters.valueMin)
  const max = parsedBound(filters.valueMax)

  return experiences.filter((experience) => {
    if (filters.contractKind) {
      const kind = experienceKind(experience)
      if (filters.contractKind === 'desconocido') {
        if (kind) return false
      } else if (kind !== filters.contractKind) {
        return false
      }
    }

    if (filters.entity && (experience.contracting_entity || '').trim() !== filters.entity) {
      return false
    }

    if (
      filters.typology &&
      !(experience.project_typologies || []).includes(filters.typology)
    ) {
      return false
    }

    const day = completionDay(experience)
    if (filters.dateFrom && (!day || day < filters.dateFrom)) return false
    if (filters.dateTo && (!day || day > filters.dateTo)) return false

    const value = experienceValueSmmlv(experience)
    if (min != null && (value == null || value < min)) return false
    if (max != null && (value == null || value > max)) return false

    return true
  })
}

export function experienceFilterChoices(experiences: CompanyExperience[]): {
  entities: string[]
  typologies: string[]
} {
  const entities = new Set<string>()
  const typologies = new Set<string>()
  experiences.forEach((experience) => {
    const entity = (experience.contracting_entity || '').trim()
    if (entity) entities.add(entity)
    ;(experience.project_typologies || []).forEach((typology) => {
      if (typology) typologies.add(typology)
    })
  })
  return {
    entities: [...entities].sort((left, right) => left.localeCompare(right, 'es')),
    typologies: [...typologies].sort((left, right) => left.localeCompare(right, 'es')),
  }
}
