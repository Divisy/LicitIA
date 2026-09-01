import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ComposedModal,
  ModalHeader,
  ModalBody,
  Loading,
  Link,
  Tag,
  Tile,
  InlineNotification,
  Button,
  IconButton,
} from '@carbon/react'
import { Download, Launch, Document, Upload, Star, StarFilled } from '@carbon/icons-react'
import {
  Tender,
  TenderDocument,
  TenderSummary,
  TenderSummaryField,
  TenderRequirements,
  TenderRequirementSection,
  TenderRequirementItem,
  TenderDocumentType,
  getTenderDocuments,
  getTenderDocumentDownloadUrl,
  getTenderSummary,
  getTenderRequirements,
  uploadTenderDocument,
} from '../api/client'
import { useFavoriteTenders } from '../hooks/useFavoriteTenders'
import './TenderDetailPanel.scss'

const EXPERIENCE_SECTION_KEYS = new Set(['experiencia_general', 'experiencia_especifica'])
const FINANCIAL_SECTION_KEYS = new Set(['indicadores_financieros'])

const REQUIREMENT_ITEM_ORDER: Record<string, string[]> = {
  experiencia_general: [
    'requirement_description',
    'contracts_minimum',
    'experience_value_tiers',
    'min_percentage_budget',
    'min_amount_smmlv',
    'time_window_years',
    'accreditation_method',
  ],
  experiencia_especifica: [
    'specific_scope',
    'specific_area_phases',
    'contracts_minimum',
    'experience_value_tiers',
    'specific_min_percentage',
    'activity_codes',
  ],
  indicadores_financieros: [
    'financial_summary',
    'liquidez_corriente',
    'endeudamiento',
    'cobertura_intereses',
    'capital_trabajo',
    'patrimonio_minimo',
    'rentabilidad_patrimonio',
    'rentabilidad_activo',
    'qualification_score',
    'matriz_2_reference',
    'accreditation_method',
    'financial_exemptions',
  ],
}

const EXPERIENCE_METRIC_KEYS = new Set([
  'min_percentage_budget',
  'min_amount_smmlv',
  'time_window_years',
  'specific_min_percentage',
  'contracts_minimum',
  'activity_codes',
])

type ExperienceValueTier = {
  contract_range: string
  percentage: number
}

const parseExperienceValueTiers = (item: TenderRequirementItem): ExperienceValueTier[] => {
  if (!Array.isArray(item.value)) {
    return []
  }
  return item.value
    .map((entry) => {
      if (!entry || typeof entry !== 'object') {
        return null
      }
      const record = entry as Record<string, unknown>
      const percentage = Number(record.percentage)
      const contractRange = String(record.contract_range || '').trim()
      if (!contractRange || !Number.isFinite(percentage)) {
        return null
      }
      return { contract_range: contractRange, percentage }
    })
    .filter((tier): tier is ExperienceValueTier => tier != null)
}

type SpecificAreaPhase = {
  phase: string
  area_percentage: number
  total_m2: number
  minimum_m2: number
  max_contracts?: number
}

type FinancialIndicatorValue = {
  indicator?: string
  formula?: string
  operator?: string
  threshold?: number
  threshold_note?: string
  threshold_by_range?: Record<
    string,
    {
      operator?: string
      threshold?: number
    }
  >
  compare_to?: string
  min_amount_cop?: number
  ctd_percentage?: number
  ctd_formula?: string
  ctd_condition?: string
  ctd_cap?: string
}

const FINANCIAL_INDICATOR_KEYS = new Set([
  'liquidez_corriente',
  'endeudamiento',
  'cobertura_intereses',
  'capital_trabajo',
  'patrimonio_minimo',
  'rentabilidad_patrimonio',
  'rentabilidad_activo',
])

const REQUIREMENT_SOURCE_LABELS: Record<string, string> = {
  pliego_condiciones: 'Pliego',
  anexo_tecnico: 'Anexo técnico',
  indicadores_financieros: 'Matriz de indicadores',
}

const parseSpecificAreaPhases = (item: TenderRequirementItem): SpecificAreaPhase[] => {
  if (!Array.isArray(item.value)) {
    return []
  }
  return item.value
    .map((entry) => {
      if (!entry || typeof entry !== 'object') {
        return null
      }
      const record = entry as Record<string, unknown>
      const areaPercentage = Number(record.area_percentage)
      const totalM2 = Number(record.total_m2)
      const minimumM2 = Number(record.minimum_m2)
      const phase = String(record.phase || '').trim()
      if (!phase || !Number.isFinite(areaPercentage) || !Number.isFinite(totalM2)) {
        return null
      }
      return {
        phase,
        area_percentage: areaPercentage,
        total_m2: totalM2,
        minimum_m2: Number.isFinite(minimumM2)
          ? minimumM2
          : Math.round((totalM2 * areaPercentage) / 100),
        max_contracts:
          typeof record.max_contracts === 'number' ? record.max_contracts : undefined,
      }
    })
    .filter((phase): phase is SpecificAreaPhase => phase != null)
}

const formatAreaM2 = (value: number): string =>
  `${Math.round(value).toLocaleString('es-CO')} m²`

const EXPERIENCE_SCOPE_KEY: Record<string, string> = {
  experiencia_general: 'requirement_description',
  experiencia_especifica: 'specific_scope',
}

const EXPERIENCE_ACCREDITATION_KEY = 'accreditation_method'

const EXPERIENCE_METRIC_LABELS: Record<string, string> = {
  min_percentage_budget: '% mínimo del PO',
  min_amount_smmlv: 'Monto en SMMLV',
  time_window_years: 'Antigüedad',
  specific_min_percentage: '% mínimo específico',
  contracts_minimum: 'Nº de contratos',
  activity_codes: 'Códigos de actividad',
}

const PO_PERCENTAGE_KEYS = new Set(['min_percentage_budget', 'specific_min_percentage'])

const parsePoPercentage = (item: TenderRequirementItem): number | null => {
  if (typeof item.value === 'number' && Number.isFinite(item.value)) {
    return item.value
  }
  const text = item.display_value || ''
  const match = text.match(/(\d{1,3}(?:[.,]\d+)?)\s*%/)
  if (!match) {
    return null
  }
  const percentage = parseFloat(match[1].replace(',', '.'))
  return Number.isFinite(percentage) ? percentage : null
}

const formatCopCurrency = (amount: number): string =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

const computePoMinimumAmount = (
  officialBudgetTotal: number | null,
  item: TenderRequirementItem
): number | null => {
  if (!PO_PERCENTAGE_KEYS.has(item.key) || officialBudgetTotal == null || officialBudgetTotal <= 0) {
    return null
  }
  const percentage = parsePoPercentage(item)
  if (percentage == null) {
    return null
  }
  return Math.round((officialBudgetTotal * percentage) / 100)
}

const parseFinancialIndicator = (item: TenderRequirementItem): FinancialIndicatorValue | null => {
  if (!item.value || typeof item.value !== 'object' || Array.isArray(item.value)) {
    return null
  }
  return item.value as FinancialIndicatorValue
}

const formatRangeThreshold = (
  key: string | undefined,
  operator: string | undefined,
  threshold: number | undefined
): string | null => {
  if (!operator || threshold == null) {
    return null
  }
  const symbol = operator === '<=' ? '≤' : '≥'
  if (key === 'endeudamiento' && threshold <= 1) {
    return `${symbol} ${(threshold * 100).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%`
  }
  if (
    (key === 'rentabilidad_patrimonio' || key === 'rentabilidad_activo') &&
    threshold > 0 &&
    threshold <= 1
  ) {
    return `${symbol} ${(threshold * 100).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%`
  }
  return `${symbol} ${threshold.toLocaleString('es-CO')}`
}

const BUDGET_RANGE_LABELS: Record<string, { title: string; detail: string }> = {
  rango_1: {
    title: 'Contrato pequeño',
    detail: 'Presupuesto oficial menor a 4.000 SMMLV',
  },
  rango_2: {
    title: 'Contrato grande',
    detail: 'Presupuesto oficial de 4.000 SMMLV en adelante',
  },
}

const FINANCIAL_INDICATOR_HINTS: Record<string, string> = {
  liquidez_corriente: '¿Puede la empresa cubrir sus deudas a corto plazo?',
  endeudamiento: '¿Qué tan endeudada está la empresa?',
  cobertura_intereses: '¿La utilidad alcanza para pagar intereses?',
  capital_trabajo: '¿Tiene recursos para operar durante el contrato?',
  patrimonio_minimo: 'Patrimonio neto mínimo exigido',
  rentabilidad_patrimonio: 'Rentabilidad sobre el patrimonio (ROE)',
  rentabilidad_activo: 'Rentabilidad sobre los activos totales (ROA)',
}

const FINANCIAL_FORMULA_PLAIN: Record<string, string> = {
  liquidez_corriente: 'Activo corriente ÷ Pasivo corriente',
  endeudamiento: 'Pasivo total ÷ Activo total',
  cobertura_intereses: 'Utilidad operacional ÷ Gastos por intereses',
  capital_trabajo: 'Activo corriente − Pasivo corriente',
  patrimonio_minimo: 'Activo total − Pasivo total',
  rentabilidad_patrimonio: 'Utilidad operacional ÷ Patrimonio',
  rentabilidad_activo: 'Utilidad operacional ÷ Activo total',
}

type FinancialThresholdRow = {
  rangeKey?: string
  label: string
  value: string
}

const buildFinancialThresholdRows = (
  itemKey: string,
  indicator: FinancialIndicatorValue
): FinancialThresholdRow[] => {
  const byRange = indicator.threshold_by_range
  if (byRange?.rango_1 && byRange?.rango_2) {
    const rows: FinancialThresholdRow[] = []
    for (const rangeKey of ['rango_1', 'rango_2'] as const) {
      const range = byRange[rangeKey]
      const formatted = formatRangeThreshold(itemKey, range?.operator, range?.threshold)
      if (!formatted) {
        continue
      }
      const rangeMeta = BUDGET_RANGE_LABELS[rangeKey]
      rows.push({
        rangeKey,
        label: rangeMeta?.title || rangeKey,
        value: formatted,
      })
    }
    return rows
  }

  const single = formatFinancialThreshold(indicator)
  if (!single) {
    return []
  }
  return [{ label: 'Mínimo exigido', value: single }]
}

const hasDualBudgetRanges = (items: TenderRequirementItem[]): boolean =>
  items.some((item) => {
    const indicator = parseFinancialIndicator(item)
    return Boolean(indicator?.threshold_by_range?.rango_1 && indicator?.threshold_by_range?.rango_2)
  })

const formatFinancialSources = (items: TenderRequirementItem[]): string | null => {
  const labels = [
    ...new Set(
      items
        .map((item) => REQUIREMENT_SOURCE_LABELS[item.source_document] || item.source_document)
        .filter(Boolean)
    ),
  ]
  if (labels.length === 0) {
    return null
  }
  return labels.join(' y ')
}

const isFinancialCitationNoise = (item: TenderRequirementItem): boolean => {
  if (!FINANCIAL_INDICATOR_KEYS.has(item.key)) {
    return isRedundantEvidence(item)
  }
  if (!item.evidence) {
    return true
  }
  const evidence = normalizeComparableText(item.evidence)
  if (evidence.length < 120) {
    return true
  }
  if (/indice de liquidez|indice de endeudamiento|rentabilidad del/.test(evidence)) {
    return true
  }
  return isRedundantEvidence(item)
}

const formatAccreditationText = (value: string): string => {
  if (/^rup\b/i.test(value.trim())) {
    return 'Registro Único de Proponentes (RUP), vigente y en firme al momento de presentar la oferta.'
  }
  if (value.toLowerCase().includes('rup') && !value.toLowerCase().includes('registro único')) {
    return value.replace(/\bRUP\b/gi, 'Registro Único de Proponentes (RUP)')
  }
  return value
}

const formatFinancialThreshold = (indicator: FinancialIndicatorValue): string | null => {
  const byRange = indicator.threshold_by_range
  if (byRange?.rango_1 && byRange?.rango_2) {
    const r1 = formatRangeThreshold(
      indicator.indicator,
      byRange.rango_1.operator,
      byRange.rango_1.threshold
    )
    const r2 = formatRangeThreshold(
      indicator.indicator,
      byRange.rango_2.operator,
      byRange.rango_2.threshold
    )
    if (r1 && r2) {
      return `${r1} · ${r2}`
    }
  }
  if (indicator.operator && indicator.threshold != null) {
    return formatRangeThreshold(indicator.indicator, indicator.operator, indicator.threshold)
  }
  return indicator.threshold_note || null
}

const parseAdvancePaymentPercentage = (summary: TenderSummary | null): number | null => {
  const field = summary?.fields?.find((entry) => entry.key === 'advance_payment_percentage')
  if (!field?.value || typeof field.value !== 'object' || Array.isArray(field.value)) {
    return null
  }
  const percentage = Number((field.value as { percentage?: number }).percentage)
  return Number.isFinite(percentage) ? percentage : null
}

const computeCtdMinimumAmount = (
  officialBudgetTotal: number | null,
  advancePaymentPercentage: number | null,
  ctdPercentage: number | null
): number | null => {
  if (officialBudgetTotal == null || officialBudgetTotal <= 0 || ctdPercentage == null) {
    return null
  }
  const advanceAmount =
    advancePaymentPercentage != null
      ? Math.round((officialBudgetTotal * advancePaymentPercentage) / 100)
      : 0
  return Math.round((officialBudgetTotal - advanceAmount) * (ctdPercentage / 100))
}

const sortRequirementItems = (
  sectionKey: string,
  items: TenderRequirementSection['items']
) => {
  const order = REQUIREMENT_ITEM_ORDER[sectionKey] || []
  return [...items].sort((a, b) => {
    const aIndex = order.indexOf(a.key)
    const bIndex = order.indexOf(b.key)
    if (aIndex === -1 && bIndex === -1) return 0
    if (aIndex === -1) return 1
    if (bIndex === -1) return -1
    return aIndex - bIndex
  })
}

const normalizeComparableText = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()

const isRedundantEvidence = (item: TenderRequirementItem) => {
  if (!item.evidence || !item.display_value) return true
  const evidence = normalizeComparableText(item.evidence)
  const display = normalizeComparableText(item.display_value)
  if (evidence.length < 24) return true
  if (display.includes(evidence) || evidence.includes(display)) return true
  return false
}

const findRequirementItem = (
  items: TenderRequirementItem[],
  key: string
): TenderRequirementItem | undefined => items.find((item) => item.key === key)

interface TenderDetailPanelProps {
  tender: Tender | null
  open: boolean
  onClose: () => void
}

const DOCUMENT_TYPE_ORDER = [
  'pliego_condiciones',
  'anexo_tecnico',
  'presupuesto',
  'indicadores_financieros',
] as const

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  pliego_condiciones: 'Pliego de condiciones',
  anexo_tecnico: 'Anexo técnico',
  presupuesto: 'Presupuesto',
  indicadores_financieros: 'Indicadores financieros',
}

const ACCEPTED_DOCUMENT_EXTENSIONS = '.pdf,.xlsx,.xls,.xlsm'

const ACCEPTED_DOCUMENT_MIME_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.xlsm']

const ACCEPTED_INDICADORES_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.xlsm', '.docx', '.doc']

const uploadExtensionsHint = (documentType: string) =>
  documentType === 'indicadores_financieros'
    ? 'PDF, XLSX, XLS, DOCX'
    : 'PDF, XLSX, XLS'

const SUMMARY_FIELD_KEYS_BY_KIND: Record<string, readonly string[]> = {
  ejecucion_obra: [
    'aiu_percentage',
    'lots_groups',
    'execution_duration',
    'advance_payment_percentage',
    'monthly_cost',
  ],
  interventoria: [
    'lots_groups',
    'execution_duration',
    'monthly_cost',
  ],
  estudios_disenos: [
    'lots_groups',
    'execution_duration',
    'monthly_cost',
  ],
  estudios_disenos_y_obra: [
    'aiu_percentage',
    'lots_groups',
    'execution_duration',
    'advance_payment_percentage',
    'monthly_cost',
  ],
  desconocido: ['lots_groups', 'execution_duration', 'monthly_cost'],
}

const DEFAULT_SUMMARY_FIELD_KEYS = SUMMARY_FIELD_KEYS_BY_KIND.desconocido

const REQUIREMENT_STATUS_LABELS: Record<string, string> = {
  extraido: 'Extraído',
  no_encontrado: 'No encontrado',
  revisar: 'Revisar',
  documento_no_disponible: 'Documento no disponible',
  no_extraible: 'No extraíble',
}

const SUMMARY_FIELD_LABELS: Record<string, string> = {
  aiu_percentage: 'Porcentaje de AIU',
  lots_groups: 'Grupos o lotes',
  execution_duration: 'Duración de la obra',
  advance_payment_percentage: 'Anticipo',
  monthly_cost: 'Flujo de caja',
}

function normalizeDurationText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

function parseDurationMonths(duration: string | null | undefined): number | null {
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

function resolveSecopBudgetAmount(
  tenderAmount: number | null | undefined
): number | null {
  if (tenderAmount != null && tenderAmount > 0) {
    return tenderAmount
  }
  return null
}

function computeMonthlyCashFlow(
  fields: TenderSummaryField[],
  tenderAmount: number | null | undefined
): number | null {
  const duration = fields.find((field) => field.key === 'execution_duration')
  const durationText = String(duration?.display_value || duration?.value || '')
  const months = parseDurationMonths(durationText)
  const total = resolveSecopBudgetAmount(tenderAmount)
  if (!months || !total) {
    return null
  }
  return Math.round(total / months)
}

function formatMonthlyCashFlow(amount: number): string {
  return `$ ${Math.round(amount).toLocaleString('es-CO').replace(/,/g, '.')}/mes`
}

const TenderDetailPanel: React.FC<TenderDetailPanelProps> = ({
  tender,
  open,
  onClose,
}) => {
  const [documents, setDocuments] = useState<TenderDocument[]>([])
  const [summary, setSummary] = useState<TenderSummary | null>(null)
  const [requirements, setRequirements] = useState<TenderRequirements | null>(null)
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [requirementsLoading, setRequirementsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [requirementsError, setRequirementsError] = useState<string | null>(null)
  const [uploadingType, setUploadingType] = useState<TenderDocumentType | null>(null)
  const [dragOverType, setDragOverType] = useState<TenderDocumentType | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [favoriteNotice, setFavoriteNotice] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pendingUploadTypeRef = useRef<TenderDocumentType | null>(null)
  const navigate = useNavigate()
  const { isFavorite, toggleFavorite } = useFavoriteTenders()

  const reloadSummary = async (tenderId: string) => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const response = await getTenderSummary(tenderId, true)
      setSummary(response)
    } catch (err: any) {
      setSummaryError(
        err?.response?.data?.detail ||
          err?.message ||
          'No se pudo cargar la información general'
      )
    } finally {
      setSummaryLoading(false)
    }
  }

  const reloadRequirements = async (tenderId: string, refresh = false) => {
    setRequirementsLoading(true)
    setRequirementsError(null)
    try {
      const response = await getTenderRequirements(tenderId, refresh)
      setRequirements(response)
    } catch (err: any) {
      setRequirementsError(
        err?.response?.data?.detail ||
          err?.message ||
          'No se pudieron cargar los requisitos de participación'
      )
    } finally {
      setRequirementsLoading(false)
    }
  }

  const reloadDocuments = async (tenderId: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await getTenderDocuments(tenderId)
      setDocuments(response.items)
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'No se pudieron cargar los documentos'
      )
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open || !tender) {
      setDocuments([])
      setSummary(null)
      setRequirements(null)
      setError(null)
      setSummaryError(null)
      setRequirementsError(null)
      setUploadError(null)
      setUploadingType(null)
      setFavoriteNotice(null)
      return
    }

    let cancelled = false
    const loadPanelData = async () => {
      await reloadDocuments(tender.id)
      if (cancelled) return
      await Promise.all([
        reloadSummary(tender.id),
        reloadRequirements(tender.id, true),
      ])
    }

    loadPanelData()
    return () => {
      cancelled = true
    }
  }, [open, tender])

  const groupedDocuments = useMemo(() => {
    const groups: Record<string, TenderDocument[]> = {}
    for (const doc of documents) {
      if (!groups[doc.document_type]) {
        groups[doc.document_type] = []
      }
      groups[doc.document_type].push(doc)
    }
    return groups
  }, [documents])

  const summaryFields = useMemo(() => {
    if (!summary?.fields) {
      return []
    }
    const keys =
      SUMMARY_FIELD_KEYS_BY_KIND[summary.contract_kind] || DEFAULT_SUMMARY_FIELD_KEYS
    const byKey = new Map(summary.fields.map((field) => [field.key, field]))
    return keys.map((key) => {
      let field =
        byKey.get(key) ||
        ({
          key,
          label: SUMMARY_FIELD_LABELS[key] || key,
          priority: 'P2',
          source: 'computed',
          status: 'unavailable' as const,
          value: null,
          display_value: null,
          source_document_id: null,
        } as TenderSummaryField)

      if (key === 'monthly_cost') {
        const computed = computeMonthlyCashFlow(summary.fields, tender?.amount)
        if (computed != null) {
          field = {
            ...field,
            label: SUMMARY_FIELD_LABELS.monthly_cost,
            status: 'available',
            value: computed,
            display_value: formatMonthlyCashFlow(computed),
          }
        } else {
          field = {
            ...field,
            label: SUMMARY_FIELD_LABELS.monthly_cost,
          }
        }
      }

      return field
    })
  }, [summary, tender?.amount])

  const isManualDocument = (doc: TenderDocument) =>
    doc.external_document_id.startsWith('manual-') ||
    (doc.description || '').toLowerCase().includes('manual')

  const isAcceptedUploadFile = (file: File, documentType: TenderDocumentType) => {
    const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`
    const allowed =
      documentType === 'indicadores_financieros'
        ? ACCEPTED_INDICADORES_EXTENSIONS
        : ACCEPTED_DOCUMENT_MIME_EXTENSIONS
    return allowed.includes(extension)
  }

  const uploadDocumentFile = async (documentType: TenderDocumentType, file: File) => {
    if (!tender) {
      return
    }
    if (!isAcceptedUploadFile(file, documentType)) {
      setUploadError(
        documentType === 'indicadores_financieros'
          ? 'Solo se permiten archivos PDF, XLSX, XLS o DOCX'
          : 'Solo se permiten archivos PDF, XLSX, XLS o XLSM'
      )
      return
    }

    setUploadingType(documentType)
    setUploadError(null)
    try {
      await uploadTenderDocument(tender.id, documentType, file)
      await Promise.all([
        reloadDocuments(tender.id),
        reloadSummary(tender.id),
        reloadRequirements(tender.id, true),
      ])
    } catch (err: any) {
      setUploadError(
        err?.response?.data?.detail ||
          err?.message ||
          'No se pudo subir el documento'
      )
    } finally {
      setUploadingType(null)
      pendingUploadTypeRef.current = null
      setDragOverType(null)
    }
  }

  const handleUploadClick = (documentType: TenderDocumentType) => {
    pendingUploadTypeRef.current = documentType
    setUploadError(null)
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    const documentType = pendingUploadTypeRef.current
    event.target.value = ''

    if (!file || !documentType) {
      return
    }

    await uploadDocumentFile(documentType, file)
  }

  const handleDragOver = (
    event: React.DragEvent<HTMLDivElement>,
    documentType: TenderDocumentType
  ) => {
    event.preventDefault()
    event.stopPropagation()
    if (!uploadingType) {
      setDragOverType(documentType)
    }
  }

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    if (event.currentTarget.contains(event.relatedTarget as Node)) {
      return
    }
    setDragOverType(null)
  }

  const handleDrop = async (
    event: React.DragEvent<HTMLDivElement>,
    documentType: TenderDocumentType
  ) => {
    event.preventDefault()
    event.stopPropagation()
    setDragOverType(null)

    if (uploadingType) {
      return
    }

    const file = event.dataTransfer.files?.[0]
    if (!file) {
      return
    }

    await uploadDocumentFile(documentType, file)
  }

  const renderSummaryValue = (field: TenderSummaryField) => {
    if (field.status === 'not_applicable') {
      return field.display_value || 'No aplica'
    }
    if (field.status === 'unavailable' || !field.display_value) {
      return 'No disponible'
    }
    if (field.key === 'monthly_cost' && field.value != null) {
      return formatMonthlyCashFlow(Number(field.value))
    }
    return field.display_value
  }

  const requirementStatusTagType = (status: string) => {
    switch (status) {
      case 'extraido':
        return 'green'
      case 'revisar':
        return 'warm-gray'
      case 'no_extraible':
      case 'documento_no_disponible':
        return 'red'
      default:
        return 'gray'
    }
  }

  const renderExperienceSection = (section: TenderRequirementSection) => {
    const items = sortRequirementItems(section.key, section.items)
    const officialBudgetTotal = resolveSecopBudgetAmount(tender?.amount)
    const scopeKey = EXPERIENCE_SCOPE_KEY[section.key]
    const scopeItem = scopeKey ? findRequirementItem(items, scopeKey) : undefined
    const accreditationItem = findRequirementItem(items, EXPERIENCE_ACCREDITATION_KEY)
    const metricItems = items.filter(
      (item) =>
        EXPERIENCE_METRIC_KEYS.has(item.key) &&
        item.key !== scopeKey &&
        Boolean(item.display_value)
    )
    const tiersItem = findRequirementItem(items, 'experience_value_tiers')
    const experienceTiers = tiersItem ? parseExperienceValueTiers(tiersItem) : []
    const areaPhasesItem = findRequirementItem(items, 'specific_area_phases')
    const specificAreaPhases = areaPhasesItem ? parseSpecificAreaPhases(areaPhasesItem) : []
    let visibleMetricItems = experienceTiers.length
      ? metricItems.filter((item) => item.key !== 'min_percentage_budget')
      : metricItems
    if (specificAreaPhases.length > 0) {
      visibleMetricItems = visibleMetricItems.filter(
        (item) => item.key !== 'specific_min_percentage'
      )
    }
    const otherItems = items.filter(
      (item) =>
        item.key !== scopeKey &&
        item.key !== EXPERIENCE_ACCREDITATION_KEY &&
        item.key !== 'specific_area_phases' &&
        item.key !== 'experience_value_tiers' &&
        !EXPERIENCE_METRIC_KEYS.has(item.key) &&
        Boolean(item.display_value)
    )
    const sourceLabel = items[0]
      ? REQUIREMENT_SOURCE_LABELS[items[0].source_document] || items[0].source_document
      : null

    return (
      <div key={section.key} className="tender-detail-panel__experience-card">
        <div className="tender-detail-panel__requirements-group-header">
          <h5 className="tender-detail-panel__requirements-group-title">{section.title}</h5>
          <Tag type={requirementStatusTagType(section.status)} size="sm">
            {REQUIREMENT_STATUS_LABELS[section.status] || section.status}
          </Tag>
        </div>

        {sourceLabel && (
          <p className="tender-detail-panel__experience-source">Fuente: {sourceLabel}</p>
        )}

        {items.length > 0 ? (
          <>
            {visibleMetricItems.length > 0 && (
              <div className="tender-detail-panel__experience-metrics">
                {visibleMetricItems.map((item) => {
                  const minimumAmount = computePoMinimumAmount(officialBudgetTotal, item)
                  return (
                  <div key={`${section.key}-${item.key}`} className="tender-detail-panel__experience-metric">
                    <span className="tender-detail-panel__experience-metric-label">
                      {EXPERIENCE_METRIC_LABELS[item.key] || item.label}
                    </span>
                    <span className="tender-detail-panel__experience-metric-value">
                      {item.display_value}
                    </span>
                    {minimumAmount != null && (
                      <span className="tender-detail-panel__experience-metric-amount">
                        Valor mínimo: {formatCopCurrency(minimumAmount)}
                      </span>
                    )}
                  </div>
                  )
                })}
              </div>
            )}

            {experienceTiers.length > 0 && (
              <div className="tender-detail-panel__experience-tiers">
                <h6 className="tender-detail-panel__experience-block-title">
                  Valor mínimo a certificar (% del PO en SMMLV)
                </h6>
                <div className="tender-detail-panel__experience-tier-grid">
                  {experienceTiers.map((tier) => {
                    const minimumAmount =
                      officialBudgetTotal != null
                        ? Math.round((officialBudgetTotal * tier.percentage) / 100)
                        : null
                    return (
                      <div
                        key={`${section.key}-tier-${tier.contract_range}`}
                        className="tender-detail-panel__experience-tier"
                      >
                        <span className="tender-detail-panel__experience-tier-range">
                          {tier.contract_range} contratos
                        </span>
                        <span className="tender-detail-panel__experience-tier-percentage">
                          {tier.percentage}% del PO
                        </span>
                        {minimumAmount != null && (
                          <span className="tender-detail-panel__experience-tier-amount">
                            Valor mínimo: {formatCopCurrency(minimumAmount)}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {specificAreaPhases.length > 0 && (
              <div className="tender-detail-panel__experience-tiers">
                <h6 className="tender-detail-panel__experience-block-title">
                  Área mínima a acreditar (experiencia específica)
                </h6>
                <div className="tender-detail-panel__experience-tier-grid">
                  {specificAreaPhases.map((phase) => (
                    <div
                      key={`${section.key}-area-${phase.phase}`}
                      className="tender-detail-panel__experience-tier"
                    >
                      <span className="tender-detail-panel__experience-tier-range">{phase.phase}</span>
                      <span className="tender-detail-panel__experience-tier-percentage">
                        ≥{phase.area_percentage}% del área del proyecto
                      </span>
                      <span className="tender-detail-panel__experience-tier-amount">
                        Mínimo: {formatAreaM2(phase.minimum_m2)} de {formatAreaM2(phase.total_m2)}
                      </span>
                      {phase.max_contracts != null && (
                        <span className="tender-detail-panel__experience-tier-amount">
                          Hasta {phase.max_contracts} contratos de la experiencia general
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {scopeItem?.display_value && specificAreaPhases.length === 0 && (
              <div className="tender-detail-panel__experience-block">
                <h6 className="tender-detail-panel__experience-block-title">Qué se exige</h6>
                <p className="tender-detail-panel__experience-prose">{scopeItem.display_value}</p>
              </div>
            )}

            {accreditationItem?.display_value && (
              <div className="tender-detail-panel__experience-block">
                <h6 className="tender-detail-panel__experience-block-title">Cómo acreditar</h6>
                <p className="tender-detail-panel__experience-prose">
                  {accreditationItem.display_value}
                </p>
              </div>
            )}

            {otherItems.length > 0 && (
              <dl className="tender-detail-panel__requirements-list tender-detail-panel__requirements-list--compact">
                {otherItems.map((item) => (
                  <div key={`${section.key}-${item.key}`} className="tender-detail-panel__requirements-item">
                    <dt>{item.label}</dt>
                    <dd>
                      <span className="tender-detail-panel__requirements-value">
                        {item.display_value}
                      </span>
                    </dd>
                  </div>
                ))}
              </dl>
            )}

            {items.some((item) => item.evidence && !isRedundantEvidence(item)) && (
              <details className="tender-detail-panel__experience-citations">
                <summary>Ver citas del pliego</summary>
                <ul>
                  {items
                    .filter((item) => item.evidence && !isRedundantEvidence(item))
                    .map((item) => (
                      <li key={`${section.key}-${item.key}-evidence`}>
                        <strong>{item.label}:</strong> {item.evidence}
                      </li>
                    ))}
                </ul>
              </details>
            )}
          </>
        ) : (
          <p className="tender-detail-panel__requirements-empty">
            {section.status === 'documento_no_disponible'
              ? 'Sube el documento correspondiente para extraer esta sección.'
              : 'No se encontraron requisitos en el documento analizado.'}
          </p>
        )}
      </div>
    )
  }

  const renderFinancialSection = (section: TenderRequirementSection) => {
    const items = sortRequirementItems(section.key, section.items)
    const officialBudgetTotal = resolveSecopBudgetAmount(tender?.amount)
    const advancePaymentPercentage = parseAdvancePaymentPercentage(summary)
    const accreditationItem = findRequirementItem(items, 'accreditation_method')
    const exemptionsItem = findRequirementItem(items, 'financial_exemptions')
    const scoreItem = findRequirementItem(items, 'qualification_score')
    const indicatorItems = items.filter(
      (item) => FINANCIAL_INDICATOR_KEYS.has(item.key) && Boolean(item.display_value)
    )
    const dualBudgetRanges = hasDualBudgetRanges(indicatorItems)
    const sourceLabel = formatFinancialSources(items)

    return (
      <div key={section.key} className="tender-detail-panel__experience-card">
        <div className="tender-detail-panel__requirements-group-header">
          <h5 className="tender-detail-panel__requirements-group-title">{section.title}</h5>
          <Tag type={requirementStatusTagType(section.status)} size="sm">
            {REQUIREMENT_STATUS_LABELS[section.status] || section.status}
          </Tag>
        </div>

        {sourceLabel && (
          <p className="tender-detail-panel__experience-source">
            Información extraída de: {sourceLabel}
          </p>
        )}

        {items.length > 0 ? (
          <>
            <p className="tender-detail-panel__financial-intro">
              {dualBudgetRanges
                ? 'Tu empresa debe cumplir estos indicadores financieros para poder participar. Los valores dependen del tamaño del contrato según su presupuesto oficial.'
                : 'Tu empresa debe cumplir estos indicadores financieros para poder participar en la licitación.'}
            </p>

            {dualBudgetRanges && (
              <div className="tender-detail-panel__financial-range-note" role="note">
                <p>
                  <strong>¿Cómo leer los dos valores?</strong> En esta licitación hay dos rangos de
                  presupuesto. Usa la fila que corresponda al presupuesto oficial del contrato:
                </p>
                <ul>
                  <li>
                    <strong>{BUDGET_RANGE_LABELS.rango_1.title}:</strong>{' '}
                    {BUDGET_RANGE_LABELS.rango_1.detail}
                  </li>
                  <li>
                    <strong>{BUDGET_RANGE_LABELS.rango_2.title}:</strong>{' '}
                    {BUDGET_RANGE_LABELS.rango_2.detail}
                  </li>
                </ul>
              </div>
            )}

            {indicatorItems.length > 0 && (
              <div className="tender-detail-panel__experience-metrics tender-detail-panel__experience-metrics--financial">
                {indicatorItems.map((item) => {
                  const indicator = parseFinancialIndicator(item)
                  const thresholdRows = indicator ? buildFinancialThresholdRows(item.key, indicator) : []
                  const ctdMinimum =
                    item.key === 'capital_trabajo' && indicator?.ctd_percentage != null
                      ? computeCtdMinimumAmount(
                          officialBudgetTotal,
                          advancePaymentPercentage,
                          indicator.ctd_percentage
                        )
                      : null
                  const formulaHint = FINANCIAL_FORMULA_PLAIN[item.key]
                  const descriptionHint = FINANCIAL_INDICATOR_HINTS[item.key]

                  return (
                    <div
                      key={`${section.key}-${item.key}`}
                      className="tender-detail-panel__experience-metric tender-detail-panel__experience-metric--financial"
                    >
                      <span className="tender-detail-panel__experience-metric-label">
                        {item.label}
                      </span>
                      {descriptionHint && (
                        <span className="tender-detail-panel__financial-metric-hint">
                          {descriptionHint}
                        </span>
                      )}

                      {item.key === 'capital_trabajo' ? (
                        <div className="tender-detail-panel__financial-capital">
                          {ctdMinimum != null ? (
                            <span className="tender-detail-panel__experience-metric-value">
                              Mínimo exigido: {formatCopCurrency(ctdMinimum)}
                            </span>
                          ) : indicator?.min_amount_cop != null ? (
                            <span className="tender-detail-panel__experience-metric-value">
                              Mínimo exigido: {formatCopCurrency(indicator.min_amount_cop)}
                            </span>
                          ) : (
                            <span className="tender-detail-panel__experience-metric-value">
                              Definido en el pliego según el presupuesto del contrato
                            </span>
                          )}
                          {indicator?.ctd_percentage != null && (
                            <span className="tender-detail-panel__experience-metric-amount">
                              Se calcula como el {indicator.ctd_percentage}% del presupuesto oficial
                              {advancePaymentPercentage != null
                                ? ` menos el anticipo (${advancePaymentPercentage}%)`
                                : ' menos el anticipo'}
                              .
                            </span>
                          )}
                          {indicator?.ctd_condition && (
                            <span className="tender-detail-panel__experience-metric-amount">
                              {indicator.ctd_condition.replace(
                                'Plazo de ejecución < 12 meses',
                                'Solo aplica si el contrato dura menos de 12 meses'
                              )}
                            </span>
                          )}
                        </div>
                      ) : thresholdRows.length > 0 ? (
                        <div className="tender-detail-panel__financial-thresholds">
                          {thresholdRows.map((row) => (
                            <div
                              key={`${item.key}-${row.rangeKey || row.label}`}
                              className="tender-detail-panel__financial-threshold-row"
                            >
                              {dualBudgetRanges && row.rangeKey && (
                                <span className="tender-detail-panel__financial-threshold-range">
                                  {row.label}
                                </span>
                              )}
                              <span className="tender-detail-panel__experience-metric-value">
                                {row.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="tender-detail-panel__experience-metric-value">
                          {indicator ? formatFinancialThreshold(indicator) : item.display_value}
                        </span>
                      )}

                      {formulaHint && item.key !== 'capital_trabajo' && (
                        <span className="tender-detail-panel__financial-formula">
                          Cálculo: {formulaHint}
                        </span>
                      )}
                      {indicator?.min_amount_cop != null && item.key !== 'capital_trabajo' && (
                        <span className="tender-detail-panel__experience-metric-amount">
                          Monto mínimo: {formatCopCurrency(indicator.min_amount_cop)}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {scoreItem?.display_value && (
              <div className="tender-detail-panel__experience-block">
                <h6 className="tender-detail-panel__experience-block-title">Calificación</h6>
                <p className="tender-detail-panel__experience-prose">{scoreItem.display_value}</p>
              </div>
            )}

            {accreditationItem?.display_value && (
              <div className="tender-detail-panel__experience-block">
                <h6 className="tender-detail-panel__experience-block-title">Cómo demostrarlo</h6>
                <p className="tender-detail-panel__experience-prose">
                  {formatAccreditationText(accreditationItem.display_value)}
                </p>
              </div>
            )}

            {exemptionsItem?.display_value && (
              <div className="tender-detail-panel__experience-block">
                <h6 className="tender-detail-panel__experience-block-title">
                  Casos especiales
                </h6>
                <p className="tender-detail-panel__experience-prose">{exemptionsItem.display_value}</p>
              </div>
            )}

            {items.some((item) => item.evidence && !isFinancialCitationNoise(item)) && (
              <details className="tender-detail-panel__experience-citations">
                <summary>Ver texto original del documento</summary>
                <ul>
                  {items
                    .filter((item) => item.evidence && !isFinancialCitationNoise(item))
                    .map((item) => (
                      <li key={`${section.key}-${item.key}-evidence`}>
                        <strong>{item.label}:</strong> {item.evidence}
                      </li>
                    ))}
                </ul>
              </details>
            )}
          </>
        ) : (
          <p className="tender-detail-panel__requirements-empty">
            {section.status === 'documento_no_disponible'
              ? 'Sube el documento correspondiente para extraer esta sección.'
              : 'No se encontraron requisitos en el documento analizado.'}
          </p>
        )}
      </div>
    )
  }

  const renderRequirementSection = (section: TenderRequirementSection) => (
    <div key={section.key} className="tender-detail-panel__requirements-group">
      <div className="tender-detail-panel__requirements-group-header">
        <h5 className="tender-detail-panel__requirements-group-title">{section.title}</h5>
        <Tag type={requirementStatusTagType(section.status)} size="sm">
          {REQUIREMENT_STATUS_LABELS[section.status] || section.status}
        </Tag>
      </div>

      {sortRequirementItems(section.key, section.items).length > 0 ? (
        <dl className="tender-detail-panel__requirements-list">
          {sortRequirementItems(section.key, section.items).map((item) => (
            <div key={`${section.key}-${item.key}`} className="tender-detail-panel__requirements-item">
              <dt>{item.label}</dt>
              <dd>
                <span className="tender-detail-panel__requirements-value">
                  {item.display_value || '—'}
                </span>
                <span className="tender-detail-panel__requirements-meta">
                  {REQUIREMENT_SOURCE_LABELS[item.source_document] || item.source_document}
                </span>
                {item.evidence && (
                  <p className="tender-detail-panel__requirements-evidence">{item.evidence}</p>
                )}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="tender-detail-panel__requirements-empty">
          {section.status === 'documento_no_disponible'
            ? 'Sube el documento correspondiente para extraer esta sección.'
            : 'No se encontraron requisitos en el documento analizado.'}
        </p>
      )}
    </div>
  )

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('es-CO', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    } catch {
      return 'N/A'
    }
  }

  const formatCurrency = (amount: number | null): string => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return ''
    if (bytes < 1024 * 1024) {
      return `${Math.round(bytes / 1024)} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (!tender) {
    return null
  }

  const title = tender.reference || tender.external_id
  const favoriteActive = isFavorite(tender.id)

  const handleToggleFavorite = () => {
    const added = toggleFavorite(tender)
    setFavoriteNotice(
      added ? 'Licitación agregada a favoritas.' : 'Licitación quitada de favoritas.'
    )
    window.setTimeout(() => setFavoriteNotice(null), 2500)
  }

  return (
    <ComposedModal open={open} onClose={onClose} size="lg" className="tender-detail-modal">
      <ModalHeader title={title} label="Detalle de licitación" closeModal={onClose} />
      <ModalBody>
        <div className="tender-detail-panel">
          <section
            className={`tender-detail-panel__favorite-bar${
              favoriteActive ? ' tender-detail-panel__favorite-bar--active' : ''
            }`}
            aria-live="polite"
          >
            <div className="tender-detail-panel__favorite-bar-main">
              <div
                className={`tender-detail-panel__favorite-icon${
                  favoriteActive ? ' tender-detail-panel__favorite-icon--active' : ''
                }`}
                aria-hidden="true"
              >
                {favoriteActive ? <StarFilled size={22} /> : <Star size={22} />}
              </div>
              <div className="tender-detail-panel__favorite-copy">
                <p className="tender-detail-panel__favorite-title">
                  {favoriteActive ? 'Guardada en favoritas' : '¿Te interesa esta licitación?'}
                </p>
                <p className="tender-detail-panel__favorite-subtitle">
                  {favoriteActive
                    ? 'Revísala cuando quieras desde tu lista de oportunidades para licitar.'
                    : 'Guárdala para estudiar el pliego y decidir con calma antes de ofertar.'}
                </p>
              </div>
            </div>
            <div className="tender-detail-panel__favorite-actions">
              {favoriteActive ? (
                <>
                  <Button
                    kind="ghost"
                    size="sm"
                    onClick={() => {
                      onClose()
                      navigate('/favorites')
                    }}
                  >
                    Ver mis favoritas
                  </Button>
                  <Button
                    kind="secondary"
                    size="sm"
                    renderIcon={StarFilled}
                    onClick={handleToggleFavorite}
                  >
                    Quitar
                  </Button>
                </>
              ) : (
                <Button
                  kind="primary"
                  size="md"
                  renderIcon={Star}
                  onClick={handleToggleFavorite}
                >
                  Guardar en favoritas
                </Button>
              )}
            </div>
            {favoriteNotice && (
              <p className="tender-detail-panel__favorite-toast" role="status">
                {favoriteNotice}
              </p>
            )}
          </section>

          <section className="tender-detail-panel__summary">
            <div className="tender-detail-panel__summary-header">
              <h3 className="tender-detail-panel__entity">{tender.entity_name}</h3>
              <div className="tender-detail-panel__summary-badges">
                {tender.state && (
                  <Tag type="blue" size="sm">
                    {tender.state}
                  </Tag>
                )}
                <IconButton
                  kind="ghost"
                  size="md"
                  label={
                    favoriteActive ? 'Quitar de favoritas' : 'Agregar a favoritas'
                  }
                  className={`tender-detail-panel__favorite-toggle${
                    favoriteActive ? ' tender-detail-panel__favorite-toggle--active' : ''
                  }`}
                  onClick={handleToggleFavorite}
                >
                  {favoriteActive ? <StarFilled size={20} /> : <Star size={20} />}
                </IconButton>
              </div>
            </div>
            <p className="tender-detail-panel__object">{tender.object_text}</p>
            <div className="tender-detail-panel__meta">
              <div>
                <span className="tender-detail-panel__meta-label">Publicación</span>
                <span>{formatDate(tender.publication_date)}</span>
              </div>
              <div>
                <span className="tender-detail-panel__meta-label">Cierre ofertas</span>
                <span>{formatDate(tender.closing_date)}</span>
              </div>
              <div>
                <span className="tender-detail-panel__meta-label">Monto</span>
                <span>{formatCurrency(tender.amount)}</span>
              </div>
              <div>
                <span className="tender-detail-panel__meta-label">Ubicación</span>
                <span>
                  {[tender.department, tender.municipality].filter(Boolean).join(', ') ||
                    'N/A'}
                </span>
              </div>
            </div>
            <Link
              href={tender.process_url}
              target="_blank"
              rel="noopener noreferrer"
              renderIcon={Launch}
              className="tender-detail-panel__secop-link"
            >
              Ver proceso en SECOP
            </Link>
          </section>

          <section className="tender-detail-panel__summary-info">
            <div className="tender-detail-panel__summary-info-header">
              <h4 className="tender-detail-panel__documents-title">Información general</h4>
              {summary?.contract_kind_label && (
                <Tag type="gray" size="sm">
                  {summary.contract_kind_label}
                </Tag>
              )}
            </div>

            {summaryLoading && (
              <div className="tender-detail-panel__loading">
                <Loading description="Extrayendo información..." withOverlay={false} small />
              </div>
            )}

            {!summaryLoading && summaryError && (
              <Tile className="tender-detail-panel__empty">
                <p>{summaryError}</p>
              </Tile>
            )}

            {!summaryLoading && !summaryError && summary && (
              <dl className="tender-detail-panel__summary-list">
                {summaryFields.map((field) => (
                  <div
                    key={field.key}
                    className={`tender-detail-panel__summary-item tender-detail-panel__summary-item--${field.status}`}
                  >
                          <dt>{SUMMARY_FIELD_LABELS[field.key] || field.label}</dt>
                    <dd>{renderSummaryValue(field)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <section className="tender-detail-panel__requirements">
            <div className="tender-detail-panel__summary-info-header">
              <h4 className="tender-detail-panel__documents-title">Requisitos de participación</h4>
            </div>

            {requirementsLoading && (
              <div className="tender-detail-panel__loading">
                <Loading description="Extrayendo requisitos..." withOverlay={false} small />
              </div>
            )}

            {!requirementsLoading && requirementsError && (
              <Tile className="tender-detail-panel__empty">
                <p>{requirementsError}</p>
              </Tile>
            )}

            {!requirementsLoading && !requirementsError && requirements && (
              <>
                {requirements.warnings.length > 0 && (
                  <InlineNotification
                    kind="info"
                    title="Aviso"
                    subtitle={requirements.warnings.join(' ')}
                    lowContrast
                    hideCloseButton
                  />
                )}
                <div className="tender-detail-panel__requirements-groups">
                  {requirements.sections.some((section) =>
                    EXPERIENCE_SECTION_KEYS.has(section.key)
                  ) && (
                    <div className="tender-detail-panel__experience-section">
                      <h5 className="tender-detail-panel__experience-heading">Experiencia requerida</h5>
                      {requirements.sections
                        .filter((section) => EXPERIENCE_SECTION_KEYS.has(section.key))
                        .map((section) => renderExperienceSection(section))}
                    </div>
                  )}
                  {requirements.sections
                    .filter((section) => FINANCIAL_SECTION_KEYS.has(section.key))
                    .map((section) => renderFinancialSection(section))}
                  {requirements.sections
                    .filter(
                      (section) =>
                        !EXPERIENCE_SECTION_KEYS.has(section.key) &&
                        !FINANCIAL_SECTION_KEYS.has(section.key)
                    )
                    .map((section) => renderRequirementSection(section))}
                </div>
              </>
            )}
          </section>

          <section className="tender-detail-panel__documents">
            <h4 className="tender-detail-panel__documents-title">Documentos clave</h4>
            <p className="tender-detail-panel__documents-hint">
              Si SECOP no trajo un documento automáticamente, puedes subir el archivo
              descargado del portal de la entidad.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_DOCUMENT_EXTENSIONS}
              className="tender-detail-panel__file-input"
              onChange={handleFileSelected}
            />

            {uploadError && (
              <InlineNotification
                kind="error"
                title="Error al subir"
                subtitle={uploadError}
                lowContrast
                onCloseButtonClick={() => setUploadError(null)}
              />
            )}

            {loading && documents.length === 0 && (
              <div className="tender-detail-panel__loading">
                <Loading description="Cargando documentos..." withOverlay={false} small />
              </div>
            )}

            {!loading && error && (
              <Tile className="tender-detail-panel__empty">
                <p>{error}</p>
              </Tile>
            )}

            {!error && (
              <div className="tender-detail-panel__groups">
                {DOCUMENT_TYPE_ORDER.map((type) => {
                  const docs = groupedDocuments[type] || []
                  const isUploading = uploadingType === type

                  return (
                    <div key={type} className="tender-detail-panel__group">
                      <h5 className="tender-detail-panel__group-title">
                        {DOCUMENT_TYPE_LABELS[type] || type}
                      </h5>

                      {docs.length === 0 ? (
                        <div
                          className={[
                            'tender-detail-panel__dropzone',
                            dragOverType === type ? 'tender-detail-panel__dropzone--active' : '',
                            isUploading ? 'tender-detail-panel__dropzone--uploading' : '',
                          ]
                            .filter(Boolean)
                            .join(' ')}
                          onDragEnter={(event) => handleDragOver(event, type)}
                          onDragOver={(event) => handleDragOver(event, type)}
                          onDragLeave={handleDragLeave}
                          onDrop={(event) => handleDrop(event, type)}
                          onClick={() => {
                            if (!isUploading && !uploadingType) {
                              handleUploadClick(type)
                            }
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              if (!isUploading && !uploadingType) {
                                handleUploadClick(type)
                              }
                            }
                          }}
                          role="button"
                          tabIndex={0}
                          aria-label={`Subir ${DOCUMENT_TYPE_LABELS[type] || type}`}
                        >
                          {isUploading ? (
                            <Loading description="Subiendo documento..." withOverlay={false} small />
                          ) : (
                            <>
                              <Upload size={20} className="tender-detail-panel__dropzone-icon" />
                              <p className="tender-detail-panel__dropzone-title">
                                Arrastra el archivo aquí
                              </p>
                              <p className="tender-detail-panel__dropzone-hint">
                                o haz clic para seleccionar · {uploadExtensionsHint(type)}
                              </p>
                            </>
                          )}
                        </div>
                      ) : (
                        <ul className="tender-detail-panel__file-list">
                          {docs.map((doc) => (
                            <li key={doc.id} className="tender-detail-panel__file-item">
                              <div className="tender-detail-panel__file-info">
                                <Document size={16} />
                                <div>
                                  <span className="tender-detail-panel__file-name">
                                    {doc.file_name}
                                  </span>
                                  <span className="tender-detail-panel__file-meta">
                                    {isManualDocument(doc) ? 'Cargado manualmente · ' : ''}
                                    {formatFileSize(doc.file_size)}
                                    {doc.file_size ? ' · ' : ''}
                                    {formatDate(doc.downloaded_at)}
                                  </span>
                                </div>
                              </div>
                              <Link
                                href={getTenderDocumentDownloadUrl(tender.id, doc.id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                renderIcon={Download}
                              >
                                Descargar
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        </div>
      </ModalBody>
    </ComposedModal>
  )
}

export default TenderDetailPanel
