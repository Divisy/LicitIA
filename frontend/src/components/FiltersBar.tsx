import React from 'react'
import {
  TextInput,
  DatePicker,
  DatePickerInput,
  Checkbox,
  Button,
} from '@carbon/react'
import {
  Search,
  Grid,
  Edit,
  Rule,
  Construction,
} from '@carbon/icons-react'
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

type ContractKindOption = {
  value: ContractKindFilter
  label: string
  shortLabel: string
  icon: React.ComponentType<{ size?: number; className?: string }>
}

const CONTRACT_KIND_OPTIONS: ContractKindOption[] = [
  { value: '', label: 'Todas', shortLabel: 'Todas', icon: Grid },
  {
    value: 'estudios_disenos',
    label: 'Estudios y diseños',
    shortLabel: 'Estudios',
    icon: Edit,
  },
  {
    value: 'interventoria',
    label: 'Interventoría',
    shortLabel: 'Interventoría',
    icon: Rule,
  },
  {
    value: 'ejecucion_obra',
    label: 'Ejecución de obra',
    shortLabel: 'Obra',
    icon: Construction,
  },
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

  const handleContractKindSelect = (value: ContractKindFilter) => {
    onContractKindChange(value)
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
        <section className="filters-bar-kind" aria-labelledby="filters-bar-kind-title">
          <div className="filters-bar-kind__header">
            <h2 id="filters-bar-kind-title" className="filters-bar-kind__title">
              Tipo de contrato
            </h2>
            <p className="filters-bar-kind__hint">
              Elige una categoría para ver solo esas licitaciones
            </p>
          </div>

          <div
            className="filters-bar-kind__options"
            role="radiogroup"
            aria-label="Tipo de contrato"
          >
            {CONTRACT_KIND_OPTIONS.map((option) => {
              const Icon = option.icon
              const isSelected = contractKind === option.value
              const optionClass =
                option.value === ''
                  ? 'all'
                  : option.value.replace('_', '-')

              return (
                <button
                  key={option.value || 'all'}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  aria-label={option.label}
                  className={[
                    'filters-bar-kind__option',
                    `filters-bar-kind__option--${optionClass}`,
                    isSelected ? 'filters-bar-kind__option--selected' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onClick={() => handleContractKindSelect(option.value)}
                >
                  <span className="filters-bar-kind__option-icon" aria-hidden="true">
                    <Icon size={20} />
                  </span>
                  <span className="filters-bar-kind__option-text">
                    <span className="filters-bar-kind__option-label filters-bar-kind__option-label--full">
                      {option.label}
                    </span>
                    <span className="filters-bar-kind__option-label filters-bar-kind__option-label--short">
                      {option.shortLabel}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        <section className="filters-bar-advanced" aria-label="Filtros adicionales">
          <div className="filters-bar-row">
            <div className="filters-bar-fields">
              <div className="filters-bar-field filters-bar-field--date">
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

              <div className="filters-bar-field filters-bar-field--date">
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

              <div className="filters-bar-field filters-bar-field--location">
                <TextInput
                  id="department"
                  labelText="Ubicación"
                  placeholder="Departamento o municipio"
                  value={department}
                  onChange={(e) => onDepartmentChange(e.target.value)}
                  size="sm"
                />
              </div>

              <div className="filters-bar-field filters-bar-field--company">
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
                size="md"
                renderIcon={Search}
                className="filters-bar-submit"
              >
                Buscar
              </Button>
            </div>
          </div>
        </section>

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
