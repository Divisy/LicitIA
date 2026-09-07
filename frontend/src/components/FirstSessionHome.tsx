import React from 'react'
import { Button, Tag } from '@carbon/react'
import {
  ArrowRight,
  Download,
  Flash,
  Partnership,
  Renew,
  Time,
} from '@carbon/icons-react'
import OnboardingProductPreview from './onboarding/OnboardingProductPreview'
import {
  JTBD_0_TITLE,
  PREGUNTA_0_HEADLINE,
  PREGUNTA_0_VALUE_POINTS,
  PRODUCT_WHY,
} from '../content/productMessaging'
import { downloadExperienceTemplate } from '../utils/portfolio'
import './FirstSessionHome.scss'

const VALUE_POINT_ICONS = {
  experience: Flash,
  updates: Renew,
  partners: Partnership,
} as const

interface FirstSessionHomeProps {
  onUpload: () => void
  onViewAll: () => void
}

const FirstSessionHome: React.FC<FirstSessionHomeProps> = ({ onUpload, onViewAll }) => {
  return (
    <div className="first-session-home">
      <div className="first-session-home__card">
        <div className="first-session-home__grid">
          <div className="first-session-home__copy">
            <Tag type="blue" size="sm">{PRODUCT_WHY.audience}</Tag>
            <h2 className="first-session-home__title">{PREGUNTA_0_HEADLINE}</h2>

            <ul className="first-session-home__points">
              {PREGUNTA_0_VALUE_POINTS.map((point) => {
                const Icon = VALUE_POINT_ICONS[point.id]
                const badge = 'badge' in point ? point.badge : undefined

                return (
                  <li key={point.id}>
                    <Icon size={18} />
                    <span>{point.label}</span>
                    {badge && <Tag type="gray" size="sm">{badge}</Tag>}
                  </li>
                )
              })}
            </ul>

            <p className="first-session-home__jtbd">{JTBD_0_TITLE}</p>

            <div className="first-session-home__actions">
              <Button size="lg" onClick={onUpload} renderIcon={ArrowRight}>
                Activar mi radar
              </Button>
              <Button
                kind="tertiary"
                size="md"
                onClick={downloadExperienceTemplate}
                renderIcon={Download}
              >
                Plantilla Excel
              </Button>
            </div>

            <p className="first-session-home__hint">
              <Time size={16} aria-hidden="true" />
              ~2 minutos para activar
            </p>
          </div>

          <div className="first-session-home__visual">
            <OnboardingProductPreview />
          </div>
        </div>
      </div>

      <p className="first-session-home__secondary">
        ¿Prefieres explorar primero?{' '}
        <button type="button" className="first-session-home__link" onClick={onViewAll}>
          Ver todas las licitaciones
        </button>
      </p>
    </div>
  )
}

export default FirstSessionHome
