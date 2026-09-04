import React, { useMemo } from 'react'
import { Tag } from '@carbon/react'
import type { Tender, TenderSummary } from '../api/client'
import {
  computeCrpcEstimated,
  formatClosingDate,
  formatCopCurrency,
  getClosingCountdown,
  parseAdvancePaymentPercentage,
  parseDurationMonths,
  resolveSecopBudgetAmount,
} from '../utils/tenderBudget'
import './DecisionSummaryBar.scss'

const OBRA_RESIDUAL_CONTRACT_KINDS = new Set(['ejecucion_obra', 'estudios_disenos_y_obra'])

export interface DecisionSummaryBarProps {
  tender: Tender
  summary: TenderSummary | null
}

const closingTagType = (urgency: string) => {
  switch (urgency) {
    case 'past':
      return 'red'
    case 'today':
    case 'soon':
      return 'warm-gray'
    default:
      return 'blue'
  }
}

const DecisionSummaryBar: React.FC<DecisionSummaryBarProps> = ({ tender, summary }) => {
  const closing = useMemo(() => getClosingCountdown(tender.closing_date), [tender.closing_date])

  const officialBudgetTotal = useMemo(
    () => resolveSecopBudgetAmount(tender.amount),
    [tender.amount]
  )

  const advancePaymentPercentage = useMemo(
    () => parseAdvancePaymentPercentage(summary),
    [summary]
  )

  const executionDurationField = summary?.fields?.find((field) => field.key === 'execution_duration')
  const executionDurationText =
    executionDurationField?.display_value &&
    executionDurationField.status !== 'unavailable' &&
    executionDurationField.status !== 'not_applicable'
      ? executionDurationField.display_value
      : null

  const executionMonths = useMemo(
    () => parseDurationMonths(executionDurationText),
    [executionDurationText]
  )

  const showCrpc =
    summary?.contract_kind != null && OBRA_RESIDUAL_CONTRACT_KINDS.has(summary.contract_kind)

  const crpcEstimated = useMemo(() => {
    if (!showCrpc) {
      return null
    }
    return computeCrpcEstimated(officialBudgetTotal, advancePaymentPercentage, executionMonths)
  }, [showCrpc, officialBudgetTotal, advancePaymentPercentage, executionMonths])

  const amountLabel =
    officialBudgetTotal != null ? formatCopCurrency(officialBudgetTotal) : 'Monto no informado'

  const detailItems: string[] = []
  if (advancePaymentPercentage != null) {
    detailItems.push(`Anticipo ${advancePaymentPercentage.toLocaleString('es-CO')}%`)
  }
  if (executionDurationText) {
    detailItems.push(`Plazo ${executionDurationText}`)
  }
  if (officialBudgetTotal != null && detailItems.length > 0) {
    detailItems.unshift(`POE ${formatCopCurrency(officialBudgetTotal)}`)
  }

  return (
    <section className="decision-summary-bar" aria-label="Resumen para decidir">
      <p className="decision-summary-bar__eyebrow">Resumen</p>
      <div className="decision-summary-bar__row decision-summary-bar__row--primary">
        {closing && (
          <Tag type={closingTagType(closing.urgency)} size="md">
            {closing.label}
          </Tag>
        )}
        {tender.closing_date && (
          <span className="decision-summary-bar__chip">{formatClosingDate(tender.closing_date)}</span>
        )}
        <span className="decision-summary-bar__chip decision-summary-bar__chip--amount">
          {amountLabel}
        </span>
        {summary?.contract_kind_label && (
          <Tag type="outline" size="md">{summary.contract_kind_label}</Tag>
        )}
      </div>
      {detailItems.length > 0 && (
        <p className="decision-summary-bar__row decision-summary-bar__row--secondary">
          {detailItems.join(' · ')}
        </p>
      )}
      {crpcEstimated != null && (
        <p className="decision-summary-bar__row decision-summary-bar__row--crpc">
          <span className="decision-summary-bar__crpc-label">CRPC estimada</span>
          <span className="decision-summary-bar__crpc-value">{formatCopCurrency(crpcEstimated)}</span>
        </p>
      )}
    </section>
  )
}

export default DecisionSummaryBar
