import axios from "axios";

// Use environment variable or default to relative path for production
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? "/api/v1" : "http://localhost:8000/api/v1");

// Log API configuration for debugging
if (import.meta.env.DEV) {
  console.log('[API Client] Base URL:', API_BASE_URL);
  console.log('[API Client] VITE_API_URL:', import.meta.env.VITE_API_URL);
  console.log('[API Client] PROD:', import.meta.env.PROD);
}

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120000, // 2 minutes timeout for experience matching (can take time with AI)
});

// Add request interceptor for debugging
client.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log('[API Request]', config.method?.toUpperCase(), config.url, config.baseURL);
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (import.meta.env.DEV || import.meta.env.PROD) {
      console.error('[API Response Error]', {
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        fullURL: error.config?.baseURL + error.config?.url,
        status: error.response?.status,
        message: error.message,
      });
    }
    return Promise.reject(error);
  }
);

export interface LeadCreate {
  email: string;
  name?: string;
  company?: string;
  source?: string;
  industry?: string;
  company_size?: string;
  role?: string;
}

export interface MatchingExperience {
  experience_id: string;
  project_description: string;
  contracting_entity: string | null;
  amount: number | null;
  score: number;
  scores: {
    keyword: number;
    amount: number;
    entity: number;
    category: number;
  };
}

export interface Tender {
  id: string;
  external_id: string;
  reference: string | null;
  source: string;
  entity_name: string;
  object_text: string;
  department: string | null;
  municipality: string | null;
  amount: number | null;
  publication_date: string | null;
  closing_date: string | null;
  state: string;
  apertura_estado: string | null;
  process_url: string;
  contract_type: string | null;
  contract_modality: string | null;
  relevance_score: number | null;
  is_relevant_interventoria_vial: boolean;
  documents_extraction_attempted_at: string | null;
  experience_match_score: number | null;
  matching_experiences: MatchingExperience[] | null;
  created_at: string;
  updated_at: string;
}

export interface TenderListResponse {
  items: Tender[];
  total: number;
  limit: number;
  offset: number;
}

export type ContractKindFilter =
  | ''
  | 'estudios_disenos'
  | 'estudios_disenos_y_obra'
  | 'interventoria'
  | 'ejecucion_obra'

export interface TenderFilters {
  department?: string;
  contract_type?: string;
  contract_modality?: string;
  contract_kind?: ContractKindFilter;
  date_from?: string;
  date_to?: string;
  match_experience?: boolean;
  only_interventoria?: boolean;
  company_name?: string;
  min_match_score?: number;
  limit?: number;
  offset?: number;
}

export async function getTenders(
  filters: TenderFilters = {}
): Promise<TenderListResponse> {
  const params = new URLSearchParams();

  if (filters.department) {
    params.append("department", filters.department);
  }
  if (filters.contract_type) {
    params.append("contract_type", filters.contract_type);
  }
  if (filters.contract_modality) {
    params.append("contract_modality", filters.contract_modality);
  }
  if (filters.contract_kind) {
    params.append("contract_kind", filters.contract_kind);
  }
  if (filters.date_from) {
    params.append("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.append("date_to", filters.date_to);
  }
  if (filters.match_experience !== undefined) {
    params.append("match_experience", filters.match_experience.toString());
  }
  if (filters.only_interventoria !== undefined) {
    params.append("only_interventoria", filters.only_interventoria.toString());
  }
  if (filters.company_name) {
    params.append("company_name", filters.company_name);
  }
  if (filters.min_match_score !== undefined) {
    params.append("min_match_score", filters.min_match_score.toString());
  }
  if (filters.limit) {
    params.append("limit", filters.limit.toString());
  }
  if (filters.offset) {
    params.append("offset", filters.offset.toString());
  }

  const url = `/tenders?${params.toString()}`;
  console.log('[API] getTenders - Request URL:', url);
  console.log('[API] getTenders - Base URL:', client.defaults.baseURL);
  console.log('[API] getTenders - Full URL:', client.defaults.baseURL + url);
  
  const response = await client.get<TenderListResponse>(url);
  
  console.log('[API] getTenders - Response:', {
    status: response.status,
    dataItems: response.data?.items?.length || 0,
    dataTotal: response.data?.total || 0,
  });
  
  // Ensure response has the expected structure
  return {
    items: response.data?.items || [],
    total: response.data?.total || 0,
    limit: response.data?.limit || filters.limit || 50,
    offset: response.data?.offset || filters.offset || 0,
  };
}

export async function getTender(id: string): Promise<Tender> {
  const response = await client.get<Tender>(`/tenders/${id}`);
  return response.data;
}

export interface TenderDocument {
  id: string;
  tender_id: string;
  external_document_id: string;
  document_type: string;
  file_name: string;
  file_path: string;
  download_url: string;
  file_size: number | null;
  extension: string | null;
  description: string | null;
  downloaded_at: string;
  created_at: string;
  updated_at: string;
}

export interface TenderDocumentListResponse {
  items: TenderDocument[];
  total: number;
}

export async function getTenderDocuments(
  tenderId: string
): Promise<TenderDocumentListResponse> {
  const response = await client.get<TenderDocumentListResponse>(
    `/tenders/${tenderId}/documents`
  );
  return {
    items: response.data?.items || [],
    total: response.data?.total || 0,
  };
}

export function getTenderDocumentDownloadUrl(
  tenderId: string,
  documentId: string
): string {
  return `${API_BASE_URL}/tenders/${tenderId}/documents/${documentId}/download`;
}

export type TenderDocumentType =
  | 'pliego_condiciones'
  | 'anexo_tecnico'
  | 'presupuesto'
  | 'indicadores_financieros'

export async function uploadTenderDocument(
  tenderId: string,
  documentType: TenderDocumentType,
  file: File
): Promise<TenderDocument> {
  const formData = new FormData()
  formData.append('document_type', documentType)
  formData.append('file', file)

  const response = await client.post<TenderDocument>(
    `/tenders/${tenderId}/documents/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

export interface TenderSummaryField {
  key: string;
  label: string;
  priority: string;
  source: string;
  status: 'available' | 'not_applicable' | 'unavailable';
  value: unknown;
  display_value: string | null;
  source_document_id: string | null;
}

export interface TenderSummary {
  tender_id: string;
  contract_kind: string;
  contract_kind_label: string;
  extracted_at: string;
  fields: TenderSummaryField[];
  cached: boolean;
}

export async function getTenderSummary(
  tenderId: string,
  refresh = false
): Promise<TenderSummary> {
  const response = await client.get<TenderSummary>(
    `/tenders/${tenderId}/summary`,
    { params: refresh ? { refresh: true } : undefined }
  );
  return response.data;
}

export interface TenderRequirementItem {
  key: string;
  label: string;
  value: unknown;
  display_value: string | null;
  confidence: number;
  source_document: string;
  source_document_id: string | null;
  evidence: string | null;
}

export interface TenderRequirementSection {
  key: string;
  title: string;
  status:
    | 'extraido'
    | 'no_encontrado'
    | 'revisar'
    | 'documento_no_disponible'
    | 'no_extraible';
  items: TenderRequirementItem[];
}

export interface TenderRequirements {
  tender_id: string;
  tender_external_id: string;
  extraction_version: string;
  extracted_at: string;
  sections: TenderRequirementSection[];
  warnings: string[];
  cached: boolean;
}

export async function getTenderRequirements(
  tenderId: string,
  refresh = false
): Promise<TenderRequirements> {
  const response = await client.get<TenderRequirements>(
    `/tenders/${tenderId}/requirements`,
    { params: refresh ? { refresh: true } : undefined }
  );
  return response.data;
}

export interface ExcelImportResponse {
  imported: number;
  errors: string[];
  message: string;
}

export async function importExperiences(
  file: File,
  companyName: string
): Promise<ExcelImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await client.post<ExcelImportResponse>(
    `/experiences/import?company_name=${encodeURIComponent(companyName)}`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
}

export interface CompanyExperience {
  id: string;
  company_name: string;
  contract_number: string | null;
  project_description: string;
  contracting_entity: string | null;
  completion_date: string | null;
  amount: number | null;
  category: string | null;
  engineering_area: string | null;
  keywords: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ExperienceListResponse {
  items: CompanyExperience[];
  total: number;
}

export async function getExperiences(
  companyName: string
): Promise<ExperienceListResponse> {
  const response = await client.get<ExperienceListResponse>(
    `/experiences?company_name=${encodeURIComponent(companyName)}`
  );
  return response.data;
}

export async function deleteExperience(id: string): Promise<void> {
  await client.delete(`/experiences/${id}`);
}

export interface CompanyExperienceCreate {
  company_name: string;
  contract_number?: string | null;
  project_description: string;
  contracting_entity?: string | null;
  completion_date?: string | null;
  amount?: number | null;
  category?: string | null;
  engineering_area?: string | null;
}

export async function createExperience(
  experience: CompanyExperienceCreate
): Promise<CompanyExperience> {
  const response = await client.post<CompanyExperience>(
    "/experiences",
    experience
  );
  return response.data;
}

export interface LeadResponse {
  id: number;
  email: string;
  name?: string;
  company?: string;
  source?: string;
  created_at: string;
}

export async function captureLead(lead: LeadCreate): Promise<LeadResponse> {
  const response = await client.post<LeadResponse>("/leads", lead);
  return response.data;
}

export interface LeadCheckResponse {
  exists: boolean;
  lead?: LeadResponse;
}

export async function checkLeadExists(
  email: string
): Promise<LeadCheckResponse> {
  try {
    const response = await client.get<LeadCheckResponse>(
      `/leads/check?email=${encodeURIComponent(email)}`
    );
    return response.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      return { exists: false };
    }
    throw err;
  }
}

export interface SupportTicketCreate {
  email: string;
  name?: string;
  company?: string;
  subject: string;
  message: string;
  category?:
    | "technical"
    | "billing"
    | "feature_request"
    | "bug_report"
    | "general"
    | "other";
  priority?: "low" | "medium" | "high" | "urgent";
}

export interface SupportTicketResponse {
  id: number;
  email: string;
  name?: string;
  company?: string;
  subject: string;
  message: string;
  category: string;
  priority: string;
  status: string;
  ticket_number: string;
  created_at: string;
}

export async function createSupportTicket(
  ticket: SupportTicketCreate
): Promise<SupportTicketResponse> {
  const response = await client.post<SupportTicketResponse>(
    "/support/tickets",
    ticket
  );
  return response.data;
}

export async function getSupportTickets(
  email?: string
): Promise<SupportTicketResponse[]> {
  const params = email ? `?email=${encodeURIComponent(email)}` : "";
  const response = await client.get<SupportTicketResponse[]>(
    `/support/tickets${params}`
  );
  return response.data;
}

export async function getSupportTicket(
  ticketNumber: string
): Promise<SupportTicketResponse> {
  const response = await client.get<SupportTicketResponse>(
    `/support/tickets/${ticketNumber}`
  );
  return response.data;
}

// Feedback API
export type FeedbackType =
  | "nps"
  | "feature_request"
  | "bug_report"
  | "general"
  | "usability";

export interface FeedbackCreate {
  email: string;
  name?: string;
  company?: string;
  type: FeedbackType;
  score?: number; // For NPS: 0-10
  message: string;
  context?: {
    page?: string;
    action?: string;
    [key: string]: any;
  };
}

export interface FeedbackResponse {
  id: number;
  email: string;
  name?: string;
  company?: string;
  type: string;
  score?: number;
  message: string;
  context?: string;
  status: string;
  created_at: string;
}

export interface FeedbackStats {
  total: number;
  by_type: Record<string, number>;
  average_nps?: number;
  by_status: Record<string, number>;
}

export async function createFeedback(
  feedback: FeedbackCreate
): Promise<FeedbackResponse> {
  const response = await client.post<FeedbackResponse>("/feedback", feedback);
  return response.data;
}

export async function getFeedback(
  email?: string,
  type?: FeedbackType
): Promise<FeedbackResponse[]> {
  const params = new URLSearchParams();
  if (email) params.append("email", email);
  if (type) params.append("type", type);
  const queryString = params.toString();
  const response = await client.get<FeedbackResponse[]>(
    `/feedback${queryString ? `?${queryString}` : ""}`
  );
  return response.data;
}

export async function getFeedbackStats(): Promise<FeedbackStats> {
  const response = await client.get<FeedbackStats>("/feedback/stats");
  return response.data;
}
