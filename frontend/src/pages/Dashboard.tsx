import React, { useState, useEffect } from 'react'
import { 
  Grid, 
  Column, 
  Button, 
  InlineNotification,
  Loading,
  Tile
} from '@carbon/react'
import { View, Download } from '@carbon/icons-react'
import FiltersBar from '../components/FiltersBar'
import TenderTable from '../components/TenderTable'
import TenderDetailPanel from '../components/TenderDetailPanel'
import OnboardingWizard from '../components/onboarding/OnboardingWizard'
import OnboardingBanner from '../components/onboarding/OnboardingBanner'
import EmptyState from '../components/empty-states/EmptyState'
import Logo from '../components/Logo'
import { useOnboarding } from '../hooks/useOnboarding'
import { getTenders, Tender, TenderFilters, ContractKindFilter } from '../api/client'
import './Dashboard.scss'

const Dashboard: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [showOnboardingBanner, setShowOnboardingBanner] = useState(false)
  
  const { state: onboardingState, startOnboarding } = useOnboarding()
  
  // Filter state
  const [filters, setFilters] = useState<TenderFilters>({
    limit: 50,
    offset: 0,
  })
  
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [department, setDepartment] = useState<string>('')
  const [companyName, setCompanyName] = useState<string>('')
  const [contractKind, setContractKind] = useState<ContractKindFilter>('')
  const [showAll, setShowAll] = useState<boolean>(false)
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null)
  
  const fetchTenders = async (
    loadAll: boolean = false,
    contractKindOverride?: ContractKindFilter
  ) => {
    setLoading(true)
    setError(null)
    
    try {
      const limit = loadAll ? 1000 : 50
      const effectiveContractKind =
        contractKindOverride !== undefined ? contractKindOverride : contractKind
      
      const params: TenderFilters = {
        limit: limit,
        offset: 0,
      }
      
      if (dateFrom) {
        params.date_from = dateFrom
      }
      if (dateTo) {
        params.date_to = dateTo
      }
      if (department) {
        params.department = department
      }
      if (effectiveContractKind) {
        params.contract_kind = effectiveContractKind
      }
      if (companyName) {
        params.company_name = companyName
      }
      
      console.log('[Dashboard] Fetching tenders with params:', params)
      const response = await getTenders(params)
      console.log('[Dashboard] Tenders response:', {
        itemsCount: response?.items?.length || 0,
        total: response?.total || 0,
        hasItems: !!response?.items
      })
      
      setTenders(response?.items || [])
      setTotal(response?.total || 0)
      
      if (!response?.items || response.items.length === 0) {
        console.warn('[Dashboard] No tenders returned from API')
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar licitaciones'
      console.error('[Dashboard] Error fetching tenders:', {
        message: errorMessage,
        status: err?.response?.status,
        url: err?.config?.url,
        baseURL: err?.config?.baseURL,
        fullError: err
      })
      setError(errorMessage)
      // Asegurar que los estados estén vacíos en caso de error
      setTenders([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    fetchTenders()
  }, [])
  
  // Check for onboarding flag on mount - this should run first
  useEffect(() => {
    const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
    const completed = localStorage.getItem('licitia_onboarding_completed')
    
    console.log('[Dashboard Mount] Checking onboarding flags:', {
      shouldStartOnboarding,
      completed,
      isActive: onboardingState.isActive
    })
    
    // If flag is set, clear completed flag and start onboarding
    // This ensures new users always get onboarding even if completed was set before
    if (shouldStartOnboarding === 'true') {
      // Clear completed flag if onboarding should start (new user)
      if (completed === 'true') {
        console.log('[Dashboard] Clearing completed flag for new user')
        localStorage.removeItem('licitia_onboarding_completed')
        localStorage.removeItem('licitia_onboarding_state')
      }
      
      console.log('[Dashboard] Starting onboarding automatically for new user')
      // Remove flag first to prevent multiple triggers
      localStorage.removeItem('licitia_start_onboarding')
      // Start onboarding immediately
      startOnboarding()
    }
  }, []) // Run only on mount
  
  // Watch for state changes to handle edge cases
  useEffect(() => {
    if (!onboardingState.isActive) {
      const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
      const completed = localStorage.getItem('licitia_onboarding_completed')
      
      if (shouldStartOnboarding === 'true' && completed !== 'true') {
        console.log('[Dashboard] Onboarding flag detected, starting...')
        localStorage.removeItem('licitia_start_onboarding')
        startOnboarding()
      }
    }
  }, [onboardingState.isActive, startOnboarding])
  
  // Separate effect for banner display
  useEffect(() => {
    const completed = localStorage.getItem('licitia_onboarding_completed')
    const hasSeenBanner = localStorage.getItem('licitia_onboarding_banner_dismissed')
    const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
    
    // Only show banner if onboarding is not active, not completed, and flag is not set
    if (!completed && !hasSeenBanner && !onboardingState.isActive && shouldStartOnboarding !== 'true') {
      const timer = setTimeout(() => {
        setShowOnboardingBanner(true)
      }, 3000)
      
      return () => {
        clearTimeout(timer)
      }
    }
  }, [onboardingState.isActive])
  
  const handleFilterSubmit = () => {
    setShowAll(false)
    fetchTenders(false)
  }

  const handleContractKindChange = (value: ContractKindFilter) => {
    setContractKind(value)
    setShowAll(false)
    fetchTenders(false, value)
  }
  
  const handleLoadAll = () => {
    setShowAll(true)
    fetchTenders(true)
  }
  
  const handleOnboardingComplete = () => {
    setShowOnboardingBanner(false)
    fetchTenders()
  }

  const handleStartOnboarding = () => {
    setShowOnboardingBanner(false)
    startOnboarding()
  }

  const handleDismissBanner = () => {
    setShowOnboardingBanner(false)
    localStorage.setItem('licitia_onboarding_banner_dismissed', 'true')
  }

  return (
    <div className="dashboard">
      <OnboardingWizard onComplete={handleOnboardingComplete} />
      
      {showOnboardingBanner && !onboardingState.isActive && (
        <OnboardingBanner
          onStart={handleStartOnboarding}
          onDismiss={handleDismissBanner}
        />
      )}
      
      <Grid className="dashboard-grid">
        <Column lg={16} md={8} sm={4}>
          <div className="dashboard-header">
            <div className="dashboard-header__logo">
              <Logo size="md" showText={true} />
            </div>
            <div className="dashboard-header__content">
              <h1 className="dashboard-title">Dashboard</h1>
              <p className="dashboard-subtitle">
                Encuentra las licitaciones perfectas para tu empresa
              </p>
            </div>
          </div>
        </Column>
      </Grid>
      
      <Grid className="dashboard-grid">
        <Column lg={16} md={8} sm={4}>
          <FiltersBar
            dateFrom={dateFrom}
            dateTo={dateTo}
            department={department}
            companyName={companyName}
            contractKind={contractKind}
            onDateFromChange={setDateFrom}
            onDateToChange={setDateTo}
            onDepartmentChange={setDepartment}
            onCompanyNameChange={setCompanyName}
            onContractKindChange={handleContractKindChange}
            onSubmit={handleFilterSubmit}
          />
        </Column>
      </Grid>
      
      {loading && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <Tile className="dashboard-loading">
              <Loading description="Cargando licitaciones..." withOverlay={false} />
            </Tile>
          </Column>
        </Grid>
      )}
      
      {error && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <InlineNotification
              kind="error"
              title="Error"
              subtitle={error}
              lowContrast={false}
            />
          </Column>
        </Grid>
      )}
      
      {!loading && !error && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <div className="dashboard-results-info">
              <p className="dashboard-results-text">
                Mostrando <strong>{tenders.length}</strong> de <strong>{total}</strong> licitaciones
              </p>
              {!showAll && tenders.length < total && (
                <Button
                  kind="secondary"
                  size="md"
                  onClick={handleLoadAll}
                  renderIcon={View}
                  className="dashboard-load-all-button"
                >
                  Ver todas las licitaciones ({total})
                </Button>
              )}
            </div>
          </Column>
        </Grid>
      )}
      
      {!loading && !error && tenders.length === 0 && total === 0 && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <EmptyState
              type="no-tenders"
              title="No se encontraron licitaciones"
              description="Intenta ajustar los filtros de búsqueda o verifica que hay licitaciones disponibles."
              action={{
                label: "Ver todas las licitaciones",
                onClick: handleLoadAll
              }}
            />
          </Column>
        </Grid>
      )}
      
      {!loading && !error && tenders.length > 0 && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <TenderTable
              tenders={tenders}
              onSelectTender={setSelectedTender}
            />
          </Column>
        </Grid>
      )}

      <TenderDetailPanel
        tender={selectedTender}
        open={selectedTender !== null}
        onClose={() => setSelectedTender(null)}
      />
    </div>
  )
}

export default Dashboard
