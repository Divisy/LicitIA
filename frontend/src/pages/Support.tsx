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
  Loading
} from '@carbon/react'
import { 
  Help,
  Send,
  CheckmarkFilled,
  Information,
  Email,
  Phone,
  Time
} from '@carbon/icons-react'
import Logo from '../components/Logo'
import { createSupportTicket, getSupportTickets, SupportTicketResponse } from '../api/client'
import './Support.scss'

const Support: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    company: '',
    subject: '',
    message: '',
    category: 'general' as const,
    priority: 'medium' as const,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [ticketNumber, setTicketNumber] = useState<string | null>(null)
  const [myTickets, setMyTickets] = useState<SupportTicketResponse[]>([])
  const [loadingTickets, setLoadingTickets] = useState(false)

  // Load user info from localStorage
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
      
      // Load user's tickets
      loadMyTickets(savedEmail)
    }
  }, [])

  const loadMyTickets = async (email: string) => {
    setLoadingTickets(true)
    try {
      const tickets = await getSupportTickets(email)
      setMyTickets(tickets)
    } catch (err) {
      console.error('Error loading tickets:', err)
      // Don't show error, just silently fail
    } finally {
      setLoadingTickets(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!formData.email || !formData.subject || !formData.message) {
      setError('Por favor completa todos los campos requeridos')
      setLoading(false)
      return
    }

    try {
      const ticket = await createSupportTicket({
        email: formData.email,
        name: formData.name || undefined,
        company: formData.company || undefined,
        subject: formData.subject,
        message: formData.message,
        category: formData.category,
        priority: formData.priority,
      })

      setTicketNumber(ticket.ticket_number)
      setSuccess(true)
      
      // Reload tickets
      if (formData.email) {
        loadMyTickets(formData.email)
      }

      // Reset form
      setFormData(prev => ({
        ...prev,
        subject: '',
        message: '',
        category: 'general',
        priority: 'medium',
      }))
    } catch (err: any) {
      console.error('Error creating ticket:', err)
      setError(err?.response?.data?.detail || err?.message || 'Error al crear el ticket. Intenta de nuevo.')
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

  const getStatusTagKind = (status: string): 'green' | 'red' | 'yellow' | 'gray' => {
    const statusLower = status.toLowerCase()
    if (statusLower === 'resolved' || statusLower === 'closed') {
      return 'green'
    } else if (statusLower === 'in_progress') {
      return 'yellow'
    } else if (statusLower === 'open') {
      return 'blue'
    }
    return 'gray'
  }

  const getPriorityTagKind = (priority: string): 'green' | 'red' | 'yellow' | 'gray' => {
    const priorityLower = priority.toLowerCase()
    if (priorityLower === 'urgent') {
      return 'red'
    } else if (priorityLower === 'high') {
      return 'yellow'
    } else if (priorityLower === 'medium') {
      return 'blue'
    }
    return 'gray'
  }

  return (
    <div className="support-page">
      <Grid className="support-grid">
        <Column lg={16} md={8} sm={4}>
          <div className="support-header">
            <Logo size="md" showText={true} />
            <div className="support-header__content">
              <h1 className="support-title">Centro de Soporte</h1>
              <p className="support-subtitle">
                Estamos aquí para ayudarte. Crea un ticket y nuestro equipo te responderá pronto.
              </p>
            </div>
          </div>
        </Column>
      </Grid>

      <Grid className="support-grid">
        <Column lg={8} md={4} sm={4}>
          <Tile className="support-form-tile">
            <div className="support-form-header">
              <Help size={24} className="support-form-icon" />
              <h2 className="support-form-title">Crear Ticket de Soporte</h2>
            </div>

            {success && ticketNumber && (
              <InlineNotification
                kind="success"
                title="¡Ticket creado exitosamente!"
                subtitle={`Tu ticket número es: ${ticketNumber}. Te contactaremos pronto.`}
                lowContrast={false}
                className="support-notification"
                onClose={() => {
                  setSuccess(false)
                  setTicketNumber(null)
                }}
              />
            )}

            {error && (
              <InlineNotification
                kind="error"
                title="Error"
                subtitle={error}
                lowContrast={false}
                className="support-notification"
                onClose={() => setError(null)}
              />
            )}

            <form onSubmit={handleSubmit} className="support-form">
              <TextInput
                id="email"
                type="email"
                labelText="Correo electrónico *"
                placeholder="tu@empresa.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                size="lg"
                className="support-input"
              />

              <div className="support-form-row">
                <TextInput
                  id="name"
                  type="text"
                  labelText="Nombre"
                  placeholder="Tu nombre"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  size="lg"
                  className="support-input"
                />

                <TextInput
                  id="company"
                  type="text"
                  labelText="Empresa"
                  placeholder="Tu empresa"
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  size="lg"
                  className="support-input"
                />
              </div>

              <TextInput
                id="subject"
                type="text"
                labelText="Asunto *"
                placeholder="Resumen breve de tu consulta"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                required
                size="lg"
                className="support-input"
                maxLength={500}
              />

              <div className="support-form-row">
                <Select
                  id="category"
                  labelText="Categoría"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value as any })}
                  size="lg"
                  className="support-select"
                >
                  <SelectItem value="general" text="General" />
                  <SelectItem value="technical" text="Técnico" />
                  <SelectItem value="billing" text="Facturación" />
                  <SelectItem value="feature_request" text="Solicitud de Funcionalidad" />
                  <SelectItem value="bug_report" text="Reporte de Error" />
                  <SelectItem value="other" text="Otro" />
                </Select>

                <Select
                  id="priority"
                  labelText="Prioridad"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                  size="lg"
                  className="support-select"
                >
                  <SelectItem value="low" text="Baja" />
                  <SelectItem value="medium" text="Media" />
                  <SelectItem value="high" text="Alta" />
                  <SelectItem value="urgent" text="Urgente" />
                </Select>
              </div>

              <TextArea
                id="message"
                labelText="Mensaje *"
                placeholder="Describe tu consulta o problema en detalle..."
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                required
                rows={6}
                className="support-textarea"
                maxLength={5000}
              />

              <div className="support-form-footer">
                <Button
                  type="submit"
                  size="lg"
                  renderIcon={Send}
                  disabled={loading}
                  className="support-submit-button"
                >
                  {loading ? 'Enviando...' : 'Crear Ticket'}
                </Button>
                <p className="support-form-note">
                  <Information size={16} />
                  Tiempo de respuesta promedio: 24 horas
                </p>
              </div>
            </form>
          </Tile>
        </Column>

        <Column lg={8} md={4} sm={4}>
          <Tile className="support-info-tile">
            <h2 className="support-info-title">Información de Contacto</h2>
            <div className="support-info-content">
              <div className="support-info-item">
                <Email size={20} />
                <div>
                  <strong>Email</strong>
                  <p>soporte@licitia.co</p>
                </div>
              </div>
              <div className="support-info-item">
                <Time size={20} />
                <div>
                  <strong>Horario de Atención</strong>
                  <p>Lunes a Viernes: 9:00 AM - 6:00 PM</p>
                </div>
              </div>
              <div className="support-info-item">
                <Information size={20} />
                <div>
                  <strong>Respuesta</strong>
                  <p>Respondemos en menos de 24 horas</p>
                </div>
              </div>
            </div>
          </Tile>

          {formData.email && (
            <Tile className="support-tickets-tile">
              <h2 className="support-tickets-title">Mis Tickets</h2>
              {loadingTickets ? (
                <Loading description="Cargando tickets..." withOverlay={false} />
              ) : myTickets.length > 0 ? (
                <div className="support-tickets-list">
                  {myTickets.map((ticket) => (
                    <div key={ticket.id} className="support-ticket-item">
                      <div className="support-ticket-header">
                        <div className="support-ticket-number">
                          #{ticket.ticket_number}
                        </div>
                        <div className="support-ticket-badges">
                          <span className={`support-ticket-badge support-ticket-badge--${getStatusTagKind(ticket.status)}`}>
                            {ticket.status === 'open' ? 'Abierto' : 
                             ticket.status === 'in_progress' ? 'En Progreso' :
                             ticket.status === 'resolved' ? 'Resuelto' : 'Cerrado'}
                          </span>
                          <span className={`support-ticket-badge support-ticket-badge--${getPriorityTagKind(ticket.priority)}`}>
                            {ticket.priority === 'urgent' ? 'Urgente' :
                             ticket.priority === 'high' ? 'Alta' :
                             ticket.priority === 'medium' ? 'Media' : 'Baja'}
                          </span>
                        </div>
                      </div>
                      <h3 className="support-ticket-subject">{ticket.subject}</h3>
                      <p className="support-ticket-message">{ticket.message.substring(0, 100)}...</p>
                      <div className="support-ticket-footer">
                        <span className="support-ticket-date">{formatDate(ticket.created_at)}</span>
                        <span className="support-ticket-category">{ticket.category}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="support-tickets-empty">
                  <p>No tienes tickets aún</p>
                </div>
              )}
            </Tile>
          )}
        </Column>
      </Grid>
    </div>
  )
}

export default Support

