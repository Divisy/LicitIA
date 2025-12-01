import React from 'react'
import { useOnboarding } from '../../hooks/useOnboarding'
import WelcomeStep from './WelcomeStep'
import MarketingInfoStep, { MarketingData } from './MarketingInfoStep'
import ProgressIndicator from './ProgressIndicator'
import './OnboardingWizard.scss'

interface OnboardingWizardProps {
  onComplete: () => void
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const {
    state,
    nextStep,
    previousStep,
    skipStep,
    setCompanyName,
    finishOnboarding,
  } = useOnboarding()

  if (!state.isActive) {
    return null
  }

  const handleMarketingComplete = (data: MarketingData) => {
    setCompanyName(data.companyName)
    finishOnboarding()
    onComplete()
  }

  const handleMarketingSkip = () => {
    // If company name was already set, use it; otherwise finish anyway
    if (state.companyName) {
      finishOnboarding()
    } else {
      // Allow skip but still finish onboarding
      finishOnboarding()
    }
    onComplete()
  }

  const steps = [
    {
      id: 'welcome',
      component: WelcomeStep,
      props: {
        onNext: nextStep,
        onSkip: () => {
          skipStep('welcome')
          finishOnboarding()
          onComplete()
        },
      },
    },
    {
      id: 'marketing-info',
      component: MarketingInfoStep,
      props: {
        onNext: handleMarketingComplete,
        onBack: previousStep,
        onSkip: handleMarketingSkip,
        initialData: {
          companyName: state.companyName || '',
          fullName: localStorage.getItem('licitia_user_name') || undefined,
          industry: localStorage.getItem('licitia_user_industry') || undefined,
          companySize: localStorage.getItem('licitia_user_company_size') || undefined,
          role: localStorage.getItem('licitia_user_role') || undefined,
        },
      },
    },
  ]

  const currentStepConfig = steps[state.currentStep]
  const CurrentStepComponent = currentStepConfig.component

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-modal">
        {state.currentStep > 0 && state.currentStep < steps.length && (
          <ProgressIndicator
            currentStep={state.currentStep}
            totalSteps={steps.length - 1}
            steps={steps.map(s => s.id)}
          />
        )}
        <CurrentStepComponent {...currentStepConfig.props} />
      </div>
    </div>
  )
}

export default OnboardingWizard

