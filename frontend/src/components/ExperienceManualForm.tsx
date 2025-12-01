import React, { useState } from 'react'
import {
  FormGroup,
  TextInput,
  NumberInput,
  DatePicker,
  DatePickerInput,
  Button,
  InlineNotification,
  Loading,
} from '@carbon/react'
import { Add, CheckmarkFilled } from '@carbon/icons-react'
import { createExperience, CompanyExperienceCreate } from '../api/client'
import './ExperienceManualForm.scss'

interface ExperienceManualFormProps {
  companyName: string
  onSuccess?: (count: number) => void
  onCancel?: () => void
}

const ExperienceManualForm: React.FC<ExperienceManualFormProps> = ({
  companyName,
  onSuccess,
  onCancel,
}) => {
  const [formData, setFormData] = useState<CompanyExperienceCreate>({
    company_name: companyName,
    project_description: '',
    contract_number: '',
    contracting_entity: '',
    completion_date: null,
    amount: null,
    category: '',
    engineering_area: '',
  })

  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [successCount, setSuccessCount] = useState(0)

  const handleInputChange = (field: keyof CompanyExperienceCreate, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setMessage(null)
  }

  const handleDateChange = (dates: Date[]) => {
    if (dates && dates.length > 0) {
      const date = dates[0]
      const dateString = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
      handleInputChange('completion_date', dateString)
    } else {
      handleInputChange('completion_date', null)
    }
  }

  const handleAmountChange = (e: any, data: { value: number | string }) => {
    const value = typeof data.value === 'string' ? data.value.replace(/[^\d]/g, '') : String(data.value || '')
    handleInputChange('amount', value ? parseFloat(value) : null)
  }

  const resetForm = () => {
    setFormData({
      company_name: companyName,
      project_description: '',
      contract_number: '',
      contracting_entity: '',
      completion_date: null,
      amount: null,
      category: '',
      engineering_area: '',
    })
    setMessage(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.project_description.trim()) {
      setMessage({ type: 'error', text: 'La descripción del proyecto es requerida' })
      return
    }

    setSubmitting(true)
    setMessage(null)

    try {
      const experienceData: CompanyExperienceCreate = {
        company_name: formData.company_name,
        project_description: formData.project_description.trim(),
        contract_number: formData.contract_number?.trim() || null,
        contracting_entity: formData.contracting_entity?.trim() || null,
        completion_date: formData.completion_date || null,
        amount: formData.amount || null,
        category: formData.category?.trim() || null,
        engineering_area: formData.engineering_area?.trim() || null,
      }

      await createExperience(experienceData)
      const newCount = successCount + 1
      setSuccessCount(newCount)
      setMessage({ type: 'success', text: `Experiencia agregada exitosamente (${newCount} total)` })
      resetForm()

      if (onSuccess) {
        onSuccess(newCount)
      }
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Error al crear la experiencia',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="experience-manual-form">
      <form onSubmit={handleSubmit} className="experience-manual-form__form">
        <FormGroup legendText="Información del Proyecto">
          <TextInput
            id="project-description"
            labelText="Descripción del Proyecto *"
            placeholder="Ej: Construcción de vía principal en Medellín"
            value={formData.project_description}
            onChange={(e) => handleInputChange('project_description', e.target.value)}
            required
            disabled={submitting}
            size="md"
            className="experience-manual-form__input"
          />
        </FormGroup>

        <div className="experience-manual-form__row">
          <FormGroup legendText="" className="experience-manual-form__group">
            <TextInput
              id="contracting-entity"
              labelText="Entidad Contratante"
              placeholder="Ej: Alcaldía de Medellín"
              value={formData.contracting_entity || ''}
              onChange={(e) => handleInputChange('contracting_entity', e.target.value)}
              disabled={submitting}
              size="md"
            />
          </FormGroup>

          <FormGroup legendText="" className="experience-manual-form__group">
            <TextInput
              id="contract-number"
              labelText="Número de Contrato"
              placeholder="Ej: CT-2024-001"
              value={formData.contract_number || ''}
              onChange={(e) => handleInputChange('contract_number', e.target.value)}
              disabled={submitting}
              size="md"
            />
          </FormGroup>
        </div>

        <div className="experience-manual-form__row">
          <FormGroup legendText="" className="experience-manual-form__group">
            <DatePicker
              datePickerType="single"
              onChange={handleDateChange}
              value={formData.completion_date ? new Date(formData.completion_date) : undefined}
            >
              <DatePickerInput
                id="completion-date"
                placeholder="dd/mm/aaaa"
                labelText="Fecha de Finalización"
                size="md"
                disabled={submitting}
              />
            </DatePicker>
          </FormGroup>

          <FormGroup legendText="" className="experience-manual-form__group">
            <NumberInput
              id="amount"
              label="Valor del Contrato (COP)"
              placeholder="Ej: 500000000"
              value={formData.amount || 0}
              onChange={handleAmountChange}
              disabled={submitting}
              size="md"
              className="experience-manual-form__amount"
            />
          </FormGroup>
        </div>

        <div className="experience-manual-form__row">
          <FormGroup legendText="" className="experience-manual-form__group">
            <TextInput
              id="category"
              labelText="Categoría"
              placeholder="Ej: Construcción"
              value={formData.category || ''}
              onChange={(e) => handleInputChange('category', e.target.value)}
              disabled={submitting}
              size="md"
            />
          </FormGroup>

          <FormGroup legendText="" className="experience-manual-form__group">
            <TextInput
              id="engineering-area"
              labelText="Área de Ingeniería"
              placeholder="Ej: Vial"
              value={formData.engineering_area || ''}
              onChange={(e) => handleInputChange('engineering_area', e.target.value)}
              disabled={submitting}
              size="md"
            />
          </FormGroup>
        </div>

        {message && (
          <InlineNotification
            kind={message.type === 'success' ? 'success' : 'error'}
            title={message.type === 'success' ? 'Éxito' : 'Error'}
            subtitle={message.text}
            lowContrast={false}
            className="experience-manual-form__message"
            onClose={() => setMessage(null)}
          />
        )}

        <div className="experience-manual-form__actions">
          {onCancel && (
            <Button
              type="button"
              kind="secondary"
              size="md"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancelar
            </Button>
          )}
          <Button
            type="submit"
            size="md"
            disabled={submitting || !formData.project_description.trim()}
            renderIcon={submitting ? undefined : Add}
            className="experience-manual-form__submit"
          >
            {submitting ? (
              <>
                <Loading small withOverlay={false} />
                Agregando...
              </>
            ) : (
              'Agregar Experiencia'
            )}
          </Button>
        </div>

        {successCount > 0 && (
          <div className="experience-manual-form__success-badge">
            <CheckmarkFilled size={16} />
            <span>{successCount} experiencia(s) agregada(s)</span>
          </div>
        )}
      </form>
    </div>
  )
}

export default ExperienceManualForm

