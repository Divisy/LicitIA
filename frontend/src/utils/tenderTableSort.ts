import type { Tender } from '../api/client'

export type TenderSortKey = 'publication_date' | 'closing_date' | 'amount' | 'match'
export type SortDirection = 'asc' | 'desc'

export const DEFAULT_TENDER_SORT_KEY: TenderSortKey = 'closing_date'
export const DEFAULT_TENDER_SORT_DIRECTION: SortDirection = 'desc'

export const SORTABLE_TENDER_COLUMNS = new Set<TenderSortKey>([
  'publication_date',
  'closing_date',
  'amount',
  'match',
])

export function isSortableTenderColumn(key: string): key is TenderSortKey {
  return SORTABLE_TENDER_COLUMNS.has(key as TenderSortKey)
}

function parseDate(value: string | null): number | null {
  if (!value) return null
  const time = Date.parse(value)
  return Number.isNaN(time) ? null : time
}

function compareNullableNumber(
  a: number | null | undefined,
  b: number | null | undefined,
  direction: SortDirection
): number {
  const left = a ?? null
  const right = b ?? null
  if (left === null && right === null) return 0
  if (left === null) return 1
  if (right === null) return -1
  return direction === 'asc' ? left - right : right - left
}

function compareNullableDate(
  a: string | null,
  b: string | null,
  direction: SortDirection
): number {
  const timeA = parseDate(a)
  const timeB = parseDate(b)
  if (timeA === null && timeB === null) return 0
  if (timeA === null) return 1
  if (timeB === null) return -1
  return direction === 'asc' ? timeA - timeB : timeB - timeA
}

export function compareTenders(
  a: Tender,
  b: Tender,
  key: TenderSortKey,
  direction: SortDirection
): number {
  switch (key) {
    case 'publication_date':
      return compareNullableDate(a.publication_date, b.publication_date, direction)
    case 'closing_date':
      return compareNullableDate(a.closing_date, b.closing_date, direction)
    case 'amount':
      return compareNullableNumber(a.amount, b.amount, direction)
    case 'match':
      return compareNullableNumber(a.experience_match_score, b.experience_match_score, direction)
    default:
      return 0
  }
}

export function sortTenders(
  tenders: Tender[],
  key: TenderSortKey,
  direction: SortDirection
): Tender[] {
  const sorted = [...tenders]
  sorted.sort((a, b) => {
    const primary = compareTenders(a, b, key, direction)
    if (primary !== 0) return primary
    return (a.entity_name || '').localeCompare(b.entity_name || '', 'es')
  })
  return sorted
}

export function getInitialSortDirectionForColumn(key: TenderSortKey): SortDirection {
  return key === 'amount' || key === 'match' ? 'asc' : 'desc'
}
