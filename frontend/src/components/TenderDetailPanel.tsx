import React, { useEffect, useMemo, useState } from 'react'
import {
  ComposedModal,
  ModalHeader,
  ModalBody,
  Loading,
  Link,
  Tag,
  Tile,
} from '@carbon/react'
import { Download, Launch, Document } from '@carbon/icons-react'
import {
  Tender,
  TenderDocument,
  TenderSummary,
  TenderSummaryField,
  getTenderDocuments,
  getTenderDocumentDownloadUrl,
  getTenderSummary,
} from '../api/client'
import './TenderDetailPanel.scss'

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

const SUMMARY_FIELD_KEYS_BY_KIND: Record<string, readonly string[]> = {
  ejecucion_obra: [
    'aiu_percentage',
    'lots_groups',
    'execution_duration',
    'advance_payment_percentage',
    'payment_method',
  ],
  interventoria: ['lots_groups', 'execution_duration', 'payment_method'],
  estudios_disenos: ['lots_groups', 'execution_duration', 'payment_method'],
  desconocido: ['lots_groups', 'execution_duration', 'payment_method'],
}

const DEFAULT_SUMMARY_FIELD_KEYS = SUMMARY_FIELD_KEYS_BY_KIND.desconocido

const SUMMARY_FIELD_LABELS: Record<string, string> = {
  aiu_percentage: 'Porcentaje de AIU',
  lots_groups: 'Grupos o lotes',
  execution_duration: 'Duración de la obra',
  advance_payment_percentage: 'Anticipo',
  payment_method: 'Forma de pago',
}

const TenderDetailPanel: React.FC<TenderDetailPanelProps> = ({
  tender,
  open,
  onClose,
}) => {
  const [documents, setDocuments] = useState<TenderDocument[]>([])
  const [summary, setSummary] = useState<TenderSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !tender) {
      setDocuments([])
      setSummary(null)
      setError(null)
      setSummaryError(null)
      return
    }

    let cancelled = false
    const loadDocuments = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await getTenderDocuments(tender.id)
        if (!cancelled) {
          setDocuments(response.items)
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(
            err?.response?.data?.detail ||
              err?.message ||
              'No se pudieron cargar los documentos'
          )
          setDocuments([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    const loadSummary = async () => {
      setSummaryLoading(true)
      setSummaryError(null)
      try {
        const response = await getTenderSummary(tender.id)
        if (!cancelled) {
          setSummary(response)
        }
      } catch (err: any) {
        if (!cancelled) {
          setSummaryError(
            err?.response?.data?.detail ||
              err?.message ||
              'No se pudo cargar la información general'
          )
          setSummary(null)
        }
      } finally {
        if (!cancelled) {
          setSummaryLoading(false)
        }
      }
    }

    loadDocuments()
    loadSummary()
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
    return keys.map((key) => byKey.get(key)).filter(
      (field): field is TenderSummaryField => Boolean(field)
    )
  }, [summary])

  const renderSummaryValue = (field: TenderSummaryField) => {
    if (field.status === 'not_applicable') {
      return field.display_value || 'No aplica'
    }
    if (field.status === 'unavailable' || !field.display_value) {
      return 'No disponible'
    }
    return field.display_value
  }

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

  return (
    <ComposedModal open={open} onClose={onClose} size="lg" className="tender-detail-modal">
      <ModalHeader title={title} label="Detalle de licitación" closeModal={onClose} />
      <ModalBody>
        <div className="tender-detail-panel">
          <section className="tender-detail-panel__summary">
            <div className="tender-detail-panel__summary-header">
              <h3 className="tender-detail-panel__entity">{tender.entity_name}</h3>
              {tender.state && (
                <Tag type="blue" size="sm">
                  {tender.state}
                </Tag>
              )}
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

          <section className="tender-detail-panel__documents">
            <h4 className="tender-detail-panel__documents-title">Documentos clave</h4>

            {loading && (
              <div className="tender-detail-panel__loading">
                <Loading description="Cargando documentos..." withOverlay={false} small />
              </div>
            )}

            {!loading && error && (
              <Tile className="tender-detail-panel__empty">
                <p>{error}</p>
              </Tile>
            )}

            {!loading && !error && documents.length === 0 && (
              <Tile className="tender-detail-panel__empty">
                {tender.documents_extraction_attempted_at ? (
                  <>
                    <p>No se encontraron documentos clave en SECOP para esta licitación.</p>
                    <p className="tender-detail-panel__empty-hint">
                      La extracción ya se ejecutó; es posible que la entidad no haya publicado
                      pliego, anexo o presupuesto en datos abiertos, o que estén dentro de
                      archivos comprimidos.
                    </p>
                  </>
                ) : (
                  <>
                    <p>Extracción de documentos pendiente.</p>
                    <p className="tender-detail-panel__empty-hint">
                      Los documentos clave se descargarán automáticamente en el próximo ciclo
                      de extracción.
                    </p>
                  </>
                )}
              </Tile>
            )}

            {!loading && !error && documents.length > 0 && (
              <div className="tender-detail-panel__groups">
                {DOCUMENT_TYPE_ORDER.filter(
                  (type) => (groupedDocuments[type] || []).length > 0
                ).map((type) => (
                  <div key={type} className="tender-detail-panel__group">
                    <h5 className="tender-detail-panel__group-title">
                      {DOCUMENT_TYPE_LABELS[type] || type}
                    </h5>
                    <ul className="tender-detail-panel__file-list">
                      {(groupedDocuments[type] || []).map((doc) => (
                        <li key={doc.id} className="tender-detail-panel__file-item">
                          <div className="tender-detail-panel__file-info">
                            <Document size={16} />
                            <div>
                              <span className="tender-detail-panel__file-name">
                                {doc.file_name}
                              </span>
                              <span className="tender-detail-panel__file-meta">
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
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </ModalBody>
    </ComposedModal>
  )
}

export default TenderDetailPanel
