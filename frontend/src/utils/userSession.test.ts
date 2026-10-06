import { afterEach, describe, expect, it } from 'vitest'
import { persistLeadSession, clearUserSession } from './userSession'
import { USER_SECTORS_STORAGE_KEY } from './companySectors'

describe('userSession', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('starts onboarding only for a new signup', () => {
    persistLeadSession(
      { email: 'nuevo@empresa.com', company: 'Obra SAS' },
      { startOnboarding: true }
    )
    expect(localStorage.getItem('licitia_start_onboarding')).toBe('true')
    expect(localStorage.getItem('licitia_user_company')).toBe('Obra SAS')
    expect(localStorage.getItem('licitia_onboarding_completed')).toBeNull()
  })

  it('does not reopen the wizard for a returning login', () => {
    persistLeadSession(
      { email: 'vuelve@empresa.com', company: 'Obra SAS', sectors: ['interventoria'] },
      { returning: true }
    )
    expect(localStorage.getItem('licitia_start_onboarding')).toBeNull()
    expect(localStorage.getItem('licitia_onboarding_completed')).toBe('true')
  })

  it('clears identity and skip flags on logout', () => {
    persistLeadSession({ email: 'a@b.com', city: 'Bogotá' }, { returning: true })
    localStorage.setItem('licitia_portfolio_skipped', 'true')
    localStorage.setItem(USER_SECTORS_STORAGE_KEY, 'interventoria')
    clearUserSession()
    expect(localStorage.getItem('licitia_user_email')).toBeNull()
    expect(localStorage.getItem('licitia_user_city')).toBeNull()
    expect(localStorage.getItem('licitia_portfolio_skipped')).toBeNull()
    expect(localStorage.getItem(USER_SECTORS_STORAGE_KEY)).toBeNull()
  })
})
