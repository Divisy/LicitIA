import React from 'react'
import { Button as CarbonButton, ButtonProps as CarbonButtonProps } from '@carbon/react'

export interface ButtonProps extends Omit<CarbonButtonProps, 'size'> {
  size?: 'sm' | 'md' | 'lg'
  variant?: 'primary' | 'secondary' | 'tertiary' | 'danger' | 'ghost'
}

export const Button: React.FC<ButtonProps> = ({
  size = 'md',
  variant = 'primary',
  children,
  ...props
}) => {
  // Map our size to Carbon's size
  const carbonSize = size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : 'md'
  
  // Map our variant to Carbon's kind
  const carbonKind = 
    variant === 'danger' ? 'danger' :
    variant === 'secondary' ? 'secondary' :
    variant === 'tertiary' ? 'tertiary' :
    variant === 'ghost' ? 'ghost' :
    'primary'

  return (
    <CarbonButton
      size={carbonSize}
      kind={carbonKind}
      {...props}
    >
      {children}
    </CarbonButton>
  )
}

export default Button

