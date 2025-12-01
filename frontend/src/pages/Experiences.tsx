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
import Logo from '../components/Logo'
import { getExperiences, CompanyExperience, getTenders, TenderFilters } from '../api/client'
import './Experiences.scss'

const Experiences: React.FC = () => {
  const [experiences, setExperiences] = useState<CompanyExperience[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [companyName, setCompanyName] = useState<string>('BEC')
  const [refreshKey, setRefreshKey] = useState(0)
  const [matchedTendersCount, setMatchedTendersCount] = useState<number | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)

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
      const data = await getExperiences(companyName.trim())
      setExperiences(data.items)
      
      // Fetch matched tenders count if we have experiences
      if (data.items.length > 0) {
        fetchMatchedTendersCount(companyName.trim())
      } else {
        setMatchedTendersCount(0)
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar experiencias'
      setError(errorMessage)
      console.error('Error fetching experiences:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchMatchedTendersCount = async (name: string) => {
    setLoadingStats(true)
    try {
      const filters: TenderFilters = {
        company_name: name,
        match_experience: true,
        min_match_score: 0.55,
        limit: 1,
        offset: 0,
      }
      const result = await getTenders(filters)
      setMatchedTendersCount(result.total)
    } catch (err) {
      console.error('Error fetching matched tenders count:', err)
      setMatchedTendersCount(null)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleUploadSuccess = (count?: number) => {
    setRefreshKey(prev => prev + 1)
    // Refresh stats after upload
    if (companyName.trim()) {
      setTimeout(() => {
        fetchMatchedTendersCount(companyName.trim())
      }, 1000)
    }
  }

  const handleDeleteSuccess = () => {
    setRefreshKey(prev => prev + 1)
    // Refresh stats after delete
    if (companyName.trim()) {
      setTimeout(() => {
        fetchMatchedTendersCount(companyName.trim())
      }, 500)
    }
  }

  return (
    <div className="experiences-page">
      {/* Page Header */}
      <div className="experiences-page-header">
        <Logo size="md" showText={true} />
        <h1 className="experiences-page-title">Gestionar Experiencias</h1>
      </div>

      {/* Step 1: Upload Experiences */}
      <Tile className="experiences-step-tile">
        <div className="experiences-step-header">
          <h2 className="experiences-step-title">
            Paso 1: Cargar experiencias
            <Information size={16} className="experiences-step-info-icon" />
          </h2>
        </div>
        <p className="experiences-step-description">
          Carga tus proyectos anteriores para que el sistema pueda encontrar licitaciones que coincidan con tu experiencia. 
          Puedes subir un archivo Excel o agregar experiencias manualmente.
        </p>
        <div className="experiences-step-content">
          <ExperienceUpload 
            onUploadSuccess={handleUploadSuccess}
            defaultCompanyName={companyName}
            showValueProposition={false}
          />
        </div>
      </Tile>

      {/* Step 2: View Experiences */}
      <Tile className="experiences-step-tile">
        <div className="experiences-step-header">
          <h2 className="experiences-step-title">
            Paso 2: Seleccione las experiencias que desea gestionar
            <Information size={16} className="experiences-step-info-icon" />
          </h2>
        </div>
        <p className="experiences-step-description">
          Visualice y gestione todas sus experiencias guardadas. Puede eliminar experiencias que ya no sean relevantes.
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
              Aún no tiene experiencias guardadas. Complete el Paso 1 para comenzar.
            </p>
          </div>
        )}
      </Tile>
    </div>
  )
}

export default Experiences

