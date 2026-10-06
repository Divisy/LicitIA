import { describe, expect, it } from 'vitest'
import { COMPANY_EMAIL_REQUIRED_MESSAGE, isCompanyEmail } from './companyEmail'

describe('company email', () => {
  it('rejects personal inboxes', () => {
    expect(isCompanyEmail('juan@gmail.com')).toBe(false)
    expect(isCompanyEmail('Ana@Hotmail.es')).toBe(false)
    expect(isCompanyEmail('otto@outlook.com')).toBe(false)
  })

  it('accepts a company domain', () => {
    expect(isCompanyEmail('licitaciones@constructorabec.com')).toBe(true)
    expect(isCompanyEmail('otto@exury.io')).toBe(true)
  })

  it('exposes copy for the signup form', () => {
    expect(COMPANY_EMAIL_REQUIRED_MESSAGE).toMatch(/correo de tu empresa/i)
  })
})
