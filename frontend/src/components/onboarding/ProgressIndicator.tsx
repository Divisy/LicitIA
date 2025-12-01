import React from 'react'
import './ProgressIndicator.scss'

interface ProgressIndicatorProps {
  currentStep: number
  totalSteps: number
  steps: string[]
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  currentStep,
  totalSteps,
  steps,
}) => {
  const progress = ((currentStep + 1) / totalSteps) * 100

  return (
    <div className="onboarding-progress-indicator">
      <div className="onboarding-progress-bar-container">
        <div 
          className="onboarding-progress-bar-fill" 
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="onboarding-progress-text">
        Paso {currentStep + 1} de {totalSteps}
      </div>
    </div>
  )
}

export default ProgressIndicator
