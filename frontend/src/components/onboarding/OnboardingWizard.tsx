import React from 'react'
import { useOnboarding } from '../../hooks/useOnboarding'
import { getPortfolioCompanyName } from '../../utils/portfolio'
import WelcomeStep from './WelcomeStep'
import RupUploadStep from './RupUploadStep'
import MarketingInfoStep, { MarketingData } from './MarketingInfoStep'
import OnboardingJourneyStrip from './OnboardingJourneyStrip'
import { parseStoredSectors, USER_SECTORS_STORAGE_KEY } from '../../utils/companySectors'
import './OnboardingWizard.scss'

const STEP = {
  WELCOME: 0,
  EXPERIENCES: 1,
  MATCH_PREVIEW: 2,
  MARKETING: 3,
} as const

interface OnboardingWizardProps {
  onComplete: () => void
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const {
    state,
    nextStep,
    previousStep,
    skipStep,
    skipPortfolioSetup,
    markExperiencesUploaded,
    finishOnboarding,
    goToStep,
  } = useOnboarding()

  if (!state.isActive) {
    return null
  }

  const resolvedCompanyName = state.companyName || getPortfolioCompanyName()

  const handleExperiencesNext = () => {
    markExperiencesUploaded()
    goToStep(STEP.MARKETING)
  }

  const handleExperiencesSkip = () => {
    skipPortfolioSetup()
    skipStep('experiences')
    goToStep(STEP.MARKETING)
  }

  const handleMarketingComplete = (_data: MarketingData) => {
    finishOnboarding()
    onComplete()
  }

  const renderStep = () => {
    switch (state.currentStep) {
      case STEP.WELCOME:
        return <WelcomeStep onNext={nextStep} />

      case STEP.EXPERIENCES:
        return (
          <RupUploadStep
            onNext={handleExperiencesNext}
            onBack={previousStep}
            onSkip={handleExperiencesSkip}
            companyName={resolvedCompanyName}
          />
        )

      case STEP.MATCH_PREVIEW:
        return (
          <MarketingInfoStep
            onNext={handleMarketingComplete}
            onBack={previousStep}
            initialData={{
              contactName: localStorage.getItem('licitia_user_name') || undefined,
              phone: localStorage.getItem('licitia_user_phone') || undefined,
              city: localStorage.getItem('licitia_user_city') || undefined,
              sectors: parseStoredSectors(localStorage.getItem(USER_SECTORS_STORAGE_KEY)),
            }}
          />
        )

      case STEP.MARKETING:
        return (
          <MarketingInfoStep
            onNext={handleMarketingComplete}
            onBack={() => goToStep(STEP.EXPERIENCES)}
            initialData={{
              contactName: localStorage.getItem('licitia_user_name') || undefined,
              phone: localStorage.getItem('licitia_user_phone') || undefined,
              city: localStorage.getItem('licitia_user_city') || undefined,
              sectors: parseStoredSectors(localStorage.getItem(USER_SECTORS_STORAGE_KEY)),
            }}
          />
        )

      default:
        return <WelcomeStep onNext={nextStep} />
    }
  }

  const getJourneyStep = () => {
    switch (state.currentStep) {
      case STEP.WELCOME:
        return 0
      case STEP.EXPERIENCES:
        return 1
      case STEP.MATCH_PREVIEW:
      case STEP.MARKETING:
        return 2
      default:
        return 0
    }
  }

  return (
    <div className="onboarding-overlay">
      <div
        className={`onboarding-modal${
          state.currentStep === STEP.WELCOME ? ' onboarding-modal--welcome' : ''
        }`}
      >
        <OnboardingJourneyStrip currentStep={getJourneyStep()} />
        {renderStep()}
      </div>
    </div>
  )
}

export default OnboardingWizard
