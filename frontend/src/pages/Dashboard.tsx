import React, { useState, useEffect, useCallback } from 'react'
import { 
  Grid, 
  Column, 
  Button, 
  InlineNotification,
  Loading,
  Tile
} from '@carbon/react'
import { View } from '@carbon/icons-react'
import FiltersBar from '../components/FiltersBar'
import TenderTable from '../components/TenderTable'
import TenderDetailPanel from '../components/TenderDetailPanel'
import OnboardingWizard from '../components/onboarding/OnboardingWizard'
import PortfolioBanner from '../components/PortfolioBanner'
import FirstSessionHome from '../components/FirstSessionHome'
import EmptyState from '../components/empty-states/EmptyState'
import Logo from '../components/Logo'
import { useOnboarding } from '../hooks/useOnboarding'
import { usePortfolioStatus } from '../hooks/usePortfolioStatus'
import { useFavoriteTenders } from '../hooks/useFavoriteTenders'
import { getTenders, Tender, TenderFilters, ContractKindFilter } from '../api/client'
import { isPortfolioSkipped } from '../utils/portfolio'
import './Dashboard.scss'

const EXPERIENCES_ONBOARDING_STEP = 1

const Dashboard: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [showAllTenders, setShowAllTenders] = useState(() => isPortfolioSkipped())
  
  const {
    state: onboardingState,
    startOnboarding,
    startOnboardingAtStep,
    finishOnboarding,
  } = useOnboarding()
  const {
    status: portfolioStatus,
    companyName: portfolioCompanyName,
    refresh: refreshPortfolio,
  } = usePortfolioStatus()
  const { isFavorite, toggleFavorite } = useFavoriteTenders()
  
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [department, setDepartment] = useState<string>('')
  const [companyName, setCompanyName] = useState<string>('')
  const [contractKind, setContractKind] = useState<ContractKindFilter>('')
  const [showAll, setShowAll] = useState<boolean>(false)
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null)

  const portfolioReady = portfolioStatus === 'ready'
  const portfolioLoading = portfolioStatus === 'loading'
  const showFirstSessionHome = !portfolioLoading && !portfolioReady && !showAllTenders
  const showTenderTable = portfolioReady || showAllTenders
  
  const fetchTenders = useCallback(async (
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
        limit,
        offset: 0,
      }
      
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (department) params.department = department
      if (effectiveContractKind) params.contract_kind = effectiveContractKind

      const effectiveCompanyName = companyName || portfolioCompanyName
      if (portfolioReady && effectiveCompanyName) {
        params.company_name = effectiveCompanyName
        params.match_experience = true
      } else if (companyName) {
        params.company_name = companyName
      }
      
      const response = await getTenders(params)
      
      setTenders(response?.items || [])
      setTotal(response?.total || 0)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage =
        axiosErr?.response?.data?.detail || axiosErr?.message || 'Error al cargar licitaciones'
      setError(errorMessage)
      setTenders([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [
    contractKind,
    dateFrom,
    dateTo,
    department,
    companyName,
    portfolioCompanyName,
    portfolioReady,
  ])
  
  useEffect(() => {
    if (!portfolioLoading && showTenderTable) {
      fetchTenders()
    }
  }, [portfolioLoading, showTenderTable, portfolioReady, fetchTenders])

  useEffect(() => {
    if (portfolioReady) {
      if (onboardingState.isActive) {
        finishOnboarding()
      }
      if (!companyName && portfolioCompanyName) {
        setCompanyName(portfolioCompanyName)
      }
    }
  }, [portfolioReady, onboardingState.isActive, finishOnboarding, companyName, portfolioCompanyName])
  
  useEffect(() => {
    const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
    const completed = localStorage.getItem('licitia_onboarding_completed')
    
    if (shouldStartOnboarding === 'true') {
      if (completed === 'true') {
        localStorage.removeItem('licitia_onboarding_completed')
        localStorage.removeItem('licitia_onboarding_state')
      }
      localStorage.removeItem('licitia_start_onboarding')
      if (!portfolioReady) {
        startOnboarding()
      }
    }
  }, [portfolioReady, startOnboarding])
  
  useEffect(() => {
    if (!onboardingState.isActive) {
      const shouldStartOnboarding = localStorage.getItem('licitia_start_onboarding')
      const completed = localStorage.getItem('licitia_onboarding_completed')
      
      if (shouldStartOnboarding === 'true' && completed !== 'true' && !portfolioReady) {
        localStorage.removeItem('licitia_start_onboarding')
        startOnboarding()
      }
    }
  }, [onboardingState.isActive, startOnboarding, portfolioReady])
  
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
    refreshPortfolio()
    if (isPortfolioSkipped()) {
      setShowAllTenders(true)
    }
    fetchTenders()
  }

  const handleStartPortfolioUpload = () => {
    startOnboardingAtStep(EXPERIENCES_ONBOARDING_STEP)
  }

  const handleViewAllTenders = () => {
    setShowAllTenders(true)
  }

  return (
    <div className="dashboard">
      <OnboardingWizard onComplete={handleOnboardingComplete} />
      
      {!portfolioLoading && !portfolioReady && (
        <PortfolioBanner onUpload={handleStartPortfolioUpload} />
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
                {portfolioReady
                  ? 'Licitaciones relevantes para tu empresa en construcción, ingeniería e interventoría'
                  : 'Encuentra licitaciones de obra pública mucho más rápido que en SECOP'}
              </p>
            </div>
          </div>
        </Column>
      </Grid>

      {showFirstSessionHome && (
        <Grid className="dashboard-grid">
          <Column lg={16} md={8} sm={4}>
            <FirstSessionHome
              onUpload={handleStartPortfolioUpload}
              onViewAll={handleViewAllTenders}
            />
          </Column>
        </Grid>
      )}
      
      {showTenderTable && (
        <>
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
                    label: 'Ver todas las licitaciones',
                    onClick: handleLoadAll,
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
                  showFavoriteColumn
                  isFavorite={isFavorite}
                  onToggleFavorite={toggleFavorite}
                />
              </Column>
            </Grid>
          )}
        </>
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
