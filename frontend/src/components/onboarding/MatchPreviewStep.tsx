import React, { useEffect, useMemo, useState } from 'react'
import { Button, Loading, Tag, Tile } from '@carbon/react'
import { ArrowRight, WatsonMachineLearning } from '@carbon/icons-react'
import { getTenders, Tender } from '../../api/client'
import { MATCH_PREVIEW_EMPTY, MATCH_PREVIEW_TITLE } from '../../content/productMessaging'
import './MatchPreviewStep.scss'

interface MatchPreviewStepProps {
  companyName: string
  onNext: () => void
  onSkipMarketing?: () => void
}

const MatchPreviewStep: React.FC<MatchPreviewStepProps> = ({
  companyName,
  onNext,
  onSkipMarketing,
}) => {
  const [loading, setLoading] = useState(true)
  const [tenders, setTenders] = useState<Tender[]>([])

  useEffect(() => {
    let cancelled = false

    const fetchTopMatches = async () => {
      setLoading(true)
      try {
        const response = await getTenders({
          limit: 50,
          offset: 0,
          company_name: companyName,
          match_experience: true,
        })

        if (cancelled) return

        const sorted = [...(response.items || [])]
          .filter((t) => t.experience_match_score != null)
          .sort(
            (a, b) =>
              (b.experience_match_score ?? 0) - (a.experience_match_score ?? 0)
          )
          .slice(0, 3)

        setTenders(sorted)
      } catch {
        if (!cancelled) {
          setTenders([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchTopMatches()
    return () => {
      cancelled = true
    }
  }, [companyName])

  const formatCurrency = (amount: number | null): string => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const getMatchTagKind = (score: number): 'green' | 'yellow' | 'red' => {
    if (score >= 0.6) return 'green'
    if (score >= 0.4) return 'yellow'
    return 'red'
  }

  const subtitle = useMemo(() => {
    if (loading) return 'Buscando licitaciones relevantes para tu empresa...'
    if (tenders.length === 0) {
      return MATCH_PREVIEW_EMPTY
    }
    return 'Estas licitaciones encajan con tu portafolio — y te muestran dónde podrías necesitar un socio:'
  }, [loading, tenders.length])

  return (
    <div className="onboarding-match-preview-step">
      <div className="onboarding-match-preview-content">
        <div className="onboarding-match-preview-header">
          <WatsonMachineLearning size={32} className="onboarding-match-preview-icon" />
          <h2 className="onboarding-match-preview-title">{MATCH_PREVIEW_TITLE}</h2>
          <p className="onboarding-match-preview-description">{subtitle}</p>
        </div>

        {loading ? (
          <div className="onboarding-match-preview-loading">
            <Loading description="Buscando matches..." withOverlay={false} />
          </div>
        ) : (
          <div className="onboarding-match-preview-list">
            {tenders.map((tender) => {
              const score = tender.experience_match_score ?? 0
              return (
                <Tile key={tender.id} className="onboarding-match-preview-card">
                  <div className="onboarding-match-preview-card__top">
                    <Tag type={getMatchTagKind(score)} size="sm">
                      {Math.round(score * 100)}% match
                    </Tag>
                    <span className="onboarding-match-preview-card__amount">
                      {formatCurrency(tender.amount)}
                    </span>
                  </div>
                  <h3 className="onboarding-match-preview-card__entity">
                    {tender.entity_name}
                  </h3>
                  <p className="onboarding-match-preview-card__object">
                    {tender.object_text || 'Sin descripción disponible'}
                  </p>
                </Tile>
              )
            })}
          </div>
        )}

        <div className="onboarding-match-preview-actions">
          <Button size="lg" onClick={onNext} renderIcon={ArrowRight}>
            Ir a mis oportunidades
          </Button>
          {onSkipMarketing && (
            <Button kind="ghost" size="md" onClick={onSkipMarketing}>
              Completar perfil (opcional)
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

export default MatchPreviewStep
