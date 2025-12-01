import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { 
  Grid, 
  Column, 
  TextInput, 
  Button as CarbonButton,
  InlineNotification,
  Tile
} from '@carbon/react'
import { 
  WatsonMachineLearning,
  ArrowRight,
  ArrowLeft
} from '@carbon/icons-react'
import { checkLeadExists } from '../api/client'
import './Login.scss'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Verificar si el email existe en el sistema
      const checkResult = await checkLeadExists(email)
      
      if (checkResult.exists && checkResult.lead) {
        // Email existe, cargar información del usuario
        localStorage.setItem('licitia_user_email', checkResult.lead.email)
        
        if (checkResult.lead.name) {
          localStorage.setItem('licitia_user_name', checkResult.lead.name)
        }
        if (checkResult.lead.company) {
          localStorage.setItem('licitia_user_company', checkResult.lead.company)
        }
        if (checkResult.lead.industry) {
          localStorage.setItem('licitia_user_industry', checkResult.lead.industry)
        }
        if (checkResult.lead.company_size) {
          localStorage.setItem('licitia_user_company_size', checkResult.lead.company_size)
        }
        if (checkResult.lead.role) {
          localStorage.setItem('licitia_user_role', checkResult.lead.role)
        }
        
        // No iniciar onboarding para usuarios existentes
        localStorage.removeItem('licitia_start_onboarding')
        
        // Redirigir al dashboard
        navigate('/dashboard')
      } else {
        // Email no existe, sugerir registro
        setError('Este email no está registrado. Por favor, regístrate primero.')
      }
    } catch (err: any) {
      console.error('Error checking lead:', err)
      setError(err?.response?.data?.detail || err?.message || 'Error al verificar el email. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-background"></div>
      <Grid className="login-grid">
        <Column lg={8} md={4} sm={4} className="login-column">
          <Tile className="login-card">
            <div className="login-header">
              <div className="login-logo">
                <WatsonMachineLearning size={32} />
                <h1 className="login-title">LicitIA</h1>
              </div>
              <h2 className="login-heading">
                Bienvenido de nuevo
              </h2>
              <p className="login-description">
                Ingresa tu email para acceder a tu cuenta
              </p>
            </div>

            <form onSubmit={handleSubmit} className="login-form">
              <TextInput
                id="email-login"
                type="email"
                labelText="Correo electrónico"
                placeholder="tu@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                size="lg"
                className="login-input"
                autoFocus
              />

              <CarbonButton
                type="submit"
                size="lg"
                renderIcon={ArrowRight}
                disabled={loading}
                className="login-button"
              >
                {loading ? 'Verificando...' : 'Iniciar sesión'}
              </CarbonButton>

              {error && (
                <InlineNotification
                  kind="error"
                  title="Error"
                  subtitle={error}
                  lowContrast={true}
                  className="login-notification"
                  onClose={() => setError(null)}
                />
              )}

              <div className="login-footer">
                <p className="login-footer-text">
                  ¿No tienes cuenta?{' '}
                  <Link to="/landing" className="login-link">
                    Regístrate gratis
                  </Link>
                </p>
                <Link to="/landing" className="login-back-link">
                  <ArrowLeft size={16} />
                  Volver a la landing
                </Link>
              </div>
            </form>
          </Tile>
        </Column>
      </Grid>
    </div>
  )
}

export default Login

