import axios from "axios";
import { getSessionEmail } from "../utils/userSession";

// Production always uses same-origin `/api/v1` (nginx/Vite proxy). That avoids
// CORS Network Error when the SPA is on a different Railway host than the API.
const API_BASE_URL = import.meta.env.DEV
  ? import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"
  : "/api/v1";

// Log API configuration for debugging
if (import.meta.env.DEV) {
  console.log('[API Client] Base URL:', API_BASE_URL);
  console.log('[API Client] VITE_API_URL:', import.meta.env.VITE_API_URL);
  console.log('[API Client] PROD:', import.meta.env.PROD);
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout for experience matching (can take time with AI)
});

// Add request interceptor for debugging
client.interceptors.request.use(
  (config) => {
    const isFormData =
      typeof FormData !== "undefined" && config.data instanceof FormData;
    if (isFormData) {
      // Let the browser set multipart boundary. A JSON default breaks file uploads.
      if (config.headers && typeof config.headers.delete === "function") {
        config.headers.delete("Content-Type");
      } else if (config.headers) {
        delete (config.headers as Record<string, unknown>)["Content-Type"];
      }
    } else if (config.headers && !config.headers["Content-Type"]) {
      config.headers["Content-Type"] = "application/json";
    }
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

export function formatApiError(error: unknown, fallback = "Error al cargar el RUP"): string {
  const err = error as {
    message?: string;
    response?: { data?: { detail?: unknown } };
  };
  const detail = err.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) return parts.join(" · ");
  }
  if (!err.response) {
    return "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.";
  }
  return fallback;
}

export interface LeadCreate {
  email: string;
  name?: string;
  company?: string;
  source?: string;
  industry?: string;
  company_size?: string;
  role?: string;
  phone?: string;
  city?: string;
  sectors?: string[];
}

export type ExperienceFitStatus = 'puede_aplicar' | 'no_aplica' | 'no_se_puede_afirmar'

export interface ExperienceFitContract {
  experience_id: string;
  contract_number: string | null;
  contracting_entity: string | null;
  amount_smmlv: number | null;
  in_general_sum: boolean;
  specific_met: boolean;
  matched_activity: string | null;
}

export interface ExperienceFit {
  status: ExperienceFitStatus;
  reason: string;
  general_sum_smmlv: number | null;
  general_minimum_smmlv: number | null;
  contracts: ExperienceFitContract[];
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
  experience_fit?: ExperienceFit | null;
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
  entity?: string;
  typology?: string[];
  match_experience?: boolean;
  experience_fit?: ExperienceFitStatus;
  only_interventoria?: boolean;
  company_name?: string;
  min_match_score?: number;
  limit?: number;
  offset?: number;
}

export async function getTenders(
  filters: TenderFilters = {}
): Promise<TenderListResponse> {
  const params = withOwnerEmail(new URLSearchParams());

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
  if (filters.entity) {
    params.append("entity", filters.entity);
  }
  if (filters.typology?.length) {
    filters.typology.forEach((value) => {
      if (value) params.append("typology", value);
    });
  }
  if (filters.experience_fit) {
    params.append("experience_fit", filters.experience_fit);
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

function withOwnerEmail(params: URLSearchParams): URLSearchParams {
  const email = getSessionEmail();
  if (email) params.set("owner_email", email);
  return params;
}

export async function importExperiences(
  file: File,
  companyName: string
): Promise<ExcelImportResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const params = withOwnerEmail(
    new URLSearchParams({
      company_name: companyName.trim() || "Mi Empresa",
    })
  );

  const response = await client.post<ExcelImportResponse>(
    `/experiences/import?${params.toString()}`,
    formData
  );
  return response.data;
}

export interface RupCapacity {
  liquidez: number | null;
  endeudamiento: number | null;
  cobertura_intereses: number | null;
  rentabilidad_patrimonio: number | null;
  rentabilidad_activo: number | null;
  capital_trabajo: number | null;
  cut_year: number | null;
  organizacional: Record<string, unknown> | null;
}

export interface RupImportResponse {
  imported_experiences: number;
  capacity: RupCapacity;
  issued_at: string | null;
  valid_until: string | null;
  nit: string | null;
  razon_social: string | null;
  warnings: string[];
  message: string;
}

export interface RupProfileResponse {
  company_name: string;
  nit: string | null;
  razon_social: string | null;
  camara: string | null;
  issued_at: string | null;
  valid_until: string | null;
  capacity: RupCapacity;
  source_pdf_filename: string | null;
  experiences_count: number;
  updated_at: string | null;
  warnings: string[];
}

export async function importRup(
  file: File,
  companyName: string
): Promise<RupImportResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const params = withOwnerEmail(
    new URLSearchParams({
      company_name: companyName.trim() || "Mi Empresa",
    })
  );

  const response = await client.post<RupImportResponse>(
    `/rup/import?${params.toString()}`,
    formData
  );
  return response.data;
}

export async function getRupProfile(
  companyName: string
): Promise<RupProfileResponse> {
  const params = withOwnerEmail(
    new URLSearchParams({ company_name: companyName })
  );
  const response = await client.get<RupProfileResponse>(
    `/rup/profile?${params.toString()}`,
    { timeout: 20000 }
  );
  return response.data;
}

export interface CompanyExperience {
  id: string;
  company_name: string;
  contract_number: string | null;
  project_description: string;
  contracting_entity: string | null;
  contractor_name: string | null;
  partner_name?: string | null;
  participation_percent?: number | null;
    completion_date: string | null;
    amount: number | null;
    amount_smmlv: number | null;
    category: string | null;
  engineering_area: string | null;
  contract_kind: string | null;
  contract_kind_label: string | null;
  specific_experience: string | null;
  has_acta_partidas?: boolean;
  specific_evidence_filename: string | null;
  project_typologies: string[] | null;
  unspsc_codes: string[] | null;
  keywords: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ExperienceListResponse {
  items: CompanyExperience[];
  total: number;
  available_typologies?: string[];
}

export async function getExperiences(
  companyName: string,
  options: { hydrateRup?: boolean } = {}
): Promise<ExperienceListResponse> {
  const params = withOwnerEmail(
    new URLSearchParams({
      company_name: companyName,
      limit: "1000",
    })
  );
  if (options.hydrateRup) {
    params.set('hydrate_rup', 'true')
  }
  const response = await client.get<ExperienceListResponse>(
    `/experiences?${params.toString()}`,
    { timeout: 20000 }
  );
  return response.data;
}

export async function deleteExperience(id: string): Promise<void> {
  await client.delete(`/experiences/${id}`);
}

export async function updateExperienceContractKind(
  experienceId: string,
  contractKind: string | null
): Promise<CompanyExperience> {
  const response = await client.patch<CompanyExperience>(
    `/experiences/${experienceId}/contract-kind`,
    { contract_kind: contractKind }
  );
  return response.data;
}

export async function uploadSpecificExperienceEvidence(
  experienceId: string,
  file: File
): Promise<CompanyExperience> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await client.post<CompanyExperience>(
    `/experiences/${experienceId}/specific-evidence`,
    formData
  );
  return response.data;
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
  const params = withOwnerEmail(new URLSearchParams());
  const qs = params.toString();
  const response = await client.post<CompanyExperience>(
    qs ? `/experiences?${qs}` : "/experiences",
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
  industry?: string;
  company_size?: string;
  role?: string;
  phone?: string;
  city?: string;
  sectors?: string[];
  created_at: string;
  onboarding_completed_at?: string | null;
}

export async function captureLead(lead: LeadCreate): Promise<LeadResponse> {
  const response = await client.post<LeadResponse>("/leads", lead, { timeout: 8000 });
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
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404) {
      return { exists: false };
    }
    throw err;
  }
}

export async function completeOnboarding(email: string): Promise<LeadResponse> {
  const response = await client.post<LeadResponse>("/leads/onboarding-complete", {
    email,
  });
  return response.data;
}

export interface RequestCodeResponse {
  exists: boolean;
  ttl_minutes?: number;
  debug_code?: string;
  email_sent?: boolean;
}

export async function requestLoginCode(email: string): Promise<RequestCodeResponse> {
  const response = await client.post<RequestCodeResponse>(
    "/auth/request-code",
    { email },
    { timeout: 15000 }
  );
  return response.data;
}

export interface VerifyCodeResponse {
  ok: boolean;
  exists: boolean;
  lead?: LeadResponse;
}

export async function verifyLoginCode(
  email: string,
  code: string
): Promise<VerifyCodeResponse> {
  const response = await client.post<VerifyCodeResponse>(
    "/auth/verify-code",
    { email, code },
    { timeout: 15000 }
  );
  return response.data;
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
