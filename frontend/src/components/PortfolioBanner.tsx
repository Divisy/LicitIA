import React from 'react'
import { Button } from '@carbon/react'
import { Radar } from '@carbon/icons-react'
import './PortfolioBanner.scss'

interface PortfolioBannerProps {
  onUpload: () => void
}

const PortfolioBanner: React.FC<PortfolioBannerProps> = ({ onUpload }) => {
  return (
    <div className="portfolio-banner">
      <div className="portfolio-banner__content">
        <Radar size={20} className="portfolio-banner__icon" />
        <div className="portfolio-banner__text">
          <strong>Tu radar aún no está activo</strong>
          <span>
            {' '}
            Sube tu portafolio para ver licitaciones relevantes en construcción, ingeniería e
            interventoría — en minutos, no horas.
          </span>
        </div>
      </div>
      <Button kind="primary" size="sm" onClick={onUpload}>
        Activar radar
      </Button>
    </div>
  )
}

export default PortfolioBanner
