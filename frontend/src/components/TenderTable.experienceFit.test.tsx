import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import TenderTable from './TenderTable'
import type { Tender } from '../api/client'

function tender(fit: Tender['experience_fit']): Tender {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    external_id: 'CO1.REQ.1',
    reference: 'LP-1',
    source: 'secop',
    entity_name: 'INVIAS',
    object_text: 'Interventoría al mejoramiento de la vía',
    department: 'Caldas',
    municipality: null,
    amount: 1000,
    publication_date: '2026-03-01T00:00:00.000Z',
    closing_date: '2026-04-01T00:00:00.000Z',
    state: 'Publicado',
    apertura_estado: 'Abierto',
    process_url: 'https://example.com',
    contract_type: 'Interventoría',
    contract_modality: null,
    relevance_score: null,
    is_relevant_interventoria_vial: false,
    documents_extraction_attempted_at: null,
    experience_match_score: null,
    matching_experiences: null,
    experience_fit: fit,
    created_at: '2026-03-01T00:00:00.000Z',
    updated_at: '2026-03-01T00:00:00.000Z',
  }
}

describe('TenderTable experience fit', () => {
  it('shows Puede aplicar instead of a match percentage', () => {
    render(
      <TenderTable
        tenders={[
          tender({
            status: 'puede_aplicar',
            reason: 'La suma de SMMLV y las partidas cubren el pliego',
            general_sum_smmlv: 302,
            general_minimum_smmlv: 300,
            contracts: [],
          }),
        ]}
      />
    )
    expect(screen.getByText('Puede aplicar')).toBeInTheDocument()
    expect(screen.queryByText(/% match/i)).not.toBeInTheDocument()
  })
})
