export type Role = 'admin' | 'operator'
export interface UserInfo { user_id: number; username: string; display_name: string; role: Role; avatar_url?: string | null }
export interface MenuItem { name: string; label: string; path: string; roles: Role[]; children?: MenuItem[] }
export interface AuthResponse { code: string; message: string; trace_id: string; data: { access_token: string; refresh_token: string; token_type: string; expires_in: number; user_info: UserInfo } }
