import React, { useRef, useState } from 'react'
import {
  Tag,
  Select,
  SelectItem,
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Button,
  InlineNotification,
  Modal,
  TextInput,
} from '@carbon/react'
import {
  Document,
  Building,
  DocumentAdd,
  WatsonMachineLearning,
  Edit,
  Layers,
  Upload,
  CheckmarkFilled,
  Renew,
} from '@carbon/icons-react'
import {
  CompanyExperience,
  formatApiError,
  updateExperienceContractKind,
  uploadSpecificExperienceEvidence,
} from '../api/client'
import { EXPERIENCE_CONTRACT_KIND_OPTIONS } from '../utils/companySectors'
import {
  EMPTY_EXPERIENCE_FILTERS,
  ExperienceListFilters,
  experienceFilterChoices,
  filterExperiences,
  hasActiveExperienceFilters,
} from '../utils/experienceFilters'
import { typologyLabel } from '../utils/projectTypology'
import './ExperienceList.scss'

interface ExperienceListProps {
  experiences: CompanyExperience[]
  companyName: string
  onDelete?: () => void
  onUpdated?: (experience: CompanyExperience) => void
}

const UNSPSC_PREVIEW_LIMIT = 3

type UnspscModalState = {
  contract: string
  contractor: string
  entity: string
  codes: string[]
}

type ObjectModalState = {
  contract: string
  entity: string
  objectText: string
}

const ExperienceList: React.FC<ExperienceListProps> = ({
  experiences,
  companyName,
  onDelete,
  onUpdated,
}) => {
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [savingKindId, setSavingKindId] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [codesModal, setCodesModal] = useState<UnspscModalState | null>(null)
  const [objectModal, setObjectModal] = useState<ObjectModalState | null>(null)
  const [filters, setFilters] = useState<ExperienceListFilters>(EMPTY_EXPERIENCE_FILTERS)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const setFilter = (field: keyof ExperienceListFilters, value: string) => {
    setFilters((current) => ({ ...current, [field]: value }))
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

  const formatSmmlv = (amount: number): string =>
    `${new Intl.NumberFormat('es-CO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount)} SMMLV`

  const formatExperienceValue = (experience: CompanyExperience) => {
    if (experience.amount_smmlv) {
      return (
        <span className="experience-list-amount">{formatSmmlv(experience.amount_smmlv)}</span>
      )
    }
    if (experience.amount) {
      return (
        <span className="experience-list-amount">{formatCurrency(experience.amount)}</span>
      )
    }
    return 'N/A'
  }

  const handleKindChange = async (experienceId: string, value: string) => {
    setSavingKindId(experienceId)
    setUploadError(null)
    try {
      const updated = await updateExperienceContractKind(experienceId, value || null)
      onUpdated?.(updated)
    } catch (error) {
      setUploadError(formatApiError(error, 'No se pudo guardar el tipo de contrato.'))
    } finally {
      setSavingKindId(null)
    }
  }

  const openEvidencePicker = (experienceId: string) => {
    setPendingId(experienceId)
    setUploadError(null)
    fileInputRef.current?.click()
  }

  const handleEvidenceSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    const experienceId = pendingId
    event.target.value = ''
    setPendingId(null)
    if (!file || !experienceId) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Sube el certificado o el acta de finalización en PDF.')
      return
    }

    setUploadingId(experienceId)
    setUploadError(null)
    try {
      const updated = await uploadSpecificExperienceEvidence(experienceId, file)
      onUpdated?.(updated)
    } catch (error) {
      setUploadError(formatApiError(error, 'No se pudo cargar el certificado o el acta.'))
    } finally {
      setUploadingId(null)
    }
  }

  if (experiences.length === 0) {
    return (
      <div className="experience-list-empty">
        <Document size={48} className="experience-list-empty-icon" />
        <p className="experience-list-empty-text">
          No se encontraron experiencias para <strong>{companyName}</strong>.
        </p>
        <p className="experience-list-empty-hint">
          Sube el certificado RUP en PDF para comenzar.
        </p>
      </div>
    )
  }

  const filtersActive = hasActiveExperienceFilters(filters)
  const visibleExperiences = filterExperiences(experiences, filters)
  const { entities, typologies } = experienceFilterChoices(experiences)
  const contractCount = experiences.length
  const visibleCount = visibleExperiences.length
  const pendingSpecificCount = visibleExperiences.filter(
    (experience) => !((experience.specific_experience || '').trim())
  ).length

  const getExperienceIcon = (kind: string | null | undefined) => {
    if (kind === 'interventoria') {
      return <WatsonMachineLearning size={20} className="experience-list-service-icon" />
    }
    if (kind === 'ejecucion_obra') {
      return <Building size={20} className="experience-list-service-icon" />
    }
    if (kind === 'estudios_disenos_y_obra') {
      return <Layers size={20} className="experience-list-service-icon" />
    }
    if (kind === 'estudios_disenos') {
      return <Edit size={20} className="experience-list-service-icon" />
    }
    return <DocumentAdd size={20} className="experience-list-service-icon" />
  }

  const headers = [
    { key: 'number', header: '#' },
    { key: 'object', header: 'Objeto del contrato' },
    { key: 'contractor', header: 'Contratista' },
    { key: 'kind', header: 'Tipo de contrato' },
    { key: 'specific', header: 'Acta' },
    { key: 'typology', header: 'Tipología' },
    { key: 'entity', header: 'Entidad contratante' },
    { key: 'contract', header: 'Contrato' },
    { key: 'date', header: 'Fecha finalización' },
    { key: 'amount', header: 'Valor (SMMLV)' },
    { key: 'unspsc', header: 'UNSPSC' },
  ]

  const rows = visibleExperiences.map((experience, index) => {
    const kind = experience.contract_kind
    const unspscCodes = (experience.unspsc_codes || []).filter(Boolean)
    const specificText = (experience.specific_experience || '').trim()
    const hasActa = Boolean((experience.specific_evidence_filename || '').trim())
    const objectText = hasActa ? specificText : ''
    const uploading = uploadingId === experience.id
    const contractor = (experience.contractor_name || '').trim()
    const partner = (experience.partner_name || '').trim()
    const participation =
      experience.participation_percent == null
        ? ''
        : `${new Intl.NumberFormat('es-CO', {
            maximumFractionDigits: 2,
          }).format(experience.participation_percent)}%`

    return {
      id: experience.id,
      number: <span className="experience-list-number">{index + 1}</span>,
      contractor: (
        <div className="experience-list-contractor">
          {contractor || '—'}
          {partner && (
            <div className="experience-list-partner">
              {partner}
              {participation ? ` · ${participation}` : ''}
            </div>
          )}
        </div>
      ),
      kind: (
        <div className="experience-list-kind">
          {getExperienceIcon(kind)}
          <Select
            id={`experience-kind-${experience.id}`}
            labelText="Tipo de contrato"
            hideLabel
            size="sm"
            value={kind && kind !== 'desconocido' ? kind : ''}
            disabled={savingKindId === experience.id}
            onChange={(event) => handleKindChange(experience.id, event.target.value)}
          >
            <SelectItem value="" text="No identificado" />
            {EXPERIENCE_CONTRACT_KIND_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value} text={option.label} />
            ))}
          </Select>
        </div>
      ),
      specific: (
        <SpecificExperienceCell
          hasObject={Boolean(specificText)}
          filename={experience.specific_evidence_filename}
          uploading={uploading}
          onUpload={() => openEvidencePicker(experience.id)}
        />
      ),
      object: objectText ? (
        <button
          type="button"
          className="experience-list-object"
          title="Ver el objeto completo"
          onClick={() =>
            setObjectModal({
              contract: experience.contract_number || 'Sin número',
              entity: experience.contracting_entity || '',
              objectText,
            })
          }
        >
          {objectText}
        </button>
      ) : (
        <span className="experience-list-object-empty">—</span>
      ),
      typology: (experience.project_typologies || []).length ? (
        <div className="experience-list-typologies">
          {(experience.project_typologies || []).map((value) => (
            <Tag key={value} type="cyan" size="sm">
              {typologyLabel(value)}
            </Tag>
          ))}
        </div>
      ) : (
        <span className="experience-list-object-empty">—</span>
      ),
      entity: experience.contracting_entity || 'N/A',
      contract: experience.contract_number || 'N/A',
      date: formatDate(experience.completion_date),
      amount: formatExperienceValue(experience),
      unspsc: unspscCodes.length ? (
        <div className="experience-list-unspsc">
          {unspscCodes.slice(0, UNSPSC_PREVIEW_LIMIT).map((code) => (
            <Tag key={code} type="gray" size="sm">
              {code}
            </Tag>
          ))}
          {unspscCodes.length > UNSPSC_PREVIEW_LIMIT && (
            <Button
              kind="ghost"
              size="sm"
              className="experience-list-unspsc-more"
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                setCodesModal({
                  contract: experience.contract_number || 'N/A',
                  contractor: contractor || '—',
                  entity: experience.contracting_entity || 'N/A',
                  codes: unspscCodes,
                })
              }}
            >
              Ver códigos ({unspscCodes.length})
            </Button>
          )}
        </div>
      ) : (
        '—'
      ),
    }
  })

  return (
    <div className="experience-list">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        className="experience-list-file-input"
        onChange={handleEvidenceSelected}
      />
      {uploadError && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={uploadError}
          lowContrast
          onClose={() => setUploadError(null)}
        />
      )}
      <div className="experience-list-filters">
        <Select
          id="experience-filter-kind"
          labelText="Tipo de contrato"
          size="sm"
          value={filters.contractKind}
          onChange={(event) => setFilter('contractKind', event.target.value)}
        >
          <SelectItem value="" text="Todos" />
          <SelectItem value="desconocido" text="No identificado" />
          {EXPERIENCE_CONTRACT_KIND_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value} text={option.label} />
          ))}
        </Select>
        <Select
          id="experience-filter-entity"
          labelText="Entidad contratante"
          size="sm"
          value={filters.entity}
          onChange={(event) => setFilter('entity', event.target.value)}
        >
          <SelectItem value="" text="Todas" />
          {entities.map((entity) => (
            <SelectItem key={entity} value={entity} text={entity} />
          ))}
        </Select>
        <Select
          id="experience-filter-typology"
          labelText="Tipología"
          size="sm"
          value={filters.typology}
          onChange={(event) => setFilter('typology', event.target.value)}
        >
          <SelectItem value="" text="Todas" />
          {typologies.map((typology) => (
            <SelectItem key={typology} value={typology} text={typologyLabel(typology)} />
          ))}
        </Select>
        <TextInput
          id="experience-filter-date-from"
          labelText="Finaliza desde"
          type="date"
          size="sm"
          value={filters.dateFrom}
          onChange={(event) => setFilter('dateFrom', event.target.value)}
        />
        <TextInput
          id="experience-filter-date-to"
          labelText="Finaliza hasta"
          type="date"
          size="sm"
          value={filters.dateTo}
          onChange={(event) => setFilter('dateTo', event.target.value)}
        />
        <TextInput
          id="experience-filter-value-min"
          labelText="Valor mínimo (SMMLV)"
          type="number"
          size="sm"
          min={0}
          value={filters.valueMin}
          onChange={(event) => setFilter('valueMin', event.target.value)}
        />
        <TextInput
          id="experience-filter-value-max"
          labelText="Valor máximo (SMMLV)"
          type="number"
          size="sm"
          min={0}
          value={filters.valueMax}
          onChange={(event) => setFilter('valueMax', event.target.value)}
        />
        {filtersActive && (
          <Button
            kind="ghost"
            size="sm"
            className="experience-list-filters-clear"
            onClick={() => setFilters(EMPTY_EXPERIENCE_FILTERS)}
          >
            Limpiar filtros
          </Button>
        )}
      </div>
      <p className="experience-list-count">
        {filtersActive
          ? `${visibleCount} de ${contractCount} contratos`
          : `${contractCount} ${contractCount === 1 ? 'contrato' : 'contratos'}`}
        {pendingSpecificCount > 0
          ? ` · ${pendingSpecificCount} sin acta`
          : visibleCount > 0
            ? ' · experiencia específica completa'
            : ''}
      </p>
      {visibleCount === 0 && (
        <p className="experience-list-filter-empty">
          Ningún contrato coincide con estos filtros.
        </p>
      )}
      {objectModal && (
        <Modal
          open
          passiveModal
          size="md"
          modalHeading="Objeto del contrato"
          onRequestClose={() => setObjectModal(null)}
        >
          <div className="experience-list-object-modal">
            <p className="experience-list-object-modal-meta">
              <strong>{objectModal.contract}</strong>
              {objectModal.entity ? ` · ${objectModal.entity}` : ''}
            </p>
            <p className="experience-list-object-modal-text">{objectModal.objectText}</p>
          </div>
        </Modal>
      )}
      {codesModal && (
        <Modal
          open
          passiveModal
          size="sm"
          modalHeading="Códigos UNSPSC del contrato"
          onRequestClose={() => setCodesModal(null)}
          className="experience-list-unspsc-modal"
        >
          <div className="experience-list-unspsc-modal-body">
            <p className="experience-list-unspsc-modal-meta">
              <strong>{codesModal.contract}</strong>
              {' · '}
              {codesModal.entity}
            </p>
            <p className="experience-list-unspsc-modal-count">
              {codesModal.codes.length}{' '}
              {codesModal.codes.length === 1 ? 'código' : 'códigos'} extraídos del RUP
            </p>
            <div className="experience-list-unspsc-modal-codes">
              {codesModal.codes.map((code) => (
                <Tag key={code} type="gray" size="sm">
                  {code}
                </Tag>
              ))}
            </div>
          </div>
        </Modal>
      )}
      {visibleCount > 0 && (
      <div className="experience-list-table-container">
        <DataTable rows={rows} headers={headers} isSortable size="md" useZebraStyles>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {headers.map((header) => (
                    <TableHeader {...getHeaderProps({ header })} key={header.key}>
                      {header.header}
                    </TableHeader>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow {...getRowProps({ row })} key={row.id}>
                    {row.cells.map((cell) => (
                      <TableCell key={cell.id}>{cell.value}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DataTable>
      </div>
      )}
    </div>
  )
}

export default ExperienceList

function SpecificExperienceCell({
  hasObject,
  filename,
  uploading,
  onUpload,
}: {
  hasObject: boolean
  filename: string | null
  uploading: boolean
  onUpload: () => void
}) {
  if (hasObject) {
    return (
      <div className="experience-list-specific experience-list-specific--filled">
        {filename && (
          <span className="experience-list-specific-file">
            <CheckmarkFilled size={14} />
            {filename}
          </span>
        )}
        <button
          type="button"
          className="experience-list-specific-replace"
          disabled={uploading}
          onClick={onUpload}
        >
          <Renew size={14} />
          {uploading ? 'Cargando…' : 'Reemplazar'}
        </button>
      </div>
    )
  }

  return (
    <div className="experience-list-specific">
      {filename && (
        <span className="experience-list-specific-file">
          {filename}
        </span>
      )}
      <button
        type="button"
        className="experience-list-specific-upload"
        disabled={uploading}
        aria-label="Cargar certificado o acta de finalización en PDF"
        title="PDF del certificado o acta de finalización"
        onClick={onUpload}
      >
        <Upload size={16} />
        {uploading ? 'Cargando…' : 'Cargar acta'}
      </button>
    </div>
  )
}
