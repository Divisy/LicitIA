import { useCallback, useEffect, useState } from 'react'
import { getExperiences } from '../api/client'
import { getPortfolioCompanyName, isPortfolioSkipped } from '../utils/portfolio'

export type PortfolioStatus = 'loading' | 'empty' | 'ready'

export function usePortfolioStatus() {
  const [status, setStatus] = useState<PortfolioStatus>('loading')
  const [experienceCount, setExperienceCount] = useState(0)
  const [companyName, setCompanyName] = useState(getPortfolioCompanyName())

  const refresh = useCallback(async () => {
    const name = getPortfolioCompanyName()
    setCompanyName(name)

    try {
      const result = await getExperiences(name)
      const count = result.total ?? result.items.length
      setExperienceCount(count)
      setStatus(count >= 1 ? 'ready' : 'empty')
    } catch {
      setExperienceCount(0)
      setStatus('empty')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    status,
    experienceCount,
    companyName,
    refresh,
    isPortfolioSkipped: isPortfolioSkipped(),
  }
}
