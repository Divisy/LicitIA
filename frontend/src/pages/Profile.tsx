import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Grid, 
  Column, 
  Tile, 
  TextInput, 
  Button, 
  InlineNotification,
  FormGroup,
  Tag,
  Loading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Toggle,
  Link,
  Information
} from '@carbon/react'
import { 
  ArrowLeft, 
  Building,
  ArrowRight,
  DocumentAdd,
  WatsonMachineLearning,
  CheckmarkFilled,
  User,
  Email,
  Phone,
  Location,
  Identification,
  Save,
  Edit,
  Launch,
  Logout,
  Information as InformationIcon,
  ChevronDown
} from '@carbon/icons-react'
import { useTheme } from '../theme/ThemeProvider'
import Logo from '../components/Logo'
import { getExperiences, CompanyExperience } from '../api/client'
import './Profile.scss'

interface CompanyProfile {
  type: string
  specialties: string[]
  averageAmount: number | null
  totalAmount: number | null
  experienceLevel: 'Principiante' | 'Intermedio' | 'Avanzado' | 'Experto'
  tenderTypes: string[]
  regions: string[]
}

interface CompanyInfo {
  companyName: string
  nit: string
  contactPerson: string
  email: string
  phone: string
  address: string
  city: string
  department: string
}

const Profile: React.FC = () => {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo>({
    companyName: '',
    nit: '',
    contactPerson: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    department: ''
  })
  const [experiences, setExperiences] = useState<CompanyExperience[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState(0)

  // Load company info from localStorage
  useEffect(() => {
    const savedCompany = localStorage.getItem('licitia_user_company')
    const savedInfo = localStorage.getItem('licitia_company_info')
    
    if (savedInfo) {
      try {
        const info = JSON.parse(savedInfo)
        setCompanyInfo(info)
        if (info.companyName) {
          fetchExperiences(info.companyName)
        }
      } catch (e) {
        console.error('Error parsing saved company info:', e)
      }
    } else if (savedCompany) {
      setCompanyInfo(prev => ({ ...prev, companyName: savedCompany }))
      fetchExperiences(savedCompany)
    } else {
      // Try to load from landing page data
      const landingEmail = localStorage.getItem('licitia_user_email')
      const landingName = localStorage.getItem('licitia_user_name')
      const landingCompany = localStorage.getItem('licitia_user_company')
      
      if (landingCompany) {
        setCompanyInfo(prev => ({
          ...prev,
          companyName: landingCompany,
          contactPerson: landingName || '',
          email: landingEmail || ''
        }))
        fetchExperiences(landingCompany)
      }
    }
  }, [])

  const fetchExperiences = async (name: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getExperiences(name.trim())
      setExperiences(data.items)
    } catch (err: any) {
      console.error('Error fetching experiences:', err)
      setError('Error al cargar experiencias')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof CompanyInfo, value: string) => {
    setCompanyInfo(prev => ({ ...prev, [field]: value }))
    setError(null)
    setSuccess(null)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!companyInfo.companyName.trim()) {
      setError('El nombre de la empresa es requerido')
      return
    }

    if (companyInfo.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(companyInfo.email)) {
      setError('Por favor ingresa un email válido')
      return
    }

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      // Save to localStorage
      localStorage.setItem('licitia_user_company', companyInfo.companyName.trim())
      localStorage.setItem('licitia_company_info', JSON.stringify(companyInfo))
      
      // Fetch experiences if company name changed
      if (companyInfo.companyName.trim()) {
        await fetchExperiences(companyInfo.companyName.trim())
      }
      
      setSuccess('Información guardada exitosamente')
      setIsEditing(false)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError('Error al guardar la información')
      console.error('Error saving company info:', err)
    } finally {
      setSaving(false)
    }
  }

  // Analyze experiences to determine company profile
  const companyProfile = useMemo<CompanyProfile | null>(() => {
    if (experiences.length === 0) return null

    const specialties = new Set<string>()
    const tenderTypes = new Set<string>()
    const regions = new Set<string>()
    let totalAmount = 0
    let amountCount = 0

    experiences.forEach(exp => {
      // Extract specialties from categories and engineering areas
      if (exp.category) {
        specialties.add(exp.category)
      }
      if (exp.engineering_area) {
        specialties.add(exp.engineering_area)
      }

      // Determine tender types based on category and area
      const categoryLower = (exp.category || '').toLowerCase()
      const areaLower = (exp.engineering_area || '').toLowerCase()
      const descriptionLower = (exp.project_description || '').toLowerCase()

      if (categoryLower.includes('interventoría') || areaLower.includes('interventoría') || descriptionLower.includes('interventoría')) {
        tenderTypes.add('Interventoría y Supervisión')
      }
      if (categoryLower.includes('construcción') || areaLower.includes('construcción') || descriptionLower.includes('construcción')) {
        tenderTypes.add('Construcción')
      }
      if (areaLower.includes('vial') || areaLower.includes('vías') || descriptionLower.includes('vial')) {
        tenderTypes.add('Infraestructura Vial')
      }
      if (descriptionLower.includes('supervisión') || descriptionLower.includes('supervision')) {
        tenderTypes.add('Supervisión de Obras')
      }
      if (descriptionLower.includes('estudio') || descriptionLower.includes('diseño')) {
        tenderTypes.add('Estudios y Diseños')
      }

      // Extract regions from contracting entity
      if (exp.contracting_entity) {
        const entity = exp.contracting_entity.toLowerCase()
        if (entity.includes('alcaldía') || entity.includes('municipio')) {
          const match = entity.match(/(?:alcaldía|municipio)\s+de\s+(\w+)/i)
          if (match) {
            regions.add(match[1])
          }
        }
      }

      // Calculate amounts
      if (exp.amount) {
        totalAmount += exp.amount
        amountCount++
      }
    })

    // Determine experience level
    let experienceLevel: 'Principiante' | 'Intermedio' | 'Avanzado' | 'Experto' = 'Principiante'
    if (experiences.length >= 20) {
      experienceLevel = 'Experto'
    } else if (experiences.length >= 10) {
      experienceLevel = 'Avanzado'
    } else if (experiences.length >= 5) {
      experienceLevel = 'Intermedio'
    }

    // Determine company type
    let companyType = 'General'
    if (tenderTypes.has('Interventoría y Supervisión')) {
      companyType = 'Especialista en Interventoría'
    } else if (tenderTypes.has('Construcción')) {
      companyType = 'Constructor'
    } else if (tenderTypes.has('Infraestructura Vial')) {
      companyType = 'Especialista en Infraestructura Vial'
    }

    return {
      type: companyType,
      specialties: Array.from(specialties).slice(0, 5),
      averageAmount: amountCount > 0 ? totalAmount / amountCount : null,
      totalAmount: totalAmount > 0 ? totalAmount : null,
      experienceLevel,
      tenderTypes: Array.from(tenderTypes),
      regions: Array.from(regions).slice(0, 5)
    }
  }, [experiences])

  // Get user initials for avatar
  const userInitials = companyInfo.contactPerson
    ? companyInfo.contactPerson.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : companyInfo.companyName
    ? companyInfo.companyName.substring(0, 2).toUpperCase()
    : 'U'

  const [isEditing, setIsEditing] = useState(false)

  return (
    <div className="profile-page">
      {/* Header Section */}
      <div className="profile-header-section">
        <div className="profile-header-logo">
          <Logo size="md" showText={true} />
        </div>
        <div className="profile-header-avatar">
          <div className="profile-header-avatar-circle">
            {userInitials}
          </div>
        </div>
        <div className="profile-header-info">
          <h1 className="profile-header-name">
            {companyInfo.contactPerson || companyInfo.companyName || 'Usuario'}
          </h1>
          {companyInfo.email && (
            <p className="profile-header-email">{companyInfo.email}</p>
          )}
        </div>
        <div className="profile-header-actions">
          {!isEditing ? (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => setIsEditing(true)}
              renderIcon={Edit}
            >
              Editar
            </Button>
          ) : (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => setIsEditing(false)}
            >
              Cancelar
            </Button>
          )}
        </div>
      </div>

      <Grid className="profile-grid" narrow>
        {/* Left Column - Company Data */}
        <Column lg={8} md={4} sm={4}>
          <Tile className="profile-data-tile">
            <div className="profile-data-header">
              <Building size={20} className="profile-data-icon" />
              <h2 className="profile-data-title">Datos de la Empresa</h2>
            </div>
            
            <form onSubmit={handleSave} className="profile-data-form">
              <div className="profile-data-grid">
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="company-name"
                    labelText="Nombre de la Empresa *"
                    placeholder="Ej: Constructora ABC S.A.S"
                    value={companyInfo.companyName}
                    onChange={(e) => handleInputChange('companyName', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                    required
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="nit"
                    labelText="NIT / RUT"
                    placeholder="Ej: 900123456-7"
                    value={companyInfo.nit}
                    onChange={(e) => handleInputChange('nit', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                    renderIcon={Identification}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="contact-person"
                    labelText="Persona de Contacto"
                    placeholder="Ej: Juan Pérez"
                    value={companyInfo.contactPerson}
                    onChange={(e) => handleInputChange('contactPerson', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                    renderIcon={User}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="email"
                    labelText="Correo Electrónico"
                    placeholder="Ej: contacto@empresa.com"
                    value={companyInfo.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    size="md"
                    type="email"
                    disabled={!isEditing}
                    renderIcon={Email}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="phone"
                    labelText="Teléfono"
                    placeholder="Ej: +57 300 123 4567"
                    value={companyInfo.phone}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                    renderIcon={Phone}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="address"
                    labelText="Dirección"
                    placeholder="Ej: Calle 123 #45-67"
                    value={companyInfo.address}
                    onChange={(e) => handleInputChange('address', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                    renderIcon={Location}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="city"
                    labelText="Ciudad"
                    placeholder="Ej: Medellín"
                    value={companyInfo.city}
                    onChange={(e) => handleInputChange('city', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                  />
                </FormGroup>
                <FormGroup className="profile-data-field">
                  <TextInput
                    id="department"
                    labelText="Departamento"
                    placeholder="Ej: Antioquia"
                    value={companyInfo.department}
                    onChange={(e) => handleInputChange('department', e.target.value)}
                    size="md"
                    disabled={!isEditing}
                  />
                </FormGroup>
              </div>

              {isEditing && (
                <>
                  {(error || success) && (
                    <InlineNotification
                      kind={error ? 'error' : 'success'}
                      title={error ? 'Error' : 'Éxito'}
                      subtitle={error || success}
                      lowContrast={false}
                      className="profile-notification"
                      onClose={() => {
                        setError(null)
                        setSuccess(null)
                      }}
                    />
                  )}

                  <div className="profile-data-actions">
                    <Button
                      type="submit"
                      size="md"
                      disabled={saving || !companyInfo.companyName.trim()}
                      renderIcon={Save}
                    >
                      {saving ? 'Guardando...' : 'Guardar cambios'}
                    </Button>
                    <Button
                      kind="secondary"
                      size="md"
                      onClick={() => {
                        setIsEditing(false)
                        setError(null)
                        setSuccess(null)
                      }}
                    >
                      Cancelar
                    </Button>
                  </div>
                </>
              )}
            </form>
          </Tile>

          {/* Quick Actions */}
          <div className="profile-quick-actions">
            <Button
              kind="ghost"
              size="sm"
              onClick={() => navigate('/experiences')}
              renderIcon={DocumentAdd}
            >
              Gestionar Experiencias
            </Button>
            <Button
              kind="ghost"
              size="sm"
              onClick={toggleTheme}
              renderIcon={WatsonMachineLearning}
            >
              {theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}
            </Button>
          </div>
        </Column>

        {/* Right Column - Profile Analysis */}
        <Column lg={8} md={4} sm={4}>

          {/* Profile Analysis */}
          {loading ? (
            <Tile className="profile-analysis-tile">
              <Loading description="Analizando perfil..." withOverlay={false} />
            </Tile>
          ) : companyProfile ? (
            <Tile className="profile-analysis-tile">
              <div className="profile-analysis-header">
                <WatsonMachineLearning size={20} className="profile-analysis-icon" />
                <h2 className="profile-analysis-title">Análisis de Perfil</h2>
              </div>

              <div className="profile-analysis-content">
                {/* Profile Type Card */}
                <div className="profile-analysis-type-card">
                  <div className="profile-analysis-type-icon">
                    <Building size={20} />
                  </div>
                  <div className="profile-analysis-type-content">
                    <div className="profile-analysis-type-name">{companyProfile.type}</div>
                    <Tag 
                      type={companyProfile.experienceLevel === 'Experto' ? 'green' : companyProfile.experienceLevel === 'Avanzado' ? 'blue' : companyProfile.experienceLevel === 'Intermedio' ? 'cyan' : 'gray'} 
                      size="sm"
                      className="profile-analysis-type-badge"
                    >
                      {companyProfile.experienceLevel}
                    </Tag>
                  </div>
                </div>

                {/* Stats Card */}
                <div className="profile-analysis-stats-card">
                  <div className="profile-analysis-stat-item">
                    <div className="profile-analysis-stat-number">{experiences.length}</div>
                    <div className="profile-analysis-stat-label">experiencias</div>
                  </div>
                  <div className="profile-analysis-stat-item">
                    <div className="profile-analysis-stat-number">{companyProfile.tenderTypes.length}</div>
                    <div className="profile-analysis-stat-label">tipos de licitaciones</div>
                  </div>
                  {companyProfile.averageAmount && (
                    <div className="profile-analysis-stat-item">
                      <div className="profile-analysis-stat-number">
                        {new Intl.NumberFormat('es-CO', {
                          style: 'currency',
                          currency: 'COP',
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                          notation: 'compact',
                          compactDisplay: 'short'
                        }).format(companyProfile.averageAmount)}
                      </div>
                      <div className="profile-analysis-stat-label">promedio proyecto</div>
                    </div>
                  )}
                </div>

                {/* Tender Types */}
                {companyProfile.tenderTypes.length > 0 && (
                  <div className="profile-analysis-section">
                    <h4 className="profile-analysis-section-title">Tipos de licitaciones disponibles</h4>
                    <div className="profile-analysis-tender-types">
                      {companyProfile.tenderTypes.map((type, idx) => (
                        <Tag key={idx} type="blue" size="sm" className="profile-analysis-tender-tag">
                          <CheckmarkFilled size={12} />
                          {type}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}

                {/* Specialties */}
                {companyProfile.specialties.length > 0 && (
                  <div className="profile-analysis-section">
                    <h4 className="profile-analysis-section-title">Especialidades</h4>
                    <div className="profile-analysis-specialties">
                      {companyProfile.specialties.map((specialty, idx) => (
                        <Tag key={idx} type="cyan" size="sm" className="profile-analysis-specialty-tag">
                          {specialty}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Tile>
          ) : experiences.length === 0 ? (
            <Tile className="profile-analysis-tile profile-analysis-tile--empty">
              <div className="profile-analysis-empty">
                <WatsonMachineLearning size={48} className="profile-analysis-empty-icon" />
                <h3 className="profile-analysis-empty-title">Sin análisis disponible</h3>
                <p className="profile-analysis-empty-text">
                  Carga experiencias para generar un análisis automático de tu perfil
                </p>
                <Button
                  kind="primary"
                  size="md"
                  onClick={() => navigate('/experiences')}
                  renderIcon={ArrowRight}
                >
                  Cargar Experiencias
                </Button>
              </div>
            </Tile>
          ) : null}
        </Column>
      </Grid>
    </div>
  )
}

export default Profile
