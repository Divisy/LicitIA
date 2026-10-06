import React from 'react'
import {
  TextInput,
  DatePicker,
  DatePickerInput,
  Button,
} from '@carbon/react'
import {
  Search,
  Grid,
  Edit,
  Rule,
  Construction,
  Layers,
} from '@carbon/icons-react'
import { ContractKindFilter } from '../api/client'
import { dateFromPickerChange } from '../utils/filterDates'
import './FiltersBar.scss'

interface FiltersBarProps {
  dateFrom: string
  dateTo: string
  department: string
  entity: string
  contractKind: ContractKindFilter
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onDepartmentChange: (value: string) => void
  onEntityChange: (value: string) => void
  onContractKindChange: (value: ContractKindFilter) => void
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
    value: 'estudios_disenos_y_obra',
    label: 'Estudios, diseños y obra',
    shortLabel: 'E+D+Obra',
    icon: Layers,
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
  entity,
  contractKind,
  onDateFromChange,
  onDateToChange,
  onDepartmentChange,
  onEntityChange,
  onContractKindChange,
  onSubmit,
}) => {
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
                  : option.value.replace(/_/g, '-')

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
                  dateFormat="d/m/Y"
                  allowInput
                  appendTo={typeof document !== 'undefined' ? document.body : undefined}
                  value={dateFrom || undefined}
                  onChange={(dates: Date[], typedValue: string) => {
                    onDateFromChange(dateFromPickerChange(dates, typedValue))
                  }}
                >
                  <DatePickerInput
                    id="date-from"
                    placeholder="dd/mm/aaaa"
                    labelText="Cierre desde"
                    size="md"
                  />
                </DatePicker>
              </div>

              <div className="filters-bar-field filters-bar-field--date">
                <DatePicker
                  datePickerType="single"
                  dateFormat="d/m/Y"
                  allowInput
                  appendTo={typeof document !== 'undefined' ? document.body : undefined}
                  value={dateTo || undefined}
                  onChange={(dates: Date[], typedValue: string) => {
                    onDateToChange(dateFromPickerChange(dates, typedValue))
                  }}
                >
                  <DatePickerInput
                    id="date-to"
                    placeholder="dd/mm/aaaa"
                    labelText="Cierre hasta"
                    size="md"
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

              <div className="filters-bar-field filters-bar-field--entity">
                <TextInput
                  id="entity"
                  labelText="Entidad contratante"
                  placeholder="INVIAS, municipio, IDU…"
                  value={entity}
                  onChange={(e) => onEntityChange(e.target.value)}
                  size="sm"
                />
              </div>
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
      </form>
    </div>
  )
}

export default FiltersBar
