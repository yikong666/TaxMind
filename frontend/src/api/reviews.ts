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
