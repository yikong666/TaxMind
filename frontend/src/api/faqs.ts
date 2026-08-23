import { http, type ApiResponse } from './http'

export interface Faq {
  id: number
  question: string
  answer: string
  category: string
  region: string
  doc_no: string | null
  effective_start: string | null
  effective_end: string | null
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export type FaqPayload = Omit<Faq, 'id' | 'created_at' | 'updated_at'>
export interface FaqFilters { keyword?: string; category?: string; region?: string; is_enabled?: boolean }
export interface FaqRouteResult {
  matched: boolean; continue_to_rag: boolean; source: 'redis' | 'mysql_bm25' | 'rag'
  score: number; faq: Faq | null
}

// FAQ 管理与路由试测统一复用鉴权请求和标准错误结构。
export async function listFaqs(filters: FaqFilters = {}): Promise<Faq[]> {
  return (await http.get<ApiResponse<Faq[]>>('/faqs', { params: filters })).data.data
}
export async function createFaq(payload: FaqPayload): Promise<Faq> {
  return (await http.post<ApiResponse<Faq>>('/faqs', payload)).data.data
}
export async function updateFaq(id: number, payload: Partial<FaqPayload>): Promise<Faq> {
  return (await http.patch<ApiResponse<Faq>>(`/faqs/${id}`, payload)).data.data
}
export async function deleteFaq(id: number): Promise<void> { await http.delete(`/faqs/${id}`) }
export async function routeFaq(payload: { query: string; region: string; query_date: string }): Promise<FaqRouteResult> {
  return (await http.post<ApiResponse<FaqRouteResult>>('/faqs/route/match', payload)).data.data
}
