import type { ContractKindFilter } from '../api/client'

export const USER_SECTORS_STORAGE_KEY = 'licitia_user_sectors'

export const COMPANY_SECTORS = [
  { value: 'estudios_disenos', label: 'Estudios y diseños' },
  { value: 'interventoria', label: 'Interventoría' },
  { value: 'ejecucion_obra', label: 'Obra' },
] as const

export type CompanySector = (typeof COMPANY_SECTORS)[number]['value']

const SECTOR_VALUES = new Set<string>(COMPANY_SECTORS.map((item) => item.value))

export function parseStoredSectors(raw: string | null | undefined): CompanySector[] {
  if (!raw) {
    return []
  }
  const unique: CompanySector[] = []
  for (const part of raw.split(',')) {
    const value = part.trim()
    if (SECTOR_VALUES.has(value) && !unique.includes(value as CompanySector)) {
      unique.push(value as CompanySector)
    }
  }
  return unique
}

export function serializeSectors(sectors: CompanySector[]): string {
  return parseStoredSectors(sectors.join(',')).join(',')
}

export function defaultContractKindFromSectors(
  sectors: CompanySector[]
): ContractKindFilter {
  if (sectors.length === 1) {
    return sectors[0]
  }
  return ''
}

export const EXPERIENCE_CONTRACT_KIND_LABELS: Record<string, string> = {
  ejecucion_obra: 'Ejecución de obra',
  estudios_disenos: 'Estudios y diseños',
  estudios_disenos_y_obra: 'Estudios, diseños y obra',
  interventoria: 'Interventoría',
  desconocido: 'No identificado',
}

export type ExperienceContractKindTag = 'blue' | 'purple' | 'teal' | 'cyan' | 'gray'

export function experienceContractKindTag(
  kind: string | null | undefined
): ExperienceContractKindTag {
  if (kind === 'ejecucion_obra') return 'blue'
  if (kind === 'estudios_disenos') return 'purple'
  if (kind === 'estudios_disenos_y_obra') return 'teal'
  if (kind === 'interventoria') return 'cyan'
  return 'gray'
}

export function experienceContractKindLabel(
  kind: string | null | undefined,
  fallback?: string | null
): string {
  if (kind && EXPERIENCE_CONTRACT_KIND_LABELS[kind]) {
    return EXPERIENCE_CONTRACT_KIND_LABELS[kind]
  }
  return fallback || EXPERIENCE_CONTRACT_KIND_LABELS.desconocido
}

export function normalizePhone(raw: string): string {
  return raw.replace(/[^\d+]/g, '')
}

export function isValidPhone(raw: string): boolean {
  const digits = normalizePhone(raw).replace(/\D/g, '')
  return digits.length >= 7 && digits.length <= 15
}
