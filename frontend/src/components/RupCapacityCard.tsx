import React from 'react'
import { Tag } from '@carbon/react'
import { RupCapacity } from '../api/client'
import './RupCapacityCard.scss'

interface RupCapacityCardProps {
  capacity: RupCapacity | null
}

type Metric = {
  id: string
  label: string
  abbr?: string
  value: string
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
  const financial: Metric[] = [
    { id: 'il', label: 'Índice de liquidez', abbr: 'IL', value: formatRatio(capacity.liquidez) },
    {
      id: 'ie',
      label: 'Índice de endeudamiento',
      abbr: 'IE',
      value: formatRatio(capacity.endeudamiento),
    },
    {
      id: 'rci',
      label: 'Cobertura de intereses',
      abbr: 'RCI',
      value: formatRatio(capacity.cobertura_intereses),
    },
    { id: 'ct', label: 'Capital de trabajo', value: formatMoney(capacity.capital_trabajo) },
  ]
  const organizational: Metric[] = [
    {
      id: 'rp',
      label: 'Rentabilidad del patrimonio',
      abbr: 'RP',
      value: formatRatio(capacity.rentabilidad_patrimonio),
    },
    {
      id: 'ra',
      label: 'Rentabilidad del activo',
      abbr: 'RA',
      value: formatRatio(capacity.rentabilidad_activo),
    },
    { id: 'size', label: 'Tamaño de empresa', value: sizeLabel(size) },
  ]

  const hasAny = [...financial, ...organizational].some((item) => item.value !== '—')
  if (!hasAny) {
    return (
      <p className="rup-capacity-card-empty">
        No se leyeron indicadores financieros u organizacionales de este RUP.
        Vuelve a cargar el PDF de la cámara si el certificado es seleccionable.
      </p>
    )
  }

  return (
    <div className="rup-capacity-card">
      <MetricGroup
        title="Capacidad financiera"
        badge={capacity.cut_year ? `Corte ${capacity.cut_year}` : undefined}
        metrics={financial}
      />
      <MetricGroup title="Capacidad organizacional" metrics={organizational} />
    </div>
  )
}

function MetricGroup({
  title,
  badge,
  metrics,
}: {
  title: string
  badge?: string
  metrics: Metric[]
}) {
  return (
    <section className="rup-capacity-group">
      <div className="rup-capacity-group-head">
        <h3 className="rup-capacity-group-title">{title}</h3>
        {badge && (
          <Tag type="gray" size="sm">
            {badge}
          </Tag>
        )}
      </div>
      <div className="rup-capacity-metrics">
        {metrics.map((metric) => (
          <article key={metric.id} className="rup-capacity-metric">
            <p className="rup-capacity-metric-label">
              {metric.label}
              {metric.abbr && <span className="rup-capacity-metric-abbr">{metric.abbr}</span>}
            </p>
            <p className="rup-capacity-metric-value">{metric.value}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

export default RupCapacityCard
