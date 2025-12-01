import React from 'react'
import { Button, Tile } from '@carbon/react'
import { 
  WatsonMachineLearning,
  Search,
  Flash,
  ChartLine,
  ArrowRight
} from '@carbon/icons-react'
import './WelcomeStep.scss'

interface WelcomeStepProps {
  onNext: () => void
  onSkip?: () => void
}

const WelcomeStep: React.FC<WelcomeStepProps> = ({ onNext, onSkip }) => {
  return (
    <div className="onboarding-welcome-step">
      <div className="onboarding-welcome-content">
        <div className="onboarding-welcome-header">
          <div className="onboarding-welcome-logo">
            <WatsonMachineLearning size={32} />
            <h1 className="onboarding-welcome-title">LicitIA</h1>
          </div>
        </div>
        
        <h2 className="onboarding-welcome-heading">
          Bienvenido a LicitIA
        </h2>
        
        <p className="onboarding-welcome-description">
          En solo 30 segundos, accede a cientos de licitaciones filtradas con IA. Sin complicaciones.
        </p>

        <div className="onboarding-welcome-features">
          <Tile className="onboarding-feature-tile">
            <div className="onboarding-feature-icon onboarding-feature-icon--matching">
              <Search size={24} />
            </div>
            <h3 className="onboarding-feature-title">Matching inteligente</h3>
            <p className="onboarding-feature-description">
              Con tu experiencia
            </p>
          </Tile>
          
          <Tile className="onboarding-feature-tile">
            <div className="onboarding-feature-icon onboarding-feature-icon--updates">
              <Flash size={24} />
            </div>
            <h3 className="onboarding-feature-title">Actualización automática</h3>
            <p className="onboarding-feature-description">
              Cada 2 horas
            </p>
          </Tile>
          
          <Tile className="onboarding-feature-tile">
            <div className="onboarding-feature-icon onboarding-feature-icon--filters">
              <ChartLine size={24} />
            </div>
            <h3 className="onboarding-feature-title">Filtros avanzados</h3>
            <p className="onboarding-feature-description">
              Y análisis detallado
            </p>
          </Tile>
        </div>

        <div className="onboarding-welcome-actions">
          <Button
            size="lg"
            onClick={onNext}
            className="onboarding-welcome-cta"
            renderIcon={ArrowRight}
          >
            Comenzar
          </Button>
          {onSkip && (
            <Button
              kind="ghost"
              size="md"
              onClick={onSkip}
              className="onboarding-welcome-skip"
            >
              Ver demo
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

export default WelcomeStep
