import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import FiltersBar from './FiltersBar'

const noop = () => {}

describe('FiltersBar entity filter', () => {
  it('shows entidad contratante and not company name', () => {
    render(
      <FiltersBar
        dateFrom=""
        dateTo=""
        department=""
        entity=""
        contractKind=""
        onDateFromChange={noop}
        onDateToChange={noop}
        onDepartmentChange={noop}
        onEntityChange={noop}
        onContractKindChange={noop}
        onSubmit={noop}
      />
    )
    expect(screen.getByLabelText('Entidad contratante')).toBeInTheDocument()
    expect(screen.queryByLabelText(/nombre de empresa/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/razón social/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Tipología de proyecto')).not.toBeInTheDocument()
  })

  it('keeps the typed entity and submits it with Buscar', async () => {
    const user = userEvent.setup()
    const onEntityChange = vi.fn()
    const onSubmit = vi.fn()
    render(
      <FiltersBar
        dateFrom=""
        dateTo=""
        department=""
        entity=""
        contractKind=""
        onDateFromChange={noop}
        onDateToChange={noop}
        onDepartmentChange={noop}
        onEntityChange={onEntityChange}
        onContractKindChange={noop}
        onSubmit={onSubmit}
      />
    )
    await user.type(screen.getByLabelText('Entidad contratante'), 'INV')
    expect(onEntityChange).toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /Buscar/i }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })
})
