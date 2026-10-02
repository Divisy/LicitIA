import React, { useRef, useState } from 'react'
import {
  Tag,
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
} from '@carbon/icons-react'
import {
  CompanyExperience,
  formatApiError,
  uploadSpecificExperienceEvidence,
} from '../api/client'
import {
  experienceContractKindLabel,
  experienceContractKindTag,
} from '../utils/companySectors'
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

const ExperienceList: React.FC<ExperienceListProps> = ({
  experiences,
  companyName,
  onDelete,
  onUpdated,
}) => {
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [codesModal, setCodesModal] = useState<UnspscModalState | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const showKindColumn = experiences.some(
    (experience) =>
      Boolean(experience.contract_kind) && experience.contract_kind !== 'desconocido'
  )
  const contractCount = experiences.length

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
    { key: 'contractor', header: 'Contratista' },
    ...(showKindColumn ? [{ key: 'kind', header: 'Tipo de contrato' }] : []),
    { key: 'specific', header: 'Experiencia específica' },
    { key: 'entity', header: 'Entidad contratante' },
    { key: 'contract', header: 'Contrato' },
    { key: 'date', header: 'Fecha finalización' },
    { key: 'amount', header: 'Valor' },
    { key: 'unspsc', header: 'UNSPSC' },
  ]

  const rows = experiences.map((experience, index) => {
    const kind = experience.contract_kind
    const kindLabel = experienceContractKindLabel(kind, experience.contract_kind_label)
    const unspscCodes = (experience.unspsc_codes || []).filter(Boolean)
    const specificText = (experience.specific_experience || '').trim()
    const uploading = uploadingId === experience.id
    const contractor = (experience.contractor_name || '').trim()

    return {
      id: experience.id,
      number: <span className="experience-list-number">{index + 1}</span>,
      contractor: (
        <div className="experience-list-contractor">{contractor || '—'}</div>
      ),
      ...(showKindColumn
        ? {
            kind: (
              <div className="experience-list-service">
                {getExperienceIcon(kind)}
                <Tag type={experienceContractKindTag(kind)} size="sm">
                  {kindLabel}
                </Tag>
              </div>
            ),
          }
        : {}),
      specific: (
        <div className="experience-list-specific">
          {specificText ? (
            <>
              <p className="experience-list-specific-text">{specificText}</p>
              {experience.specific_evidence_filename && (
                <span className="experience-list-specific-file">
                  <CheckmarkFilled size={14} />
                  {experience.specific_evidence_filename}
                </span>
              )}
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Upload}
                disabled={uploading}
                onClick={() => openEvidencePicker(experience.id)}
              >
                {uploading ? 'Cargando…' : 'Reemplazar PDF'}
              </Button>
            </>
          ) : (
            <>
              <p className="experience-list-specific-missing">
                El RUP no trae el objeto de este contrato.
              </p>
              {experience.specific_evidence_filename && (
                <span className="experience-list-specific-file">
                  Cargado: {experience.specific_evidence_filename}. No se leyó el objeto.
                </span>
              )}
              <Button
                kind="tertiary"
                size="sm"
                renderIcon={Upload}
                disabled={uploading}
                onClick={() => openEvidencePicker(experience.id)}
              >
                {uploading
                  ? 'Cargando…'
                  : experience.specific_evidence_filename
                    ? 'Reemplazar PDF'
                    : 'Cargar certificado o acta de finalización'}
              </Button>
            </>
          )}
        </div>
      ),
      entity: experience.contracting_entity || 'N/A',
      contract: experience.contract_number || 'N/A',
      date: formatDate(experience.completion_date),
      amount: experience.amount ? (
        <span className="experience-list-amount">{formatCurrency(experience.amount)}</span>
      ) : (
        'N/A'
      ),
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
      <p className="experience-list-count">
        {contractCount} {contractCount === 1 ? 'contrato' : 'contratos'} en la experiencia
      </p>
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
    </div>
  )
}

export default ExperienceList
