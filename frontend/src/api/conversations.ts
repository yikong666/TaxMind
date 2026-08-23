import { http, type ApiResponse } from './http'

export interface Citation {
  document_id?: number
  id?: number
  policy_title?: string
  original_name?: string
  question?: string
  doc_no?: string
  region?: string
  effective_start?: string | number
  effective_end?: string | number
  source_url?: string
  content?: string
  parent_content?: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  status: 'generating' | 'completed' | 'failed'
  risk_level: string | null
  route_source: string | null
  model_name: string | null
  citations: Citation[]
  error_message: string | null
  retrieval_strategy: string | null
  retrieval_queries: string[]
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation { messages: ChatMessage[] }

export interface ChatPayload {
  query: string
  knowledge_base_ids: number[]
  region: string
  query_date: string
  model: string | null
  temperature: number
  top_p: number
  max_tokens: number
  history_rounds: number
}

export interface SseEvent { event: string; data: Record<string, unknown> }

export async function listConversations(): Promise<Conversation[]> {
  return (await http.get<ApiResponse<Conversation[]>>('/conversations')).data.data
}

export async function createConversation(title = '新会话'): Promise<Conversation> {
  return (await http.post<ApiResponse<Conversation>>('/conversations', { title })).data.data
}

export async function getConversation(id: number): Promise<ConversationDetail> {
  return (await http.get<ApiResponse<ConversationDetail>>(`/conversations/${id}`)).data.data
}

export async function renameConversation(id: number, title: string): Promise<Conversation> {
  return (await http.patch<ApiResponse<Conversation>>(`/conversations/${id}`, { title })).data.data
}

export async function deleteConversation(id: number): Promise<void> {
  await http.delete(`/conversations/${id}`)
}

export async function downloadDocument(id: number, filename: string): Promise<void> {
  const response = await http.get<Blob>(`/documents/${id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `TaxMind-文档-${id}`
  link.click()
  URL.revokeObjectURL(url)
}

export async function streamChat(
  conversationId: number,
  payload: ChatPayload,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const token = sessionStorage.getItem('taxmind_access_token')
  const response = await fetch(`/api/v1/conversations/${conversationId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token ?? ''}` },
    body: JSON.stringify(payload),
  })
  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.message ?? '流式回答连接失败')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  // SSE 数据块可能跨网络包拆分，必须累计到空行后再解析完整事件。
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const event = block.split('\n').find((line) => line.startsWith('event:'))?.slice(6).trim()
      const data = block.split('\n').find((line) => line.startsWith('data:'))?.slice(5).trim()
      if (event && data) onEvent({ event, data: JSON.parse(data) })
      boundary = buffer.indexOf('\n\n')
    }
    if (done) break
  }
}
