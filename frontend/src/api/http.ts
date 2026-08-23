import axios from 'axios'

export const http = axios.create({ baseURL: '/api/v1', timeout: 10_000 })

export interface ApiResponse<T> { success: boolean; code: string; message: string; data: T }

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) return error.response?.data?.message ?? '网络连接失败，请稍后重试'
  return '操作失败，请稍后重试'
}
