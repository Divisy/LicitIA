import React from 'react'
import { 
  Grid, 
  Column, 
  TextInput, 
  DatePicker, 
  DatePickerInput,
  Checkbox,
  Button,
  Tile,
  FormGroup
} from '@carbon/react'
import { Search, Filter } from '@carbon/icons-react'
import './FiltersBar.scss'

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
  const handleDateFromChange = (event: React.SyntheticEvent<HTMLInputElement>) => {
    const value = (event.target as HTMLInputElement).value
    onDateFromChange(value)
  }

  const handleDateToChange = (event: React.SyntheticEvent<HTMLInputElement>) => {
    const value = (event.target as HTMLInputElement).value
    onDateToChange(value)
  }

  return (
    <div className="filters-bar-compact">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
        className="filters-bar-form"
      >
        <div className="filters-bar-row">
          <div className="filters-bar-fields">
            <div className="filters-bar-field">
              <DatePicker
                datePickerType="single"
                value={dateFrom ? [new Date(dateFrom)] : []}
              >
                <DatePickerInput
                  id="date-from"
                  placeholder="dd/mm/aaaa"
                  labelText=""
                  size="sm"
                  value={dateFrom}
                  onChange={handleDateFromChange}
                />
              </DatePicker>
            </div>
            
            <div className="filters-bar-field">
              <DatePicker
                datePickerType="single"
                value={dateTo ? [new Date(dateTo)] : []}
              >
                <DatePickerInput
                  id="date-to"
                  placeholder="dd/mm/aaaa"
                  labelText=""
                  size="sm"
                  value={dateTo}
                  onChange={handleDateToChange}
                />
              </DatePicker>
            </div>
            
            <div className="filters-bar-field">
              <TextInput
                id="department"
                placeholder="Departamento"
                value={department}
                onChange={(e) => onDepartmentChange(e.target.value)}
                size="sm"
                hideLabel
              />
            </div>
            
            <div className="filters-bar-field">
              <TextInput
                id="company-name"
                placeholder="Nombre de empresa"
                value={companyName}
                onChange={(e) => onCompanyNameChange(e.target.value)}
                size="sm"
                hideLabel
              />
            </div>
          </div>

          <div className="filters-bar-checkboxes">
            <Checkbox
              id="only-interventoria"
              labelText="Solo interventoría/supervisión"
              checked={onlyInterventoria}
              onChange={(_, { checked }) => onOnlyInterventoriaChange(checked)}
            />
            <Checkbox
              id="match-experience"
              labelText="Solo coincidencias con experiencia"
              checked={matchExperience}
              onChange={(_, { checked }) => onMatchExperienceChange(checked)}
            />
          </div>

          <div className="filters-bar-actions">
            <Button
              type="submit"
              size="sm"
              renderIcon={Search}
              className="filters-bar-submit"
            >
              Buscar
            </Button>
          </div>
        </div>
        
        {matchExperience && !companyName && (
          <div className="filters-bar-hint filters-bar-hint--warning">
            Ingresa el nombre de la empresa para ver coincidencias
          </div>
        )}
      </form>
    </div>
  )
}

export default FiltersBar
