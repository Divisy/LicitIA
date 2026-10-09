import React, { useEffect, useMemo, useState } from 'react'
import { DataTable, Table, TableHead, TableRow, TableHeader, TableBody, TableCell, Tag, Link, Tile, IconButton, Modal } from '@carbon/react'
import { ExperienceFitStatus, Tender } from '../api/client'
import { Launch, Star, StarFilled, ArrowUp, ArrowDown, ArrowsVertical } from '@carbon/icons-react'
import {
  DEFAULT_TENDER_SORT_DIRECTION,
  DEFAULT_TENDER_SORT_KEY,
  getInitialSortDirectionForColumn,
  isSortableTenderColumn,
  sortTenders,
  type SortDirection,
  type TenderSortKey,
} from '../utils/tenderTableSort'
import './TenderTable.scss'

interface TenderTableProps {
  tenders: Tender[]
  onSelectTender?: (tender: Tender) => void
  showFavoriteColumn?: boolean
  isFavorite?: (tenderId: string) => boolean
  onToggleFavorite?: (tender: Tender) => void
}

const TenderTable: React.FC<TenderTableProps> = ({
  tenders,
  onSelectTender,
  showFavoriteColumn = false,
  isFavorite,
  onToggleFavorite,
}) => {
  const [sortKey, setSortKey] = useState<TenderSortKey>(DEFAULT_TENDER_SORT_KEY)
  const [sortDirection, setSortDirection] = useState<SortDirection>(DEFAULT_TENDER_SORT_DIRECTION)
  const [matchTender, setMatchTender] = useState<Tender | null>(null)

  useEffect(() => {
    setSortKey(DEFAULT_TENDER_SORT_KEY)
    setSortDirection(DEFAULT_TENDER_SORT_DIRECTION)
  }, [tenders])

  const handleSort = (key: string) => {
    if (!isSortableTenderColumn(key)) return
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection(getInitialSortDirectionForColumn(key))
  }

  const sortedTenders = useMemo(
    () => sortTenders(tenders, sortKey, sortDirection),
    [tenders, sortKey, sortDirection]
  )

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('es-CO', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
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
  
  const getEstadoTagKind = (estado: string): 'green' | 'red' | 'yellow' | 'gray' => {
    const estadoLower = estado.toLowerCase()
    if (estadoLower === 'publicado' || estadoLower === 'abierto' || estadoLower === 'aprobado') {
      return 'green'
    } else if (estadoLower === 'cerrado' || estadoLower === 'cancelado' || estadoLower === 'seleccionado') {
      return 'red'
    } else if (estadoLower === 'borrador' || estadoLower === 'en aprobación') {
      return 'yellow'
    } else {
      return 'gray'
    }
  }
  
  const headers = useMemo(() => {
    const base = [
      { key: 'publication_date', header: 'Fecha Publicación' },
      { key: 'closing_date', header: 'Fecha Presentación Ofertas' },
      { key: 'entity', header: 'Entidad' },
      { key: 'department', header: 'Departamento' },
      { key: 'amount', header: 'Monto' },
      { key: 'experience_fit', header: 'Experiencia' },
      { key: 'state', header: 'Estado' },
      { key: 'link', header: 'Enlace' },
    ]
    if (showFavoriteColumn) {
      return [{ key: 'favorite', header: 'Favorita' }, ...base]
    }
    return base
  }, [showFavoriteColumn])
  
  const rows = useMemo(() => {
    return sortedTenders.map((tender) => {
      const favoriteActive = isFavorite?.(tender.id) ?? false
      return {
      id: tender.id,
      ...(showFavoriteColumn
        ? {
            favorite: (
              <IconButton
                kind="ghost"
                size="sm"
                label={favoriteActive ? 'Quitar de favoritas' : 'Guardar en favoritas'}
                className={`tender-table-favorite-btn${
                  favoriteActive ? ' tender-table-favorite-btn--active' : ''
                }`}
                onClick={(event) => {
                  event.stopPropagation()
                  onToggleFavorite?.(tender)
                }}
              >
                {favoriteActive ? <StarFilled size={18} /> : <Star size={18} />}
              </IconButton>
            ),
          }
        : {}),
      publication_date: formatDate(tender.publication_date),
      closing_date: formatDate(tender.closing_date),
      entity: (
        <div className="tender-table-entity">
          <div className="tender-table-entity-name">{tender.entity_name}</div>
          <div className="tender-table-entity-object">
            {tender.object_text || 'Sin descripción disponible'}
          </div>
        </div>
      ),
      department: tender.department || 'N/A',
      amount: (
        <span className="tender-table-amount">{formatCurrency(tender.amount)}</span>
      ),
      experience_fit: (
        <ExperienceFitTag
          fit={tender.experience_fit}
          onShowMatch={
            tender.experience_fit?.status === 'puede_aplicar'
              ? () => setMatchTender(tender)
              : undefined
          }
        />
      ),
      state: tender.state ? (
        <Tag type={getEstadoTagKind(tender.state)} size="sm">
          {tender.state}
        </Tag>
      ) : (
        <Tag type="gray" size="sm">N/A</Tag>
      ),
      link: (
        <Link
          href={tender.process_url}
          target="_blank"
          rel="noopener noreferrer"
          className="tender-table-link"
          renderIcon={Launch}
        >
          Ver proceso
        </Link>
      ),
    }
    })
  }, [sortedTenders, showFavoriteColumn, isFavorite, onToggleFavorite])
  
  if (tenders.length === 0) {
    return (
      <Tile className="tender-table-empty">
        <p className="tender-table-empty-text">
          No se encontraron licitaciones con los filtros seleccionados.
        </p>
        <p className="tender-table-empty-hint">
          Intenta ajustar los filtros o verifica que hay licitaciones disponibles.
        </p>
      </Tile>
    )
  }

  const renderSortIcon = (headerKey: string) => {
    if (!isSortableTenderColumn(headerKey)) return null
    if (sortKey !== headerKey) {
      return <ArrowsVertical size={16} className="tender-table-header-icon" aria-hidden="true" />
    }
    return sortDirection === 'asc' ? (
      <ArrowUp size={16} className="tender-table-header-icon tender-table-header-icon--active" aria-hidden="true" />
    ) : (
      <ArrowDown size={16} className="tender-table-header-icon tender-table-header-icon--active" aria-hidden="true" />
    )
  }
  
  return (
    <div className="tender-table-container">
      {onSelectTender && (
        <p className="tender-table-hint">
          Haz clic en una fila para ver el detalle y los documentos de la licitación.
        </p>
      )}
      <DataTable
        rows={rows}
        headers={headers}
        size="lg"
        useZebraStyles
      >
        {({ rows, headers, getTableProps, getRowProps }) => (
          <Table {...getTableProps()}>
            <TableHead>
              <TableRow>
                {headers.map((header) => {
                  const sortable = isSortableTenderColumn(header.key)
                  const isActive = sortKey === header.key
                  return (
                    <TableHeader
                      key={header.key}
                      className={[
                        sortable ? 'tender-table-header--sortable' : '',
                        isActive ? 'tender-table-header--active' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      aria-sort={
                        sortable
                          ? isActive
                            ? sortDirection === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                          : undefined
                      }
                    >
                      {sortable ? (
                        <button
                          type="button"
                          className="tender-table-header-button"
                          onClick={() => handleSort(header.key)}
                        >
                          <span className="tender-table-header-label">{header.header}</span>
                          {renderSortIcon(header.key)}
                        </button>
                      ) : (
                        <span className="tender-table-header-label">{header.header}</span>
                      )}
                    </TableHeader>
                  )
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const tender = sortedTenders.find((item) => item.id === row.id)
                return (
                <TableRow
                  {...getRowProps({ row })}
                  key={row.id}
                  className={onSelectTender ? 'tender-table-row--clickable' : undefined}
                  onClick={() => tender && onSelectTender?.(tender)}
                >
                  {row.cells.map((cell) => (
                    <TableCell
                      key={cell.id}
                      onClick={
                        cell.info.header === 'link' ||
                        cell.info.header === 'favorite' ||
                        cell.info.header === 'experience_fit'
                          ? (event) => event.stopPropagation()
                          : undefined
                      }
                    >
                      {cell.value}
                    </TableCell>
                  ))}
                </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </DataTable>
      {matchTender?.experience_fit && (
        <MatchContractsModal tender={matchTender} onClose={() => setMatchTender(null)} />
      )}
    </div>
  )
}

const FIT_LABEL: Record<ExperienceFitStatus, string> = {
  puede_aplicar: 'Puede aplicar',
  no_aplica: 'No aplica',
  no_se_puede_afirmar: 'No se puede afirmar',
}

function ExperienceFitTag({
  fit,
  onShowMatch,
}: {
  fit: Tender['experience_fit']
  onShowMatch?: () => void
}) {
  if (!fit) return <span>—</span>
  const type =
    fit.status === 'puede_aplicar' ? 'green' : fit.status === 'no_aplica' ? 'red' : 'gray'
  const tag = (
    <Tag type={type} size="sm">
      {FIT_LABEL[fit.status]}
    </Tag>
  )
  if (!onShowMatch) {
    return <span title={fit.reason}>{tag}</span>
  }
  return (
    <button
      type="button"
      className="tender-table-fit-button"
      title="Ver el contrato de la experiencia con el que hay match"
      onClick={onShowMatch}
    >
      {tag}
    </button>
  )
}

function MatchContractsModal({ tender, onClose }: { tender: Tender; onClose: () => void }) {
  const contracts = (tender.experience_fit?.contracts || []).filter((row) => row.in_general_sum)
  return (
    <Modal
      open
      passiveModal
      size="md"
      modalHeading="Contratos con match"
      onRequestClose={onClose}
    >
      <p className="tender-table-match-intro">
        {tender.entity_name}. El objeto de la licitación coincide con estos contratos de la experiencia.
      </p>
      <ul className="tender-table-match-list">
        {contracts.map((contract) => (
          <li key={contract.experience_id} className="tender-table-match-item">
            <p className="tender-table-match-title">
              {contract.contract_number || 'Sin número'}
            </p>
            <p className="tender-table-match-meta">
              {[
                contract.contracting_entity,
                contract.amount_smmlv != null
                  ? `${new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(contract.amount_smmlv)} SMMLV`
                  : '',
              ]
                .filter(Boolean)
                .join(' · ') || 'Sin entidad'}
            </p>
            {contract.object_text && (
              <p className="tender-table-match-object">{contract.object_text}</p>
            )}
          </li>
        ))}
      </ul>
    </Modal>
  )
}

export default TenderTable
