import React from 'react'
import './OnboardingBanner.css'

interface OnboardingBannerProps {
  onStart: () => void
  onDismiss: () => void
}

const OnboardingBanner: React.FC<OnboardingBannerProps> = ({ onStart, onDismiss }) => {
  return (
    <div className="onboarding-banner">
      <div className="banner-content">
        <div className="banner-text">
          <span className="banner-icon">✨</span>
          <div>
            <strong>¿Quieres ver licitaciones personalizadas?</strong>
            <span className="banner-subtitle"> Configura tu perfil en 2 minutos</span>
          </div>
        </div>
        <div className="banner-actions">
          <button className="btn-banner-primary" onClick={onStart}>
            Configurar perfil
          </button>
          <button className="btn-banner-dismiss" onClick={onDismiss} aria-label="Cerrar">
            ×
          </button>
        </div>
      </div>
    </div>
  )
}

export default OnboardingBanner

