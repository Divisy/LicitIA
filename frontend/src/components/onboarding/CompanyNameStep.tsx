import React, { useState } from 'react'
import { TextInput, Button, InlineNotification } from '@carbon/react'
import { ArrowLeft, ArrowRight } from '@carbon/icons-react'
import './CompanyNameStep.scss'

interface CompanyNameStepProps {
  onNext: (companyName: string) => void
  onBack: () => void
  initialValue?: string
}

const CompanyNameStep: React.FC<CompanyNameStepProps> = ({
  onNext,
  onBack,
  initialValue = '',
}) => {
  const [companyName, setCompanyName] = useState(initialValue)
  const [error, setError] = useState('')
  const [invalid, setInvalid] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!companyName.trim()) {
      setError('Por favor ingresa el nombre de tu empresa')
      setInvalid(true)
      return
    }

    if (companyName.trim().length < 2) {
      setError('El nombre debe tener al menos 2 caracteres')
      setInvalid(true)
      return
    }

    setError('')
    setInvalid(false)
    onNext(companyName.trim())
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCompanyName(e.target.value)
    setError('')
    setInvalid(false)
  }

  return (
    <div className="onboarding-company-step">
      <div className="onboarding-company-header">
        <Button
          kind="ghost"
          size="sm"
          onClick={onBack}
          renderIcon={ArrowLeft}
          className="onboarding-company-back"
        >
          Atrás
        </Button>
      </div>

      <div className="onboarding-company-content">
        <h2 className="onboarding-company-title">
          ¿Cuál es el nombre de tu empresa?
        </h2>
        
        <p className="onboarding-company-description">
          Este nombre se usará para asociar tus experiencias y encontrar licitaciones relevantes
        </p>

        <form onSubmit={handleSubmit} className="onboarding-company-form">
          <div className="onboarding-company-input-wrapper">
            <TextInput
              id="company-name"
              labelText=""
              placeholder="Ej: Constructora ABC"
              value={companyName}
              onChange={handleChange}
              invalid={invalid}
              invalidText={error}
              size="lg"
              autoFocus
              className="onboarding-company-input"
            />
          </div>

          {error && !invalid && (
            <InlineNotification
              kind="error"
              title="Error"
              subtitle={error}
              lowContrast
              className="onboarding-company-error"
            />
          )}

          <div className="onboarding-company-actions">
            <Button
              type="submit"
              size="lg"
              className="onboarding-company-submit"
              renderIcon={ArrowRight}
            >
              Continuar
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CompanyNameStep
