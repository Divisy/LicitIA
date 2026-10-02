import React from 'react'
import { Button } from '@carbon/react'
import { Partnership } from '@carbon/icons-react'
import { PORTFOLIO_BANNER_TEXT, PORTFOLIO_BANNER_TITLE } from '../content/productMessaging'
import './PortfolioBanner.scss'

interface PortfolioBannerProps {
  onUpload: () => void
}

const PortfolioBanner: React.FC<PortfolioBannerProps> = ({ onUpload }) => {
  return (
    <div className="portfolio-banner">
      <div className="portfolio-banner__content">
        <Partnership size={20} className="portfolio-banner__icon" />
        <div className="portfolio-banner__text">
          <strong>{PORTFOLIO_BANNER_TITLE}</strong>
          <span> {PORTFOLIO_BANNER_TEXT}</span>
        </div>
      </div>
      <Button kind="primary" size="sm" onClick={onUpload}>
        Cargar RUP
      </Button>
    </div>
  )
}

export default PortfolioBanner
