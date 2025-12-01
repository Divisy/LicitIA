import React, { useState } from 'react'
import { Button, Modal, TextArea, Select, SelectItem, InlineNotification, Tag } from '@carbon/react'
import { Chat, Close, Send, Idea, Warning, User, Star, CheckmarkFilled } from '@carbon/icons-react'
import { createFeedback, FeedbackType } from '../../api/client'
import './FeedbackWidget.scss'

interface FeedbackWidgetProps {
  context?: {
    page?: string
    action?: string
  }
}

const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ context }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>('general')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [messageLength, setMessageLength] = useState(0)

  const userEmail = localStorage.getItem('licitia_user_email') || ''
  const userName = localStorage.getItem('licitia_user_name') || ''
  const userCompany = localStorage.getItem('licitia_user_company') || ''

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) {
      setError('Por favor escribe tu mensaje')
      return
    }

    if (!userEmail) {
      setError('Por favor inicia sesión para enviar feedback')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await createFeedback({
        email: userEmail,
        name: userName || undefined,
        company: userCompany || undefined,
        type,
        message: message.trim(),
        context: {
          ...context,
          page: window.location.pathname,
        },
      })

      setSuccess(true)
      setMessage('')
      setMessageLength(0)
      
      // Close modal after 3 seconds
      setTimeout(() => {
        setIsOpen(false)
        setSuccess(false)
      }, 3000)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Error al enviar feedback')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        className="feedback-widget__button"
        onClick={() => setIsOpen(true)}
        aria-label="Enviar feedback"
        title="Enviar feedback"
      >
        <Chat size={20} />
        <span className="feedback-widget__button-text">Feedback</span>
      </button>

      <Modal
        open={isOpen}
        onRequestClose={() => {
          setIsOpen(false)
          setError(null)
          setSuccess(false)
          setMessage('')
          setMessageLength(0)
        }}
        modalHeading={success ? undefined : "Comparte tu feedback"}
        primaryButtonText=""
        secondaryButtonText=""
        onSecondarySubmit={() => setIsOpen(false)}
        onRequestSubmit={handleSubmit}
        primaryButtonDisabled={true}
        size="sm"
        className="feedback-widget__modal"
        hasScrollingContent={false}
        passiveModal={success}
      >
        <div className="feedback-widget__content">
          {success ? (
            <div className="feedback-widget__success">
              <div className="feedback-widget__success-icon">
                <CheckmarkFilled size={48} />
              </div>
              <h3 className="feedback-widget__success-title">¡Gracias por tu feedback!</h3>
              <p className="feedback-widget__success-message">
                Tu opinión es muy valiosa para nosotros. La revisaremos pronto y trabajaremos en mejorar LicitIA.
              </p>
              <div className="feedback-widget__success-badge">
                <Star size={16} />
                <span>¡Eres parte del futuro de LicitIA!</span>
              </div>
            </div>
          ) : (
            <>
              <div className="feedback-widget__header">
                <div className="feedback-widget__header-icon">
                  <Chat size={24} />
                </div>
                <div className="feedback-widget__header-text">
                  <p className="feedback-widget__subtitle">
                    Tu opinión nos ayuda a construir un mejor producto para todos
                  </p>
                </div>
              </div>

              {error && (
                <InlineNotification
                  kind="error"
                  title="Error"
                  subtitle={error}
                  lowContrast={false}
                  className="feedback-widget__notification"
                  onClose={() => setError(null)}
                />
              )}

              <div className="feedback-widget__type-selector">
                <label className="feedback-widget__type-label">¿Qué tipo de feedback tienes?</label>
                <div className="feedback-widget__type-options">
                  <button
                    type="button"
                    className={`feedback-widget__type-option ${type === 'feature_request' ? 'feedback-widget__type-option--active' : ''}`}
                    onClick={() => setType('feature_request')}
                  >
                    <Idea size={20} />
                    <span>Idea</span>
                  </button>
                  <button
                    type="button"
                    className={`feedback-widget__type-option ${type === 'bug_report' ? 'feedback-widget__type-option--active' : ''}`}
                    onClick={() => setType('bug_report')}
                  >
                    <Warning size={20} />
                    <span>Error</span>
                  </button>
                  <button
                    type="button"
                    className={`feedback-widget__type-option ${type === 'usability' ? 'feedback-widget__type-option--active' : ''}`}
                    onClick={() => setType('usability')}
                  >
                    <User size={20} />
                    <span>Usabilidad</span>
                  </button>
                  <button
                    type="button"
                    className={`feedback-widget__type-option ${type === 'general' ? 'feedback-widget__type-option--active' : ''}`}
                    onClick={() => setType('general')}
                  >
                    <Chat size={20} />
                    <span>General</span>
                  </button>
                </div>
              </div>

              <div className="feedback-widget__message-section">
                <label htmlFor="feedback-message" className="feedback-widget__message-label">
                  Cuéntanos más
                  {messageLength > 0 && (
                    <span className="feedback-widget__message-counter">
                      {messageLength}/2000
                    </span>
                  )}
                </label>
                <TextArea
                  id="feedback-message"
                  placeholder={
                    type === 'feature_request' 
                      ? '💡 ¿Qué funcionalidad te gustaría ver en LicitIA? Describe tu idea...'
                      : type === 'bug_report'
                      ? '🐛 Describe el error que encontraste. ¿Qué estabas haciendo cuando ocurrió?'
                      : type === 'usability'
                      ? '🎨 ¿Qué te resultó confuso o difícil de usar? ¿Cómo lo mejorarías?'
                      : '💬 Comparte tus pensamientos, sugerencias o cualquier comentario que tengas...'
                  }
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value)
                    setMessageLength(e.target.value.length)
                  }}
                  rows={6}
                  className="feedback-widget__textarea"
                  maxLength={2000}
                />
              </div>

              <div className="feedback-widget__motivation">
                <Star size={16} />
                <span>Tu feedback puede convertirse en la próxima funcionalidad de LicitIA</span>
              </div>

              <div className="feedback-widget__actions">
                <Button
                  kind="secondary"
                  size="lg"
                  onClick={() => {
                    setIsOpen(false)
                    setError(null)
                    setMessage('')
                    setMessageLength(0)
                  }}
                  className="feedback-widget__cancel-button"
                >
                  Cancelar
                </Button>
                <Button
                  kind="primary"
                  size="lg"
                  onClick={handleSubmit}
                  disabled={loading || !message.trim()}
                  renderIcon={Send}
                  className="feedback-widget__submit-button"
                >
                  {loading ? 'Enviando...' : 'Enviar Feedback'}
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </>
  )
}

export default FeedbackWidget

