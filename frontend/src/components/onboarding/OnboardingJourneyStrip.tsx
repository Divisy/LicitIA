import React from 'react'
import { CheckmarkFilled } from '@carbon/icons-react'
import './OnboardingJourneyStrip.scss'

export const ONBOARDING_JOURNEY_STEPS = [
  { id: 'value', label: 'Conoce el valor' },
  { id: 'portfolio', label: 'Sube tu portafolio' },
  { id: 'opportunities', label: 'Ve tus oportunidades' },
] as const

interface OnboardingJourneyStripProps {
  currentStep: number
  timeEstimate?: string
}

const OnboardingJourneyStrip: React.FC<OnboardingJourneyStripProps> = ({
  currentStep,
  timeEstimate = '~2 min',
}) => {
  return (
    <div className="onboarding-journey" aria-label="Progreso de configuración">
      <div className="onboarding-journey__meta">
        <span className="onboarding-journey__title">Configura tu radar</span>
        <span className="onboarding-journey__time">{timeEstimate}</span>
      </div>
      <ol className="onboarding-journey__steps">
        {ONBOARDING_JOURNEY_STEPS.map((step, index) => {
          const isComplete = index < currentStep
          const isCurrent = index === currentStep

          return (
            <li
              key={step.id}
              className={[
                'onboarding-journey__step',
                isComplete ? 'onboarding-journey__step--complete' : '',
                isCurrent ? 'onboarding-journey__step--current' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <span className="onboarding-journey__marker" aria-hidden="true">
                {isComplete ? <CheckmarkFilled size={14} /> : index + 1}
              </span>
              <span className="onboarding-journey__label">{step.label}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

export default OnboardingJourneyStrip
