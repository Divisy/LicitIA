import React, { useState } from 'react'
import { TextInput, Button, Checkbox, InlineNotification } from '@carbon/react'
import { ArrowLeft, ArrowRight } from '@carbon/icons-react'
import { captureLead } from '../../api/client'
import {
  COMPANY_SECTORS,
  CompanySector,
  isValidPhone,
  normalizePhone,
  parseStoredSectors,
  serializeSectors,
  USER_SECTORS_STORAGE_KEY,
} from '../../utils/companySectors'
import {
  COMPANY_PROFILE_STEP_LEAD,
  COMPANY_PROFILE_STEP_TITLE,
} from '../../content/productMessaging'
import './MarketingInfoStep.scss'

interface MarketingInfoStepProps {
  onNext: (data: MarketingData) => void
  onBack: () => void
  initialData?: Partial<MarketingData>
}

export interface MarketingData {
  contactName: string
  phone: string
  city: string
  sectors: CompanySector[]
}

const MarketingInfoStep: React.FC<MarketingInfoStepProps> = ({
  onNext,
  onBack,
  initialData = {},
}) => {
  const [contactName, setContactName] = useState(initialData.contactName || '')
  const [phone, setPhone] = useState(initialData.phone || '')
  const [city, setCity] = useState(initialData.city || '')
  const [sectors, setSectors] = useState<CompanySector[]>(initialData.sectors || [])
  const [error, setError] = useState('')

  const toggleSector = (value: CompanySector, checked: boolean) => {
    setSectors((current) => {
      if (checked) {
        return current.includes(value) ? current : [...current, value]
      }
      return current.filter((item) => item !== value)
    })
    setError('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const name = contactName.trim()
    const normalizedPhone = normalizePhone(phone)

    if (name.length < 2) {
      setError('Ingresa el nombre de contacto')
      return
    }
    if (!isValidPhone(normalizedPhone)) {
      setError('Ingresa un teléfono válido (mínimo 7 dígitos)')
      return
    }
    const cityName = city.trim()
    if (cityName.length < 2) {
      setError('Ingresa la ciudad')
      return
    }
    if (sectors.length === 0) {
      setError('Marca al menos un sector: estudios y diseños, interventoría u obra')
      return
    }

    setError('')

    const marketingData: MarketingData = {
      contactName: name,
      phone: normalizedPhone,
      city: cityName,
      sectors,
    }

    localStorage.setItem('licitia_user_name', marketingData.contactName)
    localStorage.setItem('licitia_user_phone', marketingData.phone)
    localStorage.setItem('licitia_user_city', marketingData.city)
    localStorage.setItem(USER_SECTORS_STORAGE_KEY, serializeSectors(marketingData.sectors))

    const userEmail = localStorage.getItem('licitia_user_email')
    const company = localStorage.getItem('licitia_user_company')
    if (userEmail) {
      captureLead({
        email: userEmail,
        name: marketingData.contactName,
        company: company || undefined,
        phone: marketingData.phone,
        city: marketingData.city,
        sectors: marketingData.sectors,
        source: 'onboarding',
      }).catch((err) => {
        console.error('Error updating lead with company profile:', err)
      })
    }

    onNext(marketingData)
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
          {COMPANY_PROFILE_STEP_TITLE}
        </h2>

        <p className="onboarding-marketing-description">
          {COMPANY_PROFILE_STEP_LEAD}
        </p>

        <form onSubmit={handleSubmit} className="onboarding-marketing-form">
          <div className="onboarding-marketing-field">
            <TextInput
              id="contact-name"
              labelText="Nombre de contacto *"
              placeholder="Ej: Juan Lopez"
              value={contactName}
              onChange={(e) => {
                setContactName(e.target.value)
                setError('')
              }}
              size="lg"
              autoFocus
            />
          </div>

          <div className="onboarding-marketing-field">
            <TextInput
              id="contact-phone"
              type="tel"
              labelText="Teléfono *"
              placeholder="Ej: +57 300 123 4567"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value)
                setError('')
              }}
              size="lg"
            />
          </div>

          <div className="onboarding-marketing-field">
            <TextInput
              id="contact-city"
              labelText="Ciudad *"
              placeholder="Ej: Bogotá"
              value={city}
              onChange={(e) => {
                setCity(e.target.value)
                setError('')
              }}
              size="lg"
            />
          </div>

          <fieldset className="onboarding-marketing-sectors">
            <legend className="onboarding-marketing-sectors-legend">
              Sector *
            </legend>
            <p className="onboarding-marketing-sectors-hint">
              Puedes marcar más de uno si la empresa hace varias líneas.
            </p>
            {COMPANY_SECTORS.map((sector) => (
              <Checkbox
                key={sector.value}
                id={`sector-${sector.value}`}
                labelText={sector.label}
                checked={sectors.includes(sector.value)}
                onChange={(_, { checked }) => toggleSector(sector.value, checked)}
              />
            ))}
          </fieldset>

          {error && (
            <InlineNotification
              kind="error"
              title="Falta información"
              subtitle={error}
              hideCloseButton
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
          </div>
        </form>
      </div>
    </div>
  )
}

export default MarketingInfoStep
