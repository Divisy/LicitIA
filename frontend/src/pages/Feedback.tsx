import React, { useState, useEffect } from 'react'
import { 
  Grid, 
  Column, 
  TextInput, 
  TextArea,
  Button,
  Select,
  SelectItem,
  InlineNotification,
  Tile,
  RadioButtonGroup,
  RadioButton,
  Tag
} from '@carbon/react'
import { 
  Chat,
  Send,
  CheckmarkFilled,
  Information,
  Idea,
  Warning,
  User,
  ThumbsUp,
  ThumbsDown
} from '@carbon/icons-react'
import Logo from '../components/Logo'
import { createFeedback, getFeedback, FeedbackType, FeedbackResponse } from '../api/client'
import './Feedback.scss'

const Feedback: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'nps' | 'feature' | 'bug' | 'general' | 'usability'>('nps')
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    company: '',
    message: '',
    npsScore: 0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [myFeedback, setMyFeedback] = useState<FeedbackResponse[]>([])

  useEffect(() => {
    const savedEmail = localStorage.getItem('licitia_user_email')
    const savedName = localStorage.getItem('licitia_user_name')
    const savedCompany = localStorage.getItem('licitia_user_company')

    if (savedEmail) {
      setFormData(prev => ({
        ...prev,
        email: savedEmail,
        name: savedName || '',
        company: savedCompany || '',
      }))
      
      loadMyFeedback(savedEmail)
    }
  }, [])

  const loadMyFeedback = async (email: string) => {
    try {
      const feedbacks = await getFeedback(email)
      setMyFeedback(feedbacks)
    } catch (err) {
      console.error('Error loading feedback:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!formData.email || !formData.message.trim()) {
      setError('Por favor completa todos los campos requeridos')
      setLoading(false)
      return
    }

    if (activeTab === 'nps' && formData.npsScore === 0) {
      setError('Por favor selecciona una puntuación')
      setLoading(false)
      return
    }

    try {
      await createFeedback({
        email: formData.email,
        name: formData.name || undefined,
        company: formData.company || undefined,
        type: activeTab,
        score: activeTab === 'nps' ? formData.npsScore : undefined,
        message: formData.message.trim(),
        context: {
          page: window.location.pathname,
        },
      })

      setSuccess(true)
      setFormData(prev => ({ ...prev, message: '', npsScore: 0 }))
      
      if (formData.email) {
        loadMyFeedback(formData.email)
      }

      setTimeout(() => setSuccess(false), 5000)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Error al enviar feedback')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('es-CO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'nps': return <ThumbsUp size={16} />
      case 'feature_request': return <Idea size={16} />
      case 'bug_report': return <Warning size={16} />
      case 'usability': return <User size={16} />
      default: return <Chat size={16} />
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'nps': return 'NPS'
      case 'feature_request': return 'Funcionalidad'
      case 'bug_report': return 'Error'
      case 'usability': return 'Usabilidad'
      default: return 'General'
    }
  }

  return (
    <div className="feedback-page">
      <Grid className="feedback-grid">
        <Column lg={16} md={8} sm={4}>
          <div className="feedback-header">
            <Logo size="md" showText={true} />
            <div className="feedback-header__content">
              <h1 className="feedback-title">Feedback y Sugerencias</h1>
              <p className="feedback-subtitle">
                Tu opinión es valiosa. Ayúdanos a mejorar LicitIA compartiendo tus ideas, reportando problemas o dándonos tu opinión.
              </p>
            </div>
          </div>
        </Column>
      </Grid>

      <Grid className="feedback-grid">
        <Column lg={10} md={4} sm={4}>
          <Tile className="feedback-form-tile">
            <div className="feedback-tabs">
              <button
                className={`feedback-tab ${activeTab === 'nps' ? 'feedback-tab--active' : ''}`}
                onClick={() => setActiveTab('nps')}
              >
                <ThumbsUp size={20} />
                <span>NPS</span>
              </button>
              <button
                className={`feedback-tab ${activeTab === 'feature' ? 'feedback-tab--active' : ''}`}
                onClick={() => setActiveTab('feature')}
              >
                <Idea size={20} />
                <span>Funcionalidad</span>
              </button>
              <button
                className={`feedback-tab ${activeTab === 'bug' ? 'feedback-tab--active' : ''}`}
                onClick={() => setActiveTab('bug')}
              >
                <Warning size={20} />
                <span>Error</span>
              </button>
              <button
                className={`feedback-tab ${activeTab === 'usability' ? 'feedback-tab--active' : ''}`}
                onClick={() => setActiveTab('usability')}
              >
                <User size={20} />
                <span>Usabilidad</span>
              </button>
              <button
                className={`feedback-tab ${activeTab === 'general' ? 'feedback-tab--active' : ''}`}
                onClick={() => setActiveTab('general')}
              >
                <Chat size={20} />
                <span>General</span>
              </button>
            </div>

            {success && (
              <InlineNotification
                kind="success"
                title="¡Gracias por tu feedback!"
                subtitle="Tu mensaje ha sido enviado exitosamente. Lo revisaremos pronto."
                lowContrast={false}
                className="feedback-notification"
                onClose={() => setSuccess(false)}
              />
            )}

            {error && (
              <InlineNotification
                kind="error"
                title="Error"
                subtitle={error}
                lowContrast={false}
                className="feedback-notification"
                onClose={() => setError(null)}
              />
            )}

            <form onSubmit={handleSubmit} className="feedback-form">
              {activeTab === 'nps' && (
                <div className="feedback-nps-section">
                  <h3 className="feedback-nps-title">
                    ¿Qué tan probable es que recomiendes LicitIA a un colega?
                  </h3>
                  <RadioButtonGroup
                    name="nps-score"
                    valueSelected={formData.npsScore}
                    onChange={(value) => setFormData({ ...formData, npsScore: parseInt(value) })}
                    className="feedback-nps-radio"
                  >
                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
                      <RadioButton
                        key={score}
                        labelText={score.toString()}
                        value={score}
                        id={`nps-${score}`}
                      />
                    ))}
                  </RadioButtonGroup>
                  <div className="feedback-nps-labels">
                    <span>Muy improbable</span>
                    <span>Muy probable</span>
                  </div>
                </div>
              )}

              <TextInput
                id="email"
                type="email"
                labelText="Correo electrónico *"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                size="lg"
                className="feedback-input"
              />

              <div className="feedback-form-row">
                <TextInput
                  id="name"
                  type="text"
                  labelText="Nombre"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  size="lg"
                  className="feedback-input"
                />

                <TextInput
                  id="company"
                  type="text"
                  labelText="Empresa"
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  size="lg"
                  className="feedback-input"
                />
              </div>

              <TextArea
                id="message"
                labelText={activeTab === 'nps' ? '¿Por qué elegiste esta puntuación? (opcional)' : 'Tu mensaje *'}
                placeholder={
                  activeTab === 'feature' ? 'Describe la funcionalidad que te gustaría ver...' :
                  activeTab === 'bug' ? 'Describe el error que encontraste...' :
                  activeTab === 'usability' ? 'Cuéntanos qué te resultó difícil o confuso...' :
                  'Tu comentario...'
                }
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                required={activeTab !== 'nps'}
                rows={6}
                className="feedback-textarea"
                maxLength={2000}
              />

              <div className="feedback-form-footer">
                <Button
                  type="submit"
                  size="lg"
                  renderIcon={Send}
                  disabled={loading}
                  className="feedback-submit-button"
                >
                  {loading ? 'Enviando...' : 'Enviar Feedback'}
                </Button>
                <p className="feedback-form-note">
                  <Information size={16} />
                  Todos los comentarios son revisados por nuestro equipo
                </p>
              </div>
            </form>
          </Tile>
        </Column>

        <Column lg={6} md={4} sm={4}>
          {myFeedback.length > 0 && (
            <Tile className="feedback-history-tile">
              <h2 className="feedback-history-title">Mi Feedback</h2>
              <div className="feedback-history-list">
                {myFeedback.slice(0, 5).map((item) => (
                  <div key={item.id} className="feedback-history-item">
                    <div className="feedback-history-header">
                      <div className="feedback-history-type">
                        {getTypeIcon(item.type)}
                        <span>{getTypeLabel(item.type)}</span>
                      </div>
                      {item.score !== null && item.score !== undefined && (
                        <Tag type="blue" size="sm">{item.score}/10</Tag>
                      )}
                    </div>
                    <p className="feedback-history-message">{item.message.substring(0, 100)}...</p>
                    <span className="feedback-history-date">{formatDate(item.created_at)}</span>
                  </div>
                ))}
              </div>
            </Tile>
          )}
        </Column>
      </Grid>
    </div>
  )
}

export default Feedback

