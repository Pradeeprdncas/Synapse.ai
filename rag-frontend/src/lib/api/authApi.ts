import { apiClient } from "./client";

export type LoginPayload = { email: string; password: string };
export type RegisterPayload = { email: string; password: string; name: string };
export type AuthUser = {
  id: number;
  email: string;
  name?: string;
  avatar_url?: string;
  role?: string;
};
export type AuthResponse = { access_token: string; token_type?: string; user?: AuthUser };
type RegisterResponse = AuthResponse | { message: string };

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient.post<AuthResponse>("/auth/login", payload).then((r) => r.data),
  register: (payload: RegisterPayload) =>
    apiClient.post<RegisterResponse>("/auth/register", payload).then((r) => r.data),
  me: () => apiClient.get<AuthUser>("/auth/me").then((r) => r.data),
  updateMe: (payload: { name?: string; email?: string; current_password?: string; new_password?: string }) =>
    apiClient.patch<AuthUser>("/auth/me", payload).then((r) => r.data),
  forgotPassword: (email: string) =>
    apiClient.post<{ ok: boolean }>("/auth/forgot-password", { email }).then((r) => r.data),
};
