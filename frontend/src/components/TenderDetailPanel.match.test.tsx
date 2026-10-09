import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import TenderDetailPanel from './TenderDetailPanel'
import type { Tender } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    getTenderDocuments: vi.fn().mockResolvedValue({ items: [] }),
    getTenderSummary: vi.fn().mockResolvedValue({
      fields: [],
      contract_kind: null,
      contract_kind_label: null,
    }),
    getTenderRequirements: vi.fn().mockResolvedValue({
      tender_id: '11111111-1111-1111-1111-111111111111',
      tender_external_id: 'CO1.REQ.1',
      extraction_version: 'test',
      extracted_at: '2026-10-09T00:00:00.000Z',
      sections: [],
      warnings: [],
      cached: true,
    }),
    uploadTenderDocument: vi.fn(),
  }
})

function tender(): Tender {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    external_id: 'CO1.REQ.1',
    reference: '4162.010.32.1.1269-2026',
    source: 'secop',
    entity_name: 'SANTIAGO DE CALI DISTRITO ESPECIAL - SECRETARIA DEL DEPORTE Y LA RECREACIÓN',
    object_text: 'REALIZAR LA INTERVENTORÍA TÉCNICA A LOS CONTRATOS DE OBRA.',
    department: 'Valle del Cauca',
    municipality: 'Cali',
    amount: 540822123,
    publication_date: '2026-09-30T00:00:00.000Z',
    closing_date: '2026-10-30T00:00:00.000Z',
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
    experience_fit: {
      status: 'puede_aplicar',
      reason: 'El objeto del acta coincide con el objeto de la licitación',
      general_sum_smmlv: null,
      general_minimum_smmlv: null,
      contracts: [
        {
          experience_id: 'exp-3396',
          contract_number: '3396 DE 2008',
          contracting_entity: 'SECRETARIA DE INTEGRACION SOCIAL',
          amount_smmlv: 222,
          in_general_sum: true,
          specific_met: false,
          matched_activity: null,
          object_text:
            'Interventoría Técnica, Administrativa y Contable de los contratos de obra de reforzamiento estructural.',
        },
      ],
    },
    created_at: '2026-03-01T00:00:00.000Z',
    updated_at: '2026-03-01T00:00:00.000Z',
  }
}

describe('TenderDetailPanel experience match', () => {
  beforeAll(() => {
    class ResizeObserverStub {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)
  })

  it('shows the matching contract as a card, not a single line', async () => {
    render(
      <MemoryRouter>
        <TenderDetailPanel tender={tender()} open onClose={() => {}} />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Coincide con tu experiencia' })).toBeTruthy()
    expect(screen.getByText('1 contrato')).toBeTruthy()
    expect(screen.getByText('3396 DE 2008')).toBeTruthy()
    expect(screen.getByText('SECRETARIA DE INTEGRACION SOCIAL')).toBeTruthy()
    expect(screen.getByText('222 SMMLV')).toBeTruthy()
    expect(screen.getByText('Objeto del acta')).toBeTruthy()
    expect(screen.getByText(/reforzamiento estructural/)).toBeTruthy()
    expect(screen.queryByText(/Match con la experiencia/)).toBeNull()
  })
})
