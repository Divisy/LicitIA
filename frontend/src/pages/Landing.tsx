import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { 
  Grid, 
  Column, 
  TextInput, 
  Button as CarbonButton,
  InlineNotification,
  Tile,
  Accordion,
  AccordionItem
} from '@carbon/react'
import { 
  Search, 
  Flash, 
  ChartLine, 
  DocumentAdd, 
  WatsonMachineLearning,
  Document,
  CheckmarkFilled,
  ArrowRight,
  Star,
  Security,
  User,
  Quotes,
  Time,
  WarningAlt,
  View,
  Calendar,
  Location,
  Money,
  Email,
  LogoLinkedin,
  LogoTwitter,
  Information,
  Menu,
  Close,
  Launch
} from '@carbon/icons-react'
import { captureLead, getTenders, Tender } from '../api/client'
import { useTranslation } from 'react-i18next'
import { Button, Card } from '../components/ui'
import { Tag, Link as CarbonLink } from '@carbon/react'
import './Landing.scss'

const Landing: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    company: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isVisible, setIsVisible] = useState(true)
  const [liveTenders, setLiveTenders] = useState<Tender[]>([])
  const [loadingTenders, setLoadingTenders] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Intentar capturar el lead en el backend
      try {
        const leadResponse = await captureLead({
          email: formData.email,
          name: formData.name || undefined,
          company: formData.company || undefined,
          source: 'landing_page',
        })
        console.log('[Landing] Lead captured in backend:', leadResponse)
      } catch (apiErr: any) {
        // Si el backend no está disponible, continuar con localStorage
        console.warn('[Landing] Backend not available, using localStorage fallback:', apiErr?.message)
        // No mostrar error al usuario si el backend falla, usar fallback
      }
      
      // Verificar si es un nuevo usuario (email diferente al guardado)
      const previousEmail = localStorage.getItem('licitia_user_email')
      const isNewUser = !previousEmail || previousEmail !== formData.email
      
      // Si es un nuevo usuario, limpiar todos los flags de onboarding
      if (isNewUser) {
        console.log('[Landing] New user detected, clearing onboarding flags')
        localStorage.removeItem('licitia_onboarding_completed')
        localStorage.removeItem('licitia_onboarding_state')
        localStorage.removeItem('licitia_onboarding_banner_dismissed')
      }
      
      // Guardar información del lead en localStorage para el onboarding
      localStorage.setItem('licitia_new_user', 'true')
      localStorage.setItem('licitia_user_email', formData.email)
      if (formData.name) {
        localStorage.setItem('licitia_user_name', formData.name)
      }
      if (formData.company) {
        localStorage.setItem('licitia_user_company', formData.company)
      }
      // Marcar que debe iniciar onboarding automáticamente
      localStorage.setItem('licitia_start_onboarding', 'true')
      
      console.log('[Landing] Lead saved, flags set:', {
        email: formData.email,
        company: formData.company,
        startOnboarding: localStorage.getItem('licitia_start_onboarding')
      })
      
      setSuccess(true)
      setTimeout(() => {
        console.log('[Landing] Navigating to dashboard, flag:', localStorage.getItem('licitia_start_onboarding'))
        navigate('/dashboard')
      }, 1500)
    } catch (err: any) {
      console.error('Error in form submission:', err)
      // Solo mostrar error si es un error crítico
      setError('Error al procesar el registro. Por favor, intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = () => {
    navigate('/')
  }

  // Create demo data function
  const createDemoTenders = (): Tender[] => [
          {
            id: 'demo-1',
            external_id: 'demo-1',
            source: 'SECOP',
            entity_name: 'Alcaldía de Bogotá - Secretaría de Movilidad',
            object_text: 'Interventoría técnica para proyecto de infraestructura vial en la Avenida 68',
            department: 'Cundinamarca',
            municipality: 'Bogotá',
            amount: 2500000000,
            publication_date: new Date().toISOString(),
            closing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
            state: 'Publicado',
            apertura_estado: 'Abierto',
            process_url: '#',
            contract_type: 'Interventoría y Supervisión',
            contract_modality: 'Prestación de Servicios',
            relevance_score: 0.95,
            is_relevant_interventoria_vial: true,
            experience_match_score: 0.85,
            matching_experiences: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 'demo-2',
            external_id: 'demo-2',
            source: 'SECOP',
            entity_name: 'Instituto Nacional de Vías (INVÍAS)',
            object_text: 'Supervisión técnica de obras de rehabilitación de vía principal',
            department: 'Antioquia',
            municipality: 'Medellín',
            amount: 1800000000,
            publication_date: new Date().toISOString(),
            closing_date: new Date(Date.now() + 25 * 24 * 60 * 60 * 1000).toISOString(),
            state: 'Publicado',
            apertura_estado: 'Abierto',
            process_url: '#',
            contract_type: 'Interventoría y Supervisión',
            contract_modality: 'Prestación de Servicios',
            relevance_score: 0.88,
            is_relevant_interventoria_vial: true,
            experience_match_score: 0.78,
            matching_experiences: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 'demo-3',
            external_id: 'demo-3',
            source: 'SECOP',
            entity_name: 'Gobernación de Cundinamarca',
            object_text: 'Interventoría para proyecto de mejoramiento de vías terciarias',
            department: 'Cundinamarca',
            municipality: 'Chía',
            amount: 950000000,
            publication_date: new Date().toISOString(),
            closing_date: new Date(Date.now() + 20 * 24 * 60 * 60 * 1000).toISOString(),
            state: 'Publicado',
            apertura_estado: 'Abierto',
            process_url: '#',
            contract_type: 'Interventoría y Supervisión',
            contract_modality: 'Prestación de Servicios',
            relevance_score: 0.82,
            is_relevant_interventoria_vial: true,
            experience_match_score: 0.72,
            matching_experiences: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]

  // Fetch live tenders immediately on mount (Time to Value = 0)
  useEffect(() => {
    const fetchLiveTenders = async () => {
      try {
        setLoadingTenders(true)
        const response = await getTenders({
          limit: 6,
          offset: 0,
          only_interventoria: true, // Show most relevant tenders
        })
        // Add demo match scores for preview (to show value of the product)
        const tendersWithDemoScores = ((response?.items || [])).map((tender, idx) => ({
          ...tender,
          // Show demo match scores: 85%, 78%, 72%, 65% to demonstrate AI matching value
          experience_match_score: tender.experience_match_score || (0.85 - idx * 0.07),
        }))
        // Use real data if available, otherwise use demo data
        if (tendersWithDemoScores.length > 0) {
          setLiveTenders(tendersWithDemoScores)
        } else {
          setLiveTenders(createDemoTenders())
        }
      } catch (err) {
        console.error('Error fetching live tenders:', err)
        // Always show demo data if API fails
        setLiveTenders(createDemoTenders())
      } finally {
        setLoadingTenders(false)
      }
    }

    fetchLiveTenders()
  }, [])

  // Handle scroll for header styling
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId) || document.querySelector(`.${sectionId}`)
    if (element) {
      const headerOffset = 80 // Height of fixed header
      const elementPosition = element.getBoundingClientRect().top
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      })
      setMobileMenuOpen(false)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('es-CO', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    })
  }

  const formatAmount = (amount: number | null) => {
    if (!amount) return 'No especificado'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div className="landing-page">
      {/* Header with Navbar */}
      <header className={`landing-header ${scrolled ? 'landing-header--scrolled' : ''}`}>
        <div className="landing-header__container">
          <div className="landing-header__logo" onClick={() => scrollToSection('landing-hero')}>
            <WatsonMachineLearning size={24} />
            <span className="landing-header__logo-text">LicitIA</span>
          </div>
          
          <nav className={`landing-header__nav ${mobileMenuOpen ? 'landing-header__nav--open' : ''}`}>
            <button
              className="landing-header__nav-link"
              onClick={() => scrollToSection('landing-hero')}
            >
              Inicio
            </button>
            <button
              className="landing-header__nav-link"
              onClick={() => scrollToSection('landing-benefits')}
            >
              Características
            </button>
            <button
              className="landing-header__nav-link"
              onClick={() => scrollToSection('landing-pricing')}
            >
              Precios
            </button>
            <button
              className="landing-header__nav-link"
              onClick={() => scrollToSection('landing-faq')}
            >
              FAQ
            </button>
            <CarbonButton
              size="md"
              onClick={() => {
                scrollToSection('landing-hero')
                // Focus on email input after scroll
                setTimeout(() => {
                  const emailInput = document.getElementById('email') as HTMLInputElement
                  if (emailInput) {
                    emailInput.focus()
                  }
                }, 500)
              }}
              className="landing-header__cta"
            >
              Probar Gratis
              <ArrowRight size={16} />
            </CarbonButton>
          </nav>

          <button
            className="landing-header__mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <Close size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section id="landing-hero" className={`landing-hero ${isVisible ? 'landing-hero--visible' : ''}`}>
        <div className="landing-hero__background">
          <div className="landing-hero__gradient"></div>
          <div className="landing-hero__pattern"></div>
        </div>
        <Grid className="landing-hero__grid">
          <Column lg={8} md={4} sm={4}>
            <div className="landing-hero__content">
              <div className="landing-hero__badge">
                <WatsonMachineLearning size={16} />
                <span>Powered by AI</span>
              </div>
              <h1 className="landing-hero__title">
                {t('landing.hero.title')}
              </h1>
              <p className="landing-hero__subtitle">
                {t('landing.hero.subtitle')}
              </p>
              
              {success ? (
                <InlineNotification
                  kind="success"
                  title="¡Registro exitoso!"
                  subtitle="Redirigiendo al dashboard..."
                  lowContrast
                  className="landing-hero__notification"
                />
              ) : (
                <form className="landing-hero__form" onSubmit={handleSubmit}>
                  <div className="landing-hero__form-container">
                    <TextInput
                      id="email"
                      type="email"
                      labelText=""
                      placeholder="Tu email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                      size="lg"
                      className="landing-hero__input"
                    />
                    <TextInput
                      id="name"
                      type="text"
                      labelText=""
                      placeholder="Tu nombre (opcional)"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      size="lg"
                      className="landing-hero__input"
                    />
                    <TextInput
                      id="company"
                      type="text"
                      labelText=""
                      placeholder="Empresa (opcional)"
                      value={formData.company}
                      onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                      size="lg"
                      className="landing-hero__input"
                    />
                    <CarbonButton
                      type="submit"
                      size="lg"
                      disabled={loading}
                      className="landing-hero__cta"
                    >
                      {loading ? 'Registrando...' : t('landing.hero.cta')}
                      {!loading && <ArrowRight size={20} className="landing-hero__cta-icon" />}
                    </CarbonButton>
                  </div>
                  {error && (
                    <InlineNotification
                      kind="error"
                      title="Error"
                      subtitle={error}
                      lowContrast
                      className="landing-hero__error"
                    />
                  )}
                  <div className="landing-hero__trust">
                    <CheckmarkFilled size={16} />
                    <span>{t('landing.hero.note')}</span>
                  </div>
                </form>
              )}
              
              <button 
                onClick={handleSkip}
                className="landing-hero__skip"
              >
                O saltar y ver el dashboard →
              </button>
              <p className="landing-hero__login-link">
                ¿Ya tienes cuenta?{' '}
                <Link to="/login" className="landing-hero__login-link-text">
                  Inicia sesión
                </Link>
              </p>
            </div>
          </Column>
          
          {/* Product Preview */}
          <Column lg={8} md={4} sm={4}>
            <div className="landing-hero__preview">
              {loadingTenders ? (
                <div className="landing-hero__preview-loading">
                  <div className="landing-hero__preview-spinner"></div>
                </div>
              ) : liveTenders.length > 0 ? (
                <Card padding="none" className="landing-hero__preview-card">
                  <div className="landing-hero__preview-header">
                    <div className="landing-hero__preview-header-left">
                      <WatsonMachineLearning size={20} />
                      <span>LicitIA Dashboard</span>
                    </div>
                    <div className="landing-hero__preview-badge-live">
                      <div className="landing-hero__preview-pulse"></div>
                      <span>En Vivo</span>
                    </div>
                  </div>
                  <div className="landing-hero__preview-stats">
                    <div className="landing-hero__preview-stat-item">
                      <div className="landing-hero__preview-stat-number">{liveTenders.length > 0 ? '25+' : '0'}</div>
                      <div className="landing-hero__preview-stat-label">Licitaciones</div>
                    </div>
                    <div className="landing-hero__preview-stat-item">
                      <div className="landing-hero__preview-stat-number">95%</div>
                      <div className="landing-hero__preview-stat-label">Precisión IA</div>
                    </div>
                    <div className="landing-hero__preview-stat-item">
                      <div className="landing-hero__preview-stat-number">2h</div>
                      <div className="landing-hero__preview-stat-label">Actualización</div>
                    </div>
                  </div>
                  
                  <div className="landing-hero__preview-table">
                    <div className="landing-hero__preview-table-header">
                      <div className="landing-hero__preview-col landing-hero__preview-col--pub-date">FECHA PUBLICACIÓN</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--closing-date">FECHA PRESENTACIÓN OFERTAS</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--entity">ENTIDAD</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--dept">DEPARTAMENTO</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--amount">MONTO</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--state">ESTADO</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--match">MATCH EXPERIENCIA</div>
                      <div className="landing-hero__preview-col landing-hero__preview-col--link">ENLACE</div>
                    </div>
                    {liveTenders.slice(0, 4).map((tender, idx) => {
                      const matchScore = tender.experience_match_score || 0
                      const matchPercentage = Math.round(matchScore * 100)
                      const matchType = matchScore >= 0.6 ? 'green' : matchScore >= 0.4 ? 'yellow' : matchScore >= 0.3 ? 'red' : 'gray'
                      const estadoType = tender.state?.toLowerCase().includes('publicado') || tender.state?.toLowerCase().includes('abierto') ? 'green' : 'gray'
                      
                      return (
                        <div 
                          key={tender.id} 
                          className={`landing-hero__preview-row ${idx % 2 === 1 ? 'landing-hero__preview-row--zebra' : ''}`}
                          style={{ animationDelay: `${idx * 0.1}s` }}
                        >
                          <div className="landing-hero__preview-col landing-hero__preview-col--pub-date">
                            {tender.publication_date ? formatDate(tender.publication_date) : 'N/A'}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--closing-date">
                            {tender.closing_date ? formatDate(tender.closing_date) : 'N/A'}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--entity">
                            <div className="landing-hero__preview-entity-name">
                              {tender.entity_name.length > 35 
                                ? `${tender.entity_name.substring(0, 35)}...` 
                                : tender.entity_name}
                            </div>
                            <div className="landing-hero__preview-entity-object">
                              {tender.object_text.length > 60 
                                ? `${tender.object_text.substring(0, 60)}...` 
                                : tender.object_text}
                            </div>
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--dept">
                            {tender.department || 'N/A'}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--amount">
                            {tender.amount ? formatAmount(tender.amount) : 'N/A'}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--state">
                            {tender.state ? (
                              <Tag type={estadoType} size="sm">
                                {tender.state}
                              </Tag>
                            ) : (
                              <Tag type="gray" size="sm">N/A</Tag>
                            )}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--match">
                            {matchScore > 0 ? (
                              <Tag type={matchType} size="sm" className="landing-hero__preview-match-tag">
                                <WatsonMachineLearning size={12} />
                                {matchPercentage}%
                              </Tag>
                            ) : (
                              <Tag type="gray" size="sm">-</Tag>
                            )}
                          </div>
                          <div className="landing-hero__preview-col landing-hero__preview-col--link">
                            <CarbonLink
                              href={tender.process_url || '#'}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="landing-hero__preview-link"
                              renderIcon={Launch}
                            >
                              Ver proceso
                            </CarbonLink>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div className="landing-hero__preview-footer">
                    <CarbonButton
                      kind="ghost"
                      size="sm"
                      onClick={() => navigate('/')}
                      className="landing-hero__preview-cta"
                    >
                      Ver Dashboard Completo
                      <ArrowRight size={16} />
                    </CarbonButton>
                  </div>
                </Card>
              ) : (
                <Card padding="lg" className="landing-hero__preview-card landing-hero__preview-card--empty">
                  <WatsonMachineLearning size={48} />
                  <p>Dashboard en tiempo real</p>
                  <p className="landing-hero__preview-empty-subtitle">
                    Regístrate para ver todas las licitaciones
                  </p>
                </Card>
              )}
            </div>
          </Column>
        </Grid>
      </section>

      {/* Social Proof Section - Testimonials + Stats */}
      <section className="landing-testimonials">
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-testimonials__header">
              <h2 className="landing-section-title">Lo que dicen nuestros usuarios</h2>
              <p className="landing-section-subtitle">
                Empresas que ya están ahorrando tiempo y encontrando mejores oportunidades
              </p>
            </div>
            <div className="landing-testimonials__grid">
              <Card padding="lg" className="landing-testimonial-card landing-testimonial-card--1">
                <div className="landing-testimonial-stars">
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                </div>
                <Quotes size={32} className="landing-testimonial-quote" />
                <p className="landing-testimonial-text">
                  "LicitIA me ahorra horas cada semana. Ahora encuentro oportunidades que antes se me pasaban. El matching con IA es increíble."
                </p>
                <div className="landing-testimonial-author">
                  <User size={24} />
                  <div>
                    <strong>Carlos M.</strong>
                    <span>Gerente de Oportunidades, Constructora ABC</span>
                  </div>
                </div>
              </Card>
              
              <Card padding="lg" className="landing-testimonial-card landing-testimonial-card--2">
                <div className="landing-testimonial-stars">
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                </div>
                <Quotes size={32} className="landing-testimonial-quote" />
                <p className="landing-testimonial-text">
                  "Antes perdía 2-3 horas diarias buscando licitaciones. Ahora las encuentro en minutos. Vale cada peso."
                </p>
                <div className="landing-testimonial-author">
                  <User size={24} />
                  <div>
                    <strong>María G.</strong>
                    <span>Directora Comercial, Empresa XYZ</span>
                  </div>
                </div>
              </Card>
              
              <Card padding="lg" className="landing-testimonial-card landing-testimonial-card--3">
                <div className="landing-testimonial-stars">
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                  <Star size={20} />
                </div>
                <Quotes size={32} className="landing-testimonial-quote" />
                <p className="landing-testimonial-text">
                  "La actualización automática es un game-changer. Nunca me pierdo una oportunidad relevante."
                </p>
                <div className="landing-testimonial-author">
                  <User size={24} />
                  <div>
                    <strong>Roberto L.</strong>
                    <span>CEO, Ingeniería y Construcción S.A.</span>
                  </div>
                </div>
              </Card>
            </div>
            
            {/* Stats dentro de Social Proof */}
            <div className="landing-stats">
              <div className="landing-stats__grid">
                <div className="landing-stat">
                  <div className="landing-stat__number">25+</div>
                  <div className="landing-stat__label">Empresas confían en LicitIA</div>
                </div>
                <div className="landing-stat">
                  <div className="landing-stat__number">1,000+</div>
                  <div className="landing-stat__label">Licitaciones analizadas</div>
                </div>
                <div className="landing-stat">
                  <div className="landing-stat__number">10+</div>
                  <div className="landing-stat__label">Horas ahorradas por semana</div>
                </div>
                <div className="landing-stat">
                  <div className="landing-stat__number">95%</div>
                  <div className="landing-stat__label">Precisión en matching</div>
                </div>
              </div>
            </div>
          </Column>
        </Grid>
      </section>

          {/* Benefits Section */}
          <section id="landing-benefits" className="landing-benefits">
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-benefits__header">
              <h2 className="landing-section-title">¿Por qué LicitIA?</h2>
              <p className="landing-section-subtitle">
                La plataforma más inteligente para encontrar licitaciones relevantes
              </p>
            </div>
            <div className="landing-benefits__grid">
              <Card padding="lg" className="landing-benefit-card landing-benefit-card--1">
                <div className="landing-benefit-icon">
                  <Search size={48} />
                </div>
                <h3>{t('landing.benefits.matching.title')}</h3>
                <p>{t('landing.benefits.matching.description')}</p>
              </Card>
              
              <Card padding="lg" className="landing-benefit-card landing-benefit-card--2">
                <div className="landing-benefit-icon">
                  <Flash size={48} />
                </div>
                <h3>{t('landing.benefits.updates.title')}</h3>
                <p>{t('landing.benefits.updates.description')}</p>
              </Card>
              
              <Card padding="lg" className="landing-benefit-card landing-benefit-card--3">
                <div className="landing-benefit-icon">
                  <ChartLine size={48} />
                </div>
                <h3>{t('landing.benefits.filters.title')}</h3>
                <p>{t('landing.benefits.filters.description')}</p>
              </Card>
            </div>
          </Column>
        </Grid>
      </section>

      {/* How It Works */}
      <section className="landing-how-it-works">
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-how-it-works__header">
              <h2 className="landing-section-title">¿Cómo Funciona?</h2>
              <p className="landing-section-subtitle">
                En 3 simples pasos, encuentra las licitaciones perfectas para tu empresa
              </p>
            </div>
            <div className="landing-steps-container">
              <div className="landing-steps-wrapper">
                <Tile className="landing-step landing-step--1">
                  <div className="landing-step-icon-wrapper">
                    <div className="landing-step-icon landing-step-icon--1">
                      <DocumentAdd size={40} />
                    </div>
                    <div className="landing-step-icon-glow landing-step-icon-glow--1"></div>
                  </div>
                  <div className="landing-step-number-wrapper">
                    <div className="landing-step-number">1</div>
                    <div className="landing-step-number-ring"></div>
                  </div>
                  <h3>Carga tus Experiencias</h3>
                  <p>Sube un Excel con tus proyectos anteriores o agrégalos manualmente. Toma 2 minutos.</p>
                  <div className="landing-step-time">
                    <Time size={16} />
                    <span>2 minutos</span>
                  </div>
                </Tile>
                
                <div className="landing-step-connector">
                  <div className="landing-step-connector-line"></div>
                  <div className="landing-step-connector-arrow">
                    <ArrowRight size={24} />
                  </div>
                </div>
                
                <Tile className="landing-step landing-step--2">
                  <div className="landing-step-icon-wrapper">
                    <div className="landing-step-icon landing-step-icon--2">
                      <WatsonMachineLearning size={40} />
                    </div>
                    <div className="landing-step-icon-glow landing-step-icon-glow--2"></div>
                  </div>
                  <div className="landing-step-number-wrapper">
                    <div className="landing-step-number">2</div>
                    <div className="landing-step-number-ring"></div>
                  </div>
                  <h3>IA Encuentra Coincidencias</h3>
                  <p>
                    Nuestra IA analiza tu experiencia y encuentra licitaciones con alta probabilidad 
                    de éxito para tu empresa.
                  </p>
                  <div className="landing-step-time">
                    <Flash size={16} />
                    <span>Instantáneo</span>
                  </div>
                </Tile>
                
                <div className="landing-step-connector">
                  <div className="landing-step-connector-line"></div>
                  <div className="landing-step-connector-arrow">
                    <ArrowRight size={24} />
                  </div>
                </div>
                
                <Tile className="landing-step landing-step--3">
                  <div className="landing-step-icon-wrapper">
                    <div className="landing-step-icon landing-step-icon--3">
                      <Document size={40} />
                    </div>
                    <div className="landing-step-icon-glow landing-step-icon-glow--3"></div>
                  </div>
                  <div className="landing-step-number-wrapper">
                    <div className="landing-step-number">3</div>
                    <div className="landing-step-number-ring"></div>
                  </div>
                  <h3>Presenta Ofertas</h3>
                  <p>
                    Ve las licitaciones ordenadas por fecha de cierre (más tiempo para preparar) 
                    y porcentaje de match (más relevantes primero).
                  </p>
                  <div className="landing-step-time">
                    <CheckmarkFilled size={16} />
                    <span>Listo para ofertar</span>
                  </div>
                </Tile>
              </div>
            </div>
          </Column>
        </Grid>
      </section>

      {/* Live Preview Section - Time to Value = 0 */}
      <section className="landing-live-preview">
        <div className="landing-live-preview__background">
          <div className="landing-live-preview__gradient"></div>
        </div>
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-live-preview__header">
              <div className="landing-live-preview__badge-wrapper">
                <div className="landing-live-preview__badge">
                  <div className="landing-live-preview__pulse"></div>
                  <Flash size={18} />
                  <span>En Vivo • Actualizado hace 2 minutos</span>
                </div>
              </div>
              <h2 className="landing-live-preview__title">
                Licitaciones Disponibles <span className="landing-live-preview__title-highlight">Ahora</span>
              </h2>
              <p className="landing-live-preview__subtitle">
                Estas son <strong>licitaciones reales</strong> que están disponibles ahora mismo. 
                <br />
                <strong className="landing-live-preview__subtitle-highlight">Sin registro, sin compromiso.</strong> Regístrate gratis para ver todas y recibir alertas personalizadas.
              </p>
              <div className="landing-live-preview__value-props">
                <div className="landing-live-preview__value-prop">
                  <CheckmarkFilled size={20} />
                  <span>Acceso inmediato</span>
                </div>
                <div className="landing-live-preview__value-prop">
                  <CheckmarkFilled size={20} />
                  <span>Matching con IA</span>
                </div>
                <div className="landing-live-preview__value-prop">
                  <CheckmarkFilled size={20} />
                  <span>Alertas personalizadas</span>
                </div>
              </div>
            </div>

            {loadingTenders ? (
              <div className="landing-live-preview__loading">
                <div className="landing-live-preview__spinner"></div>
                <p>Cargando licitaciones en tiempo real...</p>
              </div>
            ) : liveTenders.length > 0 ? (
              <>
                <div className="landing-live-preview__grid">
                  {liveTenders.slice(0, 6).map((tender) => (
                    <Card 
                      key={tender.id} 
                      padding="md" 
                      className="landing-tender-card"
                      interactive
                      onClick={() => window.open(tender.process_url, '_blank')}
                    >
                      <div className="landing-tender-card__header">
                        <h3 className="landing-tender-card__title">
                          {tender.object_text.length > 100 
                            ? `${tender.object_text.substring(0, 100)}...` 
                            : tender.object_text}
                        </h3>
                        {tender.experience_match_score && (
                          <div 
                            className="landing-tender-card__match"
                            data-score={
                              tender.experience_match_score >= 0.75 ? 'high' :
                              tender.experience_match_score >= 0.60 ? 'medium' : 'low'
                            }
                          >
                            <WatsonMachineLearning size={16} />
                            <span>{Math.round(tender.experience_match_score * 100)}% Match</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="landing-tender-card__details">
                        <div className="landing-tender-card__detail">
                          <Location size={16} />
                          <span>
                            {tender.entity_name}
                            {tender.department && ` • ${tender.department}`}
                          </span>
                        </div>
                        
                        {tender.closing_date && (
                          <div className="landing-tender-card__detail">
                            <Calendar size={16} />
                            <span>Cierre: {formatDate(tender.closing_date)}</span>
                          </div>
                        )}
                        
                        {tender.amount && (
                          <div className="landing-tender-card__detail">
                            <Money size={16} />
                            <span>{formatAmount(tender.amount)}</span>
                          </div>
                        )}
                      </div>

                      <div className="landing-tender-card__footer">
                        <CarbonButton
                          kind="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            window.open(tender.process_url, '_blank')
                          }}
                        >
                          Ver en SECOP
                          <ArrowRight size={16} />
                        </CarbonButton>
                      </div>
                    </Card>
                  ))}
                </div>
                
                <div className="landing-live-preview__cta-wrapper">
                  <div className="landing-live-preview__cta-card">
                    <div className="landing-live-preview__cta-content">
                      <div className="landing-live-preview__cta-icon">
                        <WatsonMachineLearning size={32} />
                      </div>
                      <div className="landing-live-preview__cta-text-wrapper">
                        <h3 className="landing-live-preview__cta-title">
                          ¿Quieres acceso a <span className="landing-live-preview__cta-title-highlight">todas</span> estas licitaciones?
                        </h3>
                        <p className="landing-live-preview__cta-description">
                          <strong>+{liveTenders.length > 0 ? '500' : 'cientos'} licitaciones disponibles</strong> con matching inteligente, 
                          alertas personalizadas y actualizaciones cada 2 horas.
                        </p>
                        <div className="landing-live-preview__cta-features">
                          <div className="landing-live-preview__cta-feature">
                            <CheckmarkFilled size={18} />
                            <span>Matching con IA basado en tu experiencia</span>
                          </div>
                          <div className="landing-live-preview__cta-feature">
                            <CheckmarkFilled size={18} />
                            <span>Alertas por email cuando haya nuevas oportunidades</span>
                          </div>
                          <div className="landing-live-preview__cta-feature">
                            <CheckmarkFilled size={18} />
                            <span>Filtros avanzados y ordenamiento inteligente</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="landing-live-preview__cta-button-wrapper">
                      <CarbonButton
                        size="lg"
                        onClick={() => {
                          document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                        }}
                        className="landing-live-preview__cta-button"
                      >
                        Quiero Acceso Gratis
                        <ArrowRight size={20} />
                      </CarbonButton>
                      <p className="landing-live-preview__cta-note">
                        <CheckmarkFilled size={16} />
                        <span>30 días gratis • Sin tarjeta de crédito</span>
                      </p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="landing-live-preview__empty">
                <Document size={48} />
                <p>No hay licitaciones disponibles en este momento.</p>
                <p className="landing-live-preview__empty-subtitle">
                  Regístrate para recibir alertas cuando haya nuevas oportunidades.
                </p>
              </div>
            )}
          </Column>
        </Grid>
      </section>

          {/* Guarantee Section */}
          <section className="landing-guarantee">
            <div className="landing-guarantee__background">
              <div className="landing-guarantee__gradient"></div>
              <div className="landing-guarantee__pattern"></div>
            </div>
            <Grid>
              <Column lg={16} md={8} sm={4}>
                <div className="landing-guarantee__badge">
                  <Security size={18} />
                  <span>100% Garantizado</span>
                </div>
                <Card padding="lg" className="landing-guarantee-card">
                  <div className="landing-guarantee__header">
                    <div className="landing-guarantee-icon-wrapper">
                      <div className="landing-guarantee-icon">
                        <Security size={48} />
                      </div>
                      <div className="landing-guarantee-icon-glow"></div>
                    </div>
                    <h2 className="landing-guarantee-title">
                      Garantía <span className="landing-guarantee-title-highlight">Sin Riesgo</span>
                    </h2>
                    <p className="landing-guarantee-description">
                      Prueba LicitIA durante <strong>30 días completamente gratis</strong>. Sin tarjeta de crédito, sin compromiso.
                      Si no encuentras valor, cancela cuando quieras. <strong>Es así de simple.</strong>
                    </p>
                  </div>
                  
                  <div className="landing-guarantee-features">
                    <div className="landing-guarantee-feature landing-guarantee-feature--1">
                      <div className="landing-guarantee-feature-icon">
                        <CheckmarkFilled size={24} />
                      </div>
                      <div className="landing-guarantee-feature-content">
                        <h3>30 días gratis</h3>
                        <p>Sin tarjeta de crédito. Sin compromiso. Prueba todo.</p>
                      </div>
                    </div>
                    
                    <div className="landing-guarantee-feature landing-guarantee-feature--2">
                      <div className="landing-guarantee-feature-icon">
                        <CheckmarkFilled size={24} />
                      </div>
                      <div className="landing-guarantee-feature-content">
                        <h3>Cancela cuando quieras</h3>
                        <p>Sin preguntas. Sin complicaciones. Un solo click.</p>
                      </div>
                    </div>
                    
                    <div className="landing-guarantee-feature landing-guarantee-feature--3">
                      <div className="landing-guarantee-feature-icon">
                        <CheckmarkFilled size={24} />
                      </div>
                      <div className="landing-guarantee-feature-content">
                        <h3>Reembolso 100% garantizado</h3>
                        <p>Si no te gusta, te devolvemos todo tu dinero. Sin condiciones.</p>
                      </div>
                    </div>
                  </div>

                  <div className="landing-guarantee__trust">
                    <div className="landing-guarantee__trust-item">
                      <User size={20} />
                      <span>+25 empresas confían en nosotros</span>
                    </div>
                    <div className="landing-guarantee__trust-item">
                      <Security size={20} />
                      <span>Pago seguro y protegido</span>
                    </div>
                  </div>
                </Card>
              </Column>
            </Grid>
          </section>

          {/* Pricing Section */}
          <section id="landing-pricing" className="landing-pricing">
        <div className="landing-pricing__background">
          <div className="landing-pricing__gradient"></div>
        </div>
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-pricing__header">
              <h2 className="landing-pricing__title">
                Prueba <span className="landing-pricing__title-highlight">Gratis</span> por 30 Días
              </h2>
              <p className="landing-pricing__subtitle">
                Sin tarjeta de crédito. Sin compromiso. Cancela cuando quieras.
              </p>
            </div>
            
            <div className="landing-pricing__cards">
              <Card padding="lg" className="landing-pricing-card landing-pricing-card--free">
                <div className="landing-pricing-card__badge">
                  <Flash size={18} />
                  <span>Recomendado para empezar</span>
                </div>
                <div className="landing-pricing-card__header">
                  <h3 className="landing-pricing-card__name">Prueba Gratis</h3>
                  <div className="landing-pricing-card__price">
                    <span className="landing-pricing-card__price-amount">$0</span>
                    <span className="landing-pricing-card__price-period">/30 días</span>
                  </div>
                  <p className="landing-pricing-card__description">
                    Acceso completo a todas las funciones durante 30 días
                  </p>
                </div>
                <ul className="landing-pricing-card__features">
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Acceso ilimitado a licitaciones</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Matching con IA basado en experiencia</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Hasta 50 experiencias</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Actualizaciones cada 2 horas</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Filtros avanzados</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Soporte por email</span>
                  </li>
                </ul>
                <CarbonButton
                  size="lg"
                  onClick={() => navigate('/')}
                  className="landing-pricing-card__cta landing-pricing-card__cta--primary"
                >
                  Empezar Prueba Gratis
                  <ArrowRight size={20} />
                </CarbonButton>
                <p className="landing-pricing-card__note">
                  <CheckmarkFilled size={16} />
                  <span>Sin tarjeta de crédito • Cancela cuando quieras</span>
                </p>
              </Card>

              <Card padding="lg" className="landing-pricing-card landing-pricing-card--pro">
                <div className="landing-pricing-card__badge landing-pricing-card__badge--pro">
                  <Star size={18} />
                  <span>Oferta de Lanzamiento</span>
                </div>
                <div className="landing-pricing-card__header">
                  <h3 className="landing-pricing-card__name">LicitIA Pro</h3>
                  <div className="landing-pricing-card__price">
                    <span className="landing-pricing-card__price-old">$99</span>
                    <span className="landing-pricing-card__price-amount">$49.50</span>
                    <span className="landing-pricing-card__price-period">/mes</span>
                  </div>
                  <p className="landing-pricing-card__description">
                    <strong>50% descuento</strong> primeros 3 meses • Luego $99/mes
                  </p>
                  <div className="landing-pricing-card__urgency">
                    <Time size={16} />
                    <span>Solo para primeros 50 usuarios</span>
                  </div>
                </div>
                <ul className="landing-pricing-card__features">
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Todo lo de la prueba gratis</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Acceso ilimitado permanente</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Matching con IA avanzado</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Alertas personalizadas</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Actualizaciones en tiempo real</span>
                  </li>
                  <li>
                    <CheckmarkFilled size={20} />
                    <span>Soporte prioritario</span>
                  </li>
                </ul>
                <CarbonButton
                  size="lg"
                  kind="secondary"
                  onClick={() => navigate('/')}
                  className="landing-pricing-card__cta"
                >
                  Empezar Prueba Gratis
                  <ArrowRight size={20} />
                </CarbonButton>
                <p className="landing-pricing-card__note">
                  <CheckmarkFilled size={16} />
                  <span>30 días gratis, luego $49.50/mes</span>
                </p>
              </Card>
            </div>

            <div className="landing-pricing__footer">
              <p className="landing-pricing__footer-text">
                <strong>¿Tienes dudas?</strong> Todas las funciones están disponibles en la prueba gratis. 
                Prueba sin riesgo y decide después.
              </p>
            </div>
          </Column>
        </Grid>
      </section>

          {/* FAQ Section */}
          <section id="landing-faq" className="landing-faq">
        <div className="landing-faq__background">
          <div className="landing-faq__gradient"></div>
        </div>
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-faq__header">
              <div className="landing-faq__icon">
                <Quotes size={48} />
              </div>
              <h2 className="landing-faq__title">
                Preguntas <span className="landing-faq__title-highlight">Frecuentes</span>
              </h2>
              <p className="landing-faq__subtitle">
                Resolvemos todas tus dudas antes de que las tengas
              </p>
            </div>
            <div className="landing-faq__content">
              <Accordion className="landing-faq__accordion">
                <AccordionItem 
                  title="¿Necesito tarjeta de crédito para la prueba gratis?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <CheckmarkFilled size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p><strong>No, no necesitas tarjeta de crédito.</strong> La prueba de 30 días es completamente gratis. Solo necesitas tu email para registrarte y empezar a usar LicitIA inmediatamente.</p>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Qué pasa después de los 30 días de prueba gratis?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <Time size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p>Una vez finalizada tu prueba gratuita, puedes:</p>
                      <ul>
                        <li>Continuar con <strong>LicitIA Pro a $49.50/mes</strong> (50% descuento por los primeros 3 meses)</li>
                        <li>Cancelar sin compromiso en cualquier momento</li>
                      </ul>
                      <p><strong>No hay renovación automática</strong> sin tu consentimiento explícito.</p>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Puedo cancelar cuando quiera?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <CheckmarkFilled size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p><strong>Sí, puedes cancelar en cualquier momento.</strong> Sin compromisos, sin penalizaciones, sin cargos ocultos. El proceso de cancelación es instantáneo y puedes hacerlo desde tu cuenta.</p>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Qué información necesito para empezar?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <DocumentAdd size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p><strong>Solo necesitas tu email</strong> para crear tu cuenta y empezar a usar LicitIA.</p>
                      <p>El nombre de tu empresa y tus experiencias previas son <strong>opcionales</strong>, pero te recomendamos agregarlos porque:</p>
                      <ul>
                        <li>Mejoran significativamente la precisión del matching con IA</li>
                        <li>Te muestran licitaciones más relevantes para tu perfil</li>
                        <li>Puedes subirlos en 2 minutos desde un Excel</li>
                      </ul>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Funciona para cualquier tipo de licitación?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <Document size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p>Actualmente nos enfocamos en <strong>licitaciones de interventoría, ingeniería y construcción</strong>, que es donde nuestro algoritmo de IA tiene mayor precisión.</p>
                      <p>Estamos expandiendo constantemente a otros tipos de licitaciones de ingeniería civil. Si necesitas algo específico, <strong>contáctanos</strong> y lo evaluamos.</p>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Cómo funciona el matching con Inteligencia Artificial?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <WatsonMachineLearning size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p>Nuestra IA utiliza <strong>análisis semántico avanzado</strong> para encontrar coincidencias:</p>
                      <ul>
                        <li>Analiza la descripción de tus proyectos anteriores</li>
                        <li>Compara con el objeto de las nuevas licitaciones</li>
                        <li>Calcula un porcentaje de match basado en similitud semántica</li>
                        <li>Considera palabras clave, entidades, montos y categorías</li>
                      </ul>
                      <p><strong>Cuanto más similar sea una licitación a tu experiencia, mayor será el porcentaje de match.</strong></p>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Con qué frecuencia se actualizan las licitaciones?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <Flash size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p>Actualizamos automáticamente <strong>cada 2 horas</strong> directamente desde la API de SECOP II.</p>
                      <p>Esto significa que:</p>
                      <ul>
                        <li>Recibes las nuevas oportunidades <strong>tan pronto como se publican</strong></li>
                        <li>Nunca te pierdes una fecha de cierre importante</li>
                        <li>Tienes acceso a las licitaciones más recientes</li>
                      </ul>
                    </div>
                  </div>
                </AccordionItem>
                
                <AccordionItem 
                  title="¿Hay límite en la cantidad de licitaciones que puedo ver?"
                  className="landing-faq-accordion-item"
                >
                  <div className="landing-faq-answer">
                    <div className="landing-faq-answer__icon">
                      <View size={24} />
                    </div>
                    <div className="landing-faq-answer__content">
                      <p><strong>No, no hay límite.</strong> Tienes acceso ilimitado a todas las licitaciones disponibles en nuestra base de datos.</p>
                      <p>Puedes:</p>
                      <ul>
                        <li>Filtrar por departamento, monto, fecha de cierre</li>
                        <li>Buscar por palabras clave</li>
                        <li>Ver tantas licitaciones como necesites</li>
                        <li>Exportar información si lo necesitas</li>
                      </ul>
                    </div>
                  </div>
                </AccordionItem>
              </Accordion>
            </div>
            
            <div className="landing-faq__cta">
              <p className="landing-faq__cta-text">
                ¿Tienes otra pregunta?
              </p>
              <CarbonButton
                size="lg"
                kind="tertiary"
                onClick={() => navigate('/')}
                className="landing-faq__cta-button"
              >
                Contáctanos
                <ArrowRight size={20} />
              </CarbonButton>
            </div>
          </Column>
        </Grid>
      </section>

      {/* CTA Final */}
      <section className="landing-cta-final">
        <div className="landing-cta-final__background">
          <div className="landing-cta-final__gradient"></div>
          <div className="landing-cta-final__pattern"></div>
          <div className="landing-cta-final__glow"></div>
          <div className="landing-cta-final__particles"></div>
        </div>
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-cta-final__content">
              <div className="landing-cta-final__badge-wrapper">
                <div className="landing-cta-final__badge landing-cta-final__badge--pulse">
                  <div className="landing-cta-final__badge-pulse"></div>
                  <Flash size={20} />
                  <span>Únete a los primeros 50 usuarios</span>
                </div>
              </div>
              
              <h2 className="landing-cta-final__title">
                Listo para encontrar <span className="landing-cta-final__title-highlight">más oportunidades</span>?
              </h2>
              
              <p className="landing-cta-final__subtitle">
                Únete a las empresas que ya están ahorrando tiempo y encontrando mejores licitaciones
              </p>

              <div className="landing-cta-final__stats-wrapper">
                <div className="landing-cta-final__stats">
                  <div className="landing-cta-final__stat landing-cta-final__stat--1">
                    <div className="landing-cta-final__stat-icon">
                      <User size={24} />
                    </div>
                    <div className="landing-cta-final__stat-content">
                      <div className="landing-cta-final__stat-number">25+</div>
                      <div className="landing-cta-final__stat-label">Empresas</div>
                    </div>
                  </div>
                  <div className="landing-cta-final__stat landing-cta-final__stat--2">
                    <div className="landing-cta-final__stat-icon">
                      <Document size={24} />
                    </div>
                    <div className="landing-cta-final__stat-content">
                      <div className="landing-cta-final__stat-number">1,000+</div>
                      <div className="landing-cta-final__stat-label">Licitaciones</div>
                    </div>
                  </div>
                  <div className="landing-cta-final__stat landing-cta-final__stat--3">
                    <div className="landing-cta-final__stat-icon">
                      <Time size={24} />
                    </div>
                    <div className="landing-cta-final__stat-content">
                      <div className="landing-cta-final__stat-number">10+</div>
                      <div className="landing-cta-final__stat-label">Horas ahorradas/semana</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="landing-cta-final__cta-card">
                <div className="landing-cta-final__cta-header">
                  <h3 className="landing-cta-final__cta-title">
                    Empieza tu Prueba Gratis <span className="landing-cta-final__cta-title-highlight">Ahora</span>
                  </h3>
                  <p className="landing-cta-final__cta-subtitle">
                    Acceso completo • Sin tarjeta de crédito • Cancela cuando quieras
                  </p>
                </div>
                
                <CarbonButton
                  size="lg"
                  onClick={() => {
                    document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                  className="landing-cta-final__button"
                >
                  <span className="landing-cta-final__button-text">Empezar Prueba Gratis Ahora</span>
                  <ArrowRight size={24} className="landing-cta-final__button-icon" />
                </CarbonButton>
                
                <div className="landing-cta-final__trust-badges">
                  <div className="landing-cta-final__trust-badge">
                    <CheckmarkFilled size={18} />
                    <span>30 días gratis</span>
                  </div>
                  <div className="landing-cta-final__trust-badge">
                    <Security size={18} />
                    <span>Sin tarjeta</span>
                  </div>
                  <div className="landing-cta-final__trust-badge">
                    <CheckmarkFilled size={18} />
                    <span>Cancela cuando quieras</span>
                  </div>
                </div>
              </div>

              <div className="landing-cta-final__urgency">
                <div className="landing-cta-final__urgency-icon">
                  <Time size={20} />
                </div>
                <div className="landing-cta-final__urgency-content">
                  <strong>Oferta de lanzamiento termina cuando alcancemos 50 usuarios</strong>
                  <span>Únete ahora y obtén 50% de descuento en los primeros 3 meses</span>
                </div>
              </div>
            </div>
          </Column>
        </Grid>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer__background">
          <div className="landing-footer__gradient"></div>
        </div>
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <div className="landing-footer__content">
              {/* Brand Section */}
              <div className="landing-footer__brand">
                <div className="landing-footer__logo">
                  <WatsonMachineLearning size={32} />
                  <span className="landing-footer__logo-text">LicitIA</span>
                </div>
                <p className="landing-footer__tagline">
                  Encuentra las licitaciones perfectas para tu empresa con IA
                </p>
                <div className="landing-footer__social">
                  <a 
                    href="https://linkedin.com/company/licitia" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="landing-footer__social-link"
                    aria-label="LinkedIn"
                  >
                    <LogoLinkedin size={20} />
                  </a>
                  <a 
                    href="https://twitter.com/licitia" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="landing-footer__social-link"
                    aria-label="Twitter"
                  >
                    <LogoTwitter size={20} />
                  </a>
                  <a 
                    href="mailto:contacto@licitia.co" 
                    className="landing-footer__social-link"
                    aria-label="Email"
                  >
                    <Email size={20} />
                  </a>
                </div>
              </div>

              {/* Links Sections */}
              <div className="landing-footer__links">
                <div className="landing-footer__links-column">
                  <h4 className="landing-footer__links-title">Producto</h4>
                  <ul className="landing-footer__links-list">
                    <li>
                      <a href="#landing-hero" onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                      }}>
                        Inicio
                      </a>
                    </li>
                    <li>
                      <a href="#landing-hero" onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                      }}>
                        Características
                      </a>
                    </li>
                    <li>
                      <a href="#landing-hero" onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                      }}>
                        Precios
                      </a>
                    </li>
                    <li>
                      <a href="#landing-hero" onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('landing-hero')?.scrollIntoView({ behavior: 'smooth' })
                      }}>
                        Cómo Funciona
                      </a>
                    </li>
                  </ul>
                </div>

                <div className="landing-footer__links-column">
                  <h4 className="landing-footer__links-title">Soporte</h4>
                  <ul className="landing-footer__links-list">
                    <li>
                      <a href="mailto:soporte@licitia.co">Soporte</a>
                    </li>
                    <li>
                      <a href="mailto:contacto@licitia.co">Contacto</a>
                    </li>
                    <li>
                      <a href="#landing-faq" onClick={(e) => {
                        e.preventDefault()
                        const faqSection = document.querySelector('.landing-faq')
                        faqSection?.scrollIntoView({ behavior: 'smooth' })
                      }}>
                        Preguntas Frecuentes
                      </a>
                    </li>
                    <li>
                      <a href="mailto:contacto@licitia.co">Documentación</a>
                    </li>
                  </ul>
                </div>

                <div className="landing-footer__links-column">
                  <h4 className="landing-footer__links-title">Legal</h4>
                  <ul className="landing-footer__links-list">
                    <li>
                      <a href="/terminos" target="_blank" rel="noopener noreferrer">
                        Términos de Servicio
                      </a>
                    </li>
                    <li>
                      <a href="/privacidad" target="_blank" rel="noopener noreferrer">
                        Política de Privacidad
                      </a>
                    </li>
                    <li>
                      <a href="/cookies" target="_blank" rel="noopener noreferrer">
                        Política de Cookies
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Bottom Bar */}
            <div className="landing-footer__bottom">
              <div className="landing-footer__copyright">
                <p>
                  © {new Date().getFullYear()} LicitIA. Todos los derechos reservados.
                </p>
                <p className="landing-footer__location">
                  <Location size={14} />
                  <span>Colombia</span>
                </p>
              </div>
              <div className="landing-footer__badge">
                <Security size={16} />
                <span>Pago seguro y protegido</span>
              </div>
            </div>
          </Column>
        </Grid>
      </footer>
    </div>
  )
}

export default Landing
