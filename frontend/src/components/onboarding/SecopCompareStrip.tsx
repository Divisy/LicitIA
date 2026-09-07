import React from 'react'
import { ArrowRight, CheckmarkFilled, CloseFilled } from '@carbon/icons-react'
import './SecopCompareStrip.scss'

const SECOP_ITEMS = [
  'Listado genérico de todos los procesos',
  'Horas buscando y filtrando a mano',
  'Leer el pliego para entender requisitos',
]

const LICITIA_ITEMS = [
  'Radar filtrado por tu experiencia',
  'Match % en cada licitación relevante',
  'Requisitos clave ya extraídos del pliego',
]

const SecopCompareStrip: React.FC = () => {
  return (
    <div className="secop-compare" role="region" aria-label="Comparación SECOP y LicitIA">
      <div className="secop-compare__col secop-compare__col--secop">
        <span className="secop-compare__label">Hoy en SECOP</span>
        <ul className="secop-compare__list">
          {SECOP_ITEMS.map((item) => (
            <li key={item}>
              <CloseFilled size={16} className="secop-compare__icon secop-compare__icon--muted" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="secop-compare__bridge" aria-hidden="true">
        <span className="secop-compare__bridge-icon">
          <ArrowRight size={20} />
        </span>
      </div>

      <div className="secop-compare__col secop-compare__col--licitia">
        <span className="secop-compare__label secop-compare__label--highlight">Con LicitIA</span>
        <ul className="secop-compare__list">
          {LICITIA_ITEMS.map((item) => (
            <li key={item}>
              <CheckmarkFilled size={16} className="secop-compare__icon secop-compare__icon--positive" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default SecopCompareStrip
