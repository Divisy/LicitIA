export const PORTFOLIO_SKIPPED_KEY = 'licitia_portfolio_skipped'

export function getPortfolioCompanyName(): string {
  const saved = localStorage.getItem('licitia_user_company')
  if (saved?.trim()) {
    return saved.trim()
  }

  const email = localStorage.getItem('licitia_user_email')
  if (email?.includes('@')) {
    return email.split('@')[0]
  }

  return 'Mi Empresa'
}

export function isPortfolioSkipped(): boolean {
  return localStorage.getItem(PORTFOLIO_SKIPPED_KEY) === 'true'
}

export function markPortfolioSkipped(): void {
  localStorage.setItem(PORTFOLIO_SKIPPED_KEY, 'true')
}

export function clearPortfolioSkipped(): void {
  localStorage.removeItem(PORTFOLIO_SKIPPED_KEY)
}

export function downloadExperienceTemplate(): void {
  const link = document.createElement('a')
  link.href = '/plantilla-experiencias.xlsx'
  link.download = 'plantilla-experiencias.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
