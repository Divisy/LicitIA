import { beforeAll, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExperienceList from './ExperienceList'
import { CompanyExperience } from '../api/client'

function experience(overrides: Partial<CompanyExperience> = {}): CompanyExperience {
  return {
    id: 'exp-1',
    company_name: 'BEC',
    contract_number: 'RUP-4',
    project_description: 'Obra Paipa',
    contracting_entity: 'MUNICIPIO DE PAIPA',
    contractor_name: 'CONSTRUCTORA',
    completion_date: null,
    amount: 2178220160,
    amount_smmlv: 12290.89,
    category: null,
    engineering_area: 'estudios_disenos_y_obra',
    contract_kind: 'estudios_disenos_y_obra',
    contract_kind_label: 'Estudios, diseños y obra',
    specific_experience: null,
    specific_evidence_filename: null,
    unspsc_codes: ['11101700', '11111500', '30101800', '30102000', '81101500'],
    keywords: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('ExperienceList UNSPSC preview', () => {
  beforeAll(() => {
    class ResizeObserverStub {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)
  })

  it('shows at most three codes and opens the rest in a modal', async () => {
    const user = userEvent.setup()
    render(<ExperienceList experiences={[experience()]} companyName="BEC" />)

    expect(screen.getByText('11101700')).toBeInTheDocument()
    expect(screen.getByText('11111500')).toBeInTheDocument()
    expect(screen.getByText('30101800')).toBeInTheDocument()
    expect(screen.queryByText('30102000')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ver códigos (5)' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ver códigos (5)' }))
    expect(screen.getByText('Códigos UNSPSC del contrato')).toBeInTheDocument()
    expect(screen.getByText('30102000')).toBeInTheDocument()
    expect(screen.getByText('81101500')).toBeInTheDocument()
  })

  it('does not show the modal action when there are three codes or fewer', () => {
    render(
      <ExperienceList
        experiences={[experience({ unspsc_codes: ['72141100', '81101500'] })]}
        companyName="BEC"
      />
    )
    expect(screen.queryByRole('button', { name: /Ver códigos/ })).not.toBeInTheDocument()
  })

  it('shows the RUP SMMLV value instead of converted pesos', () => {
    render(<ExperienceList experiences={[experience()]} companyName="BEC" />)
    expect(screen.getByText(/12\.290,89 SMMLV/)).toBeInTheDocument()
    expect(screen.queryByText(/2\.178\.220\.160/)).not.toBeInTheDocument()
  })

  it('shows a compact upload action instead of repeating the missing-object copy', () => {
    render(
      <ExperienceList
        experiences={[experience(), experience({ id: 'exp-2' })]}
        companyName="BEC"
      />
    )
    expect(screen.getAllByRole('button', { name: /Cargar certificado o acta/ })).toHaveLength(2)
    expect(screen.queryByText(/El RUP no trae el objeto/)).not.toBeInTheDocument()
    expect(screen.getByText(/2 contratos · 2 sin acta/)).toBeInTheDocument()
  })
})
