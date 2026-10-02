import { describe, expect, it } from 'vitest'
import {
  defaultContractKindFromSectors,
  isValidPhone,
  parseStoredSectors,
} from './companySectors'

describe('companySectors', () => {
  it('parses stored sectors and ignores unknown values', () => {
    expect(parseStoredSectors('interventoria,obra,estudios_disenos')).toEqual([
      'interventoria',
      'estudios_disenos',
    ])
  })

  it('defaults dashboard filter to the single selected sector', () => {
    expect(defaultContractKindFromSectors(['interventoria'])).toBe('interventoria')
  })

  it('keeps Todas when more than one sector is selected', () => {
    expect(
      defaultContractKindFromSectors(['estudios_disenos', 'ejecucion_obra'])
    ).toBe('')
  })

  it('accepts colombian phone numbers', () => {
    expect(isValidPhone('+57 300 123 4567')).toBe(true)
    expect(isValidPhone('123')).toBe(false)
  })
})
