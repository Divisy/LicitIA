import type { TenderSummary } from '../api/client'

function normalizeDurationText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

export function parseDurationMonths(duration: string | null | undefined): number | null {
  if (!duration) {
    return null
  }
  const text = normalizeDurationText(duration)
  const combo = text.match(/(\d+(?:[.,]\d+)?)\s*meses?\s+y\s+(\d+(?:[.,]\d+)?)\s*dias?/)
  if (combo) {
    const months = parseFloat(combo[1].replace(',', '.'))
    const days = parseFloat(combo[2].replace(',', '.'))
    return months + days / 30
  }
  const months = text.match(/(\d+(?:[.,]\d+)?)\s*meses?/)
  if (months) {
    return parseFloat(months[1].replace(',', '.'))
  }
  const days = text.match(/(\d+(?:[.,]\d+)?)\s*dias?/)
  if (days) {
    return parseFloat(days[1].replace(',', '.')) / 30
  }
  const years = text.match(/(\d+(?:[.,]\d+)?)\s*anos?/)
  if (years) {
    return parseFloat(years[1].replace(',', '.')) * 12
  }
  return null
}

export function resolveSecopBudgetAmount(
  tenderAmount: number | null | undefined
): number | null {
  if (tenderAmount != null && tenderAmount > 0) {
    return tenderAmount
  }
  return null
}

export function parseAdvancePaymentPercentage(summary: TenderSummary | null): number | null {
  const field = summary?.fields?.find((entry) => entry.key === 'advance_payment_percentage')
  if (!field?.value || typeof field.value !== 'object' || Array.isArray(field.value)) {
    return null
  }
  const percentage = Number((field.value as { percentage?: number }).percentage)
  return Number.isFinite(percentage) ? percentage : null
}

export function computeCrpcEstimated(
  officialBudgetTotal: number | null,
  advancePaymentPercentage: number | null,
  executionMonths: number | null
): number | null {
  if (officialBudgetTotal == null || officialBudgetTotal <= 0) {
    return null
  }
  const advanceAmount =
    advancePaymentPercentage != null
      ? Math.round((officialBudgetTotal * advancePaymentPercentage) / 100)
      : 0
  const net = officialBudgetTotal - advanceAmount
  if (executionMonths != null && executionMonths > 12) {
    return Math.round((net / executionMonths) * 12)
  }
  return Math.round(net)
}

export type ClosingUrgency = 'past' | 'today' | 'soon' | 'normal'

export interface ClosingCountdown {
  days: number
  label: string
  urgency: ClosingUrgency
}

export function getClosingCountdown(closingDate: string | null | undefined): ClosingCountdown | null {
  if (!closingDate) {
    return null
  }
  const closing = new Date(closingDate)
  if (Number.isNaN(closing.getTime())) {
    return null
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  closing.setHours(0, 0, 0, 0)
  const diffMs = closing.getTime() - today.getTime()
  const days = Math.round(diffMs / (1000 * 60 * 60 * 24))

  if (days < 0) {
    return { days, label: 'Cerrada', urgency: 'past' }
  }
  if (days === 0) {
    return { days, label: 'Cierra hoy', urgency: 'today' }
  }
  if (days === 1) {
    return { days, label: 'Cierra mañana', urgency: 'soon' }
  }
  const urgency: ClosingUrgency = days <= 7 ? 'soon' : 'normal'
  return { days, label: `Cierra en ${days} días`, urgency }
}

export const formatCopCurrency = (amount: number): string =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

export function formatClosingDate(dateString: string | null | undefined): string {
  if (!dateString) {
    return 'Sin fecha de cierre'
  }
  try {
    return new Date(dateString).toLocaleDateString('es-CO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return 'Sin fecha de cierre'
  }
}
