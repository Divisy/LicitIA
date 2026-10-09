import { beforeAll, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExperienceList from './ExperienceList'
import { CompanyExperience, updateExperienceContractKind } from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    updateExperienceContractKind: vi.fn(),
  }
})

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
    project_typologies: [],
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

  it('shows the extracted contract object in its own column', () => {
    render(
      <ExperienceList
        experiences={[
          experience({
            specific_experience: 'Construcción y mejoramiento de la malla vial en Paipa.',
            specific_evidence_filename: 'ACTA.pdf',
            project_typologies: ['vias'],
            partner_name: 'Otto Harry',
            participation_percent: 25,
          }),
        ]}
        companyName="BEC"
      />
    )
    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent || '')
    expect(headers[0]?.endsWith('#')).toBe(true)
    expect(headers[1]?.includes('Objeto del contrato')).toBe(true)
    expect(screen.getByText('Construcción y mejoramiento de la malla vial en Paipa.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Obra Paipa' })).not.toBeInTheDocument()
    expect(screen.getByText('Otto Harry · 25%')).toBeInTheDocument()
    expect(screen.getAllByText('Tipología').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Vías').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Reemplazar/ })).toBeInTheDocument()
  })

  it('opens the full contract object when the truncated text is clicked', async () => {
    const user = userEvent.setup()
    const fullObject =
      'INTERVENTORÍA TÉCNICA, ADMINISTRATIVA Y CONTABLE DE LOS CONTRATOS DE OBRA DE REFORZAMIENTO ESTRUCTURAL DE PLANTAS FÍSICAS.'
    render(
      <ExperienceList
        experiences={[
          experience({
            project_description: 'Texto de la planilla que no debe verse',
            specific_experience: fullObject,
            specific_evidence_filename: 'ACTA.pdf',
            contract_number: '3396 DE 2008',
            contracting_entity: 'SECRETARIA DE INTEGRACION SOCIAL',
          }),
        ]}
        companyName="BEC"
      />
    )

    await user.click(screen.getByRole('button', { name: fullObject }))
    expect(screen.getByRole('heading', { name: 'Objeto del contrato' })).toBeInTheDocument()
    expect(screen.getAllByText('3396 DE 2008').length).toBeGreaterThan(1)
    expect(screen.getAllByText(/SECRETARIA DE INTEGRACION SOCIAL/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(fullObject).length).toBeGreaterThan(1)
    expect(screen.queryByText('Texto de la planilla que no debe verse')).not.toBeInTheDocument()
  })

  it('leaves the object column empty when no acta is uploaded', () => {
    render(
      <ExperienceList
        experiences={[
          experience({
            project_description: 'Obra de la planilla',
            specific_experience: 'Experiencia escrita en la planilla',
            specific_evidence_filename: null,
          }),
        ]}
        companyName="BEC"
      />
    )

    expect(screen.queryByText('Obra de la planilla')).not.toBeInTheDocument()
    expect(screen.queryByText('Experiencia escrita en la planilla')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /planilla/ })).not.toBeInTheDocument()
  })

  it('saves the contract type the user picks', async () => {
    const user = userEvent.setup()
    const onUpdated = vi.fn()
    const saved = experience({ contract_kind: 'interventoria', contract_kind_label: 'Interventoría' })
    vi.mocked(updateExperienceContractKind).mockResolvedValue(saved)

    render(
      <ExperienceList
        experiences={[experience()]}
        companyName="BEC"
        onUpdated={onUpdated}
      />
    )

    const select = screen.getAllByRole('combobox', { name: 'Tipo de contrato' }).at(-1)!
    expect(select).toHaveValue('estudios_disenos_y_obra')
    await user.selectOptions(select, 'interventoria')
    expect(updateExperienceContractKind).toHaveBeenCalledWith('exp-1', 'interventoria')
    expect(onUpdated).toHaveBeenCalledWith(saved)
  })

  it('filters the list by contracting entity', async () => {
    const user = userEvent.setup()
    render(
      <ExperienceList
        experiences={[
          experience({ contracting_entity: 'IDU', contractor_name: 'CONSORCIO IDU' }),
          experience({
            id: 'exp-2',
            contracting_entity: 'INVIAS',
            contractor_name: 'CONSORCIO INVIAS',
          }),
        ]}
        companyName="BEC"
      />
    )

    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Entidad contratante' }),
      'INVIAS'
    )
    expect(screen.getByText('CONSORCIO INVIAS')).toBeInTheDocument()
    expect(screen.queryByText('CONSORCIO IDU')).not.toBeInTheDocument()
    expect(screen.getByText(/1 de 2 contratos/)).toBeInTheDocument()
  })
})
