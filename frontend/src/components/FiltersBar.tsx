import React from 'react'
import './FiltersBar.css'

interface FiltersBarProps {
  dateFrom: string
  dateTo: string
  department: string
  companyName: string
  matchExperience: boolean
  onlyInterventoria: boolean
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onDepartmentChange: (value: string) => void
  onCompanyNameChange: (value: string) => void
  onMatchExperienceChange: (value: boolean) => void
  onOnlyInterventoriaChange: (value: boolean) => void
  onSubmit: () => void
}

const FiltersBar: React.FC<FiltersBarProps> = ({
  dateFrom,
  dateTo,
  department,
  companyName,
  matchExperience,
  onlyInterventoria,
  onDateFromChange,
  onDateToChange,
  onDepartmentChange,
  onCompanyNameChange,
  onMatchExperienceChange,
  onOnlyInterventoriaChange,
  onSubmit,
}) => {
  return (
    <div className="filters-bar">
      <h2>Filtros</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
      >
        <div className="filters-grid">
          <div className="filter-group">
            <label htmlFor="dateFrom">Fecha desde:</label>
            <input
              type="date"
              id="dateFrom"
              value={dateFrom}
              onChange={(e) => onDateFromChange(e.target.value)}
            />
          </div>
          
          <div className="filter-group">
            <label htmlFor="dateTo">Fecha hasta:</label>
            <input
              type="date"
              id="dateTo"
              value={dateTo}
              onChange={(e) => onDateToChange(e.target.value)}
            />
          </div>
          
          <div className="filter-group">
            <label htmlFor="department">Departamento:</label>
            <input
              type="text"
              id="department"
              placeholder="Ej: Cundinamarca"
              value={department}
              onChange={(e) => onDepartmentChange(e.target.value)}
            />
          </div>
          
          <div className="filter-group">
            <label htmlFor="companyName">Nombre de empresa:</label>
            <input
              type="text"
              id="companyName"
              placeholder="Ej: BEC"
              value={companyName}
              onChange={(e) => onCompanyNameChange(e.target.value)}
            />
          </div>
          
          <div className="filter-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={onlyInterventoria}
                onChange={(e) => onOnlyInterventoriaChange(e.target.checked)}
              />
              Solo interventoría/supervisión (reduce tiempo de análisis)
            </label>
            {onlyInterventoria && (
              <span className="checkbox-hint">
                (Filtra antes del matching con IA - más rápido)
              </span>
            )}
          </div>
          
          <div className="filter-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={matchExperience}
                onChange={(e) => onMatchExperienceChange(e.target.checked)}
              />
              Solo coincidencias con experiencia
            </label>
            {matchExperience && !companyName && (
              <span className="checkbox-hint">
                (Ingresa el nombre de la empresa arriba)
              </span>
            )}
          </div>
        </div>
        
        <button type="submit" className="submit-button">
          Buscar
        </button>
      </form>
    </div>
  )
}

export default FiltersBar

