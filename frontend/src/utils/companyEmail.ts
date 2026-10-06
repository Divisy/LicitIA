const PERSONAL_EMAIL_DOMAINS = new Set([
  'gmail.com',
  'googlemail.com',
  'hotmail.com',
  'hotmail.es',
  'hotmail.co.uk',
  'outlook.com',
  'outlook.es',
  'live.com',
  'live.com.mx',
  'msn.com',
  'yahoo.com',
  'yahoo.es',
  'yahoo.com.mx',
  'ymail.com',
  'icloud.com',
  'me.com',
  'mac.com',
  'aol.com',
  'proton.me',
  'protonmail.com',
  'pm.me',
  'gmx.com',
  'gmx.es',
  'mail.com',
  'zoho.com',
  'yopmail.com',
  'tutanota.com',
  'tuta.com',
])

export const COMPANY_EMAIL_REQUIRED_MESSAGE = 'Usa el correo de tu empresa'

export function emailDomain(email: string): string {
  const trimmed = email.trim().toLowerCase()
  const at = trimmed.lastIndexOf('@')
  if (at < 0) return ''
  return trimmed.slice(at + 1)
}

export function isCompanyEmail(email: string): boolean {
  const domain = emailDomain(email)
  return Boolean(domain) && !PERSONAL_EMAIL_DOMAINS.has(domain)
}
