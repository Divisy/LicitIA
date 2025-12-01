import React from 'react'
import { WatsonMachineLearning } from '@carbon/icons-react'
import './Logo.scss'

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showText?: boolean
  variant?: 'default' | 'light' | 'dark'
  className?: string
  onClick?: () => void
}

const Logo: React.FC<LogoProps> = ({
  size = 'md',
  showText = true, // Default to always show text
  variant = 'default',
  className = '',
  onClick,
}) => {
  const sizeMap = {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48,
  }

  const iconSize = sizeMap[size]

  return (
    <div
      className={`licitia-logo licitia-logo--${size} licitia-logo--${variant} ${className} ${onClick ? 'licitia-logo--clickable' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      } : undefined}
    >
      <WatsonMachineLearning size={iconSize} className="licitia-logo__icon" />
      {showText && (
        <span className="licitia-logo__text">LicitIA</span>
      )}
    </div>
  )
}

export default Logo

