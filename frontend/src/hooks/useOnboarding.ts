import { useState, useEffect } from 'react'
import { clearPortfolioSkipped, getPortfolioCompanyName, markPortfolioSkipped } from '../utils/portfolio'

export interface OnboardingState {
  isActive: boolean
  currentStep: number
  completedSteps: string[]
  skippedSteps: string[]
  companyName: string | null
  hasSeenDashboard: boolean
}

const ONBOARDING_STATE_KEY = 'licitia_onboarding_state'
const ONBOARDING_COMPLETED_KEY = 'licitia_onboarding_completed'

const INITIAL_STATE: OnboardingState = {
  isActive: false,
  currentStep: 0,
  completedSteps: [],
  skippedSteps: [],
  companyName: null,
  hasSeenDashboard: false,
}

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(() => {
    // Check if onboarding was already completed
    const completed = localStorage.getItem(ONBOARDING_COMPLETED_KEY)
    if (completed === 'true') {
      return INITIAL_STATE
    }

    // Check if we should start onboarding from landing page flag
    const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
    if (shouldStartOnboarding === 'true') {
      // Clear completed flag if it exists (new user registration)
      const completed = localStorage.getItem(ONBOARDING_COMPLETED_KEY)
      if (completed === 'true') {
        console.log('[useOnboarding] Clearing completed flag for new user')
        localStorage.removeItem(ONBOARDING_COMPLETED_KEY)
        localStorage.removeItem(ONBOARDING_STATE_KEY)
      }
      
      // Remove flag to prevent multiple activations
      localStorage.removeItem('licitia_start_onboarding')
      // Pre-fill company name from landing page if available
      const savedCompany = localStorage.getItem('licitia_user_company')
      const initialState = { ...INITIAL_STATE, isActive: true, currentStep: 0 }
      if (savedCompany) {
        initialState.companyName = savedCompany
      }
      // Persist immediately
      localStorage.setItem(ONBOARDING_STATE_KEY, JSON.stringify(initialState))
      console.log('[useOnboarding] Initialized with onboarding active from flag')
      return initialState
    }

    // Load saved state
    const saved = localStorage.getItem(ONBOARDING_STATE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Pre-fill company name if available from landing page
        const savedCompany = localStorage.getItem('licitia_user_company')
        if (savedCompany && !parsed.companyName) {
          parsed.companyName = savedCompany
        }
        return parsed
      } catch {
        return INITIAL_STATE
      }
    }

    // Pre-fill company name from landing page if available
    const savedCompany = localStorage.getItem('licitia_user_company')
    const initialState = { ...INITIAL_STATE }
    if (savedCompany) {
      initialState.companyName = savedCompany
    }

    // First time user - DON'T start onboarding automatically
    // User can start it manually via button/banner or from landing page
    return initialState
  })

  // Persist state to localStorage
  useEffect(() => {
    if (state.isActive) {
      localStorage.setItem(ONBOARDING_STATE_KEY, JSON.stringify(state))
    }
  }, [state])

  const startOnboarding = (initialStep = 0) => {
    const newState = { ...INITIAL_STATE, isActive: true, currentStep: initialStep }
    // Pre-fill company name if available from landing page
    const savedCompany = getPortfolioCompanyName()
    if (savedCompany) {
      newState.companyName = savedCompany
    }
    setState(newState)
    // Persist immediately
    localStorage.setItem(ONBOARDING_STATE_KEY, JSON.stringify(newState))
    console.log('[useOnboarding] Started onboarding, state:', newState)
  }

  const startOnboardingAtStep = (step: number) => {
    startOnboarding(step)
  }

  const nextStep = () => {
    setState(prev => ({
      ...prev,
      currentStep: prev.currentStep + 1,
    }))
  }

  const previousStep = () => {
    setState(prev => ({
      ...prev,
      currentStep: Math.max(0, prev.currentStep - 1),
    }))
  }

  const goToStep = (step: number) => {
    setState(prev => ({
      ...prev,
      currentStep: step,
    }))
  }

  const skipStep = (stepId: string) => {
    setState(prev => ({
      ...prev,
      skippedSteps: [...prev.skippedSteps, stepId],
      currentStep: prev.currentStep + 1,
    }))
  }

  const completeStep = (stepId: string) => {
    setState(prev => ({
      ...prev,
      completedSteps: [...prev.completedSteps.filter(s => s !== stepId), stepId],
    }))
  }

  const setCompanyName = (name: string) => {
    setState(prev => ({ ...prev, companyName: name }))
    localStorage.setItem('licitia_user_company', name)
    completeStep('company-name')
  }

  const skipPortfolioSetup = () => {
    markPortfolioSkipped()
  }

  const markExperiencesUploaded = () => {
    clearPortfolioSkipped()
    completeStep('experiences')
  }

  const finishOnboarding = () => {
    setState(prev => ({ ...prev, isActive: false, hasSeenDashboard: true }))
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, 'true')
    localStorage.removeItem(ONBOARDING_STATE_KEY)
  }

  const resetOnboarding = () => {
    localStorage.removeItem(ONBOARDING_COMPLETED_KEY)
    localStorage.removeItem(ONBOARDING_STATE_KEY)
    setState({ ...INITIAL_STATE, isActive: true })
  }

  return {
    state,
    startOnboarding,
    startOnboardingAtStep,
    nextStep,
    previousStep,
    goToStep,
    skipStep,
    completeStep,
    setCompanyName,
    skipPortfolioSetup,
    markExperiencesUploaded,
    finishOnboarding,
    resetOnboarding,
  }
}

