import React, { useState } from 'react'
import { TextInput, Button, Select, SelectItem, InlineNotification } from '@carbon/react'
import { ArrowLeft, ArrowRight } from '@carbon/icons-react'
import { captureLead } from '../../api/client'
import './MarketingInfoStep.scss'

interface MarketingInfoStepProps {
  onNext: (data: MarketingData) => void
  onBack: () => void
  onSkip: () => void
  initialData?: Partial<MarketingData>
}

export interface MarketingData {
  companyName: string
  fullName?: string
  industry?: string
  companySize?: string
  role?: string
}

const MarketingInfoStep: React.FC<MarketingInfoStepProps> = ({
  onNext,
  onBack,
  onSkip,
  initialData = {},
}) => {
  const [companyName, setCompanyName] = useState(initialData.companyName || '')
  const [fullName, setFullName] = useState(initialData.fullName || '')
  const [industry, setIndustry] = useState(initialData.industry || '')
  const [companySize, setCompanySize] = useState(initialData.companySize || '')
  const [role, setRole] = useState(initialData.role || '')
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
    
    const marketingData: MarketingData = {
      companyName: companyName.trim(),
      fullName: fullName.trim() || undefined,
      industry: industry || undefined,
      companySize: companySize || undefined,
      role: role.trim() || undefined,
    }
    
    // Save to localStorage for marketing purposes
    localStorage.setItem('licitia_user_company', marketingData.companyName)
    if (marketingData.fullName) {
      localStorage.setItem('licitia_user_name', marketingData.fullName)
    }
    if (marketingData.industry) {
      localStorage.setItem('licitia_user_industry', marketingData.industry)
    }
    if (marketingData.companySize) {
      localStorage.setItem('licitia_user_company_size', marketingData.companySize)
    }
    if (marketingData.role) {
      localStorage.setItem('licitia_user_role', marketingData.role)
    }
    
    // Update lead information in backend with marketing data
    const userEmail = localStorage.getItem('licitia_user_email')
    if (userEmail) {
      captureLead({
        email: userEmail,
        name: marketingData.fullName,
        company: marketingData.companyName,
        industry: marketingData.industry,
        company_size: marketingData.companySize,
        role: marketingData.role,
        source: 'onboarding',
      }).catch((err) => {
        console.error('Error updating lead with marketing data:', err)
        // Don't block onboarding if this fails
      })
    }
    
    onNext(marketingData)
  }

  const handleCompanyNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCompanyName(e.target.value)
    setError('')
    setInvalid(false)
  }

  return (
    <div className="onboarding-marketing-step">
      <div className="onboarding-marketing-header">
        <Button
          kind="ghost"
          size="sm"
          onClick={onBack}
          renderIcon={ArrowLeft}
          className="onboarding-marketing-back"
        >
          Atrás
        </Button>
      </div>

      <div className="onboarding-marketing-content">
        <h2 className="onboarding-marketing-title">
          Cuéntanos sobre ti
        </h2>
        
        <p className="onboarding-marketing-description">
          Esta información nos ayuda a personalizar tu experiencia. Todos los campos son opcionales excepto el nombre de tu empresa.
        </p>

        <form onSubmit={handleSubmit} className="onboarding-marketing-form">
          <div className="onboarding-marketing-field">
            <TextInput
              id="company-name"
              labelText="Nombre de tu empresa *"
              placeholder="Ej: Constructora ABC"
              value={companyName}
              onChange={handleCompanyNameChange}
              invalid={invalid}
              invalidText={error}
              size="lg"
              autoFocus
              required
            />
          </div>

          <div className="onboarding-marketing-field">
            <TextInput
              id="full-name"
              labelText="Tu nombre completo"
              placeholder="Ej: Juan Pérez"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              size="lg"
            />
          </div>

          <div className="onboarding-marketing-field">
            <Select
              id="industry"
              labelText="Industria o sector"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              size="lg"
            >
              <SelectItem value="" text="Selecciona una opción" />
              <SelectItem value="construccion" text="Construcción" />
              <SelectItem value="ingenieria" text="Ingeniería" />
              <SelectItem value="interventoria" text="Interventoría/Supervisión" />
              <SelectItem value="consultoria" text="Consultoría" />
              <SelectItem value="infraestructura" text="Infraestructura" />
              <SelectItem value="otro" text="Otro" />
            </Select>
          </div>

          <div className="onboarding-marketing-field">
            <Select
              id="company-size"
              labelText="Tamaño de tu empresa"
              value={companySize}
              onChange={(e) => setCompanySize(e.target.value)}
              size="lg"
            >
              <SelectItem value="" text="Selecciona una opción" />
              <SelectItem value="1-10" text="1-10 empleados" />
              <SelectItem value="11-50" text="11-50 empleados" />
              <SelectItem value="51-200" text="51-200 empleados" />
              <SelectItem value="201-500" text="201-500 empleados" />
              <SelectItem value="500+" text="Más de 500 empleados" />
            </Select>
          </div>

          <div className="onboarding-marketing-field">
            <TextInput
              id="role"
              labelText="Tu cargo o rol"
              placeholder="Ej: Gerente de Proyectos"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              size="lg"
            />
          </div>

          {error && invalid && (
            <InlineNotification
              kind="error"
              title="Error"
              subtitle={error}
              lowContrast
              className="onboarding-marketing-error"
            />
          )}

          <div className="onboarding-marketing-actions">
            <Button
              type="submit"
              size="lg"
              className="onboarding-marketing-submit"
              renderIcon={ArrowRight}
            >
              Continuar
            </Button>
            <Button
              kind="ghost"
              size="md"
              onClick={onSkip}
              className="onboarding-marketing-skip"
            >
              Omitir y continuar
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default MarketingInfoStep

