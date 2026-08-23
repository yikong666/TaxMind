import { http, type ApiResponse } from './http'

// 反馈和转人工均绑定后端已持久化的 AI message_id，临时流式消息不可提交。
export async function submitFeedback(
  messageId: number,
  feedbackType: 'like' | 'dislike',
  reason?: string,
): Promise<void> {
  await http.post<ApiResponse<unknown>>(`/messages/${messageId}/feedback`, {
    feedback_type: feedbackType,
    reason,
  })
}

export async function handoffMessage(messageId: number, reason?: string): Promise<void> {
  await http.post<ApiResponse<unknown>>(`/messages/${messageId}/handoff`, { reason })
}

export interface ReviewTicket {
  id: number; conversation_id: number; message_id: number; trigger_reason: string
  user_question: string; ai_answer: string; citations: Record<string, unknown>[]
  risk_level: string | null; user_feedback: string | null
  status: 'pending' | 'processing' | 'resolved'; resolution: string | null
  created_at: string; updated_at: string
}

// 人工审核列表支持后端状态和风险筛选，状态流转仍由后端状态机兜底。
export async function listTickets(filters: { status?: string; risk_level?: string } = {}): Promise<ReviewTicket[]> {
  return (await http.get<ApiResponse<ReviewTicket[]>>('/tickets', { params: filters })).data.data
}
export async function updateTicket(id: number, status: ReviewTicket['status'], resolution?: string): Promise<ReviewTicket> {
  return (await http.patch<ApiResponse<ReviewTicket>>(`/tickets/${id}`, { status, resolution })).data.data
}
