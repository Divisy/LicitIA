import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import RupCapacityCard from './RupCapacityCard'
import { RupCapacity } from '../api/client'

const capacity: RupCapacity = {
  liquidez: 1.62,
  endeudamiento: 0.57,
  cobertura_intereses: 6.5,
  rentabilidad_patrimonio: 0.05,
  rentabilidad_activo: 0.02,
  capital_trabajo: 1732153922,
  cut_year: 2023,
  organizacional: { company_size: 'microempresa' },
}

describe('RupCapacityCard', () => {
  it('shows financial and organizational metrics with a cut-year badge', () => {
    render(<RupCapacityCard capacity={capacity} />)
    expect(screen.getByText('Capacidad financiera')).toBeInTheDocument()
    expect(screen.getByText('Corte 2023')).toBeInTheDocument()
    expect(screen.getByText('IL')).toBeInTheDocument()
    expect(screen.getByText('RP')).toBeInTheDocument()
    expect(screen.getByText('Microempresa')).toBeInTheDocument()
    expect(screen.getByText('1,62')).toBeInTheDocument()
  })
})
