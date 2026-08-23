import axios from 'axios'

// 所有前端请求统一走 Vite 代理和标准中文错误解析。
export const http = axios.create({ baseURL: '/api/v1', timeout: 10_000 })

http.interceptors.request.use((config) => {
  // JWT 只保存在当前标签页会话中，关闭浏览器后自动失效。
  const token = sessionStorage.getItem('taxmind_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(undefined, (error) => {
  if (axios.isAxiosError(error) && error.response?.status === 401) {
    sessionStorage.removeItem('taxmind_access_token')
    sessionStorage.removeItem('taxmind_user')
    if (location.pathname !== '/login') location.assign('/login')
  }
  return Promise.reject(error)
})

export interface ApiResponse<T> { success: boolean; code: string; message: string; data: T }

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) return error.response?.data?.message ?? '网络连接失败，请稍后重试'
  return '操作失败，请稍后重试'
}
