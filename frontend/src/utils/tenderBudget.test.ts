import { describe, expect, it } from 'vitest'
import {
  computeCrpcEstimated,
  getClosingCountdown,
  parseDurationMonths,
} from './tenderBudget'

describe('parseDurationMonths', () => {
  it('parses months', () => {
    expect(parseDurationMonths('18 meses')).toBe(18)
  })

  it('parses years', () => {
    expect(parseDurationMonths('2 años')).toBe(24)
  })
})

describe('computeCrpcEstimated', () => {
  it('uses POE minus advance when plazo <= 12 months', () => {
    expect(computeCrpcEstimated(100_000_000, 20, 10)).toBe(80_000_000)
  })

  it('prorates when plazo > 12 months', () => {
    expect(computeCrpcEstimated(120_000_000, 0, 24)).toBe(60_000_000)
  })
})

describe('getClosingCountdown', () => {
  it('returns null without date', () => {
    expect(getClosingCountdown(null)).toBeNull()
  })

  it('labels closed tenders', () => {
    const past = new Date()
    past.setDate(past.getDate() - 3)
    const result = getClosingCountdown(past.toISOString())
    expect(result?.label).toBe('Cerrada')
    expect(result?.urgency).toBe('past')
  })
})
