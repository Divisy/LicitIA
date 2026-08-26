import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Tender } from '../api/client'
import {
  addFavoriteTender,
  getFavoriteStorageKey,
  isFavoriteTender,
  loadFavoriteRefs,
  removeFavoriteTender,
  toggleFavoriteTender,
} from './favoriteTendersStorage'

const sampleTender: Tender = {
  id: '11111111-1111-1111-1111-111111111111',
  external_id: 'CO1.REQ.10000001',
  reference: 'LP-001-2026',
  source: 'secop',
  entity_name: 'Entidad de prueba',
  object_text: 'Objeto de prueba',
  department: 'Cundinamarca',
  municipality: 'Bogotá',
  amount: 1000000,
  publication_date: '2026-01-01T00:00:00.000Z',
  closing_date: '2026-02-01T00:00:00.000Z',
  state: 'Publicado',
  apertura_estado: 'Abierto',
  process_url: 'https://example.com',
  contract_type: 'Interventoría',
  contract_modality: null,
  relevance_score: null,
  is_relevant_interventoria_vial: true,
  documents_extraction_attempted_at: null,
  experience_match_score: null,
  matching_experiences: null,
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
}

describe('favoriteTendersStorage', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('licitia_user_email', 'usuario@empresa.com')
  })

  it('stores favorites per user email', () => {
    addFavoriteTender(sampleTender)

    expect(loadFavoriteRefs()).toHaveLength(1)
    expect(isFavoriteTender(sampleTender.id)).toBe(true)
    expect(getFavoriteStorageKey()).toBe('licitia_favorite_tenders:usuario@empresa.com')
  })

  it('toggles favorite state', () => {
    expect(toggleFavoriteTender(sampleTender)).toBe(true)
    expect(isFavoriteTender(sampleTender.id)).toBe(true)

    expect(toggleFavoriteTender(sampleTender)).toBe(false)
    expect(isFavoriteTender(sampleTender.id)).toBe(false)
  })

  it('removes a favorite by tender id', () => {
    addFavoriteTender(sampleTender)
    removeFavoriteTender(sampleTender.id)

    expect(loadFavoriteRefs()).toHaveLength(0)
  })

  it('dispatches change event when favorites update', () => {
    const handler = vi.fn()
    window.addEventListener('licitia:favorites-changed', handler)

    addFavoriteTender(sampleTender)

    expect(handler).toHaveBeenCalledTimes(1)
  })
})
