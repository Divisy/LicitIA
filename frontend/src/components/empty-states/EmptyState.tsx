import React from 'react'
import Logo from '../Logo'
import './EmptyState.css'

interface EmptyStateProps {
  type: 'no-experiences' | 'no-matches' | 'no-tenders'
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  illustration?: React.ReactNode
}

const EmptyState: React.FC<EmptyStateProps> = ({
  type,
  title,
  description,
  action,
  secondaryAction,
  illustration,
}) => {
  const getDefaultIllustration = () => {
    switch (type) {
      case 'no-experiences':
        return '📁'
      case 'no-matches':
        return '🔍'
      case 'no-tenders':
        return '📋'
      default:
        return '📄'
    }
  }

  return (
    <div className="empty-state">
      <div className="empty-state-content">
        <div className="empty-state-logo">
          <Logo size="lg" showText={true} />
        </div>
        <div className="empty-state-illustration">
          {illustration || <span className="empty-state-icon">{getDefaultIllustration()}</span>}
        </div>
        <h3 className="empty-state-title">{title}</h3>
        <p className="empty-state-description">{description}</p>
        {action && (
          <div className="empty-state-actions">
            <button className="btn-primary" onClick={action.onClick}>
              {action.label}
            </button>
            {secondaryAction && (
              <button className="btn-secondary" onClick={secondaryAction.onClick}>
                {secondaryAction.label}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default EmptyState

