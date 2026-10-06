import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import MarketingInfoStep from './MarketingInfoStep'

vi.mock('../../api/client', () => ({
  captureLead: vi.fn().mockResolvedValue({}),
}))

describe('MarketingInfoStep city', () => {
  it('asks for city and blocks continue without it', async () => {
    const user = userEvent.setup()
    const onNext = vi.fn()
    render(
      <MarketingInfoStep
        onNext={onNext}
        onBack={vi.fn()}
        initialData={{
          contactName: 'Rafael Tuta',
          phone: '+57 300 123 4567',
          sectors: ['ejecucion_obra'],
        }}
      />
    )
    expect(screen.getByLabelText(/Ciudad/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Continuar/ }))
    expect(onNext).not.toHaveBeenCalled()
    expect(screen.getByText(/Ingresa la ciudad/)).toBeInTheDocument()
  })
})
