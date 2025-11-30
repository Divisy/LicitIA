import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import FiltersBar from '../components/FiltersBar'
import TenderTable from '../components/TenderTable'
import { getTenders, Tender, TenderFilters } from '../api/client'
import './Dashboard.css'

const Dashboard: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  
  // Filter state (removed is_relevant as it's no longer used)
  const [filters, setFilters] = useState<TenderFilters>({
    limit: 50,
    offset: 0,
  })
  
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [department, setDepartment] = useState<string>('')
  const [companyName, setCompanyName] = useState<string>('')
  const [matchExperience, setMatchExperience] = useState<boolean>(false)
  const [onlyInterventoria, setOnlyInterventoria] = useState<boolean>(false)
  const [showAll, setShowAll] = useState<boolean>(false)
  
  const fetchTenders = async (loadAll: boolean = false) => {
    setLoading(true)
    setError(null)
    
    try {
      // Determine limit: if showAll is true or matchExperience is enabled, use a high limit
      const limit = loadAll || matchExperience ? 1000 : 50
      
      const params: TenderFilters = {
        // No need for is_relevant filter - experience matching is the main feature
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
      // OPTIMIZATION: Filter by interventoría keywords BEFORE matching (reduces AI processing time)
      if (onlyInterventoria) {
        params.only_interventoria = true
      }
      // If matchExperience is enabled, use companyName or default to "BEC"
      if (matchExperience) {
        params.match_experience = true
        params.min_match_score = 0.55  // 55% threshold (balanced for quality)
        // Use provided company name or default to "BEC" if empty
        params.company_name = companyName.trim() || "BEC"
      } else if (companyName) {
        // Only send company_name if not matching (for display purposes)
        params.company_name = companyName
      }
      
      const response = await getTenders(params)
      setTenders(response.items)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar licitaciones')
      console.error('Error fetching tenders:', err)
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    fetchTenders()
  }, [])
  
  const handleFilterSubmit = () => {
    setShowAll(false) // Reset showAll when filters change
    fetchTenders(false)
  }
  
  const handleLoadAll = () => {
    setShowAll(true)
    fetchTenders(true)
  }
  
  return (
    <div className="dashboard">
      <FiltersBar
        dateFrom={dateFrom}
        dateTo={dateTo}
        department={department}
        companyName={companyName}
        matchExperience={matchExperience}
        onlyInterventoria={onlyInterventoria}
        onDateFromChange={setDateFrom}
        onDateToChange={setDateTo}
        onDepartmentChange={setDepartment}
        onCompanyNameChange={setCompanyName}
        onMatchExperienceChange={setMatchExperience}
        onOnlyInterventoriaChange={setOnlyInterventoria}
        onSubmit={handleFilterSubmit}
      />
      
      {loading && <div className="loading">Cargando...</div>}
      {error && <div className="error">Error: {error}</div>}
      
      {!loading && !error && (
        <div className="results-info">
          <p>Mostrando {tenders.length} de {total} licitaciones</p>
          {!showAll && tenders.length < total && (
            <button 
              type="button"
              onClick={handleLoadAll}
              className="load-all-button"
            >
              Ver todas las licitaciones ({total})
            </button>
          )}
        </div>
      )}
      
      {!loading && !error && (
        <TenderTable tenders={tenders} />
      )}
    </div>
  )
}

export default Dashboard

