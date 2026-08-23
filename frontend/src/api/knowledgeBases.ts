import { http, type ApiResponse } from './http'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  kb_type: 'public_policy' | 'local_policy' | 'internal'
  document_count: number
  chunk_count: number
}

export interface PolicyMetadata {
  policy_title: string | null; doc_no: string | null; region: string | null
  tax_type: string | null; taxpayer_type: string | null; publish_date: string | null
  effective_start: string | null; effective_end: string | null
  policy_status: 'active' | 'expired' | 'replaced' | null; source_url: string | null
  is_complete?: boolean
}

export interface KnowledgeDocument {
  id: number; original_name: string; content_type: string; file_size: number
  parse_status: 'pending' | 'parsing' | 'completed' | 'failed'; parse_error: string | null
  parent_chunk_count: number; child_chunk_count: number; policy_metadata: PolicyMetadata | null
  created_at: string
}

export interface KnowledgeBaseDetail extends KnowledgeBase { documents: KnowledgeDocument[] }
export interface ChildChunk { id: number; chunk_index: number; content: string; vector_status: string }
export interface ParentChunk { id: number; chunk_index: number; heading: string | null; content: string; children: ChildChunk[] }

// 问答页只读取当前用户可访问的知识库，检索范围仍由后端再次校验。
export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return (await http.get<ApiResponse<KnowledgeBase[]>>('/knowledge-bases')).data.data
}

// 管理端 API 集中封装，页面组件只负责交互状态和业务提示。
export async function getKnowledgeBase(id: number): Promise<KnowledgeBaseDetail> {
  return (await http.get<ApiResponse<KnowledgeBaseDetail>>(`/knowledge-bases/${id}`)).data.data
}
export async function createKnowledgeBase(payload: Pick<KnowledgeBase, 'name' | 'description' | 'kb_type'>): Promise<KnowledgeBase> {
  return (await http.post<ApiResponse<KnowledgeBase>>('/knowledge-bases', payload)).data.data
}
export async function updateKnowledgeBase(id: number, payload: { name: string; description: string }): Promise<KnowledgeBase> {
  return (await http.patch<ApiResponse<KnowledgeBase>>(`/knowledge-bases/${id}`, payload)).data.data
}
export async function deleteKnowledgeBase(id: number): Promise<void> { await http.delete(`/knowledge-bases/${id}`) }
export async function uploadDocuments(id: number, files: File[]): Promise<KnowledgeDocument[]> {
  const body = new FormData(); files.forEach((file) => body.append('files', file))
  return (await http.post<ApiResponse<KnowledgeDocument[]>>(`/knowledge-bases/${id}/documents`, body, { timeout: 60_000 })).data.data
}
export async function parseDocument(id: number, payload: Record<string, number | undefined>): Promise<void> {
  await http.post(`/documents/${id}/parse`, payload, { timeout: 120_000 })
}
export async function savePolicyMetadata(id: number, payload: PolicyMetadata): Promise<void> { await http.put(`/documents/${id}/policy-metadata`, payload) }
export async function indexDocument(id: number): Promise<void> { await http.post(`/documents/${id}/index`, undefined, { timeout: 300_000 }) }
export async function listChunks(id: number): Promise<ParentChunk[]> { return (await http.get<ApiResponse<ParentChunk[]>>(`/documents/${id}/chunks`)).data.data }
export async function updateParentChunk(id: number, payload: { heading: string | null; content: string }): Promise<void> { await http.patch(`/chunks/parents/${id}`, payload) }
export async function updateChildChunk(id: number, content: string): Promise<void> { await http.patch(`/chunks/children/${id}`, { content }) }
export async function deleteParentChunk(id: number): Promise<void> { await http.delete(`/chunks/parents/${id}`) }
export async function deleteChildChunk(id: number): Promise<void> { await http.delete(`/chunks/children/${id}`) }
