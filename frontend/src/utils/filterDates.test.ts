import { describe, expect, it } from 'vitest'
import {
  dateFromPickerChange,
  formatLocalIsoDate,
  parseFilterDate,
} from './filterDates'

describe('filterDates', () => {
  it('formats a local Date as YYYY-MM-DD without UTC shift', () => {
    const date = new Date(2026, 9, 6)
    expect(formatLocalIsoDate(date)).toBe('2026-10-06')
  })

  it('parses Carbon dd/mm/yyyy input', () => {
    expect(parseFilterDate('6/10/2026')).toBe('2026-10-06')
    expect(parseFilterDate('06/10/2026')).toBe('2026-10-06')
    expect(parseFilterDate('2026-10-06')).toBe('2026-10-06')
    expect(parseFilterDate('')).toBe('')
  })

  it('keeps the calendar date when Carbon sends a Date object', () => {
    expect(dateFromPickerChange([new Date(2026, 9, 6)])).toBe('2026-10-06')
  })
})
