import React from 'react'
import { TextInput, TextInputProps } from '@carbon/react'

export interface InputProps extends TextInputProps {
  label?: string
  helperText?: string
  error?: boolean
  errorText?: string
}

export const Input: React.FC<InputProps> = ({
  label,
  helperText,
  error,
  errorText,
  ...props
}) => {
  return (
    <TextInput
      labelText={label}
      helperText={error ? errorText : helperText}
      invalid={error}
      {...props}
    />
  )
}

export default Input

