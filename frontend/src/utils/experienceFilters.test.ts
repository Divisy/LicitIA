import { describe, expect, it } from 'vitest'
import { CompanyExperience } from '../api/client'
import { filterExperiences } from './experienceFilters'

function experience(overrides: Partial<CompanyExperience> = {}): CompanyExperience {
  return {
    id: 'exp-1',
    company_name: 'BEC',
    contract_number: '1',
    project_description: 'Obra',
    contracting_entity: 'IDU',
    contractor_name: 'CONSORCIO',
    completion_date: '2014-05-31',
    amount: null,
    amount_smmlv: 3983.4,
    category: null,
    engineering_area: null,
    contract_kind: 'ejecucion_obra',
    contract_kind_label: 'Ejecución de obra',
    specific_experience: null,
    specific_evidence_filename: null,
    project_typologies: ['vias'],
    unspsc_codes: [],
    keywords: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const empty = {
  contractKind: '',
  entity: '',
  typology: '',
  dateFrom: '',
  dateTo: '',
  valueMin: '',
  valueMax: '',
}

describe('filterExperiences', () => {
  const rows = [
    experience(),
    experience({
      id: 'exp-2',
      contracting_entity: 'INVIAS',
      contract_kind: 'interventoria',
      completion_date: '2010-05-09',
      amount_smmlv: 860,
      project_typologies: ['vias', 'puentes'],
    }),
    experience({
      id: 'exp-3',
      contracting_entity: 'ALCALDIA',
      contract_kind: null,
      completion_date: null,
      amount_smmlv: null,
      project_typologies: [],
    }),
  ]

  it('filters by contract kind, entity and typology together', () => {
    const result = filterExperiences(rows, {
      ...empty,
      contractKind: 'interventoria',
      entity: 'INVIAS',
      typology: 'puentes',
    })
    expect(result.map((row) => row.id)).toEqual(['exp-2'])
  })

  it('filters by completion date and SMMLV value', () => {
    const result = filterExperiences(rows, {
      ...empty,
      dateFrom: '2012-01-01',
      dateTo: '2015-12-31',
      valueMin: '1000',
    })
    expect(result.map((row) => row.id)).toEqual(['exp-1'])
  })

  it('treats a missing kind as unidentified', () => {
    const result = filterExperiences(rows, { ...empty, contractKind: 'desconocido' })
    expect(result.map((row) => row.id)).toEqual(['exp-3'])
  })
})
