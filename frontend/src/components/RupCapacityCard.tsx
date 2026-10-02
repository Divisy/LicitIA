import React from 'react'
import { RupCapacity } from '../api/client'
import './RupCapacityCard.scss'

interface RupCapacityCardProps {
  capacity: RupCapacity | null
  cutYear?: number | null
}

function formatRatio(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatMoney(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value)
}

function sizeLabel(raw: unknown): string {
  if (typeof raw !== 'string' || !raw.trim()) return '—'
  return raw.charAt(0).toUpperCase() + raw.slice(1)
}

const RupCapacityCard: React.FC<RupCapacityCardProps> = ({ capacity }) => {
  if (!capacity) return null

  const size = capacity.organizacional?.company_size
  const hasFinancial =
    capacity.liquidez != null ||
    capacity.endeudamiento != null ||
    capacity.cobertura_intereses != null ||
    capacity.capital_trabajo != null
  const hasOrganizational =
    capacity.rentabilidad_patrimonio != null ||
    capacity.rentabilidad_activo != null ||
    Boolean(size)

  if (!hasFinancial && !hasOrganizational) {
    return (
      <p className="rup-capacity-card-empty">
        No se leyeron indicadores financieros u organizacionales de este RUP.
        Vuelve a cargar el PDF de la cámara si el certificado es seleccionable.
      </p>
    )
  }

  const cut = capacity.cut_year ? ` · corte ${capacity.cut_year}` : ''

  return (
    <div className="rup-capacity-card">
      <section className="rup-capacity-card-group">
        <h3 className="rup-capacity-card-title">Capacidad financiera{cut}</h3>
        <dl className="rup-capacity-card-grid">
          <div>
            <dt>Índice de liquidez</dt>
            <dd>{formatRatio(capacity.liquidez)}</dd>
          </div>
          <div>
            <dt>Índice de endeudamiento</dt>
            <dd>{formatRatio(capacity.endeudamiento)}</dd>
          </div>
          <div>
            <dt>Cobertura de intereses</dt>
            <dd>{formatRatio(capacity.cobertura_intereses)}</dd>
          </div>
          <div>
            <dt>Capital de trabajo</dt>
            <dd>{formatMoney(capacity.capital_trabajo)}</dd>
          </div>
        </dl>
      </section>
      <section className="rup-capacity-card-group">
        <h3 className="rup-capacity-card-title">Capacidad organizacional</h3>
        <dl className="rup-capacity-card-grid">
          <div>
            <dt>Rentabilidad del patrimonio</dt>
            <dd>{formatRatio(capacity.rentabilidad_patrimonio)}</dd>
          </div>
          <div>
            <dt>Rentabilidad del activo</dt>
            <dd>{formatRatio(capacity.rentabilidad_activo)}</dd>
          </div>
          <div>
            <dt>Tamaño de empresa</dt>
            <dd>{sizeLabel(size)}</dd>
          </div>
        </dl>
      </section>
    </div>
  )
}

export default RupCapacityCard
