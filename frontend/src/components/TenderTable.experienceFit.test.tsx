import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, describe, expect, it, vi } from 'vitest'
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
  beforeAll(() => {
    class ResizeObserverStub {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)
  })

  it('shows Puede aplicar instead of a match percentage', () => {
    render(
      <TenderTable
        tenders={[
          tender({
            status: 'puede_aplicar',
            reason: 'La suma de SMMLV y las partidas cubren el pliego',
            general_sum_smmlv: 302,
            general_minimum_smmlv: 300,
            contracts: [
              {
                experience_id: 'exp-1232',
                contract_number: '1232 DE 2006',
                contracting_entity: 'INVIAS',
                amount_smmlv: 222,
                in_general_sum: true,
                specific_met: false,
                matched_activity: null,
                object_text: 'Interventoría para el mejoramiento de la vía Las Margaritas',
              },
            ],
          }),
        ]}
      />
    )
    expect(screen.getByText('Puede aplicar')).toBeInTheDocument()
    expect(screen.queryByText(/% match/i)).not.toBeInTheDocument()
  })

  it('opens the matching experience contract from Puede aplicar', async () => {
    const user = userEvent.setup()
    render(
      <TenderTable
        tenders={[
          tender({
            status: 'puede_aplicar',
            reason: 'El objeto del acta coincide con el objeto de la licitación',
            general_sum_smmlv: null,
            general_minimum_smmlv: null,
            contracts: [
              {
                experience_id: 'exp-1232',
                contract_number: '1232 DE 2006',
                contracting_entity: 'INVIAS',
                amount_smmlv: 222,
                in_general_sum: true,
                specific_met: false,
                matched_activity: null,
                object_text: 'Interventoría para el mejoramiento de la vía Las Margaritas',
              },
            ],
          }),
        ]}
      />
    )
    await user.click(screen.getByRole('button', { name: 'Puede aplicar' }))
    expect(screen.getByText('1232 DE 2006')).toBeInTheDocument()
    expect(screen.getByText('Interventoría para el mejoramiento de la vía Las Margaritas')).toBeInTheDocument()
  })
})
