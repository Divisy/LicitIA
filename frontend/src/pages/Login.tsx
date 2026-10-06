import React, { useMemo, useState } from 'react'
import { useNavigate, Link, useLocation, useSearchParams } from 'react-router-dom'
import {
  Grid,
  Column,
  TextInput,
  Button as CarbonButton,
  InlineNotification,
  Tile,
} from '@carbon/react'
import { WatsonMachineLearning, ArrowRight, ArrowLeft } from '@carbon/icons-react'
import { formatApiError, requestLoginCode, verifyLoginCode } from '../api/client'
import { persistLeadSession } from '../utils/userSession'
import './Login.scss'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const presetEmail = searchParams.get('email') || ''
  const accountExists = Boolean(
    (location.state as { accountExists?: boolean } | null)?.accountExists
  )

  const [email, setEmail] = useState(presetEmail)
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'email' | 'code'>('email')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [unknownEmail, setUnknownEmail] = useState(false)
  const [debugCode, setDebugCode] = useState<string | null>(null)
  const [emailSent, setEmailSent] = useState(false)

  const signupLink = useMemo(
    () => (email.trim() ? `/?email=${encodeURIComponent(email.trim())}` : '/'),
    [email]
  )

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setUnknownEmail(false)
    setLoading(true)
    try {
      const result = await requestLoginCode(email.trim())
      if (!result.exists) {
        setUnknownEmail(true)
        return
      }
      setEmailSent(Boolean(result.email_sent))
      setDebugCode(result.debug_code || null)
      if (result.debug_code) {
        setCode(result.debug_code)
      }
      setStep('code')
    } catch (err: unknown) {
      setError(formatApiError(err, 'No se pudo enviar el código. Inténtalo de nuevo.'))
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await verifyLoginCode(email.trim(), code.trim())
      if (!result.exists || !result.lead) {
        setUnknownEmail(true)
        setStep('email')
        return
      }
      persistLeadSession(result.lead, { returning: true })
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(formatApiError(err, 'Código incorrecto. Inténtalo de nuevo.'))
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
              <h2 className="login-heading">Bienvenido de nuevo</h2>
              <p className="login-description">
                {step === 'email'
                  ? 'Ingresa tu correo y te enviamos un código de un solo uso.'
                  : emailSent
                    ? `Enviamos un código a ${email}. Caduca en 10 minutos.`
                    : 'El correo no se pudo enviar. Usa el código que aparece en pantalla.'}
              </p>
            </div>

            {accountExists && step === 'email' && (
              <InlineNotification
                kind="info"
                title="Esta cuenta ya está"
                subtitle="Entra con tu correo para continuar."
                lowContrast
                className="login-notification"
                hideCloseButton
              />
            )}

            {step === 'email' ? (
              <form onSubmit={handleRequestCode} className="login-form">
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
                  {loading ? 'Enviando...' : 'Enviar código'}
                </CarbonButton>

                {unknownEmail && (
                  <InlineNotification
                    kind="warning"
                    title="No hay cuenta con este correo"
                    subtitle="Crea tu cuenta para entrar al radar."
                    lowContrast
                    className="login-notification"
                    hideCloseButton
                  />
                )}

                {error && (
                  <InlineNotification
                    kind="error"
                    title="Error"
                    subtitle={error}
                    lowContrast
                    className="login-notification"
                    onClose={() => setError(null)}
                  />
                )}

                <div className="login-footer">
                  <p className="login-footer-text">
                    ¿No tienes cuenta?{' '}
                    <Link to={signupLink} className="login-link">
                      Crear cuenta
                    </Link>
                  </p>
                  <Link to="/" className="login-back-link">
                    <ArrowLeft size={16} />
                    Volver a la landing
                  </Link>
                </div>
              </form>
            ) : (
              <form onSubmit={handleVerify} className="login-form">
                <TextInput
                  id="code-login"
                  labelText="Código"
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  size="lg"
                  className="login-input"
                  autoFocus
                />

                {debugCode && !emailSent && (
                  <InlineNotification
                    kind="info"
                    title="Usa este código"
                    subtitle={debugCode}
                    lowContrast
                    className="login-notification"
                    hideCloseButton
                  />
                )}

                <CarbonButton
                  type="submit"
                  size="lg"
                  renderIcon={ArrowRight}
                  disabled={loading || code.length !== 6}
                  className="login-button"
                >
                  {loading ? 'Verificando...' : 'Entrar'}
                </CarbonButton>

                {error && (
                  <InlineNotification
                    kind="error"
                    title="Error"
                    subtitle={error}
                    lowContrast
                    className="login-notification"
                    onClose={() => setError(null)}
                  />
                )}

                <div className="login-footer">
                  <button
                    type="button"
                    className="login-link login-resend"
                    onClick={() => {
                      setStep('email')
                      setCode('')
                      setDebugCode(null)
                      setEmailSent(false)
                      setError(null)
                    }}
                  >
                    Usar otro correo o pedir otro código
                  </button>
                </div>
              </form>
            )}
          </Tile>
        </Column>
      </Grid>
    </div>
  )
}

export default Login
