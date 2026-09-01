import { describe, expect, it } from 'vitest'
import type { Tender } from '../api/client'
import {
  compareTenders,
  getInitialSortDirectionForColumn,
  sortTenders,
} from './tenderTableSort'

function makeTender(overrides: Partial<Tender> = {}): Tender {
  return {
    id: overrides.id ?? '00000000-0000-0000-0000-000000000001',
    external_id: 'CO1.REQ.TEST',
    reference: null,
    source: 'secop',
    entity_name: overrides.entity_name ?? 'Entidad A',
    object_text: 'Objeto',
    department: 'Cundinamarca',
    municipality: null,
    amount: overrides.amount ?? 1_000_000,
    publication_date: overrides.publication_date ?? '2026-01-10T00:00:00.000Z',
    closing_date: overrides.closing_date ?? '2026-02-10T00:00:00.000Z',
    state: 'Publicado',
    apertura_estado: null,
    process_url: 'https://example.com',
    contract_type: null,
    contract_modality: null,
    relevance_score: null,
    is_relevant_interventoria_vial: false,
    documents_extraction_attempted_at: null,
    experience_match_score: overrides.experience_match_score ?? null,
    matching_experiences: null,
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  }
}

describe('tenderTableSort', () => {
  it('sorts amounts ascending with nulls last', () => {
    const tenders = [
      makeTender({ id: '1', amount: 3_000_000_000 }),
      makeTender({ id: '2', amount: 400_000_000 }),
      makeTender({ id: '3', amount: null }),
      makeTender({ id: '4', amount: 1_600_000_000 }),
    ]

    const sorted = sortTenders(tenders, 'amount', 'asc')
    expect(sorted.map((item) => item.id)).toEqual(['2', '4', '1', '3'])
  })

  it('sorts amounts descending', () => {
    const tenders = [
      makeTender({ id: '1', amount: 400_000_000 }),
      makeTender({ id: '2', amount: 3_000_000_000 }),
      makeTender({ id: '3', amount: 1_400_000_000 }),
    ]

    const sorted = sortTenders(tenders, 'amount', 'desc')
    expect(sorted.map((item) => item.id)).toEqual(['2', '3', '1'])
  })

  it('sorts closing dates chronologically', () => {
    const tenders = [
      makeTender({ id: '1', closing_date: '2026-05-01T00:00:00.000Z' }),
      makeTender({ id: '2', closing_date: '2026-01-01T00:00:00.000Z' }),
      makeTender({ id: '3', closing_date: null }),
    ]

    const sorted = sortTenders(tenders, 'closing_date', 'asc')
    expect(sorted.map((item) => item.id)).toEqual(['2', '1', '3'])
  })

  it('sorts match scores descending', () => {
    const a = makeTender({ id: '1', experience_match_score: 0.2 })
    const b = makeTender({ id: '2', experience_match_score: 0.8 })
    expect(compareTenders(a, b, 'match', 'desc')).toBeGreaterThan(0)
  })

  it('uses entity name as tie-breaker', () => {
    const tenders = [
      makeTender({ id: '1', entity_name: 'Zeta', amount: 100 }),
      makeTender({ id: '2', entity_name: 'Alfa', amount: 100 }),
    ]

    const sorted = sortTenders(tenders, 'amount', 'asc')
    expect(sorted.map((item) => item.id)).toEqual(['2', '1'])
  })

  it('defaults numeric columns to ascending on first click', () => {
    expect(getInitialSortDirectionForColumn('amount')).toBe('asc')
    expect(getInitialSortDirectionForColumn('match')).toBe('asc')
  })

  it('defaults date columns to descending on first click', () => {
    expect(getInitialSortDirectionForColumn('closing_date')).toBe('desc')
    expect(getInitialSortDirectionForColumn('publication_date')).toBe('desc')
  })
})
