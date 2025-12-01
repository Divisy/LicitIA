# Guía de Implementación - Onboarding LicitIA
## Estructura Técnica y Componentes

---

## 📐 Estructura de Componentes React

### 1. OnboardingWizard Component
```typescript
// frontend/src/components/OnboardingWizard.tsx

interface OnboardingStep {
  id: string
  component: React.ComponentType
  canSkip?: boolean
  required?: boolean
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  { id: 'welcome', component: WelcomeStep, canSkip: false },
  { id: 'company-name', component: CompanyNameStep, canSkip: false },
  { id: 'experiences', component: ExperiencesStep, canSkip: true },
  { id: 'dashboard-intro', component: DashboardIntroStep, canSkip: true }
]
```

### 2. ProgressIndicator Component
```typescript
// frontend/src/components/ProgressIndicator.tsx

interface ProgressIndicatorProps {
  currentStep: number
  totalSteps: number
  steps: string[]
}
```

### 3. ContextualTooltip Component
```typescript
// frontend/src/components/ContextualTooltip.tsx

interface TooltipConfig {
  id: string
  trigger: 'auto' | 'hover' | 'click' | 'manual'
  position: 'top' | 'bottom' | 'left' | 'right'
  content: React.ReactNode
  showOnce?: boolean
  delay?: number
}
```

### 4. EmptyState Component
```typescript
// frontend/src/components/EmptyState.tsx

interface EmptyStateProps {
  type: 'no-experiences' | 'no-matches' | 'no-tenders'
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  illustration?: React.ReactNode
}
```

---

## 🗂️ Estructura de Archivos

```
frontend/src/
├── components/
│   ├── onboarding/
│   │   ├── OnboardingWizard.tsx
│   │   ├── WelcomeStep.tsx
│   │   ├── CompanyNameStep.tsx
│   │   ├── ExperiencesStep.tsx
│   │   ├── DashboardIntroStep.tsx
│   │   └── ProgressIndicator.tsx
│   ├── tooltips/
│   │   ├── ContextualTooltip.tsx
│   │   ├── TooltipManager.tsx
│   │   └── tooltipConfig.ts
│   ├── empty-states/
│   │   ├── EmptyState.tsx
│   │   ├── NoExperiencesState.tsx
│   │   ├── NoMatchesState.tsx
│   │   └── NoTendersState.tsx
│   └── ...
├── hooks/
│   ├── useOnboarding.ts
│   ├── useTooltips.ts
│   └── useLocalStorage.ts
├── utils/
│   ├── onboardingStorage.ts
│   └── analytics.ts
└── ...
```

---

## 🎨 Wireframes Detallados

### Welcome Screen
```
┌─────────────────────────────────────────────┐
│                                             │
│              [Logo LicitIA]                 │
│                                             │
│         Encuentra las licitaciones          │
│         perfectas para tu empresa           │
│                                             │
│    ┌─────────────────────────────────┐     │
│    │  IA que identifica oportunidades │     │
│    │  de interventoría vial basadas    │     │
│    │  en tu experiencia                │     │
│    └─────────────────────────────────┘     │
│                                             │
│         ┌──────────────┐                   │
│         │  Comenzar    │                   │
│         └──────────────┘                   │
│                                             │
│              [Ver demo]                    │
│                                             │
└─────────────────────────────────────────────┘
```

### Company Name Step
```
┌─────────────────────────────────────────────┐
│  ◄ Atrás    Configura tu perfil    [1/3]   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  ¿Cuál es el nombre de tu empresa? │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Ej: Constructora ABC               │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Continuar →                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### Experiences Step
```
┌─────────────────────────────────────────────┐
│  ◄ Atrás    Configura tu perfil    [2/3]   │
│                                             │
│  Carga tus experiencias anteriores          │
│  (Esto ayuda a encontrar mejores            │
│   coincidencias)                            │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │        📄 Subir archivo Excel       │   │
│  │                                     │   │
│  │   Arrastra tu archivo aquí o        │   │
│  │   haz click para seleccionar        │   │
│  │                                     │   │
│  │     [Seleccionar archivo]          │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  O [Agregar manualmente]                   │
│                                             │
│  [Saltar este paso]  [Continuar →]         │
└─────────────────────────────────────────────┘
```

### Dashboard con Tooltip
```
┌─────────────────────────────────────────────┐
│  LicitIA - Radar de Oportunidades            │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  💡 Tip: Usa los filtros para      │   │
│  │     encontrar licitaciones         │   │
│  │     específicas                    │   │
│  │  [Entendido] [Mostrar más tips]    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [Filtros...]                               │
│                                             │
│  Mostrando 50 de 52422 licitaciones         │
│                                             │
│  [Tabla de licitaciones...]                 │
└─────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Estado

### Estado de Onboarding (Zustand/Context)
```typescript
interface OnboardingState {
  isActive: boolean
  currentStep: number
  completedSteps: string[]
  skippedSteps: string[]
  companyName: string | null
  experiencesLoaded: boolean
  hasSeenDashboard: boolean
}

// Actions
- startOnboarding()
- nextStep()
- previousStep()
- skipStep(stepId: string)
- completeStep(stepId: string)
- finishOnboarding()
```

### Persistencia
```typescript
// localStorage keys
const ONBOARDING_STATE_KEY = 'licitia_onboarding_state'
const ONBOARDING_COMPLETED_KEY = 'licitia_onboarding_completed'
const TOOLTIPS_SEEN_KEY = 'licitia_tooltips_seen'
```

---

## 🎯 Configuración de Tooltips

```typescript
// frontend/src/components/tooltips/tooltipConfig.ts

export const TOOLTIP_CONFIGS: TooltipConfig[] = [
  {
    id: 'filters-intro',
    trigger: 'auto',
    position: 'bottom',
    showOnce: true,
    delay: 1000,
    content: (
      <>
        <h3>💡 Usa los filtros</h3>
        <p>Filtra por fecha, departamento y más para encontrar licitaciones específicas</p>
        <button>Entendido</button>
      </>
    )
  },
  {
    id: 'match-score-explanation',
    trigger: 'hover',
    position: 'top',
    target: '[data-tooltip="match-score"]',
    content: (
      <>
        <h3>Match Score</h3>
        <p>Indica qué tan bien coincide la licitación con tu experiencia</p>
        <ul>
          <li>>60% = Alta coincidencia</li>
          <li>40-60% = Coincidencia media</li>
        </ul>
      </>
    )
  },
  // ... más tooltips
]
```

---

## 📱 Responsive Design

### Breakpoints
- **Mobile**: < 768px
  - Onboarding en pantalla completa
  - Tooltips como modales
  - Botones de tamaño táctil (min 44px)

- **Tablet**: 768px - 1024px
  - Onboarding en modal centrado
  - Tooltips flotantes

- **Desktop**: > 1024px
  - Onboarding en modal (max-width: 600px)
  - Tooltips contextuales

---

## 🧪 Testing Strategy

### Unit Tests
- Componentes de onboarding
- Lógica de progreso
- Validación de formularios

### Integration Tests
- Flujo completo de onboarding
- Persistencia de estado
- Integración con API

### E2E Tests (Cypress/Playwright)
- Usuario completa onboarding
- Usuario salta pasos
- Usuario carga experiencias
- Usuario ve tooltips

---

## 📈 Analytics Events

```typescript
// Eventos a trackear
const ONBOARDING_EVENTS = {
  // Inicio
  'onboarding_started': {},
  'onboarding_welcome_viewed': {},
  
  // Pasos
  'onboarding_step_started': { step: string },
  'onboarding_step_completed': { step: string },
  'onboarding_step_skipped': { step: string },
  
  // Acciones
  'company_name_entered': { companyName: string },
  'experiences_uploaded': { count: number, method: 'excel' | 'manual' },
  
  // Finalización
  'onboarding_completed': { duration: number, stepsCompleted: number },
  'onboarding_abandoned': { step: string, duration: number },
  
  // Tooltips
  'tooltip_viewed': { tooltipId: string },
  'tooltip_dismissed': { tooltipId: string },
  
  // Dashboard
  'first_match_viewed': { matchScore: number },
  'dashboard_first_visit': {}
}
```

---

## 🚀 Plan de Lanzamiento

### Fase 1: MVP (Semana 1-2)
1. Welcome screen
2. Company name input
3. Basic experience upload
4. Simple progress indicator
5. One tooltip en dashboard

### Fase 2: Mejoras (Semana 3-4)
1. Tooltips contextuales completos
2. Empty states
3. Success animations
4. Skip functionality
5. Analytics integration

### Fase 3: Optimización (Semana 5+)
1. A/B testing setup
2. Onboarding adaptativo
3. Re-onboarding para inactivos
4. Gamificación sutil

---

## ✅ Checklist de Implementación

### Componentes
- [ ] OnboardingWizard
- [ ] WelcomeStep
- [ ] CompanyNameStep
- [ ] ExperiencesStep
- [ ] DashboardIntroStep
- [ ] ProgressIndicator
- [ ] ContextualTooltip
- [ ] TooltipManager
- [ ] EmptyState variants

### Hooks
- [ ] useOnboarding
- [ ] useTooltips
- [ ] useLocalStorage

### Utils
- [ ] onboardingStorage
- [ ] analytics helpers

### Styling
- [ ] Onboarding styles
- [ ] Tooltip styles
- [ ] Empty state styles
- [ ] Responsive breakpoints

### Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests

### Analytics
- [ ] Event tracking
- [ ] Funnel analysis
- [ ] Drop-off points

---

## 💡 Mejores Prácticas

1. **Performance**: Lazy load componentes de onboarding
2. **Accessibility**: ARIA labels, keyboard navigation
3. **Internationalization**: Preparar para múltiples idiomas
4. **Error Handling**: Manejo graceful de errores
5. **Loading States**: Skeleton screens durante carga
6. **Animations**: Transiciones suaves pero no distractivas

---

**Próximo Paso**: Crear mockups de alta fidelidad en Figma antes de implementar.

