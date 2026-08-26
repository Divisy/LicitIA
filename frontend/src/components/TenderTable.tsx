import React, { useMemo } from 'react'
import { DataTable, Table, TableHead, TableRow, TableHeader, TableBody, TableCell, Tag, Link, Tile, IconButton } from '@carbon/react'
import { Tender } from '../api/client'
import { WatsonMachineLearning, Launch, Star, StarFilled } from '@carbon/icons-react'
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
  
  const getMatchTagKind = (score: number | null): 'green' | 'yellow' | 'red' | 'gray' => {
    if (score === null || score === undefined) return 'gray'
    if (score >= 0.6) return 'green'
    if (score >= 0.4) return 'yellow'
    return 'red'
  }
  
  const headers = useMemo(() => {
    const base = [
      { key: 'publication_date', header: 'Fecha Publicación' },
      { key: 'closing_date', header: 'Fecha Presentación Ofertas' },
      { key: 'entity', header: 'Entidad' },
      { key: 'department', header: 'Departamento' },
      { key: 'amount', header: 'Monto' },
      { key: 'state', header: 'Estado' },
      { key: 'match', header: 'Match Experiencia' },
      { key: 'link', header: 'Enlace' },
    ]
    if (showFavoriteColumn) {
      return [{ key: 'favorite', header: '' }, ...base]
    }
    return base
  }, [showFavoriteColumn])
  
  const rows = useMemo(() => {
    return tenders.map((tender) => {
      const favoriteActive = isFavorite?.(tender.id) ?? false
      return {
      id: tender.id,
      ...(showFavoriteColumn
        ? {
            favorite: (
              <IconButton
                kind="ghost"
                size="sm"
                label={favoriteActive ? 'Quitar de favoritas' : 'Agregar a favoritas'}
                onClick={(event) => {
                  event.stopPropagation()
                  onToggleFavorite?.(tender)
                }}
              >
                {favoriteActive ? <StarFilled /> : <Star />}
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
      state: tender.state ? (
        <Tag type={getEstadoTagKind(tender.state)} size="sm">
          {tender.state}
        </Tag>
      ) : (
        <Tag type="gray" size="sm">N/A</Tag>
      ),
      match: tender.experience_match_score !== null && tender.experience_match_score !== undefined ? (
        <Tag 
          type={getMatchTagKind(tender.experience_match_score)} 
          size="sm"
          className="tender-table-match-tag"
        >
          <WatsonMachineLearning size={12} className="tender-table-match-icon" />
          {Math.round(tender.experience_match_score * 100)}%
        </Tag>
      ) : (
        <Tag type="gray" size="sm">-</Tag>
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
  }, [tenders, showFavoriteColumn, isFavorite, onToggleFavorite])
  
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
        isSortable
        size="lg"
        useZebraStyles
      >
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
              {rows.map((row) => {
                const tender = tenders.find((item) => item.id === row.id)
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
                        cell.info.header === 'link' || cell.info.header === 'favorite'
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
    </div>
  )
}

export default TenderTable
