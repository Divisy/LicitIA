import React from 'react'
import { Tender } from '../api/client'
import './TenderTable.css'

interface TenderTableProps {
  tenders: Tender[]
}

const TenderTable: React.FC<TenderTableProps> = ({ tenders }) => {
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('es-CO')
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
  
  const getEstadoBadgeClass = (estado: string): string => {
    const estadoLower = estado.toLowerCase()
    if (estadoLower === 'publicado' || estadoLower === 'abierto' || estadoLower === 'aprobado') {
      return 'estado-abierto'
    } else if (estadoLower === 'cerrado' || estadoLower === 'cancelado' || estadoLower === 'seleccionado') {
      return 'estado-cerrado'
    } else if (estadoLower === 'borrador' || estadoLower === 'en aprobación') {
      return 'estado-pendiente'
    } else {
      return 'estado-unknown'
    }
  }
  
  if (tenders.length === 0) {
    return (
      <div className="tender-table-empty">
        <p>No se encontraron licitaciones con los filtros seleccionados.</p>
      </div>
    )
  }
  
  return (
    <div className="tender-table-container">
      <table className="tender-table">
        <thead>
          <tr>
            <th>Fecha Publicación</th>
            <th>Fecha Presentación Ofertas</th>
            <th>Entidad</th>
            <th>Departamento</th>
            <th>Monto</th>
            <th>Estado</th>
            <th>Match Experiencia</th>
            <th>Enlace</th>
          </tr>
        </thead>
        <tbody>
          {tenders.map((tender) => (
            <tr key={tender.id}>
              <td>{formatDate(tender.publication_date)}</td>
              <td>{formatDate(tender.closing_date)}</td>
              <td className="entity-cell">
                <div className="entity-name">{tender.entity_name}</div>
                <div className="object-preview">
                  {tender.object_text.substring(0, 100)}
                  {tender.object_text.length > 100 ? '...' : ''}
                </div>
              </td>
              <td>{tender.department || 'N/A'}</td>
              <td className="amount-cell">{formatCurrency(tender.amount)}</td>
              <td>
                {tender.state ? (
                  <span className={`estado-badge ${getEstadoBadgeClass(tender.state)}`}>
                    {tender.state}
                  </span>
                ) : (
                  <span className="estado-badge estado-unknown">N/A</span>
                )}
              </td>
              <td>
                {tender.experience_match_score !== null && tender.experience_match_score !== undefined ? (
                  <span className={`match-badge ${tender.experience_match_score >= 0.6 ? 'high-match' : tender.experience_match_score >= 0.4 ? 'medium-match' : 'low-match'}`}>
                    {(tender.experience_match_score * 100).toFixed(0) + '%'}
                  </span>
                ) : (
                  <span className="match-badge no-match">-</span>
                )}
              </td>
              <td>
                <a
                  href={tender.process_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="process-link"
                >
                  Ver proceso
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default TenderTable

