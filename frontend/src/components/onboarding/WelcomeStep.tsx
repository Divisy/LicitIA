import React from 'react'
import { Button, Tag } from '@carbon/react'
import {
  ArrowRight,
  Flash,
  Partnership,
  Renew,
  Time,
  WatsonMachineLearning,
} from '@carbon/icons-react'
import {
  PREGUNTA_0_HEADLINE,
  PREGUNTA_0_VALUE_POINTS,
  PRODUCT_WHY,
} from '../../content/productMessaging'
import OnboardingProductPreview from './OnboardingProductPreview'
import './WelcomeStep.scss'

const VALUE_POINT_ICONS = {
  experience: Flash,
  updates: Renew,
  partners: Partnership,
} as const

const VALUE_POINT_TONES = {
  experience: 'speed',
  updates: 'sector',
  partners: 'partners',
} as const

interface WelcomeStepProps {
  onNext: () => void
  onSkip?: () => void
}

const WelcomeStep: React.FC<WelcomeStepProps> = ({ onNext, onSkip }) => {
  return (
    <div className="onboarding-welcome-step">
      <div className="onboarding-welcome-step__scroll">
        <div className="onboarding-welcome-step__grid">
          <section className="onboarding-welcome-step__intro">
            <div className="onboarding-welcome-step__brand">
              <WatsonMachineLearning size={24} aria-hidden="true" />
              <span className="onboarding-welcome-step__brand-name">LicitIA</span>
            </div>

            <p className="onboarding-welcome-step__eyebrow">
              {PRODUCT_WHY.audience}
            </p>

            <h1 className="onboarding-welcome-step__headline">{PREGUNTA_0_HEADLINE}</h1>

            <ul className="onboarding-welcome-step__points">
              {PREGUNTA_0_VALUE_POINTS.map((point) => {
                const Icon = VALUE_POINT_ICONS[point.id]
                const tone = VALUE_POINT_TONES[point.id]
                const badge = 'badge' in point ? point.badge : undefined

                return (
                  <li
                    key={point.id}
                    className={`onboarding-welcome-step__point onboarding-welcome-step__point--${tone}`}
                  >
                    <span className="onboarding-welcome-step__point-icon" aria-hidden="true">
                      <Icon size={18} />
                    </span>
                    <span className="onboarding-welcome-step__point-label">{point.label}</span>
                    {badge && (
                      <Tag type="gray" size="sm" className="onboarding-welcome-step__point-badge">
                        {badge}
                      </Tag>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>

          <div className="onboarding-welcome-step__visual">
            <OnboardingProductPreview />
          </div>
        </div>
      </div>

      <footer className="onboarding-welcome-step__footer">
        <div className="onboarding-welcome-step__footer-actions">
          <Button
            size="lg"
            onClick={onNext}
            className="onboarding-welcome-step__cta"
            renderIcon={ArrowRight}
          >
            Continuar — subir portafolio
          </Button>
          <p className="onboarding-welcome-step__hint">
            <Time size={16} aria-hidden="true" />
            Paso 1 de 3 · ~2 min
          </p>
        </div>
        {onSkip && (
          <button type="button" className="onboarding-welcome-step__skip" onClick={onSkip}>
            Explorar sin personalizar
          </button>
        )}
      </footer>
    </div>
  )
}

export default WelcomeStep
