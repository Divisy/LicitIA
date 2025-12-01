import React, { ReactNode } from 'react'
import { Tile } from '@carbon/react'
import './Card.scss'

export interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
  interactive?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  interactive = false,
  padding = 'md',
}) => {
  const paddingClass = `card--padding-${padding}`
  const interactiveClass = interactive ? 'card--interactive' : ''

  return (
    <Tile
      className={`licitia-card ${paddingClass} ${interactiveClass} ${className}`}
      onClick={onClick}
    >
      {children}
    </Tile>
  )
}

export default Card

