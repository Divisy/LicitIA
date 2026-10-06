import React, { useState, useEffect } from 'react'
import { 
  InlineNotification,
  Loading,
  Tile,
  Button
} from '@carbon/react'
import { 
  DocumentAdd,
  ArrowRight,
  Information
} from '@carbon/icons-react'
import ExperienceUpload from '../components/ExperienceUpload'
import ExperienceList from '../components/ExperienceList'
import RupCapacityCard from '../components/RupCapacityCard'
import Logo from '../components/Logo'
import { getExperiences, getRupProfile, CompanyExperience, RupProfileResponse } from '../api/client'
import './Experiences.scss'

const Experiences: React.FC = () => {
  const [experiences, setExperiences] = useState<CompanyExperience[]>([])
  const [rupProfile, setRupProfile] = useState<RupProfileResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [companyName, setCompanyName] = useState<string>('BEC')
  const [refreshKey, setRefreshKey] = useState(0)

  // Load company name from localStorage if available
  useEffect(() => {
    const savedCompany = localStorage.getItem('licitia_user_company')
    if (savedCompany) {
      setCompanyName(savedCompany)
      fetchExperiences()
    }
  }, [])

  useEffect(() => {
    if (companyName.trim() && refreshKey > 0) {
      fetchExperiences()
    }
  }, [refreshKey])

  const fetchExperiences = async () => {
    if (!companyName.trim()) {
      setError('Por favor ingresa el nombre de la empresa')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const [data, profile] = await Promise.all([
        getExperiences(companyName.trim(), { hydrateRup: true }),
        getRupProfile(companyName.trim()).catch(() => null),
      ])
      setExperiences(data.items)
      setRupProfile(profile)
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar experiencias'
      setError(errorMessage)
      console.error('Error fetching experiences:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadSuccess = (count?: number) => {
    setRefreshKey(prev => prev + 1)
  }

  const handleDeleteSuccess = () => {
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div className="experiences-page">
      {/* Page Header */}
      <div className="experiences-page-header">
        <Logo size="md" showText={true} />
        <h1 className="experiences-page-title">RUP de la empresa</h1>
      </div>

      {/* Step 1: Upload Experiences */}
      <Tile className="experiences-step-tile">
        <div className="experiences-step-header">
          <h2 className="experiences-step-title">
            Paso 1: Cargar RUP
            <Information size={16} className="experiences-step-info-icon" />
          </h2>
        </div>
        <p className="experiences-step-description">
          Carga el certificado RUP vigente (PDF de la cámara de comercio). Guardamos las experiencias y la capacidad financiera/organizacional de la empresa.
        </p>
        <div className="experiences-step-content">
          <ExperienceUpload 
            onUploadSuccess={handleUploadSuccess}
            defaultCompanyName={companyName}
            showValueProposition={false}
          />
        </div>
      </Tile>

      {rupProfile && (
        <Tile className="experiences-step-tile">
          <div className="experiences-step-header">
            <h2 className="experiences-step-title">
              Indicadores del RUP
              <Information size={16} className="experiences-step-info-icon" />
            </h2>
          </div>
          <p className="experiences-step-description">
            Extraídos del certificado para habilitar el match con las licitaciones.
          </p>
          <RupCapacityCard capacity={rupProfile.capacity} />
        </Tile>
      )}

      {/* Step 2: View Experiences */}
      <Tile className="experiences-step-tile">
        <div className="experiences-step-header">
          <h2 className="experiences-step-title">
            Paso 2: Seleccione las experiencias que desea gestionar
            <Information size={16} className="experiences-step-info-icon" />
          </h2>
        </div>
        <p className="experiences-step-description">
          El RUP no incluye el objeto de cada contrato. Carga el acta en PDF; si se lee el objeto,
          aparece en la columna Objeto del contrato.
        </p>
        
        {loading && (
          <div className="experiences-loading">
            <Loading description="Cargando experiencias..." withOverlay={false} />
          </div>
        )}

        {error && (
          <InlineNotification
            kind="error"
            title="Error"
            subtitle={error}
            lowContrast={false}
            className="experiences-error"
          />
        )}

        {!loading && !error && experiences.length > 0 && (
          <div className="experiences-step-content">
            <ExperienceList 
              experiences={experiences}
              companyName={companyName}
              onDelete={handleDeleteSuccess}
              onUpdated={(updated) => {
                setExperiences((current) =>
                  current.map((item) => (item.id === updated.id ? updated : item))
                )
              }}
            />
            <div className="experiences-step-footer">
              <Button
                kind="ghost"
                size="sm"
                onClick={() => window.location.href = '/'}
                renderIcon={ArrowRight}
                className="experiences-manage-all-button"
              >
                Ver todas las licitaciones
              </Button>
            </div>
          </div>
        )}

        {!loading && !error && experiences.length === 0 && (
          <div className="experiences-empty-state">
            <DocumentAdd size={48} className="experiences-empty-icon" />
            <p className="experiences-empty-text">
              Aún no hay un RUP cargado. Completa el Paso 1 para activar el perfil.
            </p>
          </div>
        )}
      </Tile>
    </div>
  )
}

export default Experiences

