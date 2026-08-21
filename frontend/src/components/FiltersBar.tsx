import React from 'react'
import { 
  TextInput, 
  DatePicker, 
  DatePickerInput,
  Checkbox,
  Button,
  Select,
  SelectItem,
} from '@carbon/react'
import { Search } from '@carbon/icons-react'
import { ContractKindFilter } from '../api/client'
import './FiltersBar.scss'

interface FiltersBarProps {
  dateFrom: string
  dateTo: string
  department: string
  companyName: string
  contractKind: ContractKindFilter
  matchExperience: boolean
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onDepartmentChange: (value: string) => void
  onCompanyNameChange: (value: string) => void
  onContractKindChange: (value: ContractKindFilter) => void
  onMatchExperienceChange: (value: boolean) => void
  onSubmit: () => void
}

const CONTRACT_KIND_OPTIONS: { value: ContractKindFilter; label: string }[] = [
  { value: '', label: 'Todas las categorías' },
  { value: 'estudios_disenos', label: 'Estudios y diseños' },
  { value: 'interventoria', label: 'Interventoría' },
  { value: 'ejecucion_obra', label: 'Ejecución de obra' },
]

const FiltersBar: React.FC<FiltersBarProps> = ({
  dateFrom,
  dateTo,
  department,
  companyName,
  contractKind,
  matchExperience,
  onDateFromChange,
  onDateToChange,
  onDepartmentChange,
  onCompanyNameChange,
  onContractKindChange,
  onMatchExperienceChange,
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
            <div className="filters-bar-field filters-bar-field--category">
              <Select
                id="contract-kind"
                labelText="Tipo de contrato"
                size="sm"
                value={contractKind}
                onChange={(event) =>
                  onContractKindChange(event.target.value as ContractKindFilter)
                }
              >
                {CONTRACT_KIND_OPTIONS.map((option) => (
                  <SelectItem
                    key={option.value || 'all'}
                    value={option.value}
                    text={option.label}
                  />
                ))}
              </Select>
            </div>

            <div className="filters-bar-field">
              <DatePicker
                datePickerType="single"
                value={dateFrom ? [new Date(dateFrom)] : []}
              >
                <DatePickerInput
                  id="date-from"
                  placeholder="dd/mm/aaaa"
                  labelText="Desde"
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
                  labelText="Hasta"
                  size="sm"
                  value={dateTo}
                  onChange={handleDateToChange}
                />
              </DatePicker>
            </div>
            
            <div className="filters-bar-field">
              <TextInput
                id="department"
                labelText="Ubicación"
                placeholder="Departamento o municipio"
                value={department}
                onChange={(e) => onDepartmentChange(e.target.value)}
                size="sm"
              />
            </div>
            
            <div className="filters-bar-field">
              <TextInput
                id="company-name"
                labelText="Empresa"
                placeholder="Nombre de empresa"
                value={companyName}
                onChange={(e) => onCompanyNameChange(e.target.value)}
                size="sm"
              />
            </div>
          </div>

          <div className="filters-bar-checkboxes">
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
