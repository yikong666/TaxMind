import { http, type ApiResponse } from './http'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  kb_type: 'public_policy' | 'local_policy' | 'internal'
  document_count: number
}

// 问答页只读取当前用户可访问的知识库，检索范围仍由后端再次校验。
export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return (await http.get<ApiResponse<KnowledgeBase[]>>('/knowledge-bases')).data.data
}
