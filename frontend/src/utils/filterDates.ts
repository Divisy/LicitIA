/** Dates for dashboard Desde/Hasta filters. Stored as YYYY-MM-DD in local time. */

export function formatLocalIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function parseFilterDate(value: string): string {
  const trimmed = (value || '').trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return trimmed
  }
  const dmy = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!dmy) {
    return ''
  }
  const day = dmy[1].padStart(2, '0')
  const month = dmy[2].padStart(2, '0')
  const year = dmy[3]
  return `${year}-${month}-${day}`
}

export function dateFromPickerChange(dates: Date[], typedValue?: string): string {
  if (dates[0] instanceof Date && !Number.isNaN(dates[0].getTime())) {
    return formatLocalIsoDate(dates[0])
  }
  return parseFilterDate(typedValue || '')
}
