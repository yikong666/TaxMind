import { http, type ApiResponse } from './http'

export interface CaptchaData { captcha_id: string; image_svg: string; expires_in: number }
export interface LoginPayload { username: string; password: string; captcha_id: string; captcha_code: string }
export interface RegisterPayload extends LoginPayload { confirm_password: string }
export interface UserData { id: number; username: string; is_active: boolean }
export interface TokenData { access_token: string; token_type: string; expires_in: number; user: UserData }

export async function fetchCaptcha(): Promise<CaptchaData> {
  return (await http.get<ApiResponse<CaptchaData>>('/auth/captcha')).data.data
}
export async function login(payload: LoginPayload): Promise<TokenData> {
  return (await http.post<ApiResponse<TokenData>>('/auth/login', payload)).data.data
}
export async function register(payload: RegisterPayload): Promise<UserData> {
  return (await http.post<ApiResponse<UserData>>('/auth/register', payload)).data.data
}
