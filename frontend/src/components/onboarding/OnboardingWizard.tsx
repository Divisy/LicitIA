import React from 'react'
import { useOnboarding } from '../../hooks/useOnboarding'
import { getPortfolioCompanyName } from '../../utils/portfolio'
import WelcomeStep from './WelcomeStep'
import ExperiencesStep from './ExperiencesStep'
import MatchPreviewStep from './MatchPreviewStep'
import MarketingInfoStep, { MarketingData } from './MarketingInfoStep'
import OnboardingJourneyStrip from './OnboardingJourneyStrip'
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
    setCompanyName,
    skipPortfolioSetup,
    markExperiencesUploaded,
    finishOnboarding,
    goToStep,
  } = useOnboarding()

  const hasUploadedExperiences = state.completedSteps.includes('experiences')

  if (!state.isActive) {
    return null
  }

  const resolvedCompanyName = state.companyName || getPortfolioCompanyName()

  const handleWelcomeSkip = () => {
    skipPortfolioSetup()
    skipStep('welcome')
    finishOnboarding()
    onComplete()
  }

  const handleExperiencesNext = () => {
    markExperiencesUploaded()
    nextStep()
  }

  const handleExperiencesSkip = () => {
    skipPortfolioSetup()
    skipStep('experiences')
    goToStep(STEP.MARKETING)
  }

  const handleMatchPreviewNext = () => {
    finishOnboarding()
    onComplete()
  }

  const handleMatchPreviewMarketing = () => {
    nextStep()
  }

  const handleMarketingComplete = (data: MarketingData) => {
    setCompanyName(data.companyName)
    finishOnboarding()
    onComplete()
  }

  const handleMarketingSkip = () => {
    finishOnboarding()
    onComplete()
  }

  const renderStep = () => {
    switch (state.currentStep) {
      case STEP.WELCOME:
        return <WelcomeStep onNext={nextStep} onSkip={handleWelcomeSkip} />

      case STEP.EXPERIENCES:
        return (
          <ExperiencesStep
            onNext={handleExperiencesNext}
            onBack={previousStep}
            onSkip={handleExperiencesSkip}
            companyName={resolvedCompanyName}
          />
        )

      case STEP.MATCH_PREVIEW:
        if (!hasUploadedExperiences) {
          return (
            <MarketingInfoStep
              onNext={handleMarketingComplete}
              onBack={previousStep}
              onSkip={handleMarketingSkip}
              initialData={{
                companyName: resolvedCompanyName,
                fullName: localStorage.getItem('licitia_user_name') || undefined,
                industry: localStorage.getItem('licitia_user_industry') || undefined,
                companySize: localStorage.getItem('licitia_user_company_size') || undefined,
                role: localStorage.getItem('licitia_user_role') || undefined,
              }}
            />
          )
        }
        return (
          <MatchPreviewStep
            companyName={resolvedCompanyName}
            onNext={handleMatchPreviewNext}
            onSkipMarketing={handleMatchPreviewMarketing}
          />
        )

      case STEP.MARKETING:
        return (
          <MarketingInfoStep
            onNext={handleMarketingComplete}
            onBack={() => goToStep(hasUploadedExperiences ? STEP.MATCH_PREVIEW : STEP.EXPERIENCES)}
            onSkip={handleMarketingSkip}
            initialData={{
              companyName: resolvedCompanyName,
              fullName: localStorage.getItem('licitia_user_name') || undefined,
              industry: localStorage.getItem('licitia_user_industry') || undefined,
              companySize: localStorage.getItem('licitia_user_company_size') || undefined,
              role: localStorage.getItem('licitia_user_role') || undefined,
            }}
          />
        )

      default:
        return <WelcomeStep onNext={nextStep} onSkip={handleWelcomeSkip} />
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
