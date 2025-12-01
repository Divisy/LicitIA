import React, { useState, useEffect, useRef } from 'react'
import './ContextualTooltip.css'

interface ContextualTooltipProps {
  id: string
  trigger: 'auto' | 'hover' | 'click' | 'manual'
  position: 'top' | 'bottom' | 'left' | 'right'
  content: React.ReactNode
  showOnce?: boolean
  delay?: number
  target?: string // CSS selector for target element
  onDismiss?: () => void
  children?: React.ReactNode
}

const ContextualTooltip: React.FC<ContextualTooltipProps> = ({
  id,
  trigger,
  position,
  content,
  showOnce = false,
  delay = 0,
  target,
  onDismiss,
  children,
}) => {
  const [isVisible, setIsVisible] = useState(false)
  const [hasBeenShown, setHasBeenShown] = useState(false)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    // Check if tooltip was already shown
    if (showOnce) {
      const seen = localStorage.getItem(`tooltip_seen_${id}`)
      if (seen === 'true') {
        setHasBeenShown(true)
        return
      }
    }

    // Handle auto trigger
    if (trigger === 'auto' && !hasBeenShown) {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(true)
        setHasBeenShown(true)
        if (showOnce) {
          localStorage.setItem(`tooltip_seen_${id}`, 'true')
        }
      }, delay)
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [trigger, delay, id, showOnce, hasBeenShown])

  const handleDismiss = () => {
    setIsVisible(false)
    if (showOnce) {
      localStorage.setItem(`tooltip_seen_${id}`, 'true')
    }
    if (onDismiss) {
      onDismiss()
    }
  }

  const handleMouseEnter = () => {
    if (trigger === 'hover' && !hasBeenShown) {
      setIsVisible(true)
    }
  }

  const handleMouseLeave = () => {
    if (trigger === 'hover') {
      setIsVisible(false)
    }
  }

  if (hasBeenShown && showOnce && trigger === 'auto') {
    return <>{children}</>
  }

  return (
    <div
      className="tooltip-wrapper"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {isVisible && (
        <div
          ref={tooltipRef}
          className={`contextual-tooltip tooltip-${position}`}
        >
          <div className="tooltip-content">
            {content}
          </div>
          <button
            className="tooltip-close"
            onClick={handleDismiss}
            aria-label="Cerrar"
          >
            ×
          </button>
          <div className={`tooltip-arrow arrow-${position}`} />
        </div>
      )}
    </div>
  )
}

export default ContextualTooltip

