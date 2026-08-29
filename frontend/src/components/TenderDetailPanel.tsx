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
    'contracts_minimum',
    'experience_value_tiers',
    'specific_min_percentage',
    'activity_codes',
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
] as const

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  pliego_condiciones: 'Pliego de condiciones',
  anexo_tecnico: 'Anexo técnico',
  presupuesto: 'Presupuesto',
}

const ACCEPTED_DOCUMENT_EXTENSIONS = '.pdf,.xlsx,.xls,.xlsm'

const ACCEPTED_DOCUMENT_MIME_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.xlsm']

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

const REQUIREMENT_SOURCE_LABELS: Record<string, string> = {
  pliego_condiciones: 'Pliego',
  anexo_tecnico: 'Anexo técnico',
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
    const loadDocuments = async () => {
      await reloadDocuments(tender.id)
    }

    const loadSummary = async () => {
      await reloadSummary(tender.id)
    }

    const loadRequirements = async () => {
      await reloadRequirements(tender.id, false)
    }

    loadDocuments()
    loadSummary()
    loadRequirements()
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

  const isAcceptedUploadFile = (file: File) => {
    const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`
    return ACCEPTED_DOCUMENT_MIME_EXTENSIONS.includes(extension)
  }

  const uploadDocumentFile = async (documentType: TenderDocumentType, file: File) => {
    if (!tender) {
      return
    }
    if (!isAcceptedUploadFile(file)) {
      setUploadError('Solo se permiten archivos PDF, XLSX, XLS o XLSM')
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
    const otherItems = items.filter(
      (item) =>
        item.key !== scopeKey &&
        item.key !== EXPERIENCE_ACCREDITATION_KEY &&
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
            {metricItems.length > 0 && (
              <div className="tender-detail-panel__experience-metrics">
                {metricItems.map((item) => {
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

            {scopeItem?.display_value && (
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
                    .filter((section) => !EXPERIENCE_SECTION_KEYS.has(section.key))
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
                                o haz clic para seleccionar · PDF, XLSX, XLS
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
