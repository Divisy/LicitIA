import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { Theme } from '@carbon/react'

export type ThemeMode = 'light' | 'dark'

interface ThemeContextType {
  theme: ThemeMode
  toggleTheme: () => void
  setTheme: (theme: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: ThemeMode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme = 'light',
}) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      // Check localStorage first
      if (typeof window !== 'undefined') {
        const savedTheme = localStorage.getItem('licitia-theme') as ThemeMode
        if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
          return savedTheme
        }
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
          return 'dark'
        }
      }
    } catch (e) {
      console.warn('Error reading theme from localStorage:', e)
    }
    return defaultTheme
  })

  useEffect(() => {
    // Save to localStorage
    localStorage.setItem('licitia-theme', theme)
    
    // Apply theme class to document
    document.documentElement.setAttribute('data-carbon-theme', theme === 'dark' ? 'g100' : 'white')
  }, [theme])

  const setTheme = (newTheme: ThemeMode) => {
    setThemeState(newTheme)
  }

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  const value: ThemeContextType = {
    theme,
    toggleTheme,
    setTheme,
  }

  return (
    <ThemeContext.Provider value={value}>
      <Theme theme={theme === 'dark' ? 'g100' : 'white'}>
        {children}
      </Theme>
    </ThemeContext.Provider>
  )
}

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

