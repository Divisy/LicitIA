import React, { Component, ErrorInfo, ReactNode } from 'react'
import Logo from './components/Logo'
import './ErrorBoundary.scss'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary__content">
            <div className="error-boundary__logo">
              <Logo size="xl" showText={true} />
            </div>
            <h1 className="error-boundary__title">Algo salió mal</h1>
            <p className="error-boundary__description">
              Por favor, recarga la página o contacta a soporte si el problema persiste.
            </p>
            <button
              className="error-boundary__button"
              onClick={() => window.location.reload()}
            >
              Recargar página
            </button>
            <details className="error-boundary__details">
              <summary>Detalles del error</summary>
              <pre className="error-boundary__error-text">
                {this.state.error?.toString()}
              </pre>
            </details>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

