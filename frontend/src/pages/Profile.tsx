import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ExperienceUpload from '../components/ExperienceUpload'
import ExperienceList from '../components/ExperienceList'
import { getExperiences, CompanyExperience } from '../api/client'
import './Profile.css'

const Profile: React.FC = () => {
  const [experiences, setExperiences] = useState<CompanyExperience[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [companyName, setCompanyName] = useState<string>('BEC')
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchExperiences = async () => {
    if (!companyName.trim()) return

    setLoading(true)
    setError(null)

    try {
      const data = await getExperiences(companyName.trim())
      setExperiences(data.items)
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar experiencias'
      setError(errorMessage)
      console.error('Error fetching experiences:', err)
      // Still set loading to false even on error
      setLoading(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (companyName.trim()) {
      fetchExperiences()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyName, refreshKey])

  const handleUploadSuccess = () => {
    // Refresh the experiences list
    setRefreshKey(prev => prev + 1)
  }

  const handleDeleteSuccess = () => {
    // Refresh the experiences list
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <Link to="/" className="back-button">
          ← Volver al Dashboard
        </Link>
        <h1>Perfil de la Empresa</h1>
      </div>

      <div className="profile-content">
        <div className="profile-section">
          <h2>Información de la Empresa</h2>
          <div className="company-name-input">
            <label htmlFor="company-name">Nombre de la Empresa:</label>
            <input
              type="text"
              id="company-name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Ej: BEC"
            />
            <button onClick={fetchExperiences} className="refresh-button">
              Buscar Experiencias
            </button>
          </div>
        </div>

        <div className="profile-section">
          <h2>Cargar Experiencias</h2>
          <ExperienceUpload 
            onUploadSuccess={handleUploadSuccess}
            defaultCompanyName={companyName}
          />
        </div>

        <div className="profile-section">
          <h2>Experiencias Guardadas</h2>
          {loading && <div className="loading">Cargando experiencias...</div>}
          {error && <div className="error">Error: {error}</div>}
          {!loading && !error && (
            <ExperienceList 
              experiences={experiences}
              companyName={companyName}
              onDelete={handleDeleteSuccess}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default Profile
