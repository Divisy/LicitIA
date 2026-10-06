import {
  serializeSectors,
  USER_SECTORS_STORAGE_KEY,
  type CompanySector,
} from './companySectors'

export interface SessionLead {
  email: string
  name?: string | null
  company?: string | null
  industry?: string | null
  company_size?: string | null
  role?: string | null
  phone?: string | null
  city?: string | null
  sectors?: string[] | null
  onboarding_completed_at?: string | null
}

const SESSION_KEYS = [
  'licitia_user_email',
  'licitia_user_name',
  'licitia_user_company',
  'licitia_user_industry',
  'licitia_user_company_size',
  'licitia_user_role',
  'licitia_user_phone',
  'licitia_user_city',
  'licitia_new_user',
  'licitia_onboarding_completed',
  'licitia_onboarding_state',
  'licitia_onboarding_banner_dismissed',
  'licitia_start_onboarding',
  'licitia_portfolio_skipped',
  USER_SECTORS_STORAGE_KEY,
]

export function getSessionEmail(): string {
  return (localStorage.getItem('licitia_user_email') || '').trim().toLowerCase()
}

export function persistLeadSession(
  lead: SessionLead,
  options: { startOnboarding?: boolean; returning?: boolean } = {}
): void {
  localStorage.setItem('licitia_user_email', lead.email)
  if (lead.name) localStorage.setItem('licitia_user_name', lead.name)
  if (lead.company) localStorage.setItem('licitia_user_company', lead.company)
  if (lead.industry) localStorage.setItem('licitia_user_industry', lead.industry)
  if (lead.company_size) localStorage.setItem('licitia_user_company_size', lead.company_size)
  if (lead.role) localStorage.setItem('licitia_user_role', lead.role)
  if (lead.phone) localStorage.setItem('licitia_user_phone', lead.phone)
  if (lead.city) localStorage.setItem('licitia_user_city', lead.city)
  if (lead.sectors?.length) {
    localStorage.setItem(
      USER_SECTORS_STORAGE_KEY,
      serializeSectors(lead.sectors as CompanySector[])
    )
  }

  if (options.startOnboarding) {
    localStorage.setItem('licitia_start_onboarding', 'true')
    localStorage.setItem('licitia_new_user', 'true')
    localStorage.removeItem('licitia_onboarding_completed')
    localStorage.removeItem('licitia_onboarding_state')
  } else {
    localStorage.removeItem('licitia_start_onboarding')
    localStorage.removeItem('licitia_new_user')
  }

  if (options.returning || lead.onboarding_completed_at) {
    localStorage.setItem('licitia_onboarding_completed', 'true')
    localStorage.removeItem('licitia_onboarding_state')
    localStorage.removeItem('licitia_start_onboarding')
  }
}

export function clearUserSession(): void {
  SESSION_KEYS.forEach((key) => localStorage.removeItem(key))
}
