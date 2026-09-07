import React from 'react'
import { Tag } from '@carbon/react'
import { WatsonMachineLearning } from '@carbon/icons-react'
import './OnboardingProductPreview.scss'

const PREVIEW_TENDERS = [
  {
    id: '1',
    match: 82,
    matchType: 'green' as const,
    entity: 'IDU — Interventoría vial',
    amount: '$ 4.200M',
    closing: 'Cierra en 5 días',
  },
  {
    id: '2',
    match: 71,
    matchType: 'green' as const,
    entity: 'Municipio de Envigado — Diseños',
    amount: '$ 890M',
    closing: 'Cierra en 12 días',
  },
  {
    id: '3',
    match: 58,
    matchType: 'yellow' as const,
    entity: 'INVIAS — Estudios y diseños',
    amount: '$ 2.100M',
    closing: 'Cierra en 8 días',
  },
]

const OnboardingProductPreview: React.FC = () => {
  return (
    <div className="onboarding-product-preview" aria-hidden="true">
      <div className="onboarding-product-preview__chrome">
        <span className="onboarding-product-preview__dot" />
        <span className="onboarding-product-preview__dot" />
        <span className="onboarding-product-preview__dot" />
        <span className="onboarding-product-preview__chrome-title">Tus oportunidades</span>
      </div>

      <div className="onboarding-product-preview__body">
        <div className="onboarding-product-preview__header-row">
          <span>Entidad / Objeto</span>
          <span>Match</span>
        </div>

        {PREVIEW_TENDERS.map((tender, index) => (
          <div
            key={tender.id}
            className="onboarding-product-preview__row"
            style={{ animationDelay: `${index * 120}ms` }}
          >
            <div className="onboarding-product-preview__row-main">
              <span className="onboarding-product-preview__entity">{tender.entity}</span>
              <span className="onboarding-product-preview__meta">
                {tender.amount} · {tender.closing}
              </span>
            </div>
            <Tag type={tender.matchType} size="sm" className="onboarding-product-preview__match">
              <WatsonMachineLearning size={12} />
              {tender.match}%
            </Tag>
          </div>
        ))}
      </div>

      <p className="onboarding-product-preview__caption">
        Vista previa con tu portafolio activado
      </p>
    </div>
  )
}

export default OnboardingProductPreview
