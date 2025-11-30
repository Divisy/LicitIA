import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes timeout for experience matching (can take time with AI)
})

export interface MatchingExperience {
  experience_id: string
  project_description: string
  contracting_entity: string | null
  amount: number | null
  score: number
  scores: {
    keyword: number
    amount: number
    entity: number
    category: number
  }
}

export interface Tender {
  id: string
  external_id: string
  source: string
  entity_name: string
  object_text: string
  department: string | null
  municipality: string | null
  amount: number | null
  publication_date: string | null
  closing_date: string | null
  state: string
  apertura_estado: string | null
  process_url: string
  contract_type: string | null
  contract_modality: string | null
  relevance_score: number | null
  is_relevant_interventoria_vial: boolean
  experience_match_score: number | null
  matching_experiences: MatchingExperience[] | null
  created_at: string
  updated_at: string
}

export interface TenderListResponse {
  items: Tender[]
  total: number
  limit: number
  offset: number
}

export interface TenderFilters {
  department?: string
  contract_type?: string
  contract_modality?: string
  date_from?: string
  date_to?: string
  match_experience?: boolean
  only_interventoria?: boolean
  company_name?: string
  min_match_score?: number
  limit?: number
  offset?: number
}

export async function getTenders(filters: TenderFilters = {}): Promise<TenderListResponse> {
  const params = new URLSearchParams()
  
  if (filters.department) {
    params.append('department', filters.department)
  }
  if (filters.contract_type) {
    params.append('contract_type', filters.contract_type)
  }
  if (filters.contract_modality) {
    params.append('contract_modality', filters.contract_modality)
  }
  if (filters.date_from) {
    params.append('date_from', filters.date_from)
  }
  if (filters.date_to) {
    params.append('date_to', filters.date_to)
  }
  if (filters.match_experience !== undefined) {
    params.append('match_experience', filters.match_experience.toString())
  }
  if (filters.only_interventoria !== undefined) {
    params.append('only_interventoria', filters.only_interventoria.toString())
  }
  if (filters.company_name) {
    params.append('company_name', filters.company_name)
  }
  if (filters.min_match_score !== undefined) {
    params.append('min_match_score', filters.min_match_score.toString())
  }
  if (filters.limit) {
    params.append('limit', filters.limit.toString())
  }
  if (filters.offset) {
    params.append('offset', filters.offset.toString())
  }
  
  const response = await client.get<TenderListResponse>(`/tenders?${params.toString()}`)
  return response.data
}

export async function getTender(id: string): Promise<Tender> {
  const response = await client.get<Tender>(`/tenders/${id}`)
  return response.data
}

export interface ExcelImportResponse {
  imported: number
  errors: string[]
  message: string
}

export async function importExperiences(
  file: File,
  companyName: string
): Promise<ExcelImportResponse> {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await client.post<ExcelImportResponse>(
    `/experiences/import?company_name=${encodeURIComponent(companyName)}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

export interface CompanyExperience {
  id: string
  company_name: string
  contract_number: string | null
  project_description: string
  contracting_entity: string | null
  completion_date: string | null
  amount: number | null
  category: string | null
  engineering_area: string | null
  keywords: string[] | null
  created_at: string
  updated_at: string
}

export interface ExperienceListResponse {
  items: CompanyExperience[]
  total: number
}

export async function getExperiences(companyName: string): Promise<ExperienceListResponse> {
  const response = await client.get<ExperienceListResponse>(
    `/experiences?company_name=${encodeURIComponent(companyName)}`
  )
  return response.data
}

export async function deleteExperience(id: string): Promise<void> {
  await client.delete(`/experiences/${id}`)
}

